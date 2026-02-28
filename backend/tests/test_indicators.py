import numpy as np
import pandas as pd


def make_candles(n=200, seed=42):
    """Generate synthetic OHLCV data for testing."""
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    open_ = close + rng.normal(0, 0.5, n)
    volume = rng.uniform(1000, 10000, n)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume
    })


class TestEMA:
    def test_ema_returns_series(self):
        from app.engine.indicators import compute_ema
        candles = make_candles()
        result = compute_ema(candles["close"], period=20)
        assert isinstance(result, pd.Series)
        assert len(result) == len(candles)

    def test_ema_period_one_equals_close(self):
        from app.engine.indicators import compute_ema
        candles = make_candles()
        result = compute_ema(candles["close"], period=1)
        # EMA with period 1 should equal close
        np.testing.assert_allclose(result.iloc[-1], candles["close"].iloc[-1], rtol=1e-5)

    def test_ema_all_finite(self):
        from app.engine.indicators import compute_ema
        candles = make_candles()
        result = compute_ema(candles["close"], period=20)
        assert result.notna().all()


class TestRSI:
    def test_rsi_range(self):
        from app.engine.indicators import compute_rsi
        candles = make_candles()
        rsi = compute_rsi(candles["close"], period=14)
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_rsi_returns_series(self):
        from app.engine.indicators import compute_rsi
        candles = make_candles()
        rsi = compute_rsi(candles["close"], period=14)
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(candles)


class TestMACD:
    def test_macd_returns_three_series(self):
        from app.engine.indicators import compute_macd
        candles = make_candles()
        macd, signal, hist = compute_macd(candles["close"])
        assert len(macd) == len(candles)
        assert len(signal) == len(candles)
        assert len(hist) == len(candles)

    def test_macd_histogram_is_difference(self):
        from app.engine.indicators import compute_macd
        candles = make_candles()
        macd, signal, hist = compute_macd(candles["close"])
        # Histogram = MACD line - Signal line
        expected = macd - signal
        np.testing.assert_allclose(hist.values, expected.values, rtol=1e-10)


class TestATR:
    def test_atr_positive(self):
        from app.engine.indicators import compute_atr
        candles = make_candles()
        atr = compute_atr(candles, period=14)
        valid = atr.dropna()
        assert (valid > 0).all()

    def test_atr_returns_series(self):
        from app.engine.indicators import compute_atr
        candles = make_candles()
        atr = compute_atr(candles, period=14)
        assert isinstance(atr, pd.Series)
        assert len(atr) == len(candles)


class TestStochastic:
    def test_stochastic_range(self):
        from app.engine.indicators import compute_stochastic
        candles = make_candles()
        slowk, slowd = compute_stochastic(candles)
        valid_k = slowk.dropna()
        valid_d = slowd.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()
        assert (valid_d >= 0).all() and (valid_d <= 100).all()

    def test_stochastic_returns_two_series(self):
        from app.engine.indicators import compute_stochastic
        candles = make_candles()
        slowk, slowd = compute_stochastic(candles)
        assert isinstance(slowk, pd.Series)
        assert isinstance(slowd, pd.Series)
        assert len(slowk) == len(candles)
        assert len(slowd) == len(candles)


class TestVWAP:
    def test_vwap_returns_series(self):
        from app.engine.indicators import compute_vwap
        candles = make_candles()
        vwap = compute_vwap(candles)
        assert isinstance(vwap, pd.Series)
        assert len(vwap) == len(candles)

    def test_vwap_first_value_is_typical_price(self):
        from app.engine.indicators import compute_vwap
        candles = make_candles()
        vwap = compute_vwap(candles)
        first = candles.iloc[0]
        expected_tp = (first["high"] + first["low"] + first["close"]) / 3
        np.testing.assert_allclose(vwap.iloc[0], expected_tp, rtol=1e-10)


class TestFibonacci:
    def test_fib_levels_correct(self):
        from app.engine.indicators import calculate_fib_levels
        levels = calculate_fib_levels(swing_low=100.0, swing_high=200.0)
        assert levels[0.0] == 200.0
        assert levels[1.0] == 100.0
        assert abs(levels[0.5] - 150.0) < 0.01
        assert abs(levels[0.382] - (200.0 - 0.382 * 100)) < 0.01
        assert abs(levels[0.618] - (200.0 - 0.618 * 100)) < 0.01

    def test_fib_levels_keys(self):
        from app.engine.indicators import calculate_fib_levels
        levels = calculate_fib_levels(swing_low=50.0, swing_high=150.0)
        expected_keys = {0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0}
        assert set(levels.keys()) == expected_keys


class TestADX:
    def test_adx_returns_series(self):
        from app.engine.indicators import compute_adx
        candles = make_candles()
        adx = compute_adx(candles, period=14)
        assert isinstance(adx, pd.Series)
        assert len(adx) == len(candles)

    def test_adx_non_negative(self):
        from app.engine.indicators import compute_adx
        candles = make_candles()
        adx = compute_adx(candles, period=14)
        valid = adx.dropna()
        assert (valid >= 0).all()
