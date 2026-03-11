"""SymbolRotationManager — handles adding/removing symbols from strategy watchlists.

This module owns all DB mutation logic for strategy symbol lists.
INVARIANT: Only config['symbols'] and config['exchange_map'] are ever modified here.
Signal pipeline params (min_trigger_count, ema_slope_threshold, min_confluence, etc.)
are NEVER touched — they are the strategy's identity, set by the AI Advisor at deploy time.
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Keys that belong to the signal pipeline — must never be modified here
_SIGNAL_PARAM_KEYS = frozenset({
    "min_trigger_count",
    "trigger_lookback_candles",
    "ema_slope_threshold",
    "min_confluence",
    "max_risk_per_trade",
    "max_daily_loss",
    "atr_sl_multiplier",
    "min_risk_reward",
})


class SymbolRotationManager:
    """Manages symbol list mutations on Strategy objects.

    All methods mutate ``strategy.config`` in-place. The caller is responsible
    for committing the DB session after calling these methods.
    """

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_active_symbols(self, strategy) -> list[str]:
        """Return the current symbol list from strategy.config."""
        return list(strategy.config.get("symbols", []))

    async def get_symbols_already_watched(self, db, strategies: list) -> set[str]:
        """Return union of symbols across all given strategies."""
        watched: set[str] = set()
        for s in strategies:
            watched.update(s.config.get("symbols", []))
        return watched

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def add_symbols(
        self,
        strategy,
        new_symbols: list[str],
        db,
        exchange: str | None = None,
        source: str = "ai_deploy",
    ) -> list[str]:
        """Append new_symbols to strategy.config['symbols'].

        Deduplicates against current list. Records exchange and source
        (ai_deploy | portfolio_sync | universe_discovery) per symbol so the
        watchlist API can classify symbols accurately without relying on Redis TTLs.

        Returns the list of symbols that were actually added (net-new only).
        """
        cfg = dict(strategy.config)
        current = list(cfg.get("symbols", []))
        current_set = set(current)
        exchange_map = dict(cfg.get("exchange_map", {}))
        symbol_sources = dict(cfg.get("symbol_sources", {}))

        actually_added: list[str] = []
        for sym in new_symbols:
            if sym not in current_set:
                current.append(sym)
                current_set.add(sym)
                actually_added.append(sym)
                if exchange:
                    exchange_map[sym] = exchange
                symbol_sources[sym] = source

        # Only write back the non-signal-param keys — never touch signal params
        cfg["symbols"] = current
        cfg["exchange_map"] = exchange_map
        cfg["symbol_sources"] = symbol_sources
        strategy.config = cfg

        if actually_added:
            logger.info(
                "Added %d symbols to strategy '%s' (source=%s): %s",
                len(actually_added), strategy.name, source, actually_added,
            )
        return actually_added

    async def remove_symbols(
        self,
        strategy,
        symbols_to_remove: list[str],
        db,
    ) -> list[str]:
        """Remove symbols from strategy.config['symbols'].

        Returns the list of symbols actually removed.
        """
        cfg = dict(strategy.config)
        current = list(cfg.get("symbols", []))
        remove_set = set(symbols_to_remove)
        exchange_map = dict(cfg.get("exchange_map", {}))

        new_list = [s for s in current if s not in remove_set]
        removed = [s for s in current if s in remove_set]

        for sym in removed:
            exchange_map.pop(sym, None)

        cfg["symbols"] = new_list
        cfg["exchange_map"] = exchange_map
        strategy.config = cfg

        if removed:
            logger.info(
                "Removed %d symbols from strategy '%s': %s",
                len(removed), strategy.name, removed,
            )
        return removed

    async def drop_weakest_symbols(
        self,
        strategy,
        count: int,
        db,
        open_positions: list,
        recent_trades: list,
    ) -> list[str]:
        """Drop the ``count`` weakest-performing symbols from the strategy.

        Protection rules (never drop):
        - Symbols with an open position

        Priority for dropping (highest first):
        1. Symbols with zero trades (never generated a signal)
        2. Symbols with the worst average pnl_pct over recent trades

        Returns list of dropped symbol names.
        """
        if count <= 0:
            return []

        current_symbols = set(self.get_active_symbols(strategy))
        protected = {p.symbol for p in open_positions if p.is_open}
        droppable = current_symbols - protected

        if not droppable:
            logger.warning(
                "drop_weakest: no droppable symbols for strategy '%s' "
                "(all %d symbols have open positions)",
                strategy.name, len(current_symbols),
            )
            return []

        # Build per-symbol pnl stats from recent trades
        symbol_pnl: dict[str, list[float]] = defaultdict(list)
        for trade in recent_trades:
            if trade.symbol in droppable and trade.pnl_pct is not None:
                symbol_pnl[trade.symbol].append(trade.pnl_pct)

        def _score(sym: str) -> float:
            pnls = symbol_pnl.get(sym)
            if not pnls:
                return float("-inf")  # no trade history → drop first
            return sum(pnls) / len(pnls)

        ranked = sorted(droppable, key=_score)  # worst first
        to_drop = ranked[:count]

        return await self.remove_symbols(strategy, to_drop, db)

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    async def rotate(
        self,
        strategy,
        candidates: list[str],
        db,
        max_symbols: int,
        open_positions: list,
        recent_trades: list,
        exchange: str | None = None,
    ) -> tuple[list[str], list[str]]:
        """Add candidates to strategy, rotating out weakest if at cap.

        Returns (added, dropped) lists.
        """
        current_count = len(self.get_active_symbols(strategy))
        available_slots = max_symbols - current_count

        # Filter to net-new only
        current_set = set(self.get_active_symbols(strategy))
        net_new = [c for c in candidates if c not in current_set]

        if not net_new:
            return [], []

        dropped: list[str] = []
        if available_slots < len(net_new):
            # Need to make room
            need_to_drop = len(net_new) - available_slots
            dropped = await self.drop_weakest_symbols(
                strategy, need_to_drop, db,
                open_positions=open_positions,
                recent_trades=recent_trades,
            )
            # Re-count after drops
            net_new = net_new[:len(dropped) + available_slots]

        added = await self.add_symbols(strategy, net_new, db, exchange=exchange)
        return added, dropped
