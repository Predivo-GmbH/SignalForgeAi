from app.api.backtests import WFORequest


def test_wfo_request_defaults():
    req = WFORequest(symbol="BTC/USDT", timeframe="1h")
    assert req.n_folds == 3
    assert req.train_pct == 0.7
    assert len(req.param_grid) > 0


def test_wfo_request_custom():
    req = WFORequest(symbol="ETH/USDT", timeframe="4h", days=60, n_folds=5)
    assert req.n_folds == 5
    assert req.days == 60
