"""HMM-based regime detection using Gaussian Hidden Markov Model."""

import pickle

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

from app.engine.indicators import compute_adx, compute_atr


class HMMRegimeModel:
    """3-state HMM for market regime classification."""

    STATE_LABELS = {0: "low_vol", 1: "trending", 2: "high_vol"}

    def __init__(self, n_states: int = 3):
        self.n_states = n_states
        self.model: GaussianHMM | None = None
        self._state_map: dict[int, str] = {}

    def _extract_features(self, candles: pd.DataFrame) -> np.ndarray:
        """Extract features: log returns, ATR/price ratio, ADX."""
        close = candles["close"].values
        log_returns = np.diff(np.log(close))
        atr = compute_atr(candles, period=14).values
        adx = compute_adx(candles, period=14).values

        min_len = min(len(log_returns), len(atr[~np.isnan(atr)]), len(adx[~np.isnan(adx)]))
        if min_len < 2:
            return np.zeros((2, 3))  # Fallback
        lr = log_returns[-min_len:].copy()
        atr_ratio = np.nan_to_num(atr[-min_len:].copy() / close[-min_len:], 0.0)
        adx_vals = np.nan_to_num(adx[-min_len:].copy(), 0.0)

        return np.column_stack([lr, atr_ratio, adx_vals])

    def fit(self, candles: pd.DataFrame) -> None:
        """Train the HMM on historical candle data."""
        features = self._extract_features(candles)
        self.model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=100,
            random_state=42,
        )
        self.model.fit(features)
        means = self.model.means_[:, 1]
        sorted_states = np.argsort(means)
        self._state_map = {
            int(sorted_states[0]): "low_vol",
            int(sorted_states[1]): "trending",
            int(sorted_states[2]): "high_vol",
        }

    def predict_current(self, candles: pd.DataFrame) -> str:
        if self.model is None:
            return "trending"
        features = self._extract_features(candles)
        states = self.model.predict(features)
        return self._state_map.get(int(states[-1]), "trending")

    def state_probabilities(self, candles: pd.DataFrame) -> dict[str, float]:
        if self.model is None:
            return {"low_vol": 0.33, "trending": 0.34, "high_vol": 0.33}
        features = self._extract_features(candles)
        probs = self.model.predict_proba(features)
        last_probs = probs[-1]
        return {
            self._state_map.get(i, f"state_{i}"): float(last_probs[i])
            for i in range(self.n_states)
        }

    def serialize(self) -> bytes:
        return pickle.dumps({"model": self.model, "state_map": self._state_map})

    @classmethod
    def deserialize(cls, data: bytes) -> "HMMRegimeModel":
        obj = pickle.loads(data)  # noqa: S301  # nosec B301
        instance = cls()
        instance.model = obj["model"]
        instance._state_map = obj["state_map"]
        return instance
