"""Execute pending signals — place orders via BrokerRouter.

Applies risk management checks before execution:
  - Drawdown circuit breaker: skip/reduce at high drawdown
"""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="execute_pending_signals", bind=True, max_retries=3)
def execute_pending_signals(self):
    """Query signals pending execution, run risk checks, place orders."""
    import asyncio

    from app.tasks.task_utils import task_lock

    with task_lock("execute_signals", timeout=90) as acquired:
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
    from app.models.strategy import BrokerConnection, Strategy

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

                # --- Holdings-based position cap ---
                # Simulation strategies: use paper_holdings from PaperSimulation.
                # Live trading: exchange balances only.
                # Paper (non-simulation): exchange + manual holdings.
                is_simulation = cfg.get("is_simulation", False)
                sim_record = None  # will be set if simulation
                try:
                    parts = sig.symbol.split("/")
                    base_symbol = parts[0]
                    quote_symbol = parts[1] if len(parts) > 1 else "USDT"

                    if is_simulation:
                        # Use paper_holdings from the PaperSimulation record
                        from app.models.simulation import PaperSimulation

                        sim_result = await db.execute(
                            select(PaperSimulation).where(
                                PaperSimulation.strategy_id == strategy.id,
                                PaperSimulation.status == "running",
                            )
                        )
                        sim_record = sim_result.scalar_one_or_none()

                        if sim_record and sim_record.paper_holdings:
                            paper = sim_record.paper_holdings

                            if sig.direction == "SELL":
                                available_qty = sum(
                                    h["quantity"] for h in paper
                                    if h["symbol"] == base_symbol
                                )
                                if available_qty <= 0:
                                    logger.warning(
                                        "Paper portfolio REJECT: no %s in paper holdings, "
                                        "skipping SELL signal %s",
                                        base_symbol, sig.id,
                                    )
                                    sig.status = "rejected"
                                    await db.commit()
                                    continue
                                if quantity > available_qty:
                                    logger.info(
                                        "Paper portfolio: reduced %s SELL qty %.6f -> %.6f "
                                        "for signal %s",
                                        base_symbol, quantity, available_qty, sig.id,
                                    )
                                    quantity = available_qty
                            else:
                                # BUY: check USDT balance, respecting reserve
                                entry_price = sig.entry_price or 0.0
                                required_quote = quantity * entry_price
                                available_usdt = sum(
                                    h["quantity"] for h in paper
                                    if h["symbol"] == quote_symbol
                                )

                                # Enforce USDT reserve — don't spend below reserve floor
                                reserve_pct = cfg.get("usdt_reserve_pct", 0.0)
                                if reserve_pct > 0:
                                    total_paper_value = sum(
                                        h.get("value_usd", 0) for h in paper
                                    )
                                    reserve_floor = total_paper_value * reserve_pct
                                    deployable_usdt = max(0, available_usdt - reserve_floor)
                                else:
                                    deployable_usdt = available_usdt

                                if deployable_usdt <= 0:
                                    logger.warning(
                                        "Paper portfolio REJECT: insufficient %s "
                                        "(available=%.2f, reserve=%.2f), "
                                        "skipping BUY signal %s",
                                        quote_symbol, available_usdt,
                                        available_usdt - deployable_usdt, sig.id,
                                    )
                                    sig.status = "rejected"
                                    await db.commit()
                                    continue
                                if required_quote > deployable_usdt and entry_price > 0:
                                    # Partial fill: buy what we can afford
                                    max_buyable = deployable_usdt / entry_price
                                    logger.info(
                                        "Paper portfolio: reduced %s BUY qty %.6f -> %.6f "
                                        "for signal %s (%.2f %s deployable after reserve)",
                                        base_symbol, quantity, max_buyable, sig.id,
                                        deployable_usdt, quote_symbol,
                                    )
                                    quantity = max_buyable
                        else:
                            logger.warning(
                                "No paper_holdings found for simulation strategy %s",
                                strategy.id,
                            )
                    else:
                        # Non-simulation: use live or exchange+manual holdings
                        from app.api.holdings import (
                            _fetch_exchange_holdings,
                            _fetch_manual_holdings,
                        )

                        has_live_conn = await db.execute(
                            select(BrokerConnection.id).where(
                                BrokerConnection.user_id == strategy.user_id,
                                BrokerConnection.is_paper.is_(False),
                                BrokerConnection.purpose == "trade",
                            ).limit(1)
                        )
                        is_live = has_live_conn.scalar_one_or_none() is not None

                        if is_live:
                            all_holdings = await _fetch_exchange_holdings(db, user_id)
                        else:
                            exchange_h = await _fetch_exchange_holdings(db, user_id)
                            manual_h = await _fetch_manual_holdings(db, user_id)
                            all_holdings = exchange_h + manual_h

                        if sig.direction == "SELL":
                            available_qty = sum(
                                h.quantity for h in all_holdings
                                if h.symbol == base_symbol
                            )
                            if available_qty <= 0:
                                logger.warning(
                                    "Holdings cap REJECT: no %s holdings for user %s, "
                                    "skipping SELL signal %s",
                                    base_symbol, user_id, sig.id,
                                )
                                sig.status = "rejected"
                                await db.commit()
                                continue
                            if quantity > available_qty:
                                logger.info(
                                    "Holdings cap: reduced %s SELL quantity %.6f -> %.6f "
                                    "for signal %s (actual holding)",
                                    base_symbol, quantity, available_qty, sig.id,
                                )
                                quantity = available_qty
                        else:
                            entry_price = sig.entry_price or 0.0
                            required_quote = quantity * entry_price
                            available_quote = sum(
                                h.quantity for h in all_holdings
                                if h.symbol == quote_symbol
                            )
                            if available_quote <= 0:
                                logger.warning(
                                    "Holdings cap REJECT: no %s holdings for user %s, "
                                    "skipping BUY signal %s",
                                    quote_symbol, user_id, sig.id,
                                )
                                sig.status = "rejected"
                                await db.commit()
                                continue
                            if required_quote > available_quote and entry_price > 0:
                                max_buyable = available_quote / entry_price
                                logger.info(
                                    "Holdings cap: reduced %s BUY quantity %.6f -> %.6f "
                                    "for signal %s (only %.2f %s available)",
                                    base_symbol, quantity, max_buyable, sig.id,
                                    available_quote, quote_symbol,
                                )
                                quantity = max_buyable
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

                # --- Update paper portfolio after filled trade ---
                if (
                    is_simulation
                    and sim_record
                    and order.status == "filled"
                    and filled
                    and filled > 0
                ):
                    try:
                        _update_paper_holdings(
                            sim_record, sig.direction, base_symbol,
                            quote_symbol, filled, fill_price,
                        )
                    except Exception as e:
                        logger.warning(
                            "Paper holdings update failed for signal %s: %s",
                            sig.id, e,
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


def _update_paper_holdings(
    sim,
    direction: str,
    base_symbol: str,
    quote_symbol: str,
    quantity: float,
    price: float,
) -> None:
    """Update paper_holdings on the PaperSimulation after a filled trade.

    BUY:  deduct quote (USDT), add base asset
    SELL: deduct base asset, add quote (USDT)
    """
    from sqlalchemy.orm.attributes import flag_modified

    paper = sim.paper_holdings or []
    cost = quantity * price

    if direction == "BUY":
        # Deduct USDT
        for h in paper:
            if h["symbol"] == quote_symbol:
                h["quantity"] = round(max(0, h["quantity"] - cost), 8)
                h["value_usd"] = round(h["quantity"], 2)
                break

        # Add base asset
        found = False
        for h in paper:
            if h["symbol"] == base_symbol:
                h["quantity"] = round(h["quantity"] + quantity, 8)
                h["value_usd"] = round(h["quantity"] * price, 2)
                h["price_usd"] = price
                found = True
                break
        if not found:
            paper.append({
                "symbol": base_symbol,
                "quantity": round(quantity, 8),
                "price_usd": price,
                "value_usd": round(quantity * price, 2),
            })
    else:
        # SELL: deduct base asset
        for h in paper:
            if h["symbol"] == base_symbol:
                h["quantity"] = round(max(0, h["quantity"] - quantity), 8)
                h["value_usd"] = round(h["quantity"] * price, 2)
                h["price_usd"] = price
                break

        # Add USDT proceeds
        found = False
        for h in paper:
            if h["symbol"] == quote_symbol:
                h["quantity"] = round(h["quantity"] + cost, 8)
                h["value_usd"] = round(h["quantity"], 2)
                found = True
                break
        if not found:
            paper.append({
                "symbol": quote_symbol,
                "quantity": round(cost, 8),
                "price_usd": 1.0,
                "value_usd": round(cost, 2),
            })

    # Remove holdings with zero quantity
    sim.paper_holdings = [h for h in paper if h["quantity"] > 0]
    flag_modified(sim, "paper_holdings")
