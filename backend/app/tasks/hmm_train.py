"""Weekly HMM model retraining task."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)

MIN_CANDLES_FOR_REAL_DATA = 100


@celery_app.task(name="train_hmm_regime", bind=True, max_retries=2)
def train_hmm_regime(self, symbol: str = "BTC/USDT", timeframe: str = "1h"):
    """Retrain HMM regime model on latest data and cache in Redis.

    Tries to load real candle data from the database first.
    Falls back to synthetic data if fewer than MIN_CANDLES_FOR_REAL_DATA candles
    are available.
    """
    import asyncio

    try:
        return asyncio.run(_train_async(symbol, timeframe))
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("train_hmm_regime transient error: %s — retrying", exc)
        self.retry(exc=exc, countdown=300)


async def _train_async(symbol: str, timeframe: str) -> dict:
    import numpy as np
    import pandas as pd

    from app.config import settings
    from app.core.database import task_session
    from app.core.redis_client import redis_client
    from app.data.storage import CandleStorage
    from app.engine.layers.hmm_regime import HMMRegimeModel

    # --- Try real candle data from DB ---
    df: pd.DataFrame | None = None
    data_source = "synthetic"

    try:
        async with task_session() as db:
            candles_data = await CandleStorage.load_candles_db(
                db, symbol, timeframe, limit=2000,
            )
            if len(candles_data) >= MIN_CANDLES_FOR_REAL_DATA:
                df = pd.DataFrame(candles_data)
                df = df.set_index(pd.DatetimeIndex(df["time"]))
                df = df[["open", "high", "low", "close", "volume"]].astype(float)
                data_source = "database"
                logger.info(
                    "Using %d real candles from DB for HMM training (%s %s)",
                    len(df), symbol, timeframe,
                )
            else:
                logger.info(
                    "Only %d candles in DB for %s %s (need %d) — using synthetic data",
                    len(candles_data), symbol, timeframe, MIN_CANDLES_FOR_REAL_DATA,
                )
    except Exception:
        logger.exception("Failed to load candles from DB — falling back to synthetic data")

    # --- Fallback: generate synthetic data ---
    if df is None:
        np.random.seed(None)
        n = 2000
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h")
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        df = pd.DataFrame(
            {
                "open": close + np.random.randn(n) * 0.1,
                "high": close + abs(np.random.randn(n) * 0.3),
                "low": close - abs(np.random.randn(n) * 0.3),
                "close": close,
                "volume": np.random.randint(100, 10000, n).astype(float),
            },
            index=dates,
        )

    model = HMMRegimeModel(n_states=3)
    model.fit(df)

    await redis_client.set(f"signalforge:hmm_regime:{symbol}", model.serialize(), ex=7 * 86400)

    # Cache the current regime label for fast lookup by RegimeAllocator
    current_regime = model.predict_current(df)
    await redis_client.set(
        f"signalforge:hmm_regime_label:{symbol}",
        current_regime,
        ex=7 * 86400,
    )

    return {
        "status": "trained",
        "symbol": symbol,
        "timeframe": timeframe,
        "data_source": data_source,
        "candles_used": len(df),
        "current_regime": current_regime,
    }
