"""Tests for broker adapters and router."""

import pytest

from app.execution.adapters.base import OrderSide, OrderStatus, OrderType
from app.execution.adapters.paper import PaperAdapter
from app.execution.broker_router import BrokerRouter, is_crypto_symbol


@pytest.mark.asyncio
async def test_paper_adapter_place_order():
    adapter = PaperAdapter()
    order = await adapter.place_order(
        "BTC/USDT", OrderSide.BUY, OrderType.LIMIT, 0.1, 50000.0
    )
    assert order.status == OrderStatus.FILLED
    assert order.broker == "paper"
    assert order.filled_quantity == 0.1
    assert order.average_fill_price is not None


@pytest.mark.asyncio
async def test_paper_adapter_slippage():
    adapter = PaperAdapter(slippage_pct=0.01)  # 1%
    order = await adapter.place_order(
        "BTC/USDT", OrderSide.BUY, OrderType.LIMIT, 1.0, 100.0
    )
    assert order.average_fill_price == pytest.approx(101.0, rel=0.01)


@pytest.mark.asyncio
async def test_paper_adapter_cancel():
    adapter = PaperAdapter()
    order = await adapter.place_order(
        "BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1, 50000.0
    )
    cancelled = await adapter.cancel_order(order.broker_order_id)
    assert cancelled is True
    status = await adapter.get_order_status(order.broker_order_id)
    assert status.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_paper_adapter_connect():
    adapter = PaperAdapter()
    assert await adapter.connect() is True


@pytest.mark.asyncio
async def test_paper_adapter_balance():
    adapter = PaperAdapter(initial_equity=25000.0)
    balance = await adapter.get_balance()
    assert balance.equity == 25000.0


def test_is_crypto_symbol():
    assert is_crypto_symbol("BTC/USDT") is True
    assert is_crypto_symbol("ETH/BTC") is True
    assert is_crypto_symbol("SPY") is False
    assert is_crypto_symbol("EUR/USD") is False
    assert is_crypto_symbol("AAPL") is False


@pytest.mark.asyncio
async def test_broker_router_paper_mode():
    paper = PaperAdapter()
    router = BrokerRouter(paper_adapter=paper)
    order = await router.place_order(
        "BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1, 50000.0
    )
    assert order.broker == "paper"


@pytest.mark.asyncio
async def test_broker_router_routes_crypto():
    paper_stock = PaperAdapter()
    paper_crypto = PaperAdapter()
    router = BrokerRouter(stock_adapter=paper_stock, crypto_adapter=paper_crypto)
    order = await router.place_order(
        "BTC/USDT", OrderSide.BUY, OrderType.MARKET, 0.1, 50000.0
    )
    assert order.status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_broker_router_no_adapter_raises():
    router = BrokerRouter()
    with pytest.raises(ValueError, match="No stock adapter"):
        await router.place_order("SPY", OrderSide.BUY, OrderType.MARKET, 10, 400.0)
