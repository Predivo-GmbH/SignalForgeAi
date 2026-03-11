"""UniverseManager — candidate pool and promotion logic for dynamic symbol discovery.

Workflow:
  1. Exchange fetch (done by expand_symbol_universe task) produces raw tickers
  2. filter_candidates() winnows to qualifying symbols not already watched
  3. Those symbols enter a "candidate pool" — candle ingestion begins
  4. Once enough candle history exists (promotion_lookback), get_promotion_ready()
     returns them as ready to be added to the active strategy
  5. The signal pipeline evaluates them naturally from there

This class does NOT touch strategy configs — that's SymbolRotationManager's job.
"""

import logging

logger = logging.getLogger(__name__)

_STABLECOINS = frozenset({
    "USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "UST",
    "USDE", "PYUSD", "GUSD",
})
_WRAPPED = frozenset({"WBTC", "WETH", "STETH", "WBNB", "WMATIC"})


class UniverseManager:
    """Manages the candidate symbol pool for universe expansion."""

    def __init__(
        self,
        max_candidates: int = 1000,
        promotion_lookback: int = 300,
    ):
        self.max_candidates = max_candidates
        self.promotion_lookback = promotion_lookback

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_candidates(
        self,
        tickers: list[dict],
        min_volume_usd: float,
        exclude: set[str] | None = None,
    ) -> list[dict]:
        """Filter raw exchange tickers down to qualifying candidates.

        Excludes:
        - Stablecoins
        - Wrapped tokens
        - Pairs below min_volume_usd 24h volume
        - Symbols already in ``exclude`` set (already watched)

        Returns filtered list sorted by volume descending.
        """
        exclude = exclude or set()
        result = []

        for ticker in tickers:
            symbol: str = ticker.get("symbol", "")
            if not symbol or "/" not in symbol:
                continue

            base, quote = symbol.split("/", 1)

            # Only USDT quote pairs
            if quote != "USDT":
                continue

            # Skip stablecoins and wrapped tokens
            if base in _STABLECOINS or base in _WRAPPED:
                continue

            # Skip if already watched
            if symbol in exclude:
                continue

            # Volume check
            volume = ticker.get("quoteVolume") or 0.0
            if volume < min_volume_usd:
                continue

            result.append(ticker)

        result.sort(key=lambda t: t.get("quoteVolume") or 0.0, reverse=True)
        return result

    # ------------------------------------------------------------------
    # Candidate pool management
    # ------------------------------------------------------------------

    def update_candidate_pool(
        self,
        existing_pool: set[str],
        new_candidates: list[str],
    ) -> set[str]:
        """Merge new_candidates into the existing pool, capping at max_candidates.

        Existing pool symbols have priority — new ones fill remaining slots.
        Returns the updated pool as a set.
        """
        pool = set(existing_pool)
        for sym in new_candidates:
            if len(pool) >= self.max_candidates:
                break
            pool.add(sym)
        return pool

    # ------------------------------------------------------------------
    # Promotion
    # ------------------------------------------------------------------

    def get_promotion_ready(
        self,
        candle_counts: dict[str, int],
    ) -> list[str]:
        """Return symbols from the candidate pool that have enough candle history.

        A symbol is "promotion ready" when it has >= promotion_lookback candles
        on the strategy's primary timeframe. The signal pipeline requires this
        minimum history to compute indicators reliably.

        Args:
            candle_counts: mapping of symbol -> candle count available

        Returns:
            List of symbols ready to be promoted into an active strategy.
        """
        return [
            sym for sym, count in candle_counts.items()
            if count >= self.promotion_lookback
        ]
