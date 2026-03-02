"""Alert email tasks — signal alerts and daily summary."""

import logging

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="send_daily_summary", bind=True, max_retries=3)
def send_daily_summary(self):
    """Send daily trade summary email to users with daily_summary enabled."""
    import asyncio

    asyncio.run(_send_summary_async())


async def _send_summary_async():
    from datetime import date, datetime, timezone

    from sqlalchemy import select

    from app.core.database import task_session
    from app.core.email import build_daily_summary_email, send_email
    from app.models.trade import Trade
    from app.models.user import User

    async with task_session() as db:
        # Get all active users
        result = await db.execute(select(User).where(User.is_active.is_(True)))
        users = result.scalars().all()

        today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)

        for user in users:
            config = user.alert_config or {}
            if not config.get("email_daily_summary", False):
                continue

            alert_email = config.get("alert_email", "") or user.email
            if not alert_email:
                continue

            # Get today's closed trades for this user
            res = await db.execute(
                select(Trade).where(
                    Trade.user_id == user.id,
                    Trade.exit_time >= today_start,
                )
            )
            trades = res.scalars().all()
            if not trades:
                continue

            try:
                total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
                win_count = sum(1 for t in trades if t.pnl is not None and t.pnl > 0)
                win_rate = win_count / len(trades) * 100 if trades else 0.0

                # Count open positions (trades with no exit)
                open_res = await db.execute(
                    select(Trade).where(
                        Trade.user_id == user.id,
                        Trade.exit_time.is_(None),
                    )
                )
                open_positions = len(open_res.scalars().all())

                email_html = build_daily_summary_email(
                    total_pnl=total_pnl,
                    trades_today=len(trades),
                    win_rate=win_rate,
                    open_positions=open_positions,
                )
                await send_email(
                    to=alert_email,
                    subject=f"SignalForge Daily Summary — {date.today()}",
                    html=email_html,
                )
                logger.info(
                    "Sent daily summary to %s: %d trades, PnL=%.2f",
                    alert_email,
                    len(trades),
                    total_pnl,
                )
            except Exception as e:
                logger.error("Failed to send summary to %s: %s", alert_email, e)
