"""
Layer 0: Regime Detector.

Determines current market regime using ADX (trend strength),
ATR percentile (volatility context), and optionally HMM (Hidden Markov Model)
for probabilistic regime classification.
Output: TRENDING, RANGING, TRANSITIONING, or CHAOTIC.
"""

import logging
from enum import Enum

import pandas as pd

from app.engine.indicators import compute_adx, compute_atr

logger = logging.getLogger(__name__)

try:
    from app.engine.layers.hmm_regime import HMMRegimeModel

    HAS_HMM = True
except ImportError:
    HAS_HMM = False


class Regime(Enum):
    TRENDING = "trending"
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGING = "ranging"
    TRANSITIONING = "transitioning"
    CHAOTIC = "chaotic"


# Map HMM state labels to Regime enums
_HMM_REGIME_MAP = {
    "trending": Regime.TRENDING,
    "low_vol": Regime.RANGING,
    "high_vol": Regime.CHAOTIC,
}


class RegimeDetector:
    """
    Layer 0: Determines current market regime using ADX + ATR percentile,
    enhanced with HMM probabilistic regime classification.
    Output: TRENDING, RANGING, TRANSITIONING, or CHAOTIC.
    """

    def __init__(self, use_hmm: bool = True):
        self.use_hmm = use_hmm and HAS_HMM
        self._hmm_model: "HMMRegimeModel | None" = None

    def detect(self, candles: pd.DataFrame) -> Regime:
        # Rule-based regime detection
        rule_regime = self._detect_rule_based(candles)

        # HMM-based regime detection (if available and enough data)
        if self.use_hmm and len(candles) >= 100:
            hmm_regime = self._detect_hmm(candles)
            if hmm_regime is not None:
                return self._fuse_regimes(rule_regime, hmm_regime, candles)

        return rule_regime

    def _detect_rule_based(self, candles: pd.DataFrame) -> Regime:
        adx = compute_adx(candles, period=14)
        adx_val = adx.dropna().iloc[-1] if len(adx.dropna()) > 0 else 0
        adx_regime = self._adx_regime(float(adx_val))

        atr_pct = self._atr_percentile(candles, lookback=100)

        # Chaotic: extreme volatility — requires both high ATR percentile
        # AND high ATR relative to price (normalized ATR > 3%).
        atr = compute_atr(candles, period=14)
        atr_clean = atr.dropna()
        price = float(candles["close"].iloc[-1])
        if len(atr_clean) > 0 and price > 0:
            normalized_atr = float(atr_clean.iloc[-1]) / price
        else:
            normalized_atr = 0.0

        if atr_pct > 90 and normalized_atr > 0.03:
            return Regime.CHAOTIC

        # Consensus between ADX and ATR
        if adx_regime == Regime.TRENDING:
            if atr_pct < 20:
                return Regime.TRANSITIONING
            return Regime.TRENDING
        elif adx_regime == Regime.RANGING:
            return Regime.RANGING
        else:
            return Regime.TRANSITIONING

    def _detect_hmm(self, candles: pd.DataFrame) -> Regime | None:
        """Run HMM regime detection. Returns None on failure."""
        try:
            if self._hmm_model is None:
                self._hmm_model = HMMRegimeModel(n_states=3)
            self._hmm_model.fit(candles)
            state_label = self._hmm_model.predict_current(candles)
            return _HMM_REGIME_MAP.get(state_label, Regime.TRANSITIONING)
        except Exception as e:
            logger.debug("HMM regime detection failed: %s", e)
            return None

    def _fuse_regimes(
        self, rule_regime: Regime, hmm_regime: Regime, candles: pd.DataFrame
    ) -> Regime:
        """Fuse rule-based and HMM regimes.

        The rule-based detector is always the primary authority because it has
        strict, interpretable criteria (ADX thresholds, ATR percentiles).
        The HMM provides probabilistic confirmation — it can upgrade confidence
        but never overrides the rule-based result downward.
        """
        # Both agree → high confidence, use rule-based result
        if rule_regime == hmm_regime:
            return rule_regime

        # Rule-based says CHAOTIC → trust it (strict dual criteria)
        if rule_regime == Regime.CHAOTIC:
            return Regime.CHAOTIC

        # Rule-based is always primary — return its result.
        # The HMM disagreement is logged for monitoring but doesn't change outcome.
        if hmm_regime != rule_regime:
            logger.debug(
                "HMM disagrees: rule=%s hmm=%s (using rule-based)",
                rule_regime.value, hmm_regime.value,
            )

        return rule_regime

    def _adx_regime(self, adx_value: float) -> Regime:
        if adx_value > 25:
            return Regime.TRENDING
        elif adx_value < 20:
            return Regime.RANGING
        else:
            return Regime.TRANSITIONING

    def _atr_percentile(self, candles: pd.DataFrame, lookback: int = 100) -> float:
        atr = compute_atr(candles, period=14)
        atr_clean = atr.dropna()
        if len(atr_clean) < 2:
            return 50.0
        tail = atr_clean.tail(lookback)
        current = tail.iloc[-1]
        percentile = float((tail < current).mean() * 100)
        return percentile
