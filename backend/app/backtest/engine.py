"""
Backtest engine. Runs the full SignalPipeline (Layers 0-5) on historical
data and simulates trades with proper position sizing and risk management.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.engine.layers.risk import RiskConfig
from app.engine.pipeline import SignalPipeline


@dataclass
class Trade:
    entry_idx: int
    entry_price: float
    direction: str
    stop_loss: float
    take_profit: float
    exit_idx: int | None = None
    exit_price: float | None = None
    pnl: float = 0.0

    @property
    def risk_reward(self) -> float:
        if self.exit_price is None:
            return 0
        reward = abs(self.exit_price - self.entry_price)
        risk = abs(self.entry_price - self.stop_loss)
        return reward / risk if risk > 0 else 0


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: list[float]
    metrics: dict


class BacktestEngine:
    """Walk-forward backtest using the full SignalPipeline (Layers 0-5)."""

    def __init__(
        self,
        lookback: int = 200,
        risk_pct: float = 0.02,
        atr_sl_mult: float = 2.0,
        min_confluence: int = 50,
        risk_config: RiskConfig | None = None,
    ):
        self.lookback = lookback
        self.risk_pct = risk_pct
        self.atr_sl_mult = atr_sl_mult
        self.min_confluence = min_confluence

        # Build RiskConfig: use provided config, or create one from legacy params
        if risk_config is not None:
            self._risk_config = risk_config
        else:
            self._risk_config = RiskConfig(
                max_risk_per_trade=risk_pct,
                atr_sl_multiplier=atr_sl_mult,
            )

        self._pipeline = SignalPipeline(
            risk_config=self._risk_config,
            min_confluence=min_confluence,
        )

    def run(
        self,
        candles: pd.DataFrame,
        symbol: str,
        timeframe: str,
        initial_capital: float = 10000.0,
    ) -> BacktestResult:
        trades: list[Trade] = []
        equity_curve = [initial_capital]
        capital = initial_capital
        open_trade: Trade | None = None

        for i in range(self.lookback, len(candles)):
            window = candles.iloc[: i + 1]
            current = candles.iloc[i]

            # Check if we have an open trade to manage
            if open_trade:
                if open_trade.direction == "BUY":
                    hit_sl = current["low"] <= open_trade.stop_loss
                    hit_tp = current["high"] >= open_trade.take_profit
                elif open_trade.direction == "SELL":
                    hit_sl = current["high"] >= open_trade.stop_loss
                    hit_tp = current["low"] <= open_trade.take_profit
                else:
                    hit_sl = False
                    hit_tp = False

                if hit_sl:
                    open_trade.exit_idx = i
                    open_trade.exit_price = open_trade.stop_loss
                    risk_dist = abs(open_trade.entry_price - open_trade.stop_loss)
                    if risk_dist > 0:
                        position_size = capital * self.risk_pct / risk_dist
                        if open_trade.direction == "BUY":
                            open_trade.pnl = (
                                open_trade.exit_price - open_trade.entry_price
                            ) * position_size
                        else:
                            open_trade.pnl = (
                                open_trade.entry_price - open_trade.exit_price
                            ) * position_size
                    capital += open_trade.pnl
                    trades.append(open_trade)
                    open_trade = None
                elif hit_tp:
                    open_trade.exit_idx = i
                    open_trade.exit_price = open_trade.take_profit
                    risk_dist = abs(open_trade.entry_price - open_trade.stop_loss)
                    if risk_dist > 0:
                        position_size = capital * self.risk_pct / risk_dist
                        if open_trade.direction == "BUY":
                            open_trade.pnl = (
                                open_trade.exit_price - open_trade.entry_price
                            ) * position_size
                        else:
                            open_trade.pnl = (
                                open_trade.entry_price - open_trade.exit_price
                            ) * position_size
                    capital += open_trade.pnl
                    trades.append(open_trade)
                    open_trade = None

                equity_curve.append(capital)
                continue

            # Run the full 6-layer SignalPipeline
            signal = self._pipeline.process(
                symbol=symbol,
                timeframe=timeframe,
                candles=window,
                account_equity=capital,
            )

            if signal.action in ("BUY", "SELL") and signal.stop_loss and signal.take_profit_1:
                open_trade = Trade(
                    entry_idx=i,
                    entry_price=float(current["close"]),
                    direction=signal.action,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit_1,
                )

            equity_curve.append(capital)

        # Close any remaining open trade at last price
        if open_trade:
            open_trade.exit_idx = len(candles) - 1
            open_trade.exit_price = float(candles["close"].iloc[-1])
            risk_dist = abs(open_trade.entry_price - open_trade.stop_loss)
            if risk_dist > 0:
                position_size = capital * self.risk_pct / risk_dist
                if open_trade.direction == "BUY":
                    open_trade.pnl = (
                        open_trade.exit_price - open_trade.entry_price
                    ) * position_size
                else:
                    open_trade.pnl = (
                        open_trade.entry_price - open_trade.exit_price
                    ) * position_size
            capital += open_trade.pnl
            trades.append(open_trade)
            equity_curve[-1] = capital

        metrics = self._calculate_metrics(trades, equity_curve, initial_capital)
        return BacktestResult(trades=trades, equity_curve=equity_curve, metrics=metrics)

    def _calculate_metrics(
        self,
        trades: list[Trade],
        equity_curve: list[float],
        initial_capital: float,
    ) -> dict:
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "total_return_pct": 0,
                "max_drawdown_pct": 0,
                "sharpe_ratio": 0,
                "avg_risk_reward": 0,
            }

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        total_win = sum(t.pnl for t in wins) if wins else 0
        total_loss = abs(sum(t.pnl for t in losses)) if losses else 0

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            "total_trades": len(trades),
            "win_rate": len(wins) / len(trades) * 100 if trades else 0,
            "profit_factor": (
                total_win / total_loss if total_loss > 0 else float("inf")
            ),
            "total_return_pct": (
                (equity_curve[-1] - initial_capital) / initial_capital * 100
            ),
            "max_drawdown_pct": max_dd,
            "sharpe_ratio": self._sharpe(equity_curve),
            "avg_risk_reward": (
                float(np.mean([t.risk_reward for t in wins])) if wins else 0
            ),
        }

    def _sharpe(self, equity_curve: list[float]) -> float:
        eq = np.array(equity_curve)
        returns = np.diff(eq) / eq[:-1]
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        return float(np.mean(returns) / np.std(returns) * np.sqrt(252))
