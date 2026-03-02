"""Kelly Criterion position sizing calculator.

Formula: Kelly% = W - (1-W)/R
  where W = win probability, R = avg_win / avg_loss

Uses fractional Kelly (default half-Kelly) for safety margin.
Falls back to None if insufficient trade history.
"""

import logging

logger = logging.getLogger(__name__)


class KellyCalculator:
    """Compute Kelly-optimal risk fraction from trade history."""

    @staticmethod
    async def compute(
        db,
        strategy_id: str,
        min_trades: int = 20,
        fraction: float = 0.5,
        lookback: int = 50,
        max_risk_per_trade: float = 0.10,
    ) -> float | None:
        """Return Kelly-adjusted risk fraction, or None if insufficient data.

        Parameters
        ----------
        db : AsyncSession
        strategy_id : UUID string of the strategy
        min_trades : minimum trades required before Kelly activates
        fraction : Kelly fraction (0.5 = half Kelly, 1.0 = full Kelly)
        lookback : number of recent trades to consider
        max_risk_per_trade : absolute cap on returned risk fraction

        Returns
        -------
        float or None : the effective risk per trade fraction, or None to
            indicate fallback to fixed fractional.
        """
        import uuid

        from sqlalchemy import select

        from app.models.signal import Signal
        from app.models.trade import Trade

        strat_uuid = uuid.UUID(strategy_id) if isinstance(strategy_id, str) else strategy_id

        # Get recent trades for this strategy via Signal linkage
        result = await db.execute(
            select(Trade)
            .join(Signal, Trade.signal_id == Signal.id)
            .where(Signal.strategy_id == strat_uuid)
            .order_by(Trade.exit_time.desc())
            .limit(lookback)
        )
        trades = result.scalars().all()

        if len(trades) < min_trades:
            logger.debug(
                "Kelly: only %d trades for strategy %s (need %d), using fixed fractional",
                len(trades), strategy_id, min_trades,
            )
            return None

        # Compute win rate and avg win/loss ratio
        wins = [t for t in trades if t.pnl and t.pnl > 0]
        losses = [t for t in trades if t.pnl and t.pnl < 0]

        if not wins or not losses:
            logger.debug(
                "Kelly: no wins or losses for strategy %s (W=%d, L=%d), using fixed fractional",
                strategy_id, len(wins), len(losses),
            )
            return None

        win_rate = len(wins) / len(trades)
        avg_win = sum(t.pnl for t in wins) / len(wins)
        avg_loss = abs(sum(t.pnl for t in losses) / len(losses))

        if avg_loss == 0:
            return None

        win_loss_ratio = avg_win / avg_loss

        # Kelly formula
        kelly_pct = win_rate - (1 - win_rate) / win_loss_ratio

        if kelly_pct <= 0:
            logger.info(
                "Kelly: negative edge for strategy %s (W=%.2f, R=%.2f, K=%.4f) — "
                "recommend stopping trading",
                strategy_id, win_rate, win_loss_ratio, kelly_pct,
            )
            return 0.001  # Minimum sizing rather than zero

        # Apply fractional Kelly
        effective = kelly_pct * fraction

        # Cap at max_risk_per_trade
        effective = min(effective, max_risk_per_trade)

        logger.info(
            "Kelly: strategy %s — W=%.2f R=%.2f K=%.4f frac=%.1f effective=%.4f "
            "(%d trades)",
            strategy_id, win_rate, win_loss_ratio, kelly_pct,
            fraction, effective, len(trades),
        )

        return effective
