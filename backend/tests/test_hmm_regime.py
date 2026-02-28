import numpy as np
import pandas as pd

from app.engine.layers.hmm_regime import HMMRegimeModel


def _make_candles(n=500, seed=42):
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame(
        {
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.3),
            "low": close - abs(np.random.randn(n) * 0.3),
            "close": close,
            "volume": np.random.randint(100, 10000, n).astype(float),
        },
        index=dates,
    )


def test_hmm_fit_and_predict():
    df = _make_candles()
    model = HMMRegimeModel(n_states=3)
    model.fit(df)
    regime = model.predict_current(df)
    assert regime in ("low_vol", "trending", "high_vol")


def test_hmm_state_probabilities():
    df = _make_candles()
    model = HMMRegimeModel(n_states=3)
    model.fit(df)
    probs = model.state_probabilities(df)
    assert len(probs) == 3
    assert abs(sum(probs.values()) - 1.0) < 0.01


def test_hmm_serialize_deserialize():
    df = _make_candles()
    model = HMMRegimeModel(n_states=3)
    model.fit(df)
    data = model.serialize()
    restored = HMMRegimeModel.deserialize(data)
    regime = restored.predict_current(df)
    assert regime in ("low_vol", "trending", "high_vol")
