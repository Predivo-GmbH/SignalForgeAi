"""
Indicator library wrapping ta-lib (with pure-Python fallbacks).
All functions accept pandas Series/DataFrame and return pandas Series.
"""

import numpy as np
import pandas as pd

try:
    import talib

    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    if HAS_TALIB:
        return pd.Series(talib.EMA(close.values, timeperiod=period), index=close.index)
    return close.ewm(span=period, adjust=False).mean()


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (0-100)."""
    if HAS_TALIB:
        return pd.Series(talib.RSI(close.values, timeperiod=period), index=close.index)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD — returns (macd_line, signal_line, histogram)."""
    if HAS_TALIB:
        macd, signal, hist = talib.MACD(
            close.values, fastperiod=fast, slowperiod=slow, signalperiod=signal_period
        )
        return (
            pd.Series(macd, index=close.index),
            pd.Series(signal, index=close.index),
            pd.Series(hist, index=close.index),
        )
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    if HAS_TALIB:
        return pd.Series(
            talib.ATR(
                candles["high"].values,
                candles["low"].values,
                candles["close"].values,
                timeperiod=period,
            ),
            index=candles.index,
        )
    high = candles["high"]
    low = candles["low"]
    prev_close = candles["close"].shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_stochastic(
    candles: pd.DataFrame, k_period: int = 14, d_period: int = 3, slowing: int = 3
) -> tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator — returns (slow_k, slow_d) in 0-100 range."""
    if HAS_TALIB:
        slowk, slowd = talib.STOCH(
            candles["high"].values,
            candles["low"].values,
            candles["close"].values,
            fastk_period=k_period,
            slowk_period=slowing,
            slowd_period=d_period,
        )
        return pd.Series(slowk, index=candles.index), pd.Series(
            slowd, index=candles.index
        )
    lowest_low = candles["low"].rolling(window=k_period).min()
    highest_high = candles["high"].rolling(window=k_period).max()
    fastk = 100 * (candles["close"] - lowest_low) / (highest_high - lowest_low)
    slowk = fastk.rolling(window=slowing).mean()
    slowd = slowk.rolling(window=d_period).mean()
    return slowk, slowd


def compute_vwap(candles: pd.DataFrame) -> pd.Series:
    """Volume-Weighted Average Price (cumulative intraday)."""
    typical_price = (candles["high"] + candles["low"] + candles["close"]) / 3
    cum_vol = candles["volume"].cumsum()
    cum_tp_vol = (typical_price * candles["volume"]).cumsum()
    return cum_tp_vol / cum_vol


def calculate_fib_levels(swing_low: float, swing_high: float) -> dict[float, float]:
    """Fibonacci retracement levels from swing high to swing low."""
    diff = swing_high - swing_low
    return {
        0.0: swing_high,
        0.236: swing_high - 0.236 * diff,
        0.382: swing_high - 0.382 * diff,
        0.5: swing_high - 0.5 * diff,
        0.618: swing_high - 0.618 * diff,
        0.786: swing_high - 0.786 * diff,
        1.0: swing_low,
    }


def compute_adx(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index — measures trend strength (0-100)."""
    if HAS_TALIB:
        return pd.Series(
            talib.ADX(
                candles["high"].values,
                candles["low"].values,
                candles["close"].values,
                timeperiod=period,
            ),
            index=candles.index,
        )
    # Pure-Python ADX via directional movement
    high = candles["high"]
    low = candles["low"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    plus_dm = np.where(
        (high - prev_high) > (prev_low - low), np.maximum(high - prev_high, 0), 0
    )
    minus_dm = np.where(
        (prev_low - low) > (high - prev_high), np.maximum(prev_low - low, 0), 0
    )
    atr = compute_atr(candles, period)
    plus_di = (
        100 * pd.Series(plus_dm, index=candles.index).rolling(period).mean() / atr
    )
    minus_di = (
        100 * pd.Series(minus_dm, index=candles.index).rolling(period).mean() / atr
    )
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    return adx
