from app.core.email import build_daily_summary_email, build_signal_email


def test_build_signal_email_html():
    html = build_signal_email("BTC/USDT", "BUY", 78, 50000, 49000, 52000)
    assert "BTC/USDT" in html
    assert "BUY" in html
    assert "78" in html


def test_build_daily_summary_email():
    html = build_daily_summary_email(1250.50, 5, 60.0, 2)
    assert "$1,250.50" in html
    assert "5" in html
