"""Weekly HMM model retraining task."""

from app.worker import celery_app


@celery_app.task(name="train_hmm_regime")
def train_hmm_regime(symbol: str = "BTC/USDT", timeframe: str = "1h"):
    """Retrain HMM regime model on latest data and cache in Redis."""
    import numpy as np
    import pandas as pd
    import redis

    from app.config import settings
    from app.engine.layers.hmm_regime import HMMRegimeModel

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

    r = redis.Redis.from_url(settings.redis_url)
    r.set(f"hmm_model:{symbol}:{timeframe}", model.serialize(), ex=7 * 86400)

    return {"status": "trained", "symbol": symbol, "timeframe": timeframe}
