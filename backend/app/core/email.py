"""Email helpers — build HTML emails and send via Resend."""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def build_signal_email(
    symbol: str,
    direction: str,
    confluence_score: int,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
) -> str:
    """Build an HTML email for a new trading signal."""
    colour = "#22c55e" if direction == "BUY" else "#ef4444"
    return (
        "<html><body style='font-family:sans-serif;padding:20px'>"
        "<h2 style='margin:0 0 16px'>SignalForge Alert</h2>"
        f"<p><strong>New {direction} signal</strong> for "
        f"<span style='color:{colour};font-weight:bold'>{symbol}</span></p>"
        "<table style='border-collapse:collapse;width:100%;max-width:400px'>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Direction</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd;color:{colour}'>"
        f"<strong>{direction}</strong></td></tr>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Confluence</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd'>{confluence_score}/100</td></tr>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Entry</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd'>${entry_price:,.2f}</td></tr>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Stop Loss</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd'>${stop_loss:,.2f}</td></tr>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Take Profit</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd'>${take_profit:,.2f}</td></tr>"
        "</table>"
        "<p style='color:#888;font-size:12px;margin-top:16px'>"
        "This is an automated alert from SignalForge.</p>"
        "</body></html>"
    )


def build_daily_summary_email(
    total_pnl: float,
    trades_today: int,
    win_rate: float,
    open_positions: int,
) -> str:
    """Build an HTML email for the daily trading summary."""
    pnl_colour = "#22c55e" if total_pnl >= 0 else "#ef4444"
    return (
        "<html><body style='font-family:sans-serif;padding:20px'>"
        "<h2 style='margin:0 0 16px'>SignalForge Daily Summary</h2>"
        "<table style='border-collapse:collapse;width:100%;max-width:400px'>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Total PnL</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd;color:{pnl_colour}'>"
        f"<strong>${total_pnl:,.2f}</strong></td></tr>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Trades Today</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd'>{trades_today}</td></tr>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Win Rate</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd'>{win_rate:.1f}%</td></tr>"
        f"<tr><td style='padding:6px 12px;border:1px solid #ddd'>Open Positions</td>"
        f"<td style='padding:6px 12px;border:1px solid #ddd'>{open_positions}</td></tr>"
        "</table>"
        "<p style='color:#888;font-size:12px;margin-top:16px'>"
        "This is an automated summary from SignalForge.</p>"
        "</body></html>"
    )


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns False if no API key or on error."""
    if not settings.resend_api_key:
        logger.warning("Resend API key not configured — email not sent")
        return False

    try:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": f"SignalForge <alerts@{settings.resend_domain}>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception:
        logger.exception("Failed to send email via Resend")
        return False
