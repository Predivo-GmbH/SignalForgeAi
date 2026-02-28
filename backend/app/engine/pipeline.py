"""
SignalPipeline: Orchestrates all 6 layers to produce a trade signal.

Pipeline flow:
  Layer 0: RegimeDetector   -> CHAOTIC blocks
  Layer 1: TrendFilter      -> UNDETERMINED blocks
  Layer 2: ZoneIdentifier   -> no zones blocks
  Layer 3: ConfluenceScorer -> score < 50 blocks
  Layer 4: TriggerDetector  -> not confirmed blocks
  Layer 5: RiskManager      -> rejected blocks
  -> Output: Signal with action BUY/SELL/NO_TRADE
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from app.engine.layers.confluence import ConfluenceScorer
from app.engine.layers.regime import Regime, RegimeDetector
from app.engine.layers.risk import RiskCalc, RiskConfig, RiskManager
from app.engine.layers.trend import Trend, TrendFilter
from app.engine.layers.triggers import TriggerDetector
from app.engine.layers.zones import ZoneIdentifier


@dataclass
class Signal:
    """Output of the signal pipeline — contains all trade metadata."""

    symbol: str
    timeframe: str
    action: str  # "BUY", "SELL", "NO_TRADE"
    regime: str
    trend_direction: str
    trend_strength: float
    zone: dict | None
    confluence_score: int
    triggers: list[str]
    stop_loss: float | None
    take_profit_1: float | None
    take_profit_2: float | None
    position_size: float | None
    risk_reward: float | None
    block_reason: str | None
    timestamp: str  # ISO format


class SignalPipeline:
    """
    Orchestrates Layers 0-5 to evaluate candle data and produce
    a Signal with action BUY, SELL, or NO_TRADE.
    """

    def __init__(
        self,
        risk_config: RiskConfig | None = None,
        min_confluence: int = 50,
    ):
        self.regime_detector = RegimeDetector()
        self.trend_filter = TrendFilter()
        self.zone_identifier = ZoneIdentifier()
        self.confluence_scorer = ConfluenceScorer()
        self.trigger_detector = TriggerDetector()
        self.risk_manager = RiskManager(config=risk_config)
        self.min_confluence = min_confluence

    def process(
        self,
        symbol: str,
        timeframe: str,
        candles: pd.DataFrame,
        account_equity: float = 10000,
    ) -> Signal:
        """
        Run the full pipeline on candle data and return a Signal.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT").
            timeframe: Candle timeframe (e.g., "1h", "4h").
            candles: OHLCV DataFrame.
            account_equity: Account balance for position sizing.

        Returns:
            Signal with action and all supporting metadata.
        """
        now = datetime.now(timezone.utc).isoformat()

        # Layer 0: Regime detection
        regime = self.regime_detector.detect(candles)
        if regime == Regime.CHAOTIC:
            return self._no_trade(
                symbol, timeframe, regime.value, "chaotic_regime", now
            )

        # Layer 1: Trend filter
        trend = self.trend_filter.evaluate(candles)
        if trend.direction == Trend.UNDETERMINED:
            return self._no_trade(
                symbol, timeframe, regime.value, "no_trend", now,
                trend_direction=trend.direction.value,
                trend_strength=trend.strength,
            )

        # Layer 2: Zone identification
        zones = self.zone_identifier.find_zones(candles, trend)
        if not zones:
            return self._no_trade(
                symbol, timeframe, regime.value, "no_zones", now,
                trend_direction=trend.direction.value,
                trend_strength=trend.strength,
            )

        # Evaluate each zone through Layers 3-5, pick the best
        best_signal: Signal | None = None
        best_score = -1
        last_block_reason = "no_zones"

        for zone in zones:
            # Layer 3: Confluence scoring
            confluence_score = self.confluence_scorer.score(zone, candles, trend)
            if confluence_score < self.min_confluence:
                last_block_reason = "low_confluence"
                continue

            # Layer 4: Trigger detection
            trigger = self.trigger_detector.check(candles, zone, trend)
            if not trigger.confirmed:
                last_block_reason = "no_trigger"
                continue

            # Layer 5: Risk management
            risk = self.risk_manager.calculate(
                candles, zone, trend, confluence_score, account_equity
            )
            if risk.rejected:
                last_block_reason = f"risk_rejected:{risk.reject_reason}"
                continue

            # Valid signal found — track the best by confluence score
            if confluence_score > best_score:
                best_score = confluence_score
                action = "BUY" if trend.direction == Trend.BULLISH else "SELL"
                best_signal = Signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    action=action,
                    regime=regime.value,
                    trend_direction=trend.direction.value,
                    trend_strength=trend.strength,
                    zone=zone.to_dict(),
                    confluence_score=confluence_score,
                    triggers=trigger.confirmations,
                    stop_loss=risk.stop_loss,
                    take_profit_1=risk.take_profit_1,
                    take_profit_2=risk.take_profit_2,
                    position_size=risk.position_size,
                    risk_reward=risk.risk_reward,
                    block_reason=None,
                    timestamp=now,
                )

        if best_signal is not None:
            return best_signal

        # No zone passed all layers
        return self._no_trade(
            symbol, timeframe, regime.value, last_block_reason, now,
            trend_direction=trend.direction.value,
            trend_strength=trend.strength,
        )

    @staticmethod
    def _no_trade(
        symbol: str,
        timeframe: str,
        regime: str,
        block_reason: str,
        timestamp: str,
        trend_direction: str = "undetermined",
        trend_strength: float = 0.0,
    ) -> Signal:
        """Create a NO_TRADE signal with the given block reason."""
        return Signal(
            symbol=symbol,
            timeframe=timeframe,
            action="NO_TRADE",
            regime=regime,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            zone=None,
            confluence_score=0,
            triggers=[],
            stop_loss=None,
            take_profit_1=None,
            take_profit_2=None,
            position_size=None,
            risk_reward=None,
            block_reason=block_reason,
            timestamp=timestamp,
        )
