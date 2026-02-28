import numpy as np

from app.api.analytics import compute_correlation


def test_correlation_identical_series():
    prices = list(np.cumsum(np.random.randn(100)) + 100)
    corr = compute_correlation(prices, prices)
    assert abs(corr - 1.0) < 0.01


def test_correlation_inverse_series():
    np.random.seed(42)
    prices_a = list(np.cumsum(np.random.randn(100)) + 100)
    prices_b = [200 - p for p in prices_a]
    corr = compute_correlation(prices_a, prices_b)
    assert corr < -0.9


def test_correlation_short_series():
    corr = compute_correlation([100], [100])
    assert corr == 0.0
