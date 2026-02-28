import numpy as np
import pandas as pd

from app.backtest.engine import BacktestEngine


def test_sortino_ratio_calculated():
    engine = BacktestEngine(lookback=50)
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame(
        {
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.3),
            "low": close - abs(np.random.randn(n) * 0.3),
            "close": close,
            "volume": np.random.randint(100, 10000, n).astype(float),
        },
        index=dates,
    )
    result = engine.run(df, "TEST/USD", "1h")
    assert "sortino_ratio" in result.metrics
    assert "calmar_ratio" in result.metrics
    assert isinstance(result.metrics["sortino_ratio"], float)
    assert isinstance(result.metrics["calmar_ratio"], float)


def test_calmar_zero_drawdown():
    engine = BacktestEngine(lookback=50, min_confluence=100)  # High confluence = no trades
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame(
        {
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.3),
            "low": close - abs(np.random.randn(n) * 0.3),
            "close": close,
            "volume": np.random.randint(100, 10000, n).astype(float),
        },
        index=dates,
    )
    result = engine.run(df, "TEST/USD", "1h")
    assert result.metrics["calmar_ratio"] == 0.0
