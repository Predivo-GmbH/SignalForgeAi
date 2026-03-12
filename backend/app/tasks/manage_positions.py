"""Manage open positions — update prices, risk management checks, SL/TP."""

import logging
from datetime import datetime, timezone

import pandas as pd

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="manage_positions", bind=True, max_retries=3)
def manage_positions(self):
    """Trail stops, check SL/TP, close positions as needed."""
    import asyncio

    from app.tasks.task_utils import task_lock

    with task_lock("manage_positions", timeout=120) as acquired:
        if not acquired:
            return
        try:
            asyncio.run(_manage_async())
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("manage_positions transient error: %s — retrying", exc)
            raise self.retry(exc=exc, countdown=30)
        except Exception:
            logger.exception("Unexpected error in manage_positions")


async def _set_cooldown(pos, cfg) -> None:
    """Set a Redis cooldown key after closing a position."""
    cooldown_hours = cfg.get("cooldown_hours", 0)
    if cooldown_hours > 0:
        try:
            from app.core.redis_client import redis_client

            key = f"signalforge:cooldown:{pos.user_id}:{pos.symbol}"
            await redis_client.set(key, "1", ex=int(cooldown_hours * 3600))
            logger.info(
                "Cooldown set: %s %s for %dh",
                pos.symbol, pos.user_id, cooldown_hours,
            )
        except Exception as e:
            logger.warning("Failed to set cooldown for %s: %s", pos.symbol, e)


async def _manage_async():
    from sqlalchemy import select

    from app.core.database import task_session
    from app.engine.indicators import compute_atr
    from app.execution.position_manager import PositionManagerDB
    from app.models.candle import Candle
    from app.models.position import Position
    from app.models.strategy import Strategy

    async with task_session() as db:
        result = await db.execute(
            select(Position).where(Position.is_open == True)  # noqa: E712
        )
        positions = result.scalars().all()

        # Pre-load strategy configs for all positions that have strategy_id
        strategy_ids = {pos.strategy_id for pos in positions if pos.strategy_id}
        strategy_configs: dict = {}
        if strategy_ids:
            strat_result = await db.execute(
                select(Strategy).where(Strategy.id.in_(strategy_ids))
            )
            for strat in strat_result.scalars().all():
                strategy_configs[strat.id] = strat.config or {}

        # Pre-load latest candles for ATR computation (trailing stops)
        # Collect unique symbols from positions that have trailing enabled
        symbols_needing_candles: set[str] = set()
        for pos in positions:
            cfg = strategy_configs.get(pos.strategy_id, {})
            if cfg.get("trailing_stop_enabled", False):
                symbols_needing_candles.add(pos.symbol)

        candle_cache: dict[str, pd.DataFrame] = {}
        for symbol in symbols_needing_candles:
            candle_result = await db.execute(
                select(Candle)
                .where(Candle.symbol == symbol)
                .order_by(Candle.time.desc())
                .limit(20)
            )
            candles = candle_result.scalars().all()
            if len(candles) >= 14:
                # Reverse to chronological order
                candles = list(reversed(candles))
                candle_cache[symbol] = pd.DataFrame([
                    {"high": c.high, "low": c.low, "close": c.close}
                    for c in candles
                ])

        # Pre-load latest candle per symbol for price updates (avoids N+1)
        all_symbols = {pos.symbol for pos in positions}
        latest_prices: dict[str, Candle] = {}
        if all_symbols:
            from sqlalchemy import func

            # Sub-query: max time per symbol
            subq = (
                select(Candle.symbol, func.max(Candle.time).label("max_time"))
                .where(Candle.symbol.in_(all_symbols))
                .group_by(Candle.symbol)
                .subquery()
            )
            price_result = await db.execute(
                select(Candle).join(
                    subq,
                    (Candle.symbol == subq.c.symbol)
                    & (Candle.time == subq.c.max_time),
                )
            )
            for c in price_result.scalars().all():
                latest_prices[c.symbol] = c

        for pos in positions:
            try:
                cfg = strategy_configs.get(pos.strategy_id, {})

                # ----------------------------------------------------------
                # 1. Update current_price from latest candle (pre-loaded)
                # ----------------------------------------------------------
                latest_candle = latest_prices.get(pos.symbol)
                if latest_candle:
                    pos.current_price = latest_candle.close
                    if pos.direction == "BUY":
                        pos.unrealized_pnl = (latest_candle.close - pos.entry_price) * pos.quantity
                    else:
                        pos.unrealized_pnl = (pos.entry_price - latest_candle.close) * pos.quantity

                # ----------------------------------------------------------
                # 2. Time-based stop check (Feature 7)
                # ----------------------------------------------------------
                if pos.strategy_id and pos.opened_at:
                    max_hold = cfg.get("max_hold_hours", 24.0)
                    hard_max = max_hold * 2
                    threshold_pct = cfg.get("time_stop_profit_threshold_pct", 1.0)
                    extension = max_hold * 0.5

                    hours_open = (
                        datetime.now(timezone.utc) - pos.opened_at
                    ).total_seconds() / 3600

                    # Calculate unrealized PnL %
                    pnl_pct = 0.0
                    if pos.entry_price and pos.quantity and pos.entry_price > 0:
                        pnl_pct = (
                            pos.unrealized_pnl / (pos.entry_price * pos.quantity)
                        ) * 100

                    should_time_close = False
                    if hours_open >= hard_max:
                        should_time_close = True
                    elif hours_open >= max_hold:
                        if pnl_pct <= threshold_pct:
                            should_time_close = True
                        elif hours_open >= max_hold + extension:
                            should_time_close = True

                    if should_time_close:
                        await PositionManagerDB.close_position(
                            db,
                            str(pos.id),
                            pos.current_price or pos.entry_price,
                            "time_stop",
                        )
                        await _set_cooldown(pos, cfg)
                        logger.info(
                            "Time-stop: closed position %s after %.1fh (pnl=%.2f%%)",
                            pos.id, hours_open, pnl_pct,
                        )
                        continue

                # ----------------------------------------------------------
                # 3. Break-even stop check (Feature 4)
                # ----------------------------------------------------------
                if (
                    cfg.get("break_even_enabled", False)
                    and not pos.break_even_applied
                    and pos.original_stop_loss is not None
                    and pos.current_price is not None
                ):
                    initial_risk = abs(pos.entry_price - pos.original_stop_loss)
                    r_multiple = cfg.get("break_even_r_multiple", 1.0)

                    if initial_risk > 0:
                        if pos.direction == "BUY":
                            profit_dist = pos.current_price - pos.entry_price
                        else:
                            profit_dist = pos.entry_price - pos.current_price

                        if profit_dist >= initial_risk * r_multiple:
                            pos.stop_loss = pos.entry_price
                            pos.break_even_applied = True
                            logger.info(
                                "Break-even: position %s SL moved to entry %.2f "
                                "(profit=%.2f, risk=%.2f, R=%.1f)",
                                pos.id, pos.entry_price,
                                profit_dist, initial_risk, r_multiple,
                            )

                # ----------------------------------------------------------
                # 4. Trailing stop update (Feature 1)
                # ----------------------------------------------------------
                if (
                    cfg.get("trailing_stop_enabled", False)
                    and pos.current_price is not None
                    and pos.stop_loss is not None
                ):
                    candle_df = candle_cache.get(pos.symbol)
                    if candle_df is not None and len(candle_df) >= 14:
                        atr_series = compute_atr(candle_df, period=14)
                        atr_value = float(atr_series.iloc[-1])

                        if not pd.isna(atr_value) and atr_value > 0:
                            multiplier = cfg.get("atr_trail_multiplier", 2.0)
                            trail_distance = atr_value * multiplier

                            if pos.direction == "BUY":
                                new_stop = pos.current_price - trail_distance
                                if new_stop > pos.stop_loss:
                                    old_sl = pos.stop_loss
                                    await PositionManagerDB.trail_stop(
                                        db, str(pos.id), new_stop
                                    )
                                    pos.stop_loss = new_stop
                                    pos.trailing_activated = True
                                    logger.info(
                                        "Trailing stop: position %s SL %.2f -> %.2f "
                                        "(ATR=%.2f, mult=%.1f)",
                                        pos.id, old_sl, new_stop,
                                        atr_value, multiplier,
                                    )
                            else:
                                new_stop = pos.current_price + trail_distance
                                if new_stop < pos.stop_loss:
                                    old_sl = pos.stop_loss
                                    await PositionManagerDB.trail_stop(
                                        db, str(pos.id), new_stop
                                    )
                                    pos.stop_loss = new_stop
                                    pos.trailing_activated = True
                                    logger.info(
                                        "Trailing stop: position %s SL %.2f -> %.2f "
                                        "(ATR=%.2f, mult=%.1f)",
                                        pos.id, old_sl, new_stop,
                                        atr_value, multiplier,
                                    )

                # ----------------------------------------------------------
                # 5. Check stop-loss hit
                # ----------------------------------------------------------
                if pos.stop_loss and pos.current_price:
                    if pos.direction == "BUY" and pos.current_price <= pos.stop_loss:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "stop_loss"
                        )
                        await _set_cooldown(pos, cfg)
                        logger.info("Stop-loss hit for position %s", pos.id)
                        continue
                    if pos.direction == "SELL" and pos.current_price >= pos.stop_loss:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "stop_loss"
                        )
                        await _set_cooldown(pos, cfg)
                        logger.info("Stop-loss hit for position %s", pos.id)
                        continue

                # ----------------------------------------------------------
                # 6. Check take-profit hit
                # ----------------------------------------------------------
                if pos.take_profit and pos.current_price:
                    if pos.direction == "BUY" and pos.current_price >= pos.take_profit:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "take_profit"
                        )
                        await _set_cooldown(pos, cfg)
                        logger.info("Take-profit hit for position %s", pos.id)
                        continue
                    if pos.direction == "SELL" and pos.current_price <= pos.take_profit:
                        await PositionManagerDB.close_position(
                            db, str(pos.id), pos.current_price, "take_profit"
                        )
                        await _set_cooldown(pos, cfg)
                        logger.info("Take-profit hit for position %s", pos.id)
                        continue

            except Exception as e:
                logger.exception("Position management failed for %s: %s", pos.id, e)

        # ----------------------------------------------------------
        # 7-8. Portfolio-level checks: drawdown breaker
        # ----------------------------------------------------------
        try:
            await _check_portfolio_drawdown(db, positions, strategy_configs)
        except Exception as e:
            logger.exception("Portfolio drawdown check failed: %s", e)

        await db.commit()


async def _check_portfolio_drawdown(db, positions, strategy_configs):
    """Update portfolio equity and check drawdown circuit breaker (Feature 2)."""
    from app.execution.position_manager import PositionManagerDB

    # Group positions by user_id
    user_positions: dict = {}
    for pos in positions:
        if pos.is_open:
            uid = str(pos.user_id)
            if uid not in user_positions:
                user_positions[uid] = []
            user_positions[uid].append(pos)

    for user_id, user_pos_list in user_positions.items():
        # Find if any strategy has drawdown_breaker_enabled
        breaker_enabled = False
        max_drawdown_pct = 0.15
        for pos in user_pos_list:
            cfg = strategy_configs.get(pos.strategy_id, {})
            if cfg.get("drawdown_breaker_enabled", False):
                breaker_enabled = True
                max_drawdown_pct = cfg.get("max_drawdown_pct", 0.15)
                break

        if not breaker_enabled:
            continue

        try:
            from app.execution.drawdown_breaker import DrawdownBreaker

            breaker = DrawdownBreaker(max_drawdown_pct=max_drawdown_pct)

            # Calculate current equity: sum of unrealized PnL from open positions
            total_unrealized = sum(
                p.unrealized_pnl for p in user_pos_list if p.unrealized_pnl
            )

            # Get realized PnL from trades (approximate from account_equity in config)
            account_equity = 10000.0
            for pos in user_pos_list:
                cfg = strategy_configs.get(pos.strategy_id, {})
                if cfg.get("account_equity"):
                    account_equity = cfg["account_equity"]
                    break

            current_equity = account_equity + total_unrealized
            level = await breaker.update_and_check(user_id, current_equity)

            if level >= 3:
                # Emergency: close all positions
                logger.critical(
                    "DRAWDOWN BREAKER Level 3: closing ALL positions for user %s "
                    "(equity=%.2f, drawdown=%.2f%%)",
                    user_id, current_equity,
                    ((breaker._peak - current_equity) / breaker._peak * 100)
                    if breaker._peak > 0 else 0,
                )
                for pos in user_pos_list:
                    if pos.is_open:
                        try:
                            await PositionManagerDB.close_position(
                                db,
                                str(pos.id),
                                pos.current_price or pos.entry_price,
                                "drawdown_breaker",
                            )
                            pos_cfg = strategy_configs.get(pos.strategy_id, {})
                            await _set_cooldown(pos, pos_cfg)
                        except Exception as e:
                            logger.exception(
                                "Failed to close position %s during drawdown liquidation: %s",
                                pos.id, e,
                            )
        except Exception as e:
            logger.exception("Drawdown breaker check failed for user %s: %s", user_id, e)
