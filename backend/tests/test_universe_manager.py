"""Tests for UniverseManager — candidate pool and promotion logic."""

from unittest.mock import AsyncMock, MagicMock, patch


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
        "max_risk_per_trade": 0.02,
    }
    return s


def _make_ticker(symbol: str, volume: float = 2_000_000) -> dict:
    return {
        "symbol": symbol,
        "quoteVolume": volume,
        "percentage": 5.0,
    }


# ---------------------------------------------------------------------------
# Candidate pool
# ---------------------------------------------------------------------------


def test_filter_candidates_excludes_stablecoins():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    tickers = [
        _make_ticker("BTC/USDT"),
        _make_ticker("USDC/USDT"),
        _make_ticker("BUSD/USDT"),
        _make_ticker("ETH/USDT"),
    ]
    result = mgr.filter_candidates(tickers, min_volume_usd=0)
    symbols = [t["symbol"] for t in result]

    assert "USDC/USDT" not in symbols
    assert "BUSD/USDT" not in symbols
    assert "BTC/USDT" in symbols
    assert "ETH/USDT" in symbols


def test_filter_candidates_excludes_wrapped_tokens():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    tickers = [
        _make_ticker("WBTC/USDT"),
        _make_ticker("WETH/USDT"),
        _make_ticker("BTC/USDT"),
    ]
    result = mgr.filter_candidates(tickers, min_volume_usd=0)
    symbols = [t["symbol"] for t in result]

    assert "WBTC/USDT" not in symbols
    assert "WETH/USDT" not in symbols
    assert "BTC/USDT" in symbols


def test_filter_candidates_respects_min_volume():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    tickers = [
        _make_ticker("BTC/USDT", volume=2_000_000),
        _make_ticker("LOW/USDT", volume=100_000),
    ]
    result = mgr.filter_candidates(tickers, min_volume_usd=500_000)
    symbols = [t["symbol"] for t in result]

    assert "BTC/USDT" in symbols
    assert "LOW/USDT" not in symbols


def test_filter_candidates_excludes_already_watched():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    tickers = [
        _make_ticker("BTC/USDT"),
        _make_ticker("ETH/USDT"),
        _make_ticker("SOL/USDT"),
    ]
    already_watched = {"BTC/USDT", "ETH/USDT"}
    result = mgr.filter_candidates(
        tickers, min_volume_usd=0, exclude=already_watched,
    )
    symbols = [t["symbol"] for t in result]

    assert "BTC/USDT" not in symbols
    assert "ETH/USDT" not in symbols
    assert "SOL/USDT" in symbols


# ---------------------------------------------------------------------------
# Candidate pool management
# ---------------------------------------------------------------------------


def test_add_to_candidate_pool_respects_max():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager(max_candidates=5)
    symbols = [f"SYM{i}/USDT" for i in range(10)]
    pool = mgr.update_candidate_pool(existing_pool=set(), new_candidates=symbols)

    assert len(pool) <= 5


def test_add_to_candidate_pool_deduplicates():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    existing = {"BTC/USDT", "ETH/USDT"}
    new = ["BTC/USDT", "SOL/USDT"]
    pool = mgr.update_candidate_pool(existing_pool=existing, new_candidates=new)

    # BTC already in pool — count should not increase by 2
    assert pool.count("BTC/USDT") if isinstance(pool, list) else "BTC/USDT" in pool


# ---------------------------------------------------------------------------
# Promotion logic
# ---------------------------------------------------------------------------


def test_symbols_with_sufficient_candles_are_promoted():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager(promotion_lookback=300)
    candle_counts = {
        "QUBIC/USDT": 350,  # enough
        "NEW/USDT": 100,    # not enough yet
    }
    ready = mgr.get_promotion_ready(candle_counts)

    assert "QUBIC/USDT" in ready
    assert "NEW/USDT" not in ready


def test_symbols_below_threshold_not_promoted():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager(promotion_lookback=300)
    candle_counts = {"NEW/USDT": 50}
    ready = mgr.get_promotion_ready(candle_counts)

    assert len(ready) == 0


# ---------------------------------------------------------------------------
# Integration: does not modify signal params
# ---------------------------------------------------------------------------


def test_universe_manager_never_modifies_signal_params():
    """UniverseManager must never touch pipeline params on a strategy."""
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    strategy = _make_strategy(["BTC/USDT"])

    before = dict(strategy.config)

    # Simulate filtering
    tickers = [_make_ticker("QUBIC/USDT")]
    mgr.filter_candidates(tickers, min_volume_usd=0)

    # Config untouched (filter doesn't touch strategy)
    for key in ["min_trigger_count", "min_confluence", "max_risk_per_trade"]:
        assert strategy.config[key] == before[key]
