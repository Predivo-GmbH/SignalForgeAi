"""CoinGecko API utilities — universal fallback for prices and OHLC candles.

Covers virtually every listed cryptocurrency, used as final fallback when
exchange-specific CCXT lookups fail.
"""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.coingecko.com/api/v3"
_TIMEOUT = 15.0

# ---------- Cached coin-list (symbol → CoinGecko ID) ----------

_coin_map: dict[str, str] = {}
_coin_map_ts: float = 0
_CACHE_TTL = 3600 * 6  # 6 hours


async def _ensure_coin_map() -> dict[str, str]:
    """Fetch and cache the CoinGecko coins list (symbol → id)."""
    global _coin_map, _coin_map_ts

    if _coin_map and (time.time() - _coin_map_ts) < _CACHE_TTL:
        return _coin_map

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_BASE}/coins/list")
            resp.raise_for_status()
            data = resp.json()

        mapping: dict[str, str] = {}
        for coin in data:
            sym = coin["symbol"].upper()
            cg_id = coin["id"]
            # For duplicate symbols, prefer shorter IDs (tends to be the
            # primary/popular coin, e.g. "bitcoin" over "bitcoin-wrapped")
            if sym not in mapping or len(cg_id) < len(mapping[sym]):
                mapping[sym] = cg_id

        _coin_map = mapping
        _coin_map_ts = time.time()
        logger.debug("CoinGecko coin map loaded: %d entries", len(mapping))
    except Exception:
        logger.debug("Failed to fetch CoinGecko coin list")

    return _coin_map


# ---------- Price lookup ----------


async def fetch_prices(
    symbols: list[str],
) -> dict[str, dict[str, float | None]]:
    """Fetch current USD prices + 24h change from CoinGecko.

    Returns {SYMBOL: {"price": float, "change_24h_pct": float}}.
    Only includes symbols that were resolved successfully.
    """
    coin_map = await _ensure_coin_map()
    result: dict[str, dict[str, float | None]] = {}

    # Map symbols to CoinGecko IDs
    sym_to_id: dict[str, str] = {}
    for s in symbols:
        upper = s.upper()
        cg_id = coin_map.get(upper)
        if cg_id:
            sym_to_id[upper] = cg_id

    if not sym_to_id:
        return result

    ids_csv = ",".join(sym_to_id.values())
    url = f"{_BASE}/simple/price?ids={ids_csv}&vs_currencies=usd&include_24hr_change=true"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        id_to_sym = {v: k for k, v in sym_to_id.items()}
        for cg_id, info in data.items():
            sym = id_to_sym.get(cg_id)
            if sym and info.get("usd"):
                result[sym] = {
                    "price": float(info["usd"]),
                    "change_24h_pct": float(info.get("usd_24h_change") or 0),
                }
    except Exception:
        logger.debug("CoinGecko price fetch failed for %s", ids_csv)

    return result


# ---------- OHLC candle lookup ----------

# Map our timeframes to CoinGecko `days` parameter:
#   days=1  → 30-min candles (~48 candles)
#   days=7  → 4h candles    (~42 candles)
#   days=30 → 4h candles    (~180 candles)
#   days=90 → daily candles (~90 candles)
_TF_TO_DAYS = {
    "1m": 1,
    "5m": 1,
    "15m": 1,
    "1h": 1,
    "4h": 30,
    "1d": 90,
}


async def fetch_ohlc(
    symbol: str,
    timeframe: str = "1d",
) -> list[dict]:
    """Fetch OHLC candle data from CoinGecko for a single symbol.

    Returns list of {"time": str, "open": float, "high": float,
    "low": float, "close": float, "volume": 0} dicts.
    """
    coin_map = await _ensure_coin_map()
    upper = symbol.upper()
    cg_id = coin_map.get(upper)
    if not cg_id:
        return []

    days = _TF_TO_DAYS.get(timeframe, 30)
    url = f"{_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return []

        from datetime import datetime, timezone

        return [
            {
                "time": datetime.fromtimestamp(
                    entry[0] / 1000, tz=timezone.utc
                ).isoformat(),
                "open": entry[1],
                "high": entry[2],
                "low": entry[3],
                "close": entry[4],
                "volume": 0,
            }
            for entry in data
            if len(entry) >= 5
        ]
    except Exception:
        logger.debug("CoinGecko OHLC fetch failed for %s (%s)", symbol, cg_id)
        return []
