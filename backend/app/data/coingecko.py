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

# Manual overrides for top coins whose symbols collide with shorter CoinGecko IDs.
# Without these, e.g. "BTC" might resolve to a lesser-known coin instead of "bitcoin".
_SYMBOL_OVERRIDES: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "POL": "matic-network",
    "LINK": "chainlink",
    "SHIB": "shiba-inu",
    "LTC": "litecoin",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "FIL": "filecoin",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "TAO": "bittensor",
    "RENDER": "render-token",
    "FET": "fetch-ai",
    "INJ": "injective-protocol",
    "SUI": "sui",
    "SEI": "sei-network",
    "TIA": "celestia",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "FLOKI": "floki",
    "CRO": "crypto-com-chain",
    "ALGO": "algorand",
    "VET": "vechain",
    "HBAR": "hedera-hashgraph",
    "ICP": "internet-computer",
    "GRT": "the-graph",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AAVE": "aave",
    "MKR": "maker",
    "SNX": "havven",
    "COMP": "compound-governance-token",
    "CRV": "curve-dao-token",
    "LDO": "lido-dao",
    "RPL": "rocket-pool",
    "IMX": "immutable-x",
    "RNDR": "render-token",
    "FTM": "fantom",
    "RUNE": "thorchain",
    "EGLD": "elrond-erd-2",
    "THETA": "theta-token",
    "AXS": "axie-infinity",
    "GALA": "gala",
    "ENS": "ethereum-name-service",
    "CAKE": "pancakeswap-token",
    "1INCH": "1inch",
    "JASMY": "jasmycoin",
    "TRX": "tron",
    "TON": "the-open-network",
    "KAS": "kaspa",
    "STX": "blockstack",
    "PENDLE": "pendle",
    "JUP": "jupiter-exchange-solana",
    "W": "wormhole",
    "ENA": "ethena",
    "STRK": "starknet",
    "ALPH": "alephium",
    "QUBIC": "qubic-network",
    "RIO": "realio-network",
    "ORAI": "oraichain-token",
    "ZEPH": "zephyr-protocol",
    "ABX": "alphbanx",
    "APAD": "alphpad",
    "EX": "elexium",
    "AYIN": "ayin",
}


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

        # Apply manual overrides for well-known coins
        mapping.update(_SYMBOL_OVERRIDES)

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


# ---------- Coin metadata (market cap, rank, image, volume) ----------

_metadata_cache: dict[str, dict] = {}
_metadata_cache_ts: float = 0
_METADATA_CACHE_TTL = 300  # 5 minutes


async def fetch_coin_metadata(
    symbols: list[str],
) -> dict[str, dict]:
    """Fetch coin metadata from CoinGecko /coins/markets endpoint.

    Returns {SYMBOL: {"market_cap": int, "market_cap_rank": int,
    "volume_24h": float, "image_url": str}}.
    Uses 5-minute in-memory cache.
    """
    global _metadata_cache, _metadata_cache_ts

    if _metadata_cache and (time.time() - _metadata_cache_ts) < _METADATA_CACHE_TTL:
        # Return cached entries for requested symbols
        return {s: _metadata_cache[s] for s in symbols if s in _metadata_cache}

    coin_map = await _ensure_coin_map()

    sym_to_id: dict[str, str] = {}
    for s in symbols:
        upper = s.upper()
        cg_id = coin_map.get(upper)
        if cg_id:
            sym_to_id[upper] = cg_id

    if not sym_to_id:
        return {}

    ids_csv = ",".join(sym_to_id.values())
    url = (
        f"{_BASE}/coins/markets?vs_currency=usd&ids={ids_csv}"
        f"&order=market_cap_desc&per_page=250&page=1&sparkline=false"
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        id_to_sym = {v: k for k, v in sym_to_id.items()}
        result: dict[str, dict] = {}
        for coin in data:
            sym = id_to_sym.get(coin.get("id", ""))
            if not sym:
                continue
            result[sym] = {
                "market_cap": coin.get("market_cap"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "volume_24h": coin.get("total_volume"),
                "image_url": coin.get("image"),  # 200px icon URL
            }

        _metadata_cache = result
        _metadata_cache_ts = time.time()
        logger.debug("CoinGecko metadata cached for %d coins", len(result))
        return result
    except Exception:
        logger.debug("CoinGecko metadata fetch failed")
        # Return stale cache if available
        return {s: _metadata_cache[s] for s in symbols if s in _metadata_cache}


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
