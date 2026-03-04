"""
Regime-Adaptive Backtest: HMM Macro Regime + Trailing Stops + Confirmations.

Tests whether adapting strategy to market regime can capture more volatility:
- STRONG BULL: trailing stop, long only, 2% risk
- BULL CORRECTION: swing trade, long bias, 1% risk
- RANGING: high confluence (70+), 1% risk
- BEAR TRENDING: swing trade, short bias, 1% risk
- CAPITULATION: minimal risk (0.5%)
- RECOVERY: trailing stop, long only, 1.5% risk

Compares 5 strategies:
1. Current system (fixed TP, both directions, 1% risk)
2. Trailing-stop only (no regime, just trailing stops)
3. Regime-adaptive HMM (HMM-driven strategy switching)
4. Regime+ (HMM + 8-confirmation voting + 48h cooldown + regime-exit)
5. Buy-and-hold

Insights integrated from Streamlit regime-based trading app:
- 8-confirmation voting: RSI<90, Momentum>1%, Vol<6%, Volume>20-SMA,
  ADX>25, Price>EMA50, Price>EMA200, MACD>Signal
- 48-hour cooldown after exits (12 bars on 4h)
- Force-close on regime change to Bear/Capitulation

Usage:
    cd backend
    .venv/Scripts/python.exe -u scripts/run_regime_backtest.py
"""
from __future__ import annotations

import glob as globmod
import logging
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# ── Path setup ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Disable HMM in pipeline (we use our own) ───────────────────────────
from app.engine.layers import regime as _regime_mod  # noqa: E402

_OrigRegimeDetector = _regime_mod.RegimeDetector


class _FastRegimeDetector(_OrigRegimeDetector):
    def __init__(self, use_hmm: bool = False):
        super().__init__(use_hmm=False)


_regime_mod.RegimeDetector = _FastRegimeDetector

from app.engine import indicators as _ind_mod  # noqa: E402
from app.engine.layers import confluence as _conf_mod  # noqa: E402
from app.engine.layers import risk as _risk_mod  # noqa: E402
from app.engine.layers import trend as _trend_mod  # noqa: E402
from app.engine.layers import triggers as _trig_mod  # noqa: E402
from app.engine.layers import zones as _zone_mod  # noqa: E402
from app.engine.layers.risk import RiskConfig  # noqa: E402
from app.engine.pipeline import SignalPipeline  # noqa: E402

logging.basicConfig(level=logging.WARNING)
logging.getLogger("hmmlearn").setLevel(logging.CRITICAL)

# ── Configuration ───────────────────────────────────────────────────────

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "docs", "chart-data")
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "REGIME-BACKTEST.md")

FEE_RATE = 0.00075
INITIAL_CAPITAL = 10_000.0
LOOKBACK = 200
HMM_TRAIN_WINDOW = 500  # Bars for rolling HMM training
HMM_RETRAIN_INTERVAL = 100  # Retrain every N bars
COOLDOWN_BARS = 12  # 48h cooldown on 4h candles (48/4=12)
MIN_CONFIRMATIONS = 6  # Require 6/8 confirmations to enter (Regime+ strategy)

# ── Macro Regime ────────────────────────────────────────────────────────


class MacroRegime:
    STRONG_BULL = "strong_bull"
    BULL_CORRECTION = "bull_correction"
    RANGING = "ranging"
    BEAR_TRENDING = "bear_trending"
    CAPITULATION = "capitulation"
    RECOVERY = "recovery"

    ALL = [STRONG_BULL, BULL_CORRECTION, RANGING, BEAR_TRENDING, CAPITULATION, RECOVERY]
    COLORS = {
        STRONG_BULL: "green",
        BULL_CORRECTION: "yellow",
        RANGING: "gray",
        BEAR_TRENDING: "red",
        CAPITULATION: "darkred",
        RECOVERY: "cyan",
    }


# Strategy settings per regime
REGIME_STRATEGY = {
    MacroRegime.STRONG_BULL: {
        "exit_mode": "trailing",
        "direction_filter": "BUY",
        "risk_pct": 0.02,
        "min_confluence": 50,
        "trailing_atr_mult": 2.0,
    },
    MacroRegime.BULL_CORRECTION: {
        "exit_mode": "fixed",
        "direction_filter": "BUY",
        "risk_pct": 0.01,
        "min_confluence": 50,
        "tp_ratio": 2.0,
    },
    MacroRegime.RANGING: {
        "exit_mode": "fixed",
        "direction_filter": None,
        "risk_pct": 0.01,
        "min_confluence": 70,
        "tp_ratio": 1.0,
    },
    MacroRegime.BEAR_TRENDING: {
        "exit_mode": "trailing",
        "direction_filter": "SELL",
        "risk_pct": 0.015,
        "min_confluence": 50,
        "trailing_atr_mult": 2.0,
    },
    MacroRegime.CAPITULATION: {
        "exit_mode": "fixed",
        "direction_filter": None,
        "risk_pct": 0.005,
        "min_confluence": 70,
        "tp_ratio": 1.0,
    },
    MacroRegime.RECOVERY: {
        "exit_mode": "trailing",
        "direction_filter": "BUY",
        "risk_pct": 0.015,
        "min_confluence": 50,
        "trailing_atr_mult": 2.5,
    },
}


# ── Data types ──────────────────────────────────────────────────────────


@dataclass
class BarSignal:
    action: str
    confluence: int
    atr: float
    close: float
    high: float
    low: float
    regime: str = ""
    timestamp: int = 0
    # Confirmation indicators (for 8-confirmation voting system)
    rsi: float = 50.0
    adx: float = 0.0
    momentum_pct: float = 0.0  # 1-bar return %
    volatility_pct: float = 0.0  # Rolling std of returns %
    volume_ratio: float = 1.0  # Volume / 20-SMA volume
    price_vs_ema50: float = 0.0  # price - ema50 (>0 = above)
    price_vs_ema200: float = 0.0  # price - ema200 (>0 = above)
    macd_above_signal: bool = False  # MACD line > Signal line


# ── CSV Loader ──────────────────────────────────────────────────────────


def load_csv(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df = df.rename(columns={"Volume": "volume"})
    keep = [c for c in ["time", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].copy()
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


def discover_4h_pairs(data_dir: str) -> dict[str, dict]:
    pairs = {}
    for filepath in sorted(globmod.glob(os.path.join(data_dir, "*.csv"))):
        filename = os.path.basename(filepath)
        match = re.match(r"^([A-Z]+)_([A-Z]+(?:USD|USDT)),\s*(\w+)\.csv$", filename)
        if not match:
            continue
        source, symbol, tf_raw = match.groups()
        if tf_raw != "240":
            continue
        if symbol.endswith("USDT"):
            pair_name = symbol[:-4] + "/USDT"
        elif symbol.endswith("USD"):
            pair_name = symbol[:-3] + "/USD"
        else:
            pair_name = symbol
        key = f"{pair_name}-4h"
        if key in pairs:
            if os.path.getsize(filepath) <= os.path.getsize(pairs[key]["file"]):
                continue
        pairs[key] = {"file": filepath, "tf": "4h", "source": source}
    return pairs


# ── Indicator Caching ───────────────────────────────────────────────────


class IndicatorCache:
    def __init__(self):
        self._cache: dict = {}
        self._originals: dict = {}

    def setup(self, candles: pd.DataFrame):
        close = candles["close"]
        if not self._originals:
            self._originals = {
                "compute_adx": _ind_mod.compute_adx,
                "compute_atr": _ind_mod.compute_atr,
                "compute_rsi": _ind_mod.compute_rsi,
                "compute_macd": _ind_mod.compute_macd,
                "compute_ema": _ind_mod.compute_ema,
                "compute_stochastic": _ind_mod.compute_stochastic,
                "compute_vwap": _ind_mod.compute_vwap,
                "compute_bollinger_bands": _ind_mod.compute_bollinger_bands,
                "compute_ichimoku": _ind_mod.compute_ichimoku,
                "compute_obv": _ind_mod.compute_obv,
                "compute_williams_r": _ind_mod.compute_williams_r,
                "compute_cci": _ind_mod.compute_cci,
            }
        orig = self._originals
        self._cache = {
            ("adx", 14): orig["compute_adx"](candles, 14),
            ("atr", 14): orig["compute_atr"](candles, 14),
            ("rsi", 14): orig["compute_rsi"](close, 14),
            ("macd", 12, 26, 9): orig["compute_macd"](close, 12, 26, 9),
            ("stochastic", 14, 3, 3): orig["compute_stochastic"](candles, 14, 3, 3),
            ("vwap",): orig["compute_vwap"](candles),
            ("bollinger", 20, 2.0): orig["compute_bollinger_bands"](close, 20, 2.0),
            ("ichimoku", 9, 26, 52): orig["compute_ichimoku"](candles, 9, 26, 52),
            ("obv",): orig["compute_obv"](candles),
            ("williams_r", 14): orig["compute_williams_r"](candles, 14),
            ("cci", 20): orig["compute_cci"](candles, 20),
        }
        for period in [10, 20, 50, 100, 200]:
            self._cache[("ema", period)] = orig["compute_ema"](close, period)
        self._n = len(candles)
        self._install_patches()

    def _install_patches(self):
        cache = self._cache

        def _cached_adx(candles, period=14):
            return cache[("adx", 14)].iloc[: len(candles)]

        def _cached_atr(candles, period=14):
            return cache[("atr", 14)].iloc[: len(candles)]

        def _cached_rsi(close, period=14):
            return cache[("rsi", 14)].iloc[: len(close)]

        def _cached_macd(close, fast=12, slow=26, signal_period=9):
            r = cache[("macd", 12, 26, 9)]
            n = len(close)
            return (r[0].iloc[:n], r[1].iloc[:n], r[2].iloc[:n])

        def _cached_ema(close, period):
            key = ("ema", period)
            if key in cache:
                return cache[key].iloc[: len(close)]
            return _indicator_cache._originals["compute_ema"](close, period)

        def _cached_stochastic(candles, k_period=14, d_period=3, slowing=3):
            r = cache[("stochastic", 14, 3, 3)]
            n = len(candles)
            return (r[0].iloc[:n], r[1].iloc[:n])

        def _cached_vwap(candles):
            return cache[("vwap",)].iloc[: len(candles)]

        def _cached_bollinger(close, period=20, num_std=2.0):
            r = cache[("bollinger", 20, 2.0)]
            n = len(close)
            return (r[0].iloc[:n], r[1].iloc[:n], r[2].iloc[:n])

        def _cached_ichimoku(candles, tenkan=9, kijun=26, senkou_b=52):
            r = cache[("ichimoku", 9, 26, 52)]
            n = len(candles)
            return {k: v.iloc[:n] if hasattr(v, "iloc") else v for k, v in r.items()}

        def _cached_obv(candles):
            return cache[("obv",)].iloc[: len(candles)]

        def _cached_williams_r(candles, period=14):
            return cache[("williams_r", 14)].iloc[: len(candles)]

        def _cached_cci(candles, period=20):
            return cache[("cci", 20)].iloc[: len(candles)]

        _regime_mod.compute_adx = _cached_adx
        _regime_mod.compute_atr = _cached_atr
        _risk_mod.compute_atr = _cached_atr
        _conf_mod.compute_rsi = _cached_rsi
        _conf_mod.compute_macd = _cached_macd
        _conf_mod.compute_stochastic = _cached_stochastic
        _conf_mod.compute_vwap = _cached_vwap
        _conf_mod.compute_bollinger_bands = _cached_bollinger
        _conf_mod.compute_ichimoku = _cached_ichimoku
        _conf_mod.compute_obv = _cached_obv
        _conf_mod.compute_williams_r = _cached_williams_r
        _conf_mod.compute_cci = _cached_cci
        _trig_mod.compute_macd = _cached_macd
        _trig_mod.compute_rsi = _cached_rsi
        _trig_mod.compute_stochastic = _cached_stochastic
        _zone_mod.compute_vwap = _cached_vwap
        _trend_mod.compute_ema = _cached_ema
        _trend_mod.compute_vwap = _cached_vwap


_indicator_cache = IndicatorCache()


# ── Signal Pre-Computation ─────────────────────────────────────────────


def precompute_signals(candles: pd.DataFrame, pair: str, tf: str) -> list[BarSignal]:
    pipeline = SignalPipeline(
        risk_config=RiskConfig(max_risk_per_trade=0.02, atr_sl_multiplier=2.0, min_risk_reward=0.1),
        min_confluence=1,
    )
    atr_full = _indicator_cache._cache[("atr", 14)]
    rsi_full = _indicator_cache._cache[("rsi", 14)]
    adx_full = _indicator_cache._cache[("adx", 14)]
    macd_line, macd_signal, _ = _indicator_cache._cache[("macd", 12, 26, 9)]
    ema50_full = _indicator_cache._cache[("ema", 50)]
    ema200_full = _indicator_cache._cache[("ema", 200)]

    # Pre-compute volume SMA (20-period)
    vol = candles["volume"] if "volume" in candles.columns else pd.Series(np.ones(len(candles)))
    vol_sma20 = vol.rolling(20, min_periods=1).mean()

    # Pre-compute returns for momentum/volatility
    close_arr = candles["close"]
    returns = close_arr.pct_change().fillna(0)
    roll_vol = returns.rolling(20, min_periods=1).std() * 100  # as percentage

    timestamps = candles["time"].values if "time" in candles.columns else [0] * len(candles)
    signals: list[BarSignal] = []

    for i in range(LOOKBACK, len(candles)):
        window = candles.iloc[: i + 1]
        current = candles.iloc[i]
        signal = pipeline.process(symbol=pair, timeframe=tf, candles=window, account_equity=10000.0)
        atr_val = float(atr_full.iloc[i]) if not pd.isna(atr_full.iloc[i]) else 0.0

        # Confirmation indicators
        rsi_val = float(rsi_full.iloc[i]) if not pd.isna(rsi_full.iloc[i]) else 50.0
        adx_val = float(adx_full.iloc[i]) if not pd.isna(adx_full.iloc[i]) else 0.0
        mom_pct = float(returns.iloc[i]) * 100  # 1-bar return as %
        vol_pct = float(roll_vol.iloc[i]) if not pd.isna(roll_vol.iloc[i]) else 0.0
        v_sma = float(vol_sma20.iloc[i]) if not pd.isna(vol_sma20.iloc[i]) else 1.0
        v_cur = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 1.0
        vol_ratio = v_cur / v_sma if v_sma > 0 else 1.0
        e50 = float(ema50_full.iloc[i]) if not pd.isna(ema50_full.iloc[i]) else float(current["close"])
        e200 = float(ema200_full.iloc[i]) if not pd.isna(ema200_full.iloc[i]) else float(current["close"])
        macd_above = (float(macd_line.iloc[i]) > float(macd_signal.iloc[i])
                      if not pd.isna(macd_line.iloc[i]) and not pd.isna(macd_signal.iloc[i]) else False)

        signals.append(BarSignal(
            action=signal.action, confluence=signal.confluence_score,
            atr=atr_val, close=float(current["close"]),
            high=float(current["high"]), low=float(current["low"]),
            regime=signal.regime,
            timestamp=int(timestamps[i]) if i < len(timestamps) else 0,
            rsi=rsi_val, adx=adx_val, momentum_pct=mom_pct,
            volatility_pct=vol_pct, volume_ratio=vol_ratio,
            price_vs_ema50=float(current["close"]) - e50,
            price_vs_ema200=float(current["close"]) - e200,
            macd_above_signal=macd_above,
        ))
    return signals


# ── HMM Macro Regime Detection ─────────────────────────────────────────


def compute_hmm_features(candles: pd.DataFrame) -> np.ndarray:
    """Compute 5 features for HMM: returns, range, vol_change, atr_ratio, adx."""
    close = candles["close"].values
    high = candles["high"].values
    low = candles["low"].values
    volume = candles["volume"].values if "volume" in candles.columns else np.ones(len(close))

    returns = np.diff(close) / close[:-1]
    intra_range = (high[1:] - low[1:]) / close[1:]
    vol_change = np.diff(volume) / (volume[:-1] + 1e-10)

    # ATR ratio (14-period) -- simplified
    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - close[:-1]),
                               np.abs(low[1:] - close[:-1])))
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    atr_ratio = atr / close[1:]

    # ADX (14-period) -- simplified using directional movement
    plus_dm = np.maximum(high[1:] - high[:-1], 0)
    minus_dm = np.maximum(low[:-1] - low[1:], 0)
    # Zero out when opposite DM is larger
    mask_plus = plus_dm > minus_dm
    mask_minus = minus_dm > plus_dm
    plus_dm[~mask_plus] = 0
    minus_dm[~mask_minus] = 0

    smooth_tr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    smooth_plus = pd.Series(plus_dm).rolling(14, min_periods=1).mean().values
    smooth_minus = pd.Series(minus_dm).rolling(14, min_periods=1).mean().values

    plus_di = smooth_plus / (smooth_tr + 1e-10) * 100
    minus_di = smooth_minus / (smooth_tr + 1e-10) * 100
    dx = np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10) * 100
    adx = pd.Series(dx).rolling(14, min_periods=1).mean().values / 100  # Normalize

    # Clip extreme values
    returns = np.clip(returns, -0.3, 0.3)
    vol_change = np.clip(vol_change, -5, 5)

    features = np.column_stack([returns, intra_range, vol_change, atr_ratio, adx])

    # Replace NaN/inf
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
    return features


def detect_macro_regimes_hmm(candles: pd.DataFrame, n_states: int = 6) -> list[str]:
    """Detect macro regimes using rolling HMM on candle data."""
    from hmmlearn.hmm import GaussianHMM

    features_all = compute_hmm_features(candles)
    n_bars = len(features_all)
    regimes = ["unknown"] * (n_bars + 1)  # +1 because features has one fewer row

    model = None
    state_regime_map = {}

    for i in range(HMM_TRAIN_WINDOW, n_bars):
        # Retrain periodically
        if model is None or i % HMM_RETRAIN_INTERVAL == 0:
            start = max(0, i - HMM_TRAIN_WINDOW)
            train_data = features_all[start:i]

            if len(train_data) < 100:
                regimes[i + 1] = MacroRegime.RANGING
                continue

            try:
                model = GaussianHMM(
                    n_components=min(n_states, len(train_data) // 20),
                    covariance_type="full",
                    n_iter=200,
                    random_state=42,
                )
                model.fit(train_data)

                # Map states to regimes based on their characteristics
                state_regime_map = _map_states_to_regimes(model, train_data)
            except Exception:
                model = None
                regimes[i + 1] = MacroRegime.RANGING
                continue

        # Predict current bar
        try:
            obs = features_all[i:i + 1]
            state = model.predict(obs)[0]
            regimes[i + 1] = state_regime_map.get(state, MacroRegime.RANGING)
        except Exception:
            regimes[i + 1] = MacroRegime.RANGING

    return regimes


def _map_states_to_regimes(model, train_data) -> dict[int, str]:
    """Map HMM states to macro regimes based on their mean characteristics."""
    n_states = model.n_components
    means = model.means_  # shape: (n_states, n_features)
    # Features: [returns, range, vol_change, atr_ratio, adx]

    state_info = []
    for s in range(n_states):
        state_info.append({
            "state": s,
            "mean_return": means[s][0],
            "mean_range": means[s][1],
            "mean_vol_change": means[s][2],
            "mean_atr_ratio": means[s][3],
            "mean_adx": means[s][4],
        })

    # Sort by mean return (ascending)
    state_info.sort(key=lambda x: x["mean_return"])

    mapping = {}
    if n_states >= 6:
        # 6 states: map from most bearish to most bullish
        mapping[state_info[0]["state"]] = MacroRegime.CAPITULATION  # Most negative returns
        mapping[state_info[1]["state"]] = MacroRegime.BEAR_TRENDING
        mapping[state_info[2]["state"]] = MacroRegime.RANGING  # Near-zero, lower
        mapping[state_info[3]["state"]] = MacroRegime.RANGING  # Near-zero, higher (merge with ranging)
        mapping[state_info[4]["state"]] = MacroRegime.BULL_CORRECTION
        mapping[state_info[5]["state"]] = MacroRegime.STRONG_BULL  # Most positive returns

        # Refine: check if any "near-zero return + low vol" state should be RECOVERY
        for info in state_info[2:4]:  # Middle states
            if info["mean_return"] > 0 and info["mean_adx"] > 0.2:
                mapping[info["state"]] = MacroRegime.RECOVERY
                break
    elif n_states >= 4:
        mapping[state_info[0]["state"]] = MacroRegime.BEAR_TRENDING
        mapping[state_info[1]["state"]] = MacroRegime.RANGING
        mapping[state_info[2]["state"]] = MacroRegime.BULL_CORRECTION
        mapping[state_info[3]["state"]] = MacroRegime.STRONG_BULL
        if n_states >= 5:
            mapping[state_info[0]["state"]] = MacroRegime.CAPITULATION
            mapping[state_info[1]["state"]] = MacroRegime.BEAR_TRENDING
    else:
        # Fallback for fewer states
        mapping[state_info[0]["state"]] = MacroRegime.BEAR_TRENDING
        mapping[state_info[-1]["state"]] = MacroRegime.STRONG_BULL
        for s in state_info[1:-1]:
            mapping[s["state"]] = MacroRegime.RANGING

    return mapping


def detect_macro_regimes_rules(candles: pd.DataFrame) -> list[str]:
    """Rule-based macro regime detection (EMA + ATH distance)."""
    close = candles["close"].values
    n = len(close)
    regimes = [MacroRegime.RANGING] * n

    # Pre-compute EMAs
    ema_50 = pd.Series(close).ewm(span=50, adjust=False).mean().values
    ema_200 = pd.Series(close).ewm(span=200, adjust=False).mean().values

    # Rolling ATH (500-bar lookback)
    ath_lookback = 500
    ath = pd.Series(close).rolling(ath_lookback, min_periods=1).max().values

    for i in range(200, n):
        price = close[i]
        e200 = ema_200[i]
        e200_prev = ema_200[max(0, i - 20)]
        slope = (e200 - e200_prev) / (e200_prev + 1e-10)
        dd = (ath[i] - price) / (ath[i] + 1e-10)

        if price > e200 and slope > 0.005:
            if dd < 0.10:
                regimes[i] = MacroRegime.STRONG_BULL
            else:
                regimes[i] = MacroRegime.BULL_CORRECTION
        elif price < e200 and slope < -0.005:
            if dd > 0.50:
                regimes[i] = MacroRegime.CAPITULATION
            else:
                regimes[i] = MacroRegime.BEAR_TRENDING
        elif price > e200 and slope < 0:
            regimes[i] = MacroRegime.RECOVERY
        else:
            regimes[i] = MacroRegime.RANGING

    return regimes


# ── Replay Engines ──────────────────────────────────────────────────────


def replay_current_system(signals: list[BarSignal], initial_capital: float = 10_000.0) -> dict:
    """Current system: fixed TP 1.0x ATR, both directions, 1% risk, partial_tp."""
    params = {"min_confluence": 60, "atr_sl_multiplier": 2.0, "max_risk_per_trade": 0.01, "tp_ratio": 1.0}
    return _replay_fixed(signals, params, enable_partial_tp=True, direction_filter=None, initial_capital=initial_capital)


def replay_trailing_only(signals: list[BarSignal], initial_capital: float = 10_000.0) -> dict:
    """Trailing stop on all trades, both directions, 1% risk."""
    return _replay_trailing(signals, min_conf=60, risk_pct=0.01, atr_mult=2.0,
                            trailing_atr_mult=2.0, direction_filter=None, initial_capital=initial_capital)


def replay_regime_adaptive(
    signals: list[BarSignal],
    macro_regimes: list[str],
    initial_capital: float = 10_000.0,
) -> dict:
    """Regime-adaptive strategy: switches between modes based on macro regime."""
    capital = initial_capital
    equity = [capital]
    trades = []
    regime_trades = {r: 0 for r in MacroRegime.ALL}
    regime_pnl = {r: 0.0 for r in MacroRegime.ALL}

    open_trade = None
    pos_size = 0.0
    trailing_high = 0.0
    trailing_low = float("inf")
    current_exit_mode = "fixed"
    current_tp = 0.0
    current_sl = 0.0
    entry_regime = MacroRegime.RANGING

    # Align macro_regimes to signals (macro_regimes is for candles, signals starts at LOOKBACK)
    # We need the regime at the candle index corresponding to each signal
    regime_offset = LOOKBACK  # signals[0] corresponds to candles[LOOKBACK]

    for i, sig in enumerate(signals):
        candle_idx = i + regime_offset
        if candle_idx < len(macro_regimes):
            macro = macro_regimes[candle_idx]
        else:
            macro = MacroRegime.RANGING

        strategy = REGIME_STRATEGY.get(macro, REGIME_STRATEGY[MacroRegime.RANGING])

        if open_trade is not None:
            h, l = sig.high, sig.low

            if current_exit_mode == "trailing":
                # Update trailing levels
                if open_trade["direction"] == "BUY":
                    trailing_high = max(trailing_high, h)
                    trail_sl = trailing_high - sig.atr * open_trade.get("trailing_mult", 2.0)
                    current_sl = max(current_sl, trail_sl)  # Only move up
                    hit_sl = l <= current_sl
                    hit_tp = False  # No fixed TP in trailing mode
                else:
                    trailing_low = min(trailing_low, l)
                    trail_sl = trailing_low + sig.atr * open_trade.get("trailing_mult", 2.0)
                    current_sl = min(current_sl, trail_sl)  # Only move down
                    hit_sl = h >= current_sl
                    hit_tp = False
            else:
                # Fixed TP/SL
                if open_trade["direction"] == "BUY":
                    hit_sl = l <= current_sl
                    hit_tp = h >= current_tp
                else:
                    hit_sl = h >= current_sl
                    hit_tp = l <= current_tp

            if hit_sl or hit_tp:
                exit_price = current_sl if hit_sl else current_tp
                fee = exit_price * pos_size * FEE_RATE
                if open_trade["direction"] == "BUY":
                    gross_pnl = (exit_price - open_trade["entry_price"]) * pos_size
                else:
                    gross_pnl = (open_trade["entry_price"] - exit_price) * pos_size
                pnl = gross_pnl - fee
                capital += pnl

                trades.append({
                    "direction": open_trade["direction"],
                    "pnl": pnl,
                    "exit_mode": current_exit_mode,
                    "regime": entry_regime,
                })
                regime_trades[entry_regime] = regime_trades.get(entry_regime, 0) + 1
                regime_pnl[entry_regime] = regime_pnl.get(entry_regime, 0) + pnl
                open_trade = None

            equity.append(capital)
            continue

        # No open trade -- check entry
        if sig.action in ("BUY", "SELL") and sig.confluence >= strategy["min_confluence"]:
            # Direction filter
            df = strategy.get("direction_filter")
            if df and sig.action != df:
                equity.append(capital)
                continue

            if sig.atr <= 0:
                equity.append(capital)
                continue

            atr_mult = 2.0
            sl_dist = sig.atr * atr_mult
            entry = sig.close
            risk_pct = strategy["risk_pct"]

            if sig.action == "BUY":
                sl = entry - sl_dist
            else:
                sl = entry + sl_dist

            risk_dist = abs(entry - sl)
            if risk_dist <= 0:
                equity.append(capital)
                continue
            pos_size = capital * risk_pct / risk_dist

            entry_fee = entry * pos_size * FEE_RATE
            capital -= entry_fee

            current_exit_mode = strategy["exit_mode"]
            current_sl = sl

            if current_exit_mode == "trailing":
                trailing_high = sig.high
                trailing_low = sig.low
                current_tp = 0  # No fixed TP
                open_trade = {
                    "entry_price": entry,
                    "direction": sig.action,
                    "trailing_mult": strategy.get("trailing_atr_mult", 2.0),
                }
            else:
                tp_ratio = strategy.get("tp_ratio", 1.0)
                if sig.action == "BUY":
                    current_tp = entry + sl_dist * tp_ratio
                else:
                    current_tp = entry - sl_dist * tp_ratio
                open_trade = {"entry_price": entry, "direction": sig.action}

            entry_regime = macro

        equity.append(capital)

    # Close open trade
    if open_trade and signals:
        last = signals[-1]
        fee = last.close * pos_size * FEE_RATE
        if open_trade["direction"] == "BUY":
            gross_pnl = (last.close - open_trade["entry_price"]) * pos_size
        else:
            gross_pnl = (open_trade["entry_price"] - last.close) * pos_size
        pnl = gross_pnl - fee
        capital += pnl
        trades.append({"direction": open_trade["direction"], "pnl": pnl,
                        "exit_mode": current_exit_mode, "regime": entry_regime})
        regime_trades[entry_regime] = regime_trades.get(entry_regime, 0) + 1
        regime_pnl[entry_regime] = regime_pnl.get(entry_regime, 0) + pnl
        equity[-1] = capital

    wins = [t for t in trades if t["pnl"] > 0]
    return {
        "total_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "total_return_pct": (capital - initial_capital) / initial_capital * 100,
        "final_equity": capital,
        "max_drawdown_pct": _max_drawdown(equity),
        "regime_trades": regime_trades,
        "regime_pnl": regime_pnl,
        "equity": equity,
    }


def _replay_fixed(signals, params, enable_partial_tp=False, direction_filter=None,
                   initial_capital=10_000.0) -> dict:
    """Standard fixed TP/SL replay."""
    min_conf = params["min_confluence"]
    atr_mult = params["atr_sl_multiplier"]
    risk_pct = params["max_risk_per_trade"]
    tp_ratio = params.get("tp_ratio", 1.0)

    capital = initial_capital
    equity = [capital]
    trades = []
    open_trade = None
    pos_size = 0.0
    partial_closed = False
    tp2 = 0.0
    partial_pnl = 0.0

    for i, sig in enumerate(signals):
        if open_trade is not None:
            h, l = sig.high, sig.low
            hit_sl = hit_tp = False
            if open_trade["direction"] == "BUY":
                hit_sl = l <= open_trade["sl"]
                hit_tp = h >= open_trade["tp"]
            else:
                hit_sl = h >= open_trade["sl"]
                hit_tp = l <= open_trade["tp"]

            if enable_partial_tp and not partial_closed and hit_tp:
                exit_price = open_trade["tp"]
                half = pos_size * 0.5
                fee = exit_price * half * FEE_RATE
                if open_trade["direction"] == "BUY":
                    pp = (exit_price - open_trade["entry"]) * half - fee
                else:
                    pp = (open_trade["entry"] - exit_price) * half - fee
                partial_pnl = pp
                capital += pp
                open_trade["sl"] = open_trade["entry"]
                open_trade["tp"] = tp2
                partial_closed = True
                pos_size = half
                equity.append(capital)
                continue

            if hit_sl or hit_tp:
                exit_price = open_trade["sl"] if hit_sl else open_trade["tp"]
                fee = exit_price * pos_size * FEE_RATE
                if open_trade["direction"] == "BUY":
                    gross = (exit_price - open_trade["entry"]) * pos_size
                else:
                    gross = (open_trade["entry"] - exit_price) * pos_size
                pnl = gross - fee + partial_pnl
                capital += gross - fee
                trades.append({"pnl": pnl, "direction": open_trade["direction"]})
                open_trade = None

            equity.append(capital)
            continue

        if sig.action in ("BUY", "SELL") and sig.confluence >= min_conf:
            if direction_filter and sig.action != direction_filter:
                equity.append(capital)
                continue
            if sig.atr <= 0:
                equity.append(capital)
                continue

            sl_dist = sig.atr * atr_mult
            entry = sig.close
            if sig.action == "BUY":
                sl = entry - sl_dist
                tp = entry + sl_dist * tp_ratio
                tp2 = entry + sl_dist * 2.618
            else:
                sl = entry + sl_dist
                tp = entry - sl_dist * tp_ratio
                tp2 = entry - sl_dist * 2.618

            risk_dist = abs(entry - sl)
            if risk_dist <= 0:
                equity.append(capital)
                continue
            pos_size = capital * risk_pct / risk_dist
            entry_fee = entry * pos_size * FEE_RATE
            capital -= entry_fee

            open_trade = {"entry": entry, "direction": sig.action, "sl": sl, "tp": tp}
            partial_closed = False
            partial_pnl = 0.0

        equity.append(capital)

    if open_trade and signals:
        last = signals[-1]
        fee = last.close * pos_size * FEE_RATE
        if open_trade["direction"] == "BUY":
            gross = (last.close - open_trade["entry"]) * pos_size
        else:
            gross = (open_trade["entry"] - last.close) * pos_size
        pnl = gross - fee + partial_pnl
        capital += gross - fee
        trades.append({"pnl": pnl, "direction": open_trade["direction"]})
        equity[-1] = capital

    wins = [t for t in trades if t["pnl"] > 0]
    return {
        "total_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "total_return_pct": (capital - initial_capital) / initial_capital * 100,
        "final_equity": capital,
        "max_drawdown_pct": _max_drawdown(equity),
        "equity": equity,
    }


def _replay_trailing(signals, min_conf, risk_pct, atr_mult, trailing_atr_mult,
                      direction_filter, initial_capital=10_000.0) -> dict:
    """Trailing stop replay -- no fixed TP."""
    capital = initial_capital
    equity = [capital]
    trades = []
    open_trade = None
    pos_size = 0.0
    trailing_high = 0.0
    trailing_low = float("inf")
    current_sl = 0.0

    for i, sig in enumerate(signals):
        if open_trade is not None:
            h, l = sig.high, sig.low

            if open_trade["direction"] == "BUY":
                trailing_high = max(trailing_high, h)
                trail_sl = trailing_high - sig.atr * trailing_atr_mult
                current_sl = max(current_sl, trail_sl)
                hit_sl = l <= current_sl
            else:
                trailing_low = min(trailing_low, l)
                trail_sl = trailing_low + sig.atr * trailing_atr_mult
                current_sl = min(current_sl, trail_sl)
                hit_sl = h >= current_sl

            if hit_sl:
                fee = current_sl * pos_size * FEE_RATE
                if open_trade["direction"] == "BUY":
                    gross = (current_sl - open_trade["entry"]) * pos_size
                else:
                    gross = (open_trade["entry"] - current_sl) * pos_size
                pnl = gross - fee
                capital += pnl
                trades.append({"pnl": pnl, "direction": open_trade["direction"]})
                open_trade = None

            equity.append(capital)
            continue

        if sig.action in ("BUY", "SELL") and sig.confluence >= min_conf:
            if direction_filter and sig.action != direction_filter:
                equity.append(capital)
                continue
            if sig.atr <= 0:
                equity.append(capital)
                continue

            sl_dist = sig.atr * atr_mult
            entry = sig.close
            if sig.action == "BUY":
                sl = entry - sl_dist
            else:
                sl = entry + sl_dist

            risk_dist = abs(entry - sl)
            if risk_dist <= 0:
                equity.append(capital)
                continue
            pos_size = capital * risk_pct / risk_dist
            entry_fee = entry * pos_size * FEE_RATE
            capital -= entry_fee

            open_trade = {"entry": entry, "direction": sig.action}
            current_sl = sl
            trailing_high = sig.high
            trailing_low = sig.low

        equity.append(capital)

    if open_trade and signals:
        last = signals[-1]
        fee = last.close * pos_size * FEE_RATE
        if open_trade["direction"] == "BUY":
            gross = (last.close - open_trade["entry"]) * pos_size
        else:
            gross = (open_trade["entry"] - last.close) * pos_size
        pnl = gross - fee
        capital += pnl
        trades.append({"pnl": pnl, "direction": open_trade["direction"]})
        equity[-1] = capital

    wins = [t for t in trades if t["pnl"] > 0]
    return {
        "total_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "total_return_pct": (capital - initial_capital) / initial_capital * 100,
        "final_equity": capital,
        "max_drawdown_pct": _max_drawdown(equity),
        "equity": equity,
    }


def count_confirmations(sig: BarSignal, direction: str) -> int:
    """Count how many of the 8 confirmations pass for entry.

    Confirmations (from Streamlit regime app):
    1. RSI < 90 (not overbought -- for BUY; RSI > 10 for SELL)
    2. Momentum > 1% (for BUY; < -1% for SELL)
    3. Volatility < 6% (not too volatile)
    4. Volume > 20-SMA (above-average volume)
    5. ADX > 25 (trending market)
    6. Price > EMA50 (for BUY; < EMA50 for SELL)
    7. Price > EMA200 (for BUY; < EMA200 for SELL)
    8. MACD > Signal (for BUY; MACD < Signal for SELL)
    """
    count = 0
    if direction == "BUY":
        if sig.rsi < 90:
            count += 1
        if sig.momentum_pct > 1.0:
            count += 1
        if sig.volatility_pct < 6.0:
            count += 1
        if sig.volume_ratio > 1.0:
            count += 1
        if sig.adx > 25:
            count += 1
        if sig.price_vs_ema50 > 0:
            count += 1
        if sig.price_vs_ema200 > 0:
            count += 1
        if sig.macd_above_signal:
            count += 1
    else:  # SELL
        if sig.rsi > 10:
            count += 1
        if sig.momentum_pct < -1.0:
            count += 1
        if sig.volatility_pct < 6.0:
            count += 1
        if sig.volume_ratio > 1.0:
            count += 1
        if sig.adx > 25:
            count += 1
        if sig.price_vs_ema50 < 0:
            count += 1
        if sig.price_vs_ema200 < 0:
            count += 1
        if not sig.macd_above_signal:
            count += 1
    return count


def replay_regime_plus(
    signals: list[BarSignal],
    macro_regimes: list[str],
    initial_capital: float = 10_000.0,
    leverage: float = 1.0,
    min_confirms: int = MIN_CONFIRMATIONS,
    force_trailing: bool = False,
) -> dict:
    """Regime+ strategy: HMM regime + 8-confirmation voting + 48h cooldown + regime-exit.

    Integrates insights from the Streamlit regime-based trading app:
    - Requires min_confirms / 8 confirmations to enter
    - COOLDOWN_BARS bar cooldown after every exit (48h on 4h candles)
    - Force-close on adverse regime change (long in bear/capitulation)
    - Optional leverage multiplier on position sizing
    - force_trailing: override all exit modes to trailing (for aggressive variant)
    """
    capital = initial_capital
    equity = [capital]
    trades = []
    regime_trades = {r: 0 for r in MacroRegime.ALL}
    regime_pnl = {r: 0.0 for r in MacroRegime.ALL}
    confirmation_stats = {"entries_checked": 0, "entries_passed": 0, "total_confirmations": 0}

    open_trade = None
    pos_size = 0.0
    trailing_high = 0.0
    trailing_low = float("inf")
    current_exit_mode = "fixed"
    current_tp = 0.0
    current_sl = 0.0
    entry_regime = MacroRegime.RANGING
    cooldown_remaining = 0  # Bars until allowed to enter again

    regime_offset = LOOKBACK

    for i, sig in enumerate(signals):
        candle_idx = i + regime_offset
        if candle_idx < len(macro_regimes):
            macro = macro_regimes[candle_idx]
        else:
            macro = MacroRegime.RANGING

        strategy = REGIME_STRATEGY.get(macro, REGIME_STRATEGY[MacroRegime.RANGING])

        # Decrement cooldown
        if cooldown_remaining > 0:
            cooldown_remaining -= 1

        if open_trade is not None:
            h, l = sig.high, sig.low

            # === REGIME-EXIT: Force close on adverse regime change ===
            force_close = False
            if open_trade["direction"] == "BUY":
                if macro in (MacroRegime.BEAR_TRENDING, MacroRegime.CAPITULATION):
                    force_close = True
            elif open_trade["direction"] == "SELL":
                if macro in (MacroRegime.STRONG_BULL, MacroRegime.RECOVERY):
                    force_close = True

            if force_close:
                exit_price = sig.close
                fee = exit_price * pos_size * FEE_RATE
                if open_trade["direction"] == "BUY":
                    gross_pnl = (exit_price - open_trade["entry_price"]) * pos_size
                else:
                    gross_pnl = (open_trade["entry_price"] - exit_price) * pos_size
                pnl = gross_pnl - fee
                capital += pnl
                trades.append({
                    "direction": open_trade["direction"], "pnl": pnl,
                    "exit_mode": "regime_exit", "regime": entry_regime,
                    "exit_reason": f"regime_change_to_{macro}",
                })
                regime_trades[entry_regime] = regime_trades.get(entry_regime, 0) + 1
                regime_pnl[entry_regime] = regime_pnl.get(entry_regime, 0) + pnl
                open_trade = None
                cooldown_remaining = COOLDOWN_BARS
                equity.append(capital)
                continue

            # Normal exit logic (same as regime-adaptive)
            if current_exit_mode == "trailing":
                if open_trade["direction"] == "BUY":
                    trailing_high = max(trailing_high, h)
                    trail_sl = trailing_high - sig.atr * open_trade.get("trailing_mult", 2.0)
                    current_sl = max(current_sl, trail_sl)
                    hit_sl = l <= current_sl
                    hit_tp = False
                else:
                    trailing_low = min(trailing_low, l)
                    trail_sl = trailing_low + sig.atr * open_trade.get("trailing_mult", 2.0)
                    current_sl = min(current_sl, trail_sl)
                    hit_sl = h >= current_sl
                    hit_tp = False
            else:
                if open_trade["direction"] == "BUY":
                    hit_sl = l <= current_sl
                    hit_tp = h >= current_tp
                else:
                    hit_sl = h >= current_sl
                    hit_tp = l <= current_tp

            if hit_sl or hit_tp:
                exit_price = current_sl if hit_sl else current_tp
                fee = exit_price * pos_size * FEE_RATE
                if open_trade["direction"] == "BUY":
                    gross_pnl = (exit_price - open_trade["entry_price"]) * pos_size
                else:
                    gross_pnl = (open_trade["entry_price"] - exit_price) * pos_size
                pnl = gross_pnl - fee
                capital += pnl
                trades.append({
                    "direction": open_trade["direction"], "pnl": pnl,
                    "exit_mode": current_exit_mode, "regime": entry_regime,
                })
                regime_trades[entry_regime] = regime_trades.get(entry_regime, 0) + 1
                regime_pnl[entry_regime] = regime_pnl.get(entry_regime, 0) + pnl
                open_trade = None
                cooldown_remaining = COOLDOWN_BARS

            equity.append(capital)
            continue

        # === No open trade -- check entry ===
        # Cooldown check
        if cooldown_remaining > 0:
            equity.append(capital)
            continue

        if sig.action in ("BUY", "SELL") and sig.confluence >= strategy["min_confluence"]:
            # Direction filter (from regime)
            df = strategy.get("direction_filter")
            if df and sig.action != df:
                equity.append(capital)
                continue

            if sig.atr <= 0:
                equity.append(capital)
                continue

            # === 8-CONFIRMATION VOTING ===
            confirmation_stats["entries_checked"] += 1
            n_conf = count_confirmations(sig, sig.action)
            confirmation_stats["total_confirmations"] += n_conf

            if n_conf < min_confirms:
                equity.append(capital)
                continue

            confirmation_stats["entries_passed"] += 1

            # Entry
            atr_mult = 2.0
            sl_dist = sig.atr * atr_mult
            entry = sig.close
            risk_pct = strategy["risk_pct"]

            if sig.action == "BUY":
                sl = entry - sl_dist
            else:
                sl = entry + sl_dist

            risk_dist = abs(entry - sl)
            if risk_dist <= 0:
                equity.append(capital)
                continue
            pos_size = capital * risk_pct * leverage / risk_dist

            entry_fee = entry * pos_size * FEE_RATE
            capital -= entry_fee

            current_exit_mode = "trailing" if force_trailing else strategy["exit_mode"]
            current_sl = sl

            if current_exit_mode == "trailing":
                trailing_high = sig.high
                trailing_low = sig.low
                current_tp = 0
                open_trade = {
                    "entry_price": entry,
                    "direction": sig.action,
                    "trailing_mult": strategy.get("trailing_atr_mult", 2.0),
                }
            else:
                tp_ratio = strategy.get("tp_ratio", 1.0)
                if sig.action == "BUY":
                    current_tp = entry + sl_dist * tp_ratio
                else:
                    current_tp = entry - sl_dist * tp_ratio
                open_trade = {"entry_price": entry, "direction": sig.action}

            entry_regime = macro

        equity.append(capital)

    # Close open trade at end
    if open_trade and signals:
        last = signals[-1]
        fee = last.close * pos_size * FEE_RATE
        if open_trade["direction"] == "BUY":
            gross_pnl = (last.close - open_trade["entry_price"]) * pos_size
        else:
            gross_pnl = (open_trade["entry_price"] - last.close) * pos_size
        pnl = gross_pnl - fee
        capital += pnl
        trades.append({"direction": open_trade["direction"], "pnl": pnl,
                        "exit_mode": current_exit_mode, "regime": entry_regime})
        regime_trades[entry_regime] = regime_trades.get(entry_regime, 0) + 1
        regime_pnl[entry_regime] = regime_pnl.get(entry_regime, 0) + pnl
        equity[-1] = capital

    wins = [t for t in trades if t["pnl"] > 0]
    regime_exits = sum(1 for t in trades if t.get("exit_mode") == "regime_exit")
    return {
        "total_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "total_return_pct": (capital - initial_capital) / initial_capital * 100,
        "final_equity": capital,
        "max_drawdown_pct": _max_drawdown(equity),
        "regime_trades": regime_trades,
        "regime_pnl": regime_pnl,
        "regime_exits": regime_exits,
        "confirmation_stats": confirmation_stats,
        "equity": equity,
    }


def _max_drawdown(equity: list[float]) -> float:
    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return max_dd


def buy_and_hold_return(signals: list[BarSignal], capital: float = 10_000.0) -> dict:
    if not signals:
        return {"total_return_pct": 0, "final_equity": capital, "max_drawdown_pct": 0}
    start = signals[0].close
    end = signals[-1].close
    qty = capital / start
    entry_fee = capital * FEE_RATE
    exit_value = qty * end
    exit_fee = exit_value * FEE_RATE
    net = exit_value - entry_fee - exit_fee

    # B&H equity curve
    equity = []
    for s in signals:
        val = qty * s.close - entry_fee - (qty * s.close * FEE_RATE)
        equity.append(val)

    return {
        "total_return_pct": (net - capital) / capital * 100,
        "final_equity": net,
        "max_drawdown_pct": _max_drawdown(equity) if equity else 0,
    }


# ── Report Generation ───────────────────────────────────────────────────


def generate_report(all_results: dict, elapsed: float) -> str:
    L = []
    L.append("# Regime-Adaptive Backtest Results\n")
    L.append(f"> Generated on 2026-03-04 | Runtime: {elapsed:.0f}s")
    L.append(f"> Timeframe: 4h candles (Jan 2021 - Mar 2026)")
    L.append(f"> Transaction costs: {FEE_RATE*100:.3f}% per side")
    L.append(f"> Starting capital: ${INITIAL_CAPITAL:,.0f} per pair")
    L.append(f"> HMM training: rolling {HMM_TRAIN_WINDOW}-bar window, retrain every {HMM_RETRAIN_INTERVAL} bars")
    L.append(f"> Regime+ confirmations: {MIN_CONFIRMATIONS}/8 required | Cooldown: {COOLDOWN_BARS} bars (48h)\n")

    # ── Strategy comparison ──
    L.append("## 1. Strategy Comparison (Return %)\n")
    L.append("| Pair | Current | Trailing | Rules | HMM | R+ 1x | R+ 2.5x | R+ AGG 4x | B&H |")
    L.append("|------|---------|----------|-------|-----|-------|---------|----------|-----|")

    strat_keys = ["current", "trailing", "regime_rules", "regime_hmm", "regime_plus", "regime_plus_lev", "regime_plus_agg", "bh"]
    totals = {k: 0 for k in strat_keys}
    total_start = 0

    for pair in sorted(all_results.keys()):
        r = all_results[pair]
        pair_short = pair.replace("-4h", "")

        vals = {k: r[k]["total_return_pct"] for k in strat_keys}
        best_val = max(vals.values())

        def fmt(k):
            v = vals[k]
            trades = r[k].get("total_trades", 0)
            bold = "**" if v == best_val else ""
            return f"{bold}{v:+.1f}%{bold} ({trades}t)"

        L.append(
            f"| {pair_short} | {fmt('current')} | {fmt('trailing')} | "
            f"{fmt('regime_rules')} | {fmt('regime_hmm')} | "
            f"{fmt('regime_plus')} | {fmt('regime_plus_lev')} | "
            f"{fmt('regime_plus_agg')} | "
            f"{r['bh']['total_return_pct']:+.1f}% |"
        )
        for k in strat_keys:
            totals[k] += r[k]["final_equity"]
        total_start += INITIAL_CAPITAL

    # Portfolio row
    for key in totals:
        totals[key] = (totals[key] - total_start) / total_start * 100

    L.append(
        f"| **PORTFOLIO** | **{totals['current']:+.1f}%** | "
        f"**{totals['trailing']:+.1f}%** | "
        f"**{totals['regime_rules']:+.1f}%** | **{totals['regime_hmm']:+.1f}%** | "
        f"**{totals['regime_plus']:+.1f}%** | **{totals['regime_plus_lev']:+.1f}%** | "
        f"**{totals['regime_plus_agg']:+.1f}%** | "
        f"**{totals['bh']:+.1f}%** |"
    )
    L.append("")

    # ── Drawdown comparison ──
    L.append("---\n")
    L.append("## 2. Max Drawdown Comparison\n")
    L.append("| Pair | Current | Trailing | Rules | HMM | R+ 1x | R+ 2.5x | R+ AGG 4x | B&H |")
    L.append("|------|---------|----------|-------|-----|-------|---------|----------|-----|")

    for pair in sorted(all_results.keys()):
        r = all_results[pair]
        pair_short = pair.replace("-4h", "")
        cells = [f"-{r[k]['max_drawdown_pct']:.1f}%" for k in strat_keys]
        L.append(f"| {pair_short} | {' | '.join(cells)} |")
    L.append("")

    # ── Win rate comparison ──
    L.append("---\n")
    L.append("## 3. Win Rate Comparison\n")
    L.append("| Pair | Current | Trailing | Rules | HMM | R+ 1x | R+ 2.5x | R+ AGG 4x |")
    L.append("|------|---------|----------|-------|-----|-------|---------|----------|")

    for pair in sorted(all_results.keys()):
        r = all_results[pair]
        pair_short = pair.replace("-4h", "")
        cells = [f"{r[k]['win_rate']:.0f}%" for k in strat_keys if k != "bh"]
        L.append(f"| {pair_short} | {' | '.join(cells)} |")
    L.append("")

    # ── Regime+ Details ──
    L.append("---\n")
    L.append("## 4. Regime+ Strategy Details\n")
    L.append("The Regime+ strategy adds three key mechanisms on top of HMM regime-adaptive:\n")
    L.append(f"- **8-Confirmation Voting:** {MIN_CONFIRMATIONS}/8 must pass before entry")
    L.append("  (RSI<90, Momentum>1%, Vol<6%, Volume>20-SMA, ADX>25, Price>EMA50, Price>EMA200, MACD>Signal)")
    L.append(f"- **48h Cooldown:** {COOLDOWN_BARS} bars after every exit before re-entry")
    L.append("- **Regime-Exit:** Force close when regime flips to adverse (long->bear, short->bull)\n")
    L.append("### Variants Tested\n")
    L.append("| Variant | Leverage | Confirmations | Exit Mode | Description |")
    L.append("|---------|----------|---------------|-----------|-------------|")
    L.append(f"| **R+ 1x** | 1.0x | {MIN_CONFIRMATIONS}/8 | Per-regime | Conservative baseline |")
    L.append(f"| **R+ 2.5x** | 2.5x | {MIN_CONFIRMATIONS}/8 | Per-regime | Leveraged version |")
    L.append("| **R+ AGG 4x** | 4.0x | 5/8 | All trailing | Aggressive: fewer confirmations, higher leverage, trailing stops |\n")

    L.append("### Confirmation Filter Impact\n")
    L.append("| Pair | Signals Checked | Passed Filter | Filter Rate | Regime Exits |")
    L.append("|------|----------------|--------------|------------|-------------|")

    for pair in sorted(all_results.keys()):
        r = all_results[pair]["regime_plus"]
        pair_short = pair.replace("-4h", "")
        cs = r.get("confirmation_stats", {})
        checked = cs.get("entries_checked", 0)
        passed = cs.get("entries_passed", 0)
        rate = passed / checked * 100 if checked > 0 else 0
        regime_exits = r.get("regime_exits", 0)
        L.append(f"| {pair_short} | {checked} | {passed} | {rate:.0f}% | {regime_exits} |")
    L.append("")

    # ── Regime breakdown (Regime+) ──
    L.append("---\n")
    L.append("## 5. Regime Breakdown: Regime+ Strategy (1x)\n")
    L.append("Trades and P&L per detected macro regime.\n")
    L.append("| Pair | Strong Bull | Bull Correction | Ranging | Bear Trending | Capitulation | Recovery |")
    L.append("|------|-----------|----------------|---------|-------------|-------------|----------|")

    for pair in sorted(all_results.keys()):
        r = all_results[pair]["regime_plus"]
        pair_short = pair.replace("-4h", "")
        cells = []
        for regime in MacroRegime.ALL:
            rt = r.get("regime_trades", {}).get(regime, 0)
            rp = r.get("regime_pnl", {}).get(regime, 0.0)
            if rt > 0:
                cells.append(f"{rt}t ${rp:+,.0f}")
            else:
                cells.append("-")
        L.append(f"| {pair_short} | {' | '.join(cells)} |")
    L.append("")

    # ── Regime time distribution ──
    L.append("---\n")
    L.append("## 6. Regime Time Distribution (HMM)\n")
    L.append("Percentage of bars classified into each macro regime.\n")
    L.append("| Pair | Strong Bull | Bull Correction | Ranging | Bear Trending | Capitulation | Recovery |")
    L.append("|------|-----------|----------------|---------|-------------|-------------|----------|")

    for pair in sorted(all_results.keys()):
        r = all_results[pair]
        dist = r.get("regime_distribution", {})
        pair_short = pair.replace("-4h", "")
        cells = [f"{dist.get(regime, 0):.1f}%" for regime in MacroRegime.ALL]
        L.append(f"| {pair_short} | {' | '.join(cells)} |")
    L.append("")

    # ── Key findings ──
    L.append("---\n")
    L.append("## 7. Key Findings\n")

    # Which strategy wins?
    strategies = {
        "Current System": totals["current"],
        "Trailing Only": totals["trailing"],
        "Regime Rules": totals["regime_rules"],
        "Regime HMM": totals["regime_hmm"],
        "Regime+ (1x)": totals["regime_plus"],
        "Regime+ (2.5x)": totals["regime_plus_lev"],
        "Regime+ AGG (4x)": totals["regime_plus_agg"],
        "Buy & Hold": totals["bh"],
    }
    best_name = max(strategies, key=strategies.get)
    L.append(f"- **Best overall strategy:** {best_name} ({strategies[best_name]:+.1f}%)")

    # Key comparisons
    L.append(f"- **Current system:** {totals['current']:+.1f}%")
    L.append(f"- **Trailing stops:** {totals['trailing']:+.1f}% ({totals['trailing'] - totals['current']:+.1f}% vs current)")
    L.append(f"- **Regime HMM:** {totals['regime_hmm']:+.1f}% ({totals['regime_hmm'] - totals['current']:+.1f}% vs current)")
    L.append(f"- **Regime+ (1x):** {totals['regime_plus']:+.1f}% ({totals['regime_plus'] - totals['current']:+.1f}% vs current)")
    L.append(f"- **Regime+ (2.5x):** {totals['regime_plus_lev']:+.1f}% ({totals['regime_plus_lev'] - totals['current']:+.1f}% vs current)")
    L.append(f"- **Regime+ AGG (4x):** {totals['regime_plus_agg']:+.1f}% ({totals['regime_plus_agg'] - totals['current']:+.1f}% vs current)")
    L.append(f"- **Buy & Hold:** {totals['bh']:+.1f}%")

    L.append("")
    L.append("### Insights from HMM Regime Terminal Approach\n")
    L.append("Based on the Jim Simons / RETech regime terminal model:")
    L.append("- HMM detects hidden market states that drive strategy selection")
    L.append("- Confirmation voting acts as a second-factor authentication for entries")
    L.append("- Signal hysteresis (cooldown) prevents overtrading in choppy transitions")
    L.append("- Regime-exit prevents holding through structural market shifts")
    L.append("- The model is a living algorithm -- retrain and evolve as market structure changes")

    L.append("")
    return "\n".join(L)


# ── Main ────────────────────────────────────────────────────────────────


def main():
    overall_start = time.time()

    print("=" * 70)
    print("  Regime-Adaptive Backtest (HMM + Trailing Stops)")
    print("=" * 70)

    # ── Load data ──
    print("\n[1/5] Loading 4h data...")
    pairs = discover_4h_pairs(DATA_DIR)
    target = ["BTC/USD-4h", "ETH/USD-4h", "SOL/USD-4h", "BNB/USD-4h",
              "ADA/USD-4h", "DOGE/USD-4h", "LINK/USD-4h", "XRP/USD-4h"]

    pairs_candles = {}
    for pair_key in target:
        if pair_key not in pairs:
            continue
        df = load_csv(pairs[pair_key]["file"])
        if len(df) < 300:
            continue
        pairs_candles[pair_key] = df
        start_ts = int(df["time"].iloc[0]) if "time" in df.columns else 0
        start_date = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d") if start_ts > 0 else "?"
        end_ts = int(df["time"].iloc[-1]) if "time" in df.columns else 0
        end_date = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d") if end_ts > 0 else "?"
        print(f"  {pair_key}: {len(df):,} bars ({start_date} to {end_date})")

    # ── Pre-compute signals ──
    print(f"\n[2/5] Pre-computing pipeline signals ({len(pairs_candles)} pairs)...")
    pairs_signals = {}
    for pair, candles in pairs_candles.items():
        t0 = time.time()
        _indicator_cache.setup(candles)
        signals = precompute_signals(candles, pair, "4h")
        pairs_signals[pair] = signals
        el = time.time() - t0
        n_sig = sum(1 for s in signals if s.action in ("BUY", "SELL"))
        print(f"  {pair}: {len(signals)} bars, {n_sig} signals, {el:.1f}s")

    # ── Detect macro regimes ──
    print(f"\n[3/5] Detecting macro regimes...")

    pairs_regimes_hmm = {}
    pairs_regimes_rules = {}
    for pair, candles in pairs_candles.items():
        t0 = time.time()

        # HMM-based
        hmm_regimes = detect_macro_regimes_hmm(candles, n_states=6)
        pairs_regimes_hmm[pair] = hmm_regimes

        # Rule-based
        rule_regimes = detect_macro_regimes_rules(candles)
        pairs_regimes_rules[pair] = rule_regimes

        # Distribution
        total = len(hmm_regimes)
        dist = {}
        for regime in MacroRegime.ALL:
            count = sum(1 for r in hmm_regimes if r == regime)
            dist[regime] = count / total * 100
        el = time.time() - t0
        regime_summary = ", ".join(f"{r.replace('_', ' ')[:8]}={dist.get(r, 0):.0f}%" for r in MacroRegime.ALL if dist.get(r, 0) > 1)
        print(f"  {pair}: {regime_summary} ({el:.1f}s)")

    # ── Run all strategies ──
    print(f"\n[4/5] Running strategy comparison (8 variants per pair)...")

    all_results = {}
    for pair in sorted(pairs_signals.keys()):
        signals = pairs_signals[pair]
        candles = pairs_candles[pair]

        # 1. Current system
        current = replay_current_system(signals)

        # 2. Trailing only
        trailing = replay_trailing_only(signals)

        # 3. Regime-adaptive (rules)
        regime_rules = replay_regime_adaptive(signals, pairs_regimes_rules[pair])

        # 4. Regime-adaptive (HMM)
        regime_hmm = replay_regime_adaptive(signals, pairs_regimes_hmm[pair])

        # 5. Regime+ (HMM + confirmations + cooldown + regime-exit) @ 1x
        regime_plus = replay_regime_plus(signals, pairs_regimes_hmm[pair], leverage=1.0)

        # 6. Regime+ @ 2.5x leverage
        regime_plus_lev = replay_regime_plus(signals, pairs_regimes_hmm[pair], leverage=2.5)

        # 7. Regime+ AGGRESSIVE: 4x leverage, 5/8 confirmations, trailing stop
        regime_plus_agg = replay_regime_plus(signals, pairs_regimes_hmm[pair],
                                              leverage=4.0, min_confirms=5, force_trailing=True)

        # 8. Buy-and-hold
        bh = buy_and_hold_return(signals)

        # Regime distribution
        total = len(pairs_regimes_hmm[pair])
        dist = {}
        for regime in MacroRegime.ALL:
            count = sum(1 for r in pairs_regimes_hmm[pair] if r == regime)
            dist[regime] = count / total * 100

        all_results[pair] = {
            "current": current,
            "trailing": trailing,
            "regime_rules": regime_rules,
            "regime_hmm": regime_hmm,
            "regime_plus": regime_plus,
            "regime_plus_lev": regime_plus_lev,
            "regime_plus_agg": regime_plus_agg,
            "bh": bh,
            "regime_distribution": dist,
        }

        cs = regime_plus.get("confirmation_stats", {})
        filter_rate = (cs.get("entries_passed", 0) / cs.get("entries_checked", 1) * 100) if cs.get("entries_checked", 0) > 0 else 0
        print(f"  {pair}: Current {current['total_return_pct']:+.1f}% | "
              f"Trail {trailing['total_return_pct']:+.1f}% | "
              f"Rules {regime_rules['total_return_pct']:+.1f}% | "
              f"HMM {regime_hmm['total_return_pct']:+.1f}% | "
              f"R+ {regime_plus['total_return_pct']:+.1f}% | "
              f"R+2.5x {regime_plus_lev['total_return_pct']:+.1f}% | "
              f"R+AGG {regime_plus_agg['total_return_pct']:+.1f}% | "
              f"B&H {bh['total_return_pct']:+.1f}%")

    # ── Generate report ──
    print(f"\n[5/5] Generating report...")
    elapsed = time.time() - overall_start
    report = generate_report(all_results, elapsed)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'=' * 70}")
    print(f"  Report saved to: {OUTPUT_PATH}")
    print(f"  Total runtime: {elapsed:.0f}s")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
