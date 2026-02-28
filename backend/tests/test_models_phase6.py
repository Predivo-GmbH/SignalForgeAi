"""Tests for Phase 6 database models (Order, Position, BacktestResult, User.alert_config).

Note: SQLAlchemy 2.0 ``mapped_column(default=...)`` only applies during INSERT
(server/session side), not on pure Python construction.  We verify column
defaults via ``__table__.c.<col>.default.arg`` and check explicit construction.
"""

from uuid import uuid4

from app.models.backtest_result import BacktestResult
from app.models.order import Order
from app.models.position import Position
from app.models.user import User


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
class TestOrderModel:
    def test_tablename(self):
        assert Order.__tablename__ == "orders"

    def test_column_defaults(self):
        """Verify the DB-level column defaults are configured correctly."""
        cols = Order.__table__.c
        assert cols.status.default.arg == "pending"
        assert cols.filled_quantity.default.arg == 0.0

    def test_explicit_construction(self):
        uid = uuid4()
        order = Order(
            user_id=uid,
            symbol="BTC/USDT",
            direction="BUY",
            order_type="limit",
            quantity=0.1,
            price=50000.0,
            broker="paper",
            status="pending",
            filled_quantity=0.0,
        )
        assert order.user_id == uid
        assert order.symbol == "BTC/USDT"
        assert order.direction == "BUY"
        assert order.order_type == "limit"
        assert order.quantity == 0.1
        assert order.price == 50000.0
        assert order.broker == "paper"
        assert order.status == "pending"
        assert order.filled_quantity == 0.0
        assert order.error_message is None
        assert order.broker_order_id is None

    def test_all_fields(self):
        uid = uuid4()
        sid = uuid4()
        order = Order(
            user_id=uid,
            signal_id=sid,
            symbol="ETH/USDT",
            direction="SELL",
            order_type="market",
            quantity=1.5,
            price=None,
            stop_loss=2800.0,
            take_profit=3200.0,
            broker="alpaca",
            broker_order_id="alp-123",
            status="filled",
            filled_quantity=1.5,
            average_fill_price=3050.0,
        )
        assert order.signal_id == sid
        assert order.direction == "SELL"
        assert order.order_type == "market"
        assert order.price is None
        assert order.stop_loss == 2800.0
        assert order.take_profit == 3200.0
        assert order.broker_order_id == "alp-123"
        assert order.status == "filled"
        assert order.filled_quantity == 1.5
        assert order.average_fill_price == 3050.0

    def test_nullable_fields_default_none(self):
        order = Order(
            user_id=uuid4(),
            symbol="BTC/USDT",
            direction="BUY",
            order_type="market",
            quantity=1.0,
            broker="paper",
        )
        assert order.signal_id is None
        assert order.price is None
        assert order.average_fill_price is None
        assert order.stop_loss is None
        assert order.take_profit is None
        assert order.broker_order_id is None
        assert order.error_message is None


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------
class TestPositionModel:
    def test_tablename(self):
        assert Position.__tablename__ == "positions"

    def test_column_defaults(self):
        """Verify the DB-level column defaults are configured correctly."""
        cols = Position.__table__.c
        assert cols.is_open.default.arg is True
        assert cols.unrealized_pnl.default.arg == 0.0

    def test_explicit_construction(self):
        uid = uuid4()
        pos = Position(
            user_id=uid,
            symbol="BTC/USDT",
            direction="BUY",
            quantity=0.1,
            entry_price=50000.0,
            broker="paper",
            is_open=True,
            unrealized_pnl=0.0,
        )
        assert pos.user_id == uid
        assert pos.symbol == "BTC/USDT"
        assert pos.direction == "BUY"
        assert pos.quantity == 0.1
        assert pos.entry_price == 50000.0
        assert pos.broker == "paper"
        assert pos.is_open is True
        assert pos.unrealized_pnl == 0.0
        assert pos.closed_at is None
        assert pos.current_price is None

    def test_all_fields(self):
        uid = uuid4()
        oid = uuid4()
        pos = Position(
            user_id=uid,
            order_id=oid,
            symbol="SOL/USDT",
            direction="BUY",
            quantity=10.0,
            entry_price=150.0,
            current_price=155.0,
            stop_loss=140.0,
            take_profit=170.0,
            broker="ccxt",
            broker_position_id="ccxt-pos-456",
            is_open=True,
            unrealized_pnl=50.0,
        )
        assert pos.order_id == oid
        assert pos.current_price == 155.0
        assert pos.stop_loss == 140.0
        assert pos.take_profit == 170.0
        assert pos.broker_position_id == "ccxt-pos-456"
        assert pos.unrealized_pnl == 50.0

    def test_nullable_fields_default_none(self):
        pos = Position(
            user_id=uuid4(),
            symbol="BTC/USDT",
            direction="BUY",
            quantity=1.0,
            entry_price=50000.0,
            broker="paper",
        )
        assert pos.order_id is None
        assert pos.current_price is None
        assert pos.stop_loss is None
        assert pos.take_profit is None
        assert pos.broker_position_id is None
        assert pos.closed_at is None


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------
class TestBacktestResultModel:
    def test_tablename(self):
        assert BacktestResult.__tablename__ == "backtest_results"

    def test_column_default_trade_count(self):
        """Verify the DB-level trade_count default is configured."""
        cols = BacktestResult.__table__.c
        assert cols.trade_count.default.arg == 0

    def test_basic_fields(self):
        result = BacktestResult(
            user_id=uuid4(),
            symbol="BTC/USDT",
            timeframe="1h",
            days=30,
            metrics={"win_rate": 0.55, "sharpe": 1.2},
            trade_count=42,
        )
        assert result.metrics["win_rate"] == 0.55
        assert result.metrics["sharpe"] == 1.2
        assert result.trade_count == 42
        assert result.equity_curve is None

    def test_with_equity_curve(self):
        curve = [100.0, 102.5, 101.0, 105.0]
        result = BacktestResult(
            user_id=uuid4(),
            symbol="ETH/USDT",
            timeframe="4h",
            days=60,
            metrics={"total_return": 0.12},
            equity_curve=curve,
            trade_count=18,
            win_rate=0.62,
            sharpe_ratio=1.8,
            max_drawdown=-0.05,
            total_pnl=1200.0,
        )
        assert result.equity_curve == curve
        assert result.win_rate == 0.62
        assert result.sharpe_ratio == 1.8
        assert result.max_drawdown == -0.05
        assert result.total_pnl == 1200.0

    def test_with_strategy_id(self):
        sid = uuid4()
        result = BacktestResult(
            user_id=uuid4(),
            strategy_id=sid,
            symbol="BTC/USDT",
            timeframe="1d",
            days=90,
            metrics={"win_rate": 0.48},
            trade_count=0,
        )
        assert result.strategy_id == sid

    def test_nullable_fields_default_none(self):
        result = BacktestResult(
            user_id=uuid4(),
            symbol="BTC/USDT",
            timeframe="1h",
            days=30,
            metrics={},
        )
        assert result.strategy_id is None
        assert result.equity_curve is None
        assert result.win_rate is None
        assert result.sharpe_ratio is None
        assert result.max_drawdown is None
        assert result.total_pnl is None


# ---------------------------------------------------------------------------
# User.alert_config
# ---------------------------------------------------------------------------
class TestUserAlertConfig:
    def test_alert_config_default_none(self):
        user = User(
            email="test@example.com",
            password_hash="hashed",
        )
        assert user.alert_config is None

    def test_alert_config_with_data(self):
        config = {
            "email_enabled": True,
            "webhook_url": "https://hooks.example.com/alert",
            "min_confluence": 7,
        }
        user = User(
            email="test2@example.com",
            password_hash="hashed",
            alert_config=config,
        )
        assert user.alert_config == config
        assert user.alert_config["email_enabled"] is True
        assert user.alert_config["min_confluence"] == 7

    def test_alert_config_column_is_nullable(self):
        cols = User.__table__.c
        assert cols.alert_config.nullable is True
