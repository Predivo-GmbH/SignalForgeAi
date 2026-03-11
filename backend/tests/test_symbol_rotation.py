"""Tests for SymbolRotationManager."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


def _make_strategy(symbols: list[str], extra_config: dict | None = None) -> MagicMock:
    """Create a mock strategy with the given symbols in config."""
    s = MagicMock()
    s.id = "test-strategy-id"
    s.name = "Test Strategy"
    s.config = {
        "symbols": list(symbols),
        "timeframes": ["4h"],
        "exchange_map": {},
        # Signal params — must never be modified
        "min_trigger_count": 2,
        "trigger_lookback_candles": 50,
        "ema_slope_threshold": 0.001,
        "min_confluence": 70,
        "max_risk_per_trade": 0.02,
    }
    if extra_config:
        s.config.update(extra_config)
    return s


def _make_trade(symbol: str, pnl_pct: float) -> MagicMock:
    t = MagicMock()
    t.symbol = symbol
    t.pnl_pct = pnl_pct
    return t


def _make_position(symbol: str) -> MagicMock:
    p = MagicMock()
    p.symbol = symbol
    p.is_open = True
    return p


# ---------------------------------------------------------------------------
# get_active_symbols
# ---------------------------------------------------------------------------


def test_get_active_symbols_reads_config():
    from app.advisor.symbol_rotation import SymbolRotationManager

    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT", "ETH/USDT"])
    assert mgr.get_active_symbols(strategy) == ["BTC/USDT", "ETH/USDT"]


def test_get_active_symbols_empty_config():
    from app.advisor.symbol_rotation import SymbolRotationManager

    mgr = SymbolRotationManager()
    strategy = _make_strategy([])
    assert mgr.get_active_symbols(strategy) == []


# ---------------------------------------------------------------------------
# add_symbols
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_symbols_appends_to_config():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT"])

    added = await mgr.add_symbols(strategy, ["ETH/USDT", "SOL/USDT"], db)

    assert "ETH/USDT" in strategy.config["symbols"]
    assert "SOL/USDT" in strategy.config["symbols"]
    assert "BTC/USDT" in strategy.config["symbols"]
    assert added == ["ETH/USDT", "SOL/USDT"]


@pytest.mark.asyncio
async def test_add_symbols_deduplicates():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT", "ETH/USDT"])

    added = await mgr.add_symbols(strategy, ["ETH/USDT", "SOL/USDT"], db)

    # ETH/USDT already present — should not be duplicated
    assert strategy.config["symbols"].count("ETH/USDT") == 1
    assert added == ["SOL/USDT"]  # only actually new ones returned


@pytest.mark.asyncio
async def test_add_symbols_does_not_modify_signal_params():
    """CORE INTEGRITY TEST: signal pipeline params must never change."""
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT"])

    before = {
        "min_trigger_count": strategy.config["min_trigger_count"],
        "trigger_lookback_candles": strategy.config["trigger_lookback_candles"],
        "ema_slope_threshold": strategy.config["ema_slope_threshold"],
        "min_confluence": strategy.config["min_confluence"],
        "max_risk_per_trade": strategy.config["max_risk_per_trade"],
    }

    await mgr.add_symbols(strategy, ["ETH/USDT"], db)

    for key, val in before.items():
        assert strategy.config[key] == val, f"{key} was modified!"


@pytest.mark.asyncio
async def test_add_symbols_updates_exchange_map():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT"])

    await mgr.add_symbols(strategy, ["ETH/USDT"], db, exchange="kucoin")

    assert strategy.config["exchange_map"].get("ETH/USDT") == "kucoin"


@pytest.mark.asyncio
async def test_add_symbols_returns_empty_when_all_duplicates():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT", "ETH/USDT"])

    added = await mgr.add_symbols(strategy, ["BTC/USDT", "ETH/USDT"], db)

    assert added == []


# ---------------------------------------------------------------------------
# remove_symbols
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_symbols_removes_from_config():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT", "ETH/USDT", "SOL/USDT"])

    removed = await mgr.remove_symbols(strategy, ["ETH/USDT"], db)

    assert "ETH/USDT" not in strategy.config["symbols"]
    assert "BTC/USDT" in strategy.config["symbols"]
    assert removed == ["ETH/USDT"]


@pytest.mark.asyncio
async def test_remove_symbols_does_not_modify_signal_params():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT", "ETH/USDT"])

    before_confluence = strategy.config["min_confluence"]
    await mgr.remove_symbols(strategy, ["ETH/USDT"], db)
    assert strategy.config["min_confluence"] == before_confluence


# ---------------------------------------------------------------------------
# drop_weakest_symbols
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drop_weakest_excludes_open_positions():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT", "ETH/USDT", "SOL/USDT"])

    # ETH has open position — must be protected
    open_positions = [_make_position("ETH/USDT")]
    trades = [
        _make_trade("BTC/USDT", -0.05),
        _make_trade("SOL/USDT", -0.10),  # worst performer
        _make_trade("ETH/USDT", -0.20),  # worst but has open position
    ]

    dropped = await mgr.drop_weakest_symbols(
        strategy, count=1, db=db,
        open_positions=open_positions, recent_trades=trades,
    )

    assert "ETH/USDT" not in dropped
    assert len(dropped) == 1


@pytest.mark.asyncio
async def test_drop_weakest_prefers_zero_trade_symbols():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT", "ETH/USDT", "SOL/USDT"])

    # SOL has no trades — should be first to drop
    trades = [
        _make_trade("BTC/USDT", 0.05),
        _make_trade("ETH/USDT", 0.03),
        # SOL: no trades
    ]

    dropped = await mgr.drop_weakest_symbols(
        strategy, count=1, db=db,
        open_positions=[], recent_trades=trades,
    )

    assert "SOL/USDT" in dropped


# ---------------------------------------------------------------------------
# rotate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rotate_stays_within_max_cap():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    # Strategy already at cap
    symbols = [f"SYM{i}/USDT" for i in range(25)]
    strategy = _make_strategy(symbols)

    candidates = ["NEW1/USDT", "NEW2/USDT"]
    added, dropped = await mgr.rotate(
        strategy, candidates, db,
        max_symbols=25, open_positions=[], recent_trades=[],
    )

    assert len(strategy.config["symbols"]) <= 25
    assert len(added) <= len(candidates)
    assert len(dropped) == len(added)


@pytest.mark.asyncio
async def test_rotate_adds_without_dropping_when_below_cap():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT"])  # Only 1, cap is 25

    added, dropped = await mgr.rotate(
        strategy, ["ETH/USDT", "SOL/USDT"], db,
        max_symbols=25, open_positions=[], recent_trades=[],
    )

    assert added == ["ETH/USDT", "SOL/USDT"]
    assert dropped == []


@pytest.mark.asyncio
async def test_rotate_returns_added_and_dropped_lists():
    from app.advisor.symbol_rotation import SymbolRotationManager

    db = AsyncMock()
    mgr = SymbolRotationManager()
    strategy = _make_strategy(["BTC/USDT"])

    added, dropped = await mgr.rotate(
        strategy, ["ETH/USDT"], db,
        max_symbols=25, open_positions=[], recent_trades=[],
    )

    assert isinstance(added, list)
    assert isinstance(dropped, list)
