"""Market scanner — discovers and ranks top crypto pairs by volume."""

import logging

import ccxt
import pandas as pd

logger = logging.getLogger(__name__)

# Stablecoins and wrapped tokens to exclude from scanning
EXCLUDE_QUOTES = {"USDC", "BUSD", "TUSD", "DAI", "FDUSD", "USDP", "UST"}
EXCLUDE_BASES = {"USDC", "BUSD", "TUSD", "DAI", "FDUSD", "USDP", "UST", "WBTC", "WETH", "STETH"}


class MarketScanner:
    """Scans Binance for top crypto trading pairs by volume."""

    def __init__(self, exchange_id: str = "binance"):
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({"enableRateLimit": True})

    def scan_top_pairs(self, quote: str = "USDT", top_n: int = 50) -> list[dict]:
        """Fetch all USDT pairs, rank by 24h quote volume, return top N.

        Returns list of dicts:
            [{symbol, price, volume_24h, change_pct_24h, market_cap_rank}, ...]
        """
        logger.info("Loading markets from %s...", self.exchange.id)
        self.exchange.load_markets()

        # Filter for spot USDT pairs, exclude stablecoins
        usdt_symbols = []
        for symbol, market in self.exchange.markets.items():
            if (
                market.get("quote") == quote
                and market.get("spot", False)
                and market.get("active", True)
                and market.get("base") not in EXCLUDE_BASES
            ):
                usdt_symbols.append(symbol)

        logger.info("Found %d %s spot pairs, fetching tickers...", len(usdt_symbols), quote)

        # Fetch all tickers at once (single API call)
        tickers = self.exchange.fetch_tickers(usdt_symbols)

        pairs = []
        for symbol, ticker in tickers.items():
            quote_volume = ticker.get("quoteVolume") or 0
            if quote_volume < 1_000_000:  # Skip pairs with < $1M daily volume
                continue
            pairs.append({
                "symbol": symbol,
                "price": ticker.get("last") or 0,
                "volume_24h": quote_volume,
                "change_pct_24h": ticker.get("percentage") or 0,
            })

        # Sort by volume descending
        pairs.sort(key=lambda x: x["volume_24h"], reverse=True)

        # Add rank
        for i, p in enumerate(pairs[:top_n]):
            p["rank"] = i + 1

        result = pairs[:top_n]
        logger.info("Top %d pairs by volume (highest: %s at $%.0f vol)",
                     len(result),
                     result[0]["symbol"] if result else "N/A",
                     result[0]["volume_24h"] if result else 0)
        return result

    def fetch_candles_batch(
        self, symbols: list[str], timeframe: str = "1h", limit: int = 200,
    ) -> dict[str, pd.DataFrame]:
        """Fetch candles for multiple symbols.

        Returns dict mapping symbol -> OHLCV DataFrame.
        """
        result = {}
        for i, symbol in enumerate(symbols):
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                if not ohlcv:
                    continue
                df = pd.DataFrame(
                    ohlcv, columns=["time", "open", "high", "low", "close", "volume"],
                )
                df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
                result[symbol] = df
                if (i + 1) % 10 == 0:
                    logger.info("Fetched candles for %d/%d symbols...", i + 1, len(symbols))
            except Exception as e:
                logger.warning("Failed to fetch candles for %s: %s", symbol, e)
        logger.info("Fetched candles for %d/%d symbols", len(result), len(symbols))
        return result
