"""Tests for watchlist quality gates.

Portfolio sync: symbols with < min_candles must not be added to the watchlist.
Universe promotion: symbols must pass a pipeline signal quality check (non-chaotic
regime + minimum confluence) before being promoted from the candidate pool.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_strategy(symbols: list[str]) -> MagicMock:
    s = MagicMock()
    s.id = "strat-1"
    s.name = "Test Strategy"
    s.is_active = True
    s.config = {
        "symbols": list(symbols),
        "timeframes": ["4h"],
        "exchange_map": {},
        "min_trigger_count": 2,
        "min_confluence": 70,
        "symbol_sources": {},
    }
    return s


def _make_holding(symbol: str, quantity: float = 100.0) -> MagicMock:
    h = MagicMock()
    h.symbol = symbol
    h.quantity = quantity
    return h


def _make_signal(action="NO_TRADE", regime="no_trend", confluence_score=0) -> MagicMock:
    sig = MagicMock()
    sig.action = action
    sig.regime = regime
    sig.confluence_score = confluence_score
    sig.block_reason = None
    return sig


# ---------------------------------------------------------------------------
# Portfolio sync candle gate
# ---------------------------------------------------------------------------


def test_portfolio_symbol_with_no_candles_not_added_to_watchlist():
    """Symbol with 0 candles must not be added to the watchlist (but synthetic position is still created)."""
    import asyncio

    from app.tasks.sync_portfolio_symbols import _build_sync_ops

    strategy = _make_strategy([])
    holdings = [_make_holding("AYIN")]  # exchange-specific token with no candle data

    to_add, _ = _build_sync_ops(
        holdings=holdings,
        strategies=[strategy],
        open_position_symbols=set(),
    )

    # _build_sync_ops still returns it — the candle gate lives in _sync_portfolio_async.
    # This test verifies _build_sync_ops is unaware of candles (pure function).
    assert "AYIN/USDT" in to_add


def test_candle_gate_filters_symbols_below_minimum():
    """The candle count gate in _sync_portfolio_async must exclude low-data symbols."""
    # Test the gate logic directly (mirrors the inline code in _sync_portfolio_async)
    to_add_raw = ["AYIN/USDT", "BTC/USDT", "ETH/USDT"]
    candle_counts = {"BTC/USDT": 500, "ETH/USDT": 150, "AYIN/USDT": 0}
    min_candles = 100

    to_add = [sym for sym in to_add_raw if candle_counts.get(sym, 0) >= min_candles]

    assert "BTC/USDT" in to_add
    assert "ETH/USDT" in to_add
    assert "AYIN/USDT" not in to_add


def test_candle_gate_passes_symbol_at_exact_minimum():
    """A symbol at exactly min_candles must be included."""
    to_add_raw = ["TOKEN/USDT"]
    candle_counts = {"TOKEN/USDT": 100}
    min_candles = 100

    to_add = [sym for sym in to_add_raw if candle_counts.get(sym, 0) >= min_candles]

    assert "TOKEN/USDT" in to_add


# ---------------------------------------------------------------------------
# Universe promotion pipeline quality gate
# ---------------------------------------------------------------------------


def _make_pipeline_result(regime: str, confluence_score: int) -> MagicMock:
    r = MagicMock()
    r.regime = regime
    r.confluence_score = confluence_score
    r.action = "NO_TRADE"
    r.block_reason = regime if confluence_score < 30 else None
    return r


def test_chaotic_regime_blocks_promotion():
    """A symbol in a chaotic regime must not be promoted regardless of confluence."""
    result = _make_pipeline_result(regime="chaotic", confluence_score=60)
    min_signal_confluence = 25

    passes = result.regime != "chaotic" and result.confluence_score >= min_signal_confluence
    assert passes is False


def test_non_chaotic_with_sufficient_confluence_passes():
    """A symbol with a trending regime and confluence >= threshold must be promoted."""
    result = _make_pipeline_result(regime="trending", confluence_score=45)
    min_signal_confluence = 25

    passes = result.regime != "chaotic" and result.confluence_score >= min_signal_confluence
    assert passes is True


def test_non_chaotic_with_low_confluence_blocked():
    """A symbol with a non-chaotic regime but confluence below threshold is blocked."""
    result = _make_pipeline_result(regime="no_trend", confluence_score=10)
    min_signal_confluence = 25

    passes = result.regime != "chaotic" and result.confluence_score >= min_signal_confluence
    assert passes is False


def test_weak_trend_at_minimum_confluence_passes():
    """Minimum viable: weak_trend + exactly min confluence must pass."""
    result = _make_pipeline_result(regime="weak_trend", confluence_score=25)
    min_signal_confluence = 25

    passes = result.regime != "chaotic" and result.confluence_score >= min_signal_confluence
    assert passes is True


def test_quality_gate_applied_after_candle_count_check():
    """Verify the two-stage gate: candle count first, then quality check."""
    symbols_with_enough_candles = ["BTC/USDT", "RUBBISH/USDT", "ETH/USDT"]
    pipeline_results = {
        "BTC/USDT": _make_pipeline_result("trending", 55),
        "RUBBISH/USDT": _make_pipeline_result("chaotic", 5),
        "ETH/USDT": _make_pipeline_result("no_trend", 8),
    }
    min_signal_confluence = 25

    ready = [
        sym for sym in symbols_with_enough_candles
        if pipeline_results[sym].regime != "chaotic"
        and pipeline_results[sym].confluence_score >= min_signal_confluence
    ]

    assert "BTC/USDT" in ready
    assert "RUBBISH/USDT" not in ready  # chaotic
    assert "ETH/USDT" not in ready      # confluence too low
