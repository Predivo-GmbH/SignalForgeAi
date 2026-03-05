"""Minimum notional value enforcement per exchange.

Exchanges reject orders below their minimum notional (price × quantity).
This module provides conservative static floors so that the system never
generates signals or orders that would be instantly rejected — including
paper trades, which should be realistic.

Values sourced from exchange documentation (March 2026).
"""

import logging

logger = logging.getLogger(__name__)

# Conservative minimum notional values in USDT/USD per exchange.
# These are the *lowest common floor* for USDT-quoted spot pairs.
# Per-pair limits may be higher (e.g. Binance BTC/USDT = 10 USDT),
# but using the exchange-wide floor as a safe baseline.
EXCHANGE_MIN_NOTIONAL: dict[str, float] = {
    "binance": 5.0,
    "kraken": 0.5,
    "mexc": 1.0,
    "kucoin": 0.1,
    "cryptocom": 1.0,
    "gateio": 10.0,   # API orders require 10 USDT
    "coinbase": 1.0,
    "bybit": 1.0,
    "okx": 1.0,
    "htx": 5.0,
    "bitfinex": 5.0,
    "bitstamp": 5.0,
}

# When we can't determine the exchange, use the highest floor across all
# exchanges so we never produce an order any exchange would reject.
SAFE_MIN_NOTIONAL = max(EXCHANGE_MIN_NOTIONAL.values())  # 10.0 (Gate.io API)


def get_min_notional(exchange: str | None) -> float:
    """Return the minimum notional value (in USDT) for a given exchange.

    If the exchange is unknown or None, returns the most conservative
    (highest) minimum across all exchanges.
    """
    if exchange:
        return EXCHANGE_MIN_NOTIONAL.get(exchange.lower(), SAFE_MIN_NOTIONAL)
    return SAFE_MIN_NOTIONAL


def check_min_notional(
    *,
    symbol: str,
    quantity: float,
    price: float,
    exchange: str | None,
) -> tuple[bool, float, float]:
    """Check whether an order meets the exchange's minimum notional.

    Returns:
        (passes, notional_value, min_required)
    """
    notional = price * quantity
    minimum = get_min_notional(exchange)
    passes = notional >= minimum
    if not passes:
        logger.info(
            "Min notional REJECT: %s on %s — notional $%.4f < minimum $%.2f "
            "(price=%.8f, qty=%.8f)",
            symbol, exchange or "unknown", notional, minimum, price, quantity,
        )
    return passes, notional, minimum


def resolve_exchange_for_symbol(
    symbol: str,
    strategy_config: dict | None,
) -> str | None:
    """Determine which exchange a symbol targets from its strategy config.

    Returns the exchange name from ``exchange_map``, or None if the symbol
    has no explicit mapping. There is no global default — each symbol must
    be mapped to its source exchange.
    """
    if strategy_config:
        exchange_map = strategy_config.get("exchange_map", {})
        if symbol in exchange_map:
            return exchange_map[symbol]
    return None
