"""Tests for sync_portfolio_symbols Celery task."""

from unittest.mock import AsyncMock, MagicMock, patch


def _make_holding(symbol: str, quantity: float = 100.0) -> MagicMock:
    h = MagicMock()
    h.symbol = symbol
    h.quantity = quantity
    return h


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
    }
    return s


# ---------------------------------------------------------------------------
# Task registration
# ---------------------------------------------------------------------------


def test_sync_portfolio_symbols_task_registered():
    from app.tasks.sync_portfolio_symbols import sync_portfolio_symbols

    assert sync_portfolio_symbols.name == "sync_portfolio_symbols"


# ---------------------------------------------------------------------------
# Core logic: held assets get added
# ---------------------------------------------------------------------------


def test_held_asset_not_in_strategy_gets_added():
    """A held asset missing from all strategies must be added."""
    from app.tasks.sync_portfolio_symbols import _build_sync_ops

    strategy = _make_strategy(["BTC/USDT"])
    holdings = [_make_holding("QUBIC"), _make_holding("BTC")]

    to_add, to_remove = _build_sync_ops(
        holdings=holdings,
        strategies=[strategy],
        open_position_symbols=set(),
    )

    assert "QUBIC/USDT" in to_add
    assert "BTC/USDT" not in to_add  # already watched


def test_held_asset_already_in_strategy_not_duplicated():
    """If a holding is already in the strategy, nothing changes."""
    from app.tasks.sync_portfolio_symbols import _build_sync_ops

    strategy = _make_strategy(["BTC/USDT", "QUBIC/USDT"])
    holdings = [_make_holding("QUBIC")]

    to_add, to_remove = _build_sync_ops(
        holdings=holdings,
        strategies=[strategy],
        open_position_symbols=set(),
    )

    assert "QUBIC/USDT" not in to_add


def test_not_held_symbol_never_auto_removed():
    """Add-only policy: a watched symbol not in holdings is NOT removed automatically.
    Removal requires explicit user action — we cannot reliably verify all holdings
    (hardware wallets, unsupported exchanges, failed API calls).
    """
    from app.tasks.sync_portfolio_symbols import _build_sync_ops

    strategy = _make_strategy(["BTC/USDT", "QUBIC/USDT"])
    holdings = [_make_holding("BTC")]  # QUBIC not in API balances

    to_add, to_remove = _build_sync_ops(
        holdings=holdings,
        strategies=[strategy],
        open_position_symbols=set(),
    )

    # QUBIC stays in watchlist even though we can't confirm the balance via API
    assert "QUBIC/USDT" not in to_remove
    assert to_remove == []


# ---------------------------------------------------------------------------
# Symbol normalisation: "QUBIC" -> "QUBIC/USDT"
# ---------------------------------------------------------------------------


def test_holding_symbol_normalised_to_usdt_pair():
    """ManualHolding.symbol is a bare ticker — must be normalised to EXCHANGE pair."""
    from app.tasks.sync_portfolio_symbols import _normalise_symbol

    assert _normalise_symbol("QUBIC") == "QUBIC/USDT"
    assert _normalise_symbol("BTC") == "BTC/USDT"
    assert _normalise_symbol("ETH/USDT") == "ETH/USDT"   # already normalised
    assert _normalise_symbol("eth/usdt") == "ETH/USDT"   # lowercase handled


def test_xbt_alias_resolved_to_btc():
    """XBT (Kraken's BTC ticker) should normalise to BTC/USDT, not XBT/USDT."""
    from app.tasks.sync_portfolio_symbols import _normalise_symbol

    assert _normalise_symbol("XBT") == "BTC/USDT"
    assert _normalise_symbol("XBT/USDT") == "BTC/USDT"


def test_kfee_is_not_excluded():
    """KFEE (Kraken fee token) is a real exchange token — it must NOT be filtered out."""
    from app.tasks.sync_portfolio_symbols import _build_sync_ops

    strategy = _make_strategy([])
    holdings = [_make_holding("KFEE")]

    to_add, _ = _build_sync_ops(
        holdings=holdings,
        strategies=[strategy],
        open_position_symbols=set(),
    )

    assert "KFEE/USDT" in to_add


def test_stablecoin_holdings_skipped():
    """USDT/USDC holdings should not be added as trading pairs."""
    from app.tasks.sync_portfolio_symbols import _build_sync_ops

    strategy = _make_strategy(["BTC/USDT"])
    holdings = [
        _make_holding("USDT"),
        _make_holding("USDC"),
        _make_holding("BTC"),
    ]

    to_add, _ = _build_sync_ops(
        holdings=holdings,
        strategies=[strategy],
        open_position_symbols=set(),
    )

    assert "USDT/USDT" not in to_add
    assert "USDC/USDT" not in to_add


# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------


def test_task_skips_when_feature_disabled():
    """Task exits early when portfolio_symbol_sync_enabled=False."""
    import asyncio

    from app.tasks.sync_portfolio_symbols import _sync_portfolio_async

    with patch("app.tasks.sync_portfolio_symbols.settings") as mock_settings:
        mock_settings.portfolio_symbol_sync_enabled = False
        asyncio.run(_sync_portfolio_async())


# ---------------------------------------------------------------------------
# Exchange holdings are included in sync
# ---------------------------------------------------------------------------


def test_exchange_holdings_included_in_sync_ops():
    """Holdings from live exchange connections must be treated the same as manual."""
    from app.tasks.sync_portfolio_symbols import _ExchangeHolding, _build_sync_ops

    strategy = _make_strategy(["BTC/USDT"])
    exchange_holding = _ExchangeHolding(symbol="RENDER", quantity=50.0)

    to_add, _ = _build_sync_ops(
        holdings=[exchange_holding],
        strategies=[strategy],
        open_position_symbols=set(),
    )

    assert "RENDER/USDT" in to_add


def test_fetch_all_exchange_holdings_aggregates_connections():
    """_fetch_all_exchange_holdings calls CCXTAdapter for each broker connection."""
    import asyncio

    from app.tasks.sync_portfolio_symbols import _fetch_all_exchange_holdings

    mock_conn = MagicMock()
    mock_conn.broker = "binance"
    mock_conn.api_key_enc = "enc_key"
    mock_conn.api_secret_enc = "enc_secret"
    mock_conn.api_passphrase_enc = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_conn]
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_adapter = MagicMock()
    mock_adapter.get_full_balance = AsyncMock(return_value={"RENDER": 50.0, "BTC": 0.5})
    mock_adapter.close = AsyncMock()

    with (
        patch("app.tasks.sync_portfolio_symbols.decrypt_value", return_value="decrypted"),
        patch("app.tasks.sync_portfolio_symbols.CCXTAdapter", return_value=mock_adapter),
    ):
        holdings = asyncio.run(_fetch_all_exchange_holdings(mock_db))

    symbols = {h.symbol for h in holdings}
    assert "RENDER" in symbols
    assert "BTC" in symbols


# ---------------------------------------------------------------------------
# Synthetic portfolio positions — pipeline protection
# ---------------------------------------------------------------------------


def test_synthetic_position_created_for_held_symbol():
    """Held symbol without an open BUY position must get a synthetic one created."""
    import asyncio

    from app.tasks.sync_portfolio_symbols import _sync_portfolio_positions

    mock_db = AsyncMock()

    # No existing open positions
    open_result = MagicMock()
    open_result.scalars.return_value.all.return_value = []

    # Latest candle close = 42.0
    candle_result = MagicMock()
    candle_result.first.return_value = (42.0,)

    mock_db.execute = AsyncMock(side_effect=[open_result, candle_result])

    asyncio.run(_sync_portfolio_positions(
        db=mock_db,
        user_id="00000000-0000-0000-0000-000000000001",
        strategy_id="00000000-0000-0000-0000-000000000002",
        held_symbols={"PEPE/USDT"},
        primary_timeframe="4h",
    ))

    # A Position object must have been added to the session
    mock_db.add.assert_called_once()
    added = mock_db.add.call_args[0][0]
    from app.models.position import Position
    assert isinstance(added, Position)
    assert added.symbol == "PEPE/USDT"
    assert added.direction == "BUY"
    assert added.broker == "portfolio_sync"
    assert added.entry_price == 42.0
    assert added.is_open is True


def test_synthetic_position_not_created_when_open_buy_exists():
    """If a real open BUY position already exists, no synthetic position is created."""
    import asyncio

    from app.tasks.sync_portfolio_symbols import _sync_portfolio_positions

    mock_db = AsyncMock()

    existing_pos = MagicMock()
    existing_pos.symbol = "PEPE/USDT"
    existing_pos.direction = "BUY"
    existing_pos.broker = "paper"  # real pipeline position, not synthetic
    existing_pos.is_open = True

    open_result = MagicMock()
    open_result.scalars.return_value.all.return_value = [existing_pos]
    mock_db.execute = AsyncMock(return_value=open_result)

    asyncio.run(_sync_portfolio_positions(
        db=mock_db,
        user_id="00000000-0000-0000-0000-000000000001",
        strategy_id="00000000-0000-0000-0000-000000000002",
        held_symbols={"PEPE/USDT"},
        primary_timeframe="4h",
    ))

    mock_db.add.assert_not_called()


def test_synthetic_position_closed_when_holding_gone():
    """A synthetic position for a symbol no longer held must be closed."""
    import asyncio
    from datetime import timezone

    from app.tasks.sync_portfolio_symbols import _sync_portfolio_positions

    mock_db = AsyncMock()

    existing_syn = MagicMock()
    existing_syn.symbol = "PEPE/USDT"
    existing_syn.direction = "BUY"
    existing_syn.broker = "portfolio_sync"
    existing_syn.is_open = True
    existing_syn.closed_at = None

    open_result = MagicMock()
    open_result.scalars.return_value.all.return_value = [existing_syn]
    mock_db.execute = AsyncMock(return_value=open_result)

    asyncio.run(_sync_portfolio_positions(
        db=mock_db,
        user_id="00000000-0000-0000-0000-000000000001",
        strategy_id="00000000-0000-0000-0000-000000000002",
        held_symbols=set(),  # PEPE no longer held
        primary_timeframe="4h",
    ))

    assert existing_syn.is_open is False
    assert existing_syn.closed_at is not None


def test_fetch_all_exchange_holdings_ignores_failed_connections():
    """If one exchange fails, others still succeed."""
    import asyncio

    from app.tasks.sync_portfolio_symbols import _fetch_all_exchange_holdings

    mock_conn_ok = MagicMock()
    mock_conn_ok.broker = "binance"
    mock_conn_ok.api_key_enc = "enc"
    mock_conn_ok.api_secret_enc = "enc"
    mock_conn_ok.api_passphrase_enc = None

    mock_conn_bad = MagicMock()
    mock_conn_bad.broker = "broken_exchange"
    mock_conn_bad.api_key_enc = "enc"
    mock_conn_bad.api_secret_enc = "enc"
    mock_conn_bad.api_passphrase_enc = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_conn_ok, mock_conn_bad]
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    call_count = 0

    def adapter_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        if call_count == 1:
            m.get_full_balance = AsyncMock(return_value={"ETH": 1.0})
            m.close = AsyncMock()
        else:
            m.get_full_balance = AsyncMock(side_effect=Exception("auth error"))
            m.close = AsyncMock()
        return m

    with (
        patch("app.tasks.sync_portfolio_symbols.decrypt_value", return_value="decrypted"),
        patch("app.tasks.sync_portfolio_symbols.CCXTAdapter", side_effect=adapter_factory),
    ):
        holdings = asyncio.run(_fetch_all_exchange_holdings(mock_db))

    assert any(h.symbol == "ETH" for h in holdings)
