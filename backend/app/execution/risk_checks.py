from dataclasses import dataclass


@dataclass
class AccountState:
    equity: float
    daily_pnl: float
    open_positions: int
    max_positions: int = 5


@dataclass
class CheckResult:
    approved: bool
    reason: str | None = None


class PreTradeChecker:
    def __init__(
        self,
        max_daily_loss_pct: float = 0.06,
        max_risk_per_trade_pct: float = 0.02,
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_risk_per_trade_pct = max_risk_per_trade_pct

    def check(self, state: AccountState, risk_amount: float) -> CheckResult:
        # Daily loss check
        if abs(state.daily_pnl) >= state.equity * self.max_daily_loss_pct:
            return CheckResult(approved=False, reason="daily_loss_exceeded")

        # Max positions check
        if state.open_positions >= state.max_positions:
            return CheckResult(approved=False, reason="max_positions_reached")

        # Per-trade risk check
        if risk_amount > state.equity * self.max_risk_per_trade_pct:
            return CheckResult(approved=False, reason="risk_per_trade_exceeded")

        return CheckResult(approved=True)
