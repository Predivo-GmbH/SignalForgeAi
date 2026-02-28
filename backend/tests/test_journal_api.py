from app.api.journal import _build_trade_prompt


def test_build_trade_prompt_includes_trade_data():
    trade_data = {
        "symbol": "BTC/USDT",
        "direction": "BUY",
        "entry_price": 50000,
        "exit_price": 51000,
        "pnl": 200,
        "confluence_score": 72,
        "exit_reason": "take_profit",
    }
    prompt = _build_trade_prompt(trade_data)
    assert "BTC/USDT" in prompt
    assert "BUY" in prompt
    assert "200" in prompt


def test_build_trade_prompt_handles_losing_trade():
    trade_data = {
        "symbol": "EUR/USD",
        "direction": "SELL",
        "entry_price": 1.0800,
        "exit_price": 1.0850,
        "pnl": -150,
        "confluence_score": 45,
        "exit_reason": "stop_loss",
    }
    prompt = _build_trade_prompt(trade_data)
    assert "stop_loss" in prompt
    assert "-150" in prompt
