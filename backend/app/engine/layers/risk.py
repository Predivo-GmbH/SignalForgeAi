"""
Layer 5: Risk Manager.

Calculates position sizing, stop-loss, and take-profit levels
based on ATR, Fibonacci extensions, and confluence scoring.

Key rules:
  - ATR-based stop loss: entry +/- ATR x multiplier
  - Fibonacci extension take profits: 161.8% and 261.8%
  - Minimum risk:reward check — reject if below threshold
  - Position sizing scaled by confluence score (50->0.5x, 100->1.0x)
"""

from dataclasses import dataclass

import pandas as pd

from app.engine.indicators import compute_atr
from app.engine.layers.trend import Trend, TrendResult
from app.engine.layers.zones import EntryZone


@dataclass
class RiskConfig:
    max_risk_per_trade: float = 0.02  # 2% of equity
    max_daily_loss: float = 0.06  # 6% of equity
    atr_sl_multiplier: float = 2.0
    min_risk_reward: float = 1.5


@dataclass
class RiskCalc:
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    position_size: float
    risk_amount: float
    risk_reward: float
    atr_value: float
    rejected: bool
    reject_reason: str | None = None


class RiskManager:
    """
    Layer 5: Calculates risk parameters for a potential trade.

    Uses ATR for stop-loss distance, Fibonacci extensions for targets,
    and scales position size by confluence score.
    """

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()

    def calculate(
        self,
        candles: pd.DataFrame,
        zone: EntryZone,
        trend: TrendResult,
        confluence_score: float,
        account_equity: float,
    ) -> RiskCalc:
        """Calculate stop-loss, take-profit, and position size."""
        entry = float(candles["close"].iloc[-1])

        # ATR for volatility-based stop distance
        atr = compute_atr(candles, period=14)
        atr_value = float(atr.iloc[-1])
        if pd.isna(atr_value) or atr_value <= 0:
            return self._rejected("ATR is invalid or zero", entry, atr_value)

        sl_distance = atr_value * self.config.atr_sl_multiplier

        # Determine direction-specific levels
        # TP uses Fibonacci extension ratios applied to risk distance:
        #   TP1 = 1.618x risk distance (R:R = 1.618)
        #   TP2 = 2.618x risk distance (R:R = 2.618)
        if trend.direction == Trend.BEARISH:
            stop_loss = entry + sl_distance
            take_profit_1 = entry - sl_distance * 1.618
            take_profit_2 = entry - sl_distance * 2.618
        else:
            # Default to bullish for UNDETERMINED as well
            stop_loss = entry - sl_distance
            take_profit_1 = entry + sl_distance * 1.618
            take_profit_2 = entry + sl_distance * 2.618

        # Risk distance (always positive)
        risk_distance = abs(entry - stop_loss)
        if risk_distance == 0:
            return self._rejected("Risk distance is zero", entry, atr_value)

        # Risk:reward ratio
        reward_distance = abs(take_profit_1 - entry)
        risk_reward = reward_distance / risk_distance

        # Reject if below minimum R:R
        if risk_reward < self.config.min_risk_reward:
            return RiskCalc(
                stop_loss=stop_loss,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
                position_size=0,
                risk_amount=0,
                risk_reward=risk_reward,
                atr_value=atr_value,
                rejected=True,
                reject_reason=f"R:R {risk_reward:.2f} below minimum {self.config.min_risk_reward}",
            )

        # Confluence score multiplier: 50 -> 0.5x, 100 -> 1.0x (linear)
        score_multiplier = max(0.1, min(1.0, confluence_score / 100.0))

        # Position sizing: (equity * risk_pct * score_multiplier) / risk_distance
        risk_amount = account_equity * self.config.max_risk_per_trade * score_multiplier
        position_size = risk_amount / risk_distance

        return RiskCalc(
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            position_size=position_size,
            risk_amount=risk_amount,
            risk_reward=risk_reward,
            atr_value=atr_value,
            rejected=False,
            reject_reason=None,
        )

    @staticmethod
    def _rejected(reason: str, entry: float, atr_value: float) -> RiskCalc:
        """Return a rejected RiskCalc with zeroed values."""
        return RiskCalc(
            stop_loss=0,
            take_profit_1=0,
            take_profit_2=0,
            position_size=0,
            risk_amount=0,
            risk_reward=0,
            atr_value=atr_value if not pd.isna(atr_value) else 0,
            rejected=True,
            reject_reason=reason,
        )
