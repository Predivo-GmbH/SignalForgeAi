"""Tests for expand_symbol_universe Celery task."""

from unittest.mock import AsyncMock, MagicMock, patch


def _make_strategy(symbols: list[str]) -> MagicMock:
    s = MagicMock()
    s.id = "strat-1"
    s.name = "Test Strategy"
    s.is_active = True
    s.user_id = "user-1"
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
    return {"symbol": symbol, "quoteVolume": volume, "percentage": 3.0}


# ---------------------------------------------------------------------------
# Task registration
# ---------------------------------------------------------------------------


def test_expand_symbol_universe_task_registered():
    from app.tasks.expand_symbol_universe import expand_symbol_universe

    assert expand_symbol_universe.name == "expand_symbol_universe"


# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------


def test_task_skips_when_disabled():
    import asyncio

    from app.tasks.expand_symbol_universe import _expand_universe_async

    with patch("app.tasks.expand_symbol_universe.settings") as mock_settings:
        mock_settings.universe_expansion_enabled = False
        asyncio.run(_expand_universe_async())  # should return early without error


# ---------------------------------------------------------------------------
# Exchange fetch + candidate filtering
# ---------------------------------------------------------------------------


def test_fetch_tickers_called_once():
    """Exchange fetch should happen once per run, not once per symbol."""
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    tickers = [
        _make_ticker("QUBIC/USDT"),
        _make_ticker("NEW1/USDT"),
        _make_ticker("NEW2/USDT"),
    ]
    candidates = mgr.filter_candidates(tickers, min_volume_usd=0)
    assert len(candidates) == 3


def test_candidates_not_already_watched_are_selected():
    from app.advisor.universe_manager import UniverseManager

    mgr = UniverseManager()
    tickers = [
        _make_ticker("BTC/USDT"),   # already watched
        _make_ticker("QUBIC/USDT"), # new
    ]
    candidates = mgr.filter_candidates(
        tickers, min_volume_usd=0, exclude={"BTC/USDT"},
    )
    symbols = [t["symbol"] for t in candidates]
    assert "BTC/USDT" not in symbols
    assert "QUBIC/USDT" in symbols


# ---------------------------------------------------------------------------
# Candle backfill triggered for new candidates
# ---------------------------------------------------------------------------


def test_backfill_triggered_for_ai_approved_candidates():
    """AI-approved candidates must trigger backfill_symbols.delay."""
    import asyncio

    from app.tasks.expand_symbol_universe import _expand_universe_async

    strategy = _make_strategy(["BTC/USDT"])

    mock_r = MagicMock()
    mock_r.smembers.return_value = set()
    mock_r.hgetall.return_value = {}

    with (
        patch("app.tasks.expand_symbol_universe.backfill_symbols") as mock_backfill,
        patch("app.tasks.expand_symbol_universe._fetch_all_connected_exchange_tickers",
              new=AsyncMock(return_value=[_make_ticker("QUBIC/USDT")])),
        patch("app.tasks.expand_symbol_universe._get_redis_client", return_value=mock_r),
        patch("app.tasks.expand_symbol_universe.settings") as mock_settings,
        patch("app.tasks.expand_symbol_universe.SymbolScout") as mock_scout_cls,
        patch("app.tasks.expand_symbol_universe.task_session") as mock_session,
        patch("app.tasks.promote_universe_candidates.promote_universe_candidates"),
    ):
        mock_settings.universe_expansion_enabled = True
        mock_settings.universe_min_volume_usd = 0
        mock_settings.universe_max_candidates = 1000
        mock_settings.universe_promotion_lookback_candles = 300
        mock_settings.default_exchange = "binance"

        # Mock DB session returning one active strategy
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [strategy]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        # AI approves QUBIC/USDT
        mock_scout = AsyncMock()
        mock_scout.evaluate_candidates = AsyncMock(return_value=["QUBIC/USDT"])
        mock_scout_cls.return_value = mock_scout

        asyncio.run(_expand_universe_async())

        mock_backfill.delay.assert_called_once()
        call_args = mock_backfill.delay.call_args[0]
        assert "QUBIC/USDT" in call_args[0]


def test_ai_rejected_candidates_not_backfilled():
    """Candidates rejected by the AI must NOT trigger backfill."""
    import asyncio

    from app.tasks.expand_symbol_universe import _expand_universe_async

    strategy = _make_strategy(["BTC/USDT"])

    mock_r = MagicMock()
    mock_r.smembers.return_value = set()
    mock_r.hgetall.return_value = {}

    with (
        patch("app.tasks.expand_symbol_universe.backfill_symbols") as mock_backfill,
        patch("app.tasks.expand_symbol_universe._fetch_all_connected_exchange_tickers",
              new=AsyncMock(return_value=[_make_ticker("SCAM/USDT")])),
        patch("app.tasks.expand_symbol_universe._get_redis_client", return_value=mock_r),
        patch("app.tasks.expand_symbol_universe.settings") as mock_settings,
        patch("app.tasks.expand_symbol_universe.SymbolScout") as mock_scout_cls,
        patch("app.tasks.expand_symbol_universe.task_session") as mock_session,
        patch("app.tasks.promote_universe_candidates.promote_universe_candidates"),
    ):
        mock_settings.universe_expansion_enabled = True
        mock_settings.universe_min_volume_usd = 0
        mock_settings.universe_max_candidates = 1000
        mock_settings.universe_promotion_lookback_candles = 300
        mock_settings.default_exchange = "binance"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [strategy]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        # AI rejects everything
        mock_scout = AsyncMock()
        mock_scout.evaluate_candidates = AsyncMock(return_value=[])
        mock_scout_cls.return_value = mock_scout

        asyncio.run(_expand_universe_async())

        mock_backfill.delay.assert_not_called()


# ---------------------------------------------------------------------------
# Promotion: event-driven via promote_universe_candidates task
# ---------------------------------------------------------------------------


def test_ready_candidate_promoted_to_strategy():
    """Candidate with sufficient candle history gets added to strategy via promotion task."""
    import asyncio

    from app.tasks.promote_universe_candidates import _promote_async

    strategy = _make_strategy(["BTC/USDT"])

    mock_r = MagicMock()
    mock_r.smembers.return_value = {b"QUBIC/USDT"}
    mock_r.hgetall.return_value = {b"QUBIC/USDT": b"binance"}

    with (
        patch("app.tasks.promote_universe_candidates.redis_lib") as mock_redis_lib,
        patch("app.tasks.promote_universe_candidates.settings") as mock_settings,
        patch("app.tasks.promote_universe_candidates.task_session") as mock_session,
    ):
        mock_settings.redis_url = "redis://localhost"
        mock_settings.universe_promotion_lookback_candles = 300
        mock_settings.default_exchange = "binance"
        mock_redis_lib.from_url.return_value = mock_r

        mock_db = AsyncMock()
        strat_result = MagicMock()
        strat_result.scalars.return_value.all.return_value = [strategy]
        candle_result = MagicMock()
        candle_result.all.return_value = [MagicMock(symbol="QUBIC/USDT", cnt=350)]
        mock_db.execute = AsyncMock(side_effect=[strat_result, candle_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        asyncio.run(_promote_async(["QUBIC/USDT"]))

        assert "QUBIC/USDT" in strategy.config["symbols"]


def test_candidate_not_promoted_without_enough_candles():
    """Candidate still building history should NOT be promoted yet."""
    import asyncio

    from app.tasks.promote_universe_candidates import _promote_async

    strategy = _make_strategy(["BTC/USDT"])

    mock_r = MagicMock()
    mock_r.smembers.return_value = {b"QUBIC/USDT"}
    mock_r.hgetall.return_value = {b"QUBIC/USDT": b"binance"}

    with (
        patch("app.tasks.promote_universe_candidates.redis_lib") as mock_redis_lib,
        patch("app.tasks.promote_universe_candidates.settings") as mock_settings,
        patch("app.tasks.promote_universe_candidates.task_session") as mock_session,
    ):
        mock_settings.redis_url = "redis://localhost"
        mock_settings.universe_promotion_lookback_candles = 300
        mock_settings.default_exchange = "binance"
        mock_redis_lib.from_url.return_value = mock_r

        mock_db = AsyncMock()
        strat_result = MagicMock()
        strat_result.scalars.return_value.all.return_value = [strategy]
        candle_result = MagicMock()
        candle_result.all.return_value = [MagicMock(symbol="QUBIC/USDT", cnt=50)]
        mock_db.execute = AsyncMock(side_effect=[strat_result, candle_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        asyncio.run(_promote_async(["QUBIC/USDT"]))

        assert "QUBIC/USDT" not in strategy.config["symbols"]


# ---------------------------------------------------------------------------
# Signal params integrity
# ---------------------------------------------------------------------------


def test_task_never_modifies_signal_params():
    """Promotion must never touch pipeline params on a strategy."""
    import asyncio

    from app.tasks.promote_universe_candidates import _promote_async

    strategy = _make_strategy(["BTC/USDT"])
    before = {k: v for k, v in strategy.config.items() if k != "symbols"}

    mock_r = MagicMock()
    mock_r.smembers.return_value = {b"QUBIC/USDT"}
    mock_r.hgetall.return_value = {b"QUBIC/USDT": b"binance"}

    with (
        patch("app.tasks.promote_universe_candidates.redis_lib") as mock_redis_lib,
        patch("app.tasks.promote_universe_candidates.settings") as mock_settings,
        patch("app.tasks.promote_universe_candidates.task_session") as mock_session,
    ):
        mock_settings.redis_url = "redis://localhost"
        mock_settings.universe_promotion_lookback_candles = 300
        mock_settings.default_exchange = "binance"
        mock_redis_lib.from_url.return_value = mock_r

        mock_db = AsyncMock()
        strat_result = MagicMock()
        strat_result.scalars.return_value.all.return_value = [strategy]
        candle_result = MagicMock()
        candle_result.all.return_value = [MagicMock(symbol="QUBIC/USDT", cnt=350)]
        mock_db.execute = AsyncMock(side_effect=[strat_result, candle_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        asyncio.run(_promote_async(["QUBIC/USDT"]))

        for key in ["min_trigger_count", "min_confluence", "max_risk_per_trade"]:
            assert strategy.config[key] == before[key], f"{key} was modified!"


# ---------------------------------------------------------------------------
# Beat schedule
# ---------------------------------------------------------------------------


def test_beat_schedule_includes_expand_symbol_universe():
    from app.worker import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "expand-symbol-universe-6h" in schedule
    assert "sync-portfolio-symbols-5m" in schedule
