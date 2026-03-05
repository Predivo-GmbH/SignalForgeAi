"""Execute pending signals — place orders via BrokerRouter.

Applies risk management checks before execution:
  - Drawdown circuit breaker (Feature 2): skip/reduce at high drawdown
  - Correlation penalty (Feature 8): reduce sizing for correlated positions
"""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="execute_pending_signals", bind=True, max_retries=3)
def execute_pending_signals(self):
    """Query signals pending execution, run risk checks, place orders."""
    import asyncio

    from app.tasks.task_utils import task_lock

    with task_lock("execute_signals", timeout=1800) as acquired:
        if not acquired:
            return
        try:
            asyncio.run(_execute_async())
        except (ConnectionError, OSError, TimeoutError) as exc:
            logger.warning("execute_pending_signals transient error: %s — retrying", exc)
            raise self.retry(exc=exc, countdown=30)
        except Exception:
            logger.exception("Unexpected error in execute_pending_signals")


async def _execute_async():
    from sqlalchemy import select

    from app.core.database import task_session
    from app.execution.adapters.paper import PaperAdapter
    from app.execution.broker_router import BrokerRouter
    from app.execution.executor import OrderExecutor
    from app.execution.position_manager import PositionManagerDB
    from app.models.order import Order
    from app.models.signal import Signal
    from app.models.strategy import Strategy

    # Default to paper adapter
    paper = PaperAdapter()
    router = BrokerRouter(paper_adapter=paper)
    executor = OrderExecutor(broker_router=router)

    async with task_session() as db:
        # Query actionable signals with status "pending" that have a strategy
        # (we need strategy.user_id to create the order)
        result = await db.execute(
            select(Signal)
            .where(
                Signal.direction.in_(["BUY", "SELL"]),
                Signal.status == "pending",
                Signal.strategy_id.isnot(None),
            )
            .order_by(Signal.created_at.desc())
            .limit(10)
        )
        signals = result.scalars().all()

        # Pre-load all needed strategies in a single query (avoids N+1)
        strategy_ids = {sig.strategy_id for sig in signals if sig.strategy_id}
        strategies_by_id: dict = {}
        if strategy_ids:
            strat_result = await db.execute(
                select(Strategy).where(Strategy.id.in_(strategy_ids))
            )
            for strat in strat_result.scalars().all():
                strategies_by_id[strat.id] = strat

        for sig in signals:
            try:
                # Resolve user_id from the pre-loaded strategy
                strategy = strategies_by_id.get(sig.strategy_id)
                if strategy is None:
                    logger.warning("Signal %s has no valid strategy, skipping", sig.id)
                    continue

                cfg = strategy.config or {}
                user_id = str(strategy.user_id)
                has_size = sig.position_size and sig.position_size > 0
                quantity = sig.position_size if has_size else 0.01

                # --- Drawdown circuit breaker check (Feature 2) ---
                if cfg.get("drawdown_breaker_enabled", False):
                    try:
                        from app.execution.drawdown_breaker import DrawdownBreaker

                        breaker = DrawdownBreaker(
                            max_drawdown_pct=cfg.get("max_drawdown_pct", 0.15)
                        )
                        multiplier = await breaker.get_sizing_multiplier(user_id)
                        if multiplier <= 0:
                            logger.warning(
                                "Drawdown breaker HALT: skipping signal %s for user %s",
                                sig.id, user_id,
                            )
                            sig.status = "rejected"
                            await db.commit()
                            continue
                        if multiplier < 1.0:
                            old_qty = quantity
                            quantity *= multiplier
                            logger.info(
                                "Drawdown breaker: reduced quantity %.6f -> %.6f "
                                "for signal %s (multiplier=%.2f)",
                                old_qty, quantity, sig.id, multiplier,
                            )
                    except Exception as e:
                        logger.warning("Drawdown breaker check failed: %s", e)

                # --- Correlation penalty check (Feature 8) ---
                if cfg.get("correlation_auto_reduce", False):
                    try:
                        from app.execution.correlation_monitor import CorrelationMonitor

                        monitor = CorrelationMonitor()
                        penalty = await monitor.get_cached_penalty(user_id)
                        if penalty < 1.0:
                            old_qty = quantity
                            quantity *= penalty
                            logger.info(
                                "Correlation penalty: reduced quantity %.6f -> %.6f "
                                "for signal %s (penalty=%.2f)",
                                old_qty, quantity, sig.id, penalty,
                            )
                    except Exception as e:
                        logger.warning("Correlation penalty check failed: %s", e)

                # Skip if quantity reduced to effectively zero
                if quantity <= 0:
                    logger.warning(
                        "Quantity reduced to zero for signal %s, skipping", sig.id
                    )
                    sig.status = "rejected"
                    await db.commit()
                    continue

                # --- Minimum notional check (exchange-enforced floor) ---
                try:
                    from app.execution.min_notional import (
                        check_min_notional,
                        resolve_exchange_for_symbol,
                    )

                    target_exchange = resolve_exchange_for_symbol(
                        sig.symbol, cfg,
                    )
                    entry_price = sig.entry_price or 0.0
                    passes, notional, minimum = check_min_notional(
                        symbol=sig.symbol,
                        quantity=quantity,
                        price=entry_price,
                        exchange=target_exchange,
                    )
                    if not passes:
                        logger.warning(
                            "Min notional REJECT: signal %s for %s — "
                            "notional $%.4f < $%.2f minimum on %s",
                            sig.id, sig.symbol, notional, minimum, target_exchange,
                        )
                        sig.status = "rejected"
                        await db.commit()
                        continue
                except Exception as e:
                    logger.warning("Min notional check failed (proceeding): %s", e)

                # --- Holdings-based position cap (use actual exchange balances) ---
                try:
                    from app.api.holdings import _fetch_exchange_holdings

                    exchange_holdings = await _fetch_exchange_holdings(db, user_id)
                    base_symbol = sig.symbol.split("/")[0]

                    # Sum across all exchanges (user may hold asset on multiple)
                    available_qty = sum(
                        h.quantity for h in exchange_holdings
                        if h.symbol == base_symbol
                    )

                    if available_qty <= 0:
                        logger.warning(
                            "Holdings cap REJECT: no %s holdings for user %s, "
                            "skipping signal %s",
                            base_symbol, user_id, sig.id,
                        )
                        sig.status = "rejected"
                        await db.commit()
                        continue

                    if quantity > available_qty:
                        logger.info(
                            "Holdings cap: reduced %s quantity %.6f -> %.6f "
                            "for signal %s (actual holding)",
                            base_symbol, quantity, available_qty, sig.id,
                        )
                        quantity = available_qty
                except Exception as e:
                    logger.warning(
                        "Holdings cap check failed (proceeding with formula size): %s", e
                    )

                # --- Position-aware safety check (defense-in-depth) ---
                buy_position = await PositionManagerDB.find_open_position(
                    db, user_id, sig.symbol, direction="BUY",
                )
                if sig.direction == "BUY" and buy_position:
                    logger.info(
                        "PositionFilter REJECT: BUY signal %s for %s — "
                        "open BUY position exists",
                        sig.id, sig.symbol,
                    )
                    sig.status = "rejected"
                    await db.commit()
                    continue
                if sig.direction == "SELL" and not buy_position:
                    logger.info(
                        "PositionFilter REJECT: SELL signal %s for %s — "
                        "no open BUY position to close",
                        sig.id, sig.symbol,
                    )
                    sig.status = "rejected"
                    await db.commit()
                    continue

                # --- Idempotency check: skip if an active order already exists ---
                existing_order = await db.execute(
                    select(Order.id).where(
                        Order.signal_id == sig.id,
                        Order.status.notin_(["rejected", "cancelled", "failed"]),
                    ).limit(1)
                )
                if existing_order.scalar_one_or_none():
                    logger.info(
                        "Signal %s already has an active order, skipping (idempotency)",
                        sig.id,
                    )
                    continue

                signal_dict = {
                    "signal_id": str(sig.id),
                    "symbol": sig.symbol,
                    "direction": sig.direction,
                    "quantity": quantity,
                    "price": sig.entry_price,
                    "order_type": "market",
                    "stop_loss": sig.stop_loss,
                    "take_profit": sig.take_profit_1,
                }
                order = await executor.execute_signal(
                    db, user_id, signal_dict
                )

                # Only mark active if order was actually accepted
                if order.status in ("rejected", "cancelled"):
                    sig.status = "rejected"
                    logger.warning(
                        "Signal %s order rejected (status=%s), marking signal rejected",
                        sig.id, order.status,
                    )
                else:
                    sig.status = "active"

                    # --- Position management for filled orders ---
                    filled = order.filled_quantity
                    if order.status == "filled" and filled and filled > 0:
                        fill_price = order.average_fill_price or sig.entry_price

                        if sig.direction == "SELL":
                            # SELL = close existing BUY position (exit trade)
                            buy_pos = await PositionManagerDB.find_open_position(
                                db, user_id, sig.symbol, direction="BUY",
                            )
                            if buy_pos:
                                result = await PositionManagerDB.close_position(
                                    db, str(buy_pos.id), fill_price,
                                    reason="sell_signal", user_id=user_id,
                                )
                                logger.info(
                                    "Closed BUY position %s for %s — pnl=%.2f (sell signal)",
                                    buy_pos.id, sig.symbol, result["pnl"],
                                )
                            else:
                                logger.warning(
                                    "SELL filled for %s but no BUY position found to close",
                                    sig.symbol,
                                )
                        else:
                            # BUY = open new position
                            pos = await PositionManagerDB.open_position(
                                db,
                                user_id=user_id,
                                symbol=sig.symbol,
                                direction=sig.direction,
                                quantity=order.filled_quantity,
                                entry_price=fill_price,
                                stop_loss=sig.stop_loss,
                                take_profit=sig.take_profit_1,
                                broker=order.broker or "paper",
                                order_id=str(order.id),
                                strategy_id=str(sig.strategy_id) if sig.strategy_id else None,
                            )
                            logger.info(
                                "Opened position %s for %s %s — qty=%.6f entry=%.2f",
                                pos.id, sig.direction, sig.symbol,
                                order.filled_quantity, fill_price,
                            )

                logger.info(
                    "Executed signal %s -> order %s status=%s",
                    sig.id,
                    order.id,
                    order.status,
                )
            except Exception as e:
                sig.status = "failed"
                logger.exception("Failed to execute signal %s: %s", sig.id, e)

            # Commit after each signal to prevent stuck "pending" state
            await db.commit()
