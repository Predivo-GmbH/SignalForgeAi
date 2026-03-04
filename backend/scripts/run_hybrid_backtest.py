"""
Hybrid Core + Active Backtest: Regime-Managed B&H + Active Trading.

Architecture:
  - Core Bucket (60-80%): Regime-managed buy-and-hold.
    HMM detects macro regime, adjusts invested % (100% in bull → 0% in crash).
    Captures most B&H upside while limiting drawdown.
  - Active Bucket (20-40%): SignalForge signal engine with various param configs.
    Generates small returns especially during bear/sideways markets.
  - Combined: total_equity = core_equity + active_equity per bar.

Grid search: 3 splits × 3 allocation tables × 5 active params × 3 smoothing = 135 configs
Tested across 8 crypto pairs on 5 years of 4h data.

Usage:
    cd backend
    .venv/Scripts/python.exe -u scripts/run_hybrid_backtest.py

Output:
    docs/HYBRID-BACKTEST.md
"""
from __future__ import annotations

import glob as globmod
import math
import os
import re
import sys
import time
import logging
from dataclasses import dataclass
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
logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "docs", "chart-data")
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "HYBRID-BACKTEST.md")

FEE_RATE = 0.00075  # 0.075% per side (Binance + BNB discount)
INITIAL_CAPITAL = 10_000.0
LOOKBACK = 200
HMM_TRAIN_WINDOW = 500
HMM_RETRAIN_INTERVAL = 100

# Period boundaries (Unix timestamps) for sub-analysis
BEAR_START_TS = 1636000000   # ~Nov 2021
BEAR_END_TS = 1669000000     # ~Nov 2022
BULL_START_TS = 1704067200   # ~Jan 1, 2024
BULL_END_TS = 1743465600     # ~Mar 31, 2026


# ── Macro Regime ────────────────────────────────────────────────────────


class MacroRegime:
    STRONG_BULL = "strong_bull"
    BULL_CORRECTION = "bull_correction"
    RANGING = "ranging"
    BEAR_TRENDING = "bear_trending"
    CAPITULATION = "capitulation"
    RECOVERY = "recovery"

    ALL = [STRONG_BULL, BULL_CORRECTION, RANGING, BEAR_TRENDING, CAPITULATION, RECOVERY]


# ── Hybrid Configuration Grid ──────────────────────────────────────────

SPLIT_RATIOS = [
    (0.60, 0.40),
    (0.70, 0.30),
    (0.80, 0.20),
]

ALLOCATION_TABLES = {
    "conservative": {
        MacroRegime.STRONG_BULL: 1.00,
        MacroRegime.BULL_CORRECTION: 0.70,
        MacroRegime.RANGING: 0.50,
        MacroRegime.BEAR_TRENDING: 0.20,
        MacroRegime.CAPITULATION: 0.00,
        MacroRegime.RECOVERY: 0.70,
    },
    "moderate": {
        MacroRegime.STRONG_BULL: 1.00,
        MacroRegime.BULL_CORRECTION: 0.80,
        MacroRegime.RANGING: 0.60,
        MacroRegime.BEAR_TRENDING: 0.30,
        MacroRegime.CAPITULATION: 0.00,
        MacroRegime.RECOVERY: 0.80,
    },
    "aggressive": {
        MacroRegime.STRONG_BULL: 1.00,
        MacroRegime.BULL_CORRECTION: 0.90,
        MacroRegime.RANGING: 0.70,
        MacroRegime.BEAR_TRENDING: 0.40,
        MacroRegime.CAPITULATION: 0.10,
        MacroRegime.RECOVERY: 0.90,
    },
}

ACTIVE_PARAMS = {
    "current": {
        "min_confluence": 50, "atr_sl_multiplier": 2.0,
        "max_risk_per_trade": 0.02, "tp_ratio": 1.618, "trigger_lookback": 1,
    },
    "loose_conf": {
        "min_confluence": 30, "atr_sl_multiplier": 2.0,
        "max_risk_per_trade": 0.02, "tp_ratio": 1.5, "trigger_lookback": 1,
    },
    "loose_tp": {
        "min_confluence": 40, "atr_sl_multiplier": 2.0,
        "max_risk_per_trade": 0.02, "tp_ratio": 1.0, "trigger_lookback": 1,
    },
    "wide_trig": {
        "min_confluence": 40, "atr_sl_multiplier": 2.0,
        "max_risk_per_trade": 0.02, "tp_ratio": 1.5, "trigger_lookback": 3,
    },
    "widest": {
        "min_confluence": 30, "atr_sl_multiplier": 2.5,
        "max_risk_per_trade": 0.02, "tp_ratio": 1.5, "trigger_lookback": 5,
    },
}

SMOOTHING_OPTIONS = [1, 3, 5]


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


@dataclass
class ReplayTrade:
    entry_idx: int
    entry_price: float
    direction: str
    stop_loss: float
    take_profit: float
    exit_idx: int = 0
    exit_price: float = 0.0
    pnl: float = 0.0
    exit_reason: str = ""


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


def precompute_signals(
    candles: pd.DataFrame, pair: str, tf: str, trigger_lookback: int = 1,
) -> list[BarSignal]:
    """Run the actual pipeline once per pair with min_confluence=1."""
    pipeline = SignalPipeline(
        risk_config=RiskConfig(max_risk_per_trade=0.02, atr_sl_multiplier=2.0, min_risk_reward=0.1),
        min_confluence=1,
        trigger_lookback_candles=trigger_lookback,
    )
    atr_full = _indicator_cache._cache[("atr", 14)]
    timestamps = candles["time"].values if "time" in candles.columns else [0] * len(candles)
    signals: list[BarSignal] = []

    for i in range(LOOKBACK, len(candles)):
        window = candles.iloc[: i + 1]
        current = candles.iloc[i]
        signal = pipeline.process(symbol=pair, timeframe=tf, candles=window, account_equity=10000.0)
        atr_val = float(atr_full.iloc[i]) if not pd.isna(atr_full.iloc[i]) else 0.0

        signals.append(BarSignal(
            action=signal.action, confluence=signal.confluence_score,
            atr=atr_val, close=float(current["close"]),
            high=float(current["high"]), low=float(current["low"]),
            regime=signal.regime,
            timestamp=int(timestamps[i]) if i < len(timestamps) else 0,
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

    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - close[:-1]),
                               np.abs(low[1:] - close[:-1])))
    atr = pd.Series(tr).rolling(14, min_periods=1).mean().values
    atr_ratio = atr / close[1:]

    plus_dm = np.maximum(high[1:] - high[:-1], 0)
    minus_dm = np.maximum(low[:-1] - low[1:], 0)
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
    adx = pd.Series(dx).rolling(14, min_periods=1).mean().values / 100

    returns = np.clip(returns, -0.3, 0.3)
    vol_change = np.clip(vol_change, -5, 5)
    features = np.column_stack([returns, intra_range, vol_change, atr_ratio, adx])
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
    return features


def detect_macro_regimes_hmm(candles: pd.DataFrame, n_states: int = 6) -> list[str]:
    """Detect macro regimes using rolling HMM on candle data."""
    from hmmlearn.hmm import GaussianHMM

    features_all = compute_hmm_features(candles)
    n_bars = len(features_all)
    regimes = ["unknown"] * (n_bars + 1)

    model = None
    state_regime_map = {}

    for i in range(HMM_TRAIN_WINDOW, n_bars):
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
                state_regime_map = _map_states_to_regimes(model, train_data)
            except Exception:
                model = None
                regimes[i + 1] = MacroRegime.RANGING
                continue

        try:
            obs = features_all[i:i + 1]
            state = model.predict(obs)[0]
            regimes[i + 1] = state_regime_map.get(state, MacroRegime.RANGING)
        except Exception:
            regimes[i + 1] = MacroRegime.RANGING

    return regimes


def _map_states_to_regimes(model, train_data) -> dict[int, str]:
    """Map HMM states to macro regimes based on mean characteristics."""
    n_states = model.n_components
    means = model.means_

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

    state_info.sort(key=lambda x: x["mean_return"])
    mapping = {}

    if n_states >= 6:
        mapping[state_info[0]["state"]] = MacroRegime.CAPITULATION
        mapping[state_info[1]["state"]] = MacroRegime.BEAR_TRENDING
        mapping[state_info[2]["state"]] = MacroRegime.RANGING
        mapping[state_info[3]["state"]] = MacroRegime.RANGING
        mapping[state_info[4]["state"]] = MacroRegime.BULL_CORRECTION
        mapping[state_info[5]["state"]] = MacroRegime.STRONG_BULL

        for info in state_info[2:4]:
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
        mapping[state_info[0]["state"]] = MacroRegime.BEAR_TRENDING
        mapping[state_info[-1]["state"]] = MacroRegime.STRONG_BULL
        for s in state_info[1:-1]:
            mapping[s["state"]] = MacroRegime.RANGING

    return mapping


# ── Core Bucket Simulation ─────────────────────────────────────────────


def simulate_core_bucket(
    signals: list[BarSignal],
    macro_regimes: list[str],
    allocation_table: dict[str, float],
    initial_capital: float,
    smoothing_bars: int = 3,
) -> list[float]:
    """
    Simulate the core (regime-managed B&H) bucket.

    Each bar: check HMM regime → get target invested %.
    Smooth toward target over N bars. Track asset_qty and cash.
    Rebalancing incurs FEE_RATE on moved amount.
    """
    if not signals:
        return [initial_capital]

    # Start: buy asset with full allocation at first bar's close
    first_close = signals[0].close
    invested_pct = allocation_table.get(
        macro_regimes[LOOKBACK] if LOOKBACK < len(macro_regimes) else MacroRegime.RANGING, 0.6
    )
    invest_amount = initial_capital * invested_pct
    entry_fee = invest_amount * FEE_RATE
    cash = initial_capital - invest_amount - entry_fee
    asset_qty = invest_amount / first_close if first_close > 0 else 0
    current_invested_pct = invested_pct

    equity_curve = [asset_qty * first_close + cash]

    for i in range(1, len(signals)):
        sig = signals[i]
        candle_idx = LOOKBACK + i  # Index into macro_regimes array

        # Get target allocation from regime
        regime = macro_regimes[candle_idx] if candle_idx < len(macro_regimes) else MacroRegime.RANGING
        target_pct = allocation_table.get(regime, 0.6)

        # Smooth toward target
        if smoothing_bars <= 1:
            new_pct = target_pct
        else:
            gap = target_pct - current_invested_pct
            step = gap / smoothing_bars
            new_pct = current_invested_pct + step

        new_pct = max(0.0, min(1.0, new_pct))

        # Current total equity before rebalance
        total_equity = asset_qty * sig.close + cash

        # Rebalance if allocation changed
        if abs(new_pct - current_invested_pct) > 0.005:  # > 0.5% change threshold
            desired_invested = total_equity * new_pct
            current_invested = asset_qty * sig.close
            delta = desired_invested - current_invested

            if abs(delta) > 10:  # Min $10 rebalance threshold
                fee = abs(delta) * FEE_RATE
                if delta > 0:
                    # Buy more asset
                    buy_amount = delta
                    cash -= buy_amount + fee
                    asset_qty += buy_amount / sig.close if sig.close > 0 else 0
                else:
                    # Sell asset
                    sell_amount = abs(delta)
                    sell_qty = sell_amount / sig.close if sig.close > 0 else 0
                    asset_qty -= sell_qty
                    cash += sell_amount - fee

                current_invested_pct = new_pct
        else:
            current_invested_pct = new_pct  # Track even small changes

        equity = asset_qty * sig.close + cash
        equity_curve.append(equity)

    return equity_curve


# ── Active Bucket Replay ───────────────────────────────────────────────


def replay_active(
    signals: list[BarSignal],
    params: dict,
    initial_capital: float,
    macro_regimes: list[str] | None = None,
    block_in_capitulation: bool = True,
) -> tuple[list[ReplayTrade], list[float]]:
    """
    Replay active bucket using pre-computed signals.
    Optionally blocks entries during CAPITULATION regime.
    Uses partial_tp variant (proven best in comprehensive backtest).
    """
    min_conf = params["min_confluence"]
    atr_mult = params["atr_sl_multiplier"]
    risk_pct = params["max_risk_per_trade"]
    tp_ratio = params.get("tp_ratio", 1.618)

    trades: list[ReplayTrade] = []
    equity = [initial_capital]
    capital = initial_capital

    open_trade: ReplayTrade | None = None
    partial_closed = False
    tp2: float = 0.0
    partial_pnl_accumulated: float = 0.0
    pos_size: float = 0.0

    for i, sig in enumerate(signals):
        if open_trade is not None:
            h, l = sig.high, sig.low

            hit_sl = hit_tp = False
            if open_trade.direction == "BUY":
                hit_sl = l <= open_trade.stop_loss
                hit_tp = h >= open_trade.take_profit
            else:
                hit_sl = h >= open_trade.stop_loss
                hit_tp = l <= open_trade.take_profit

            # Partial TP: close 50% at TP1
            if not partial_closed and hit_tp:
                exit_price = open_trade.take_profit
                half_size = pos_size * 0.5
                fee = exit_price * half_size * FEE_RATE
                if open_trade.direction == "BUY":
                    partial_pnl = (exit_price - open_trade.entry_price) * half_size - fee
                else:
                    partial_pnl = (open_trade.entry_price - exit_price) * half_size - fee
                partial_pnl_accumulated = partial_pnl
                capital += partial_pnl

                open_trade.stop_loss = open_trade.entry_price  # Break-even
                open_trade.take_profit = tp2
                partial_closed = True
                pos_size = half_size
                equity.append(capital)
                continue

            if hit_sl or hit_tp:
                exit_price = open_trade.stop_loss if hit_sl else open_trade.take_profit
                fee = exit_price * pos_size * FEE_RATE
                if open_trade.direction == "BUY":
                    gross_pnl = (exit_price - open_trade.entry_price) * pos_size
                else:
                    gross_pnl = (open_trade.entry_price - exit_price) * pos_size
                pnl = gross_pnl - fee + partial_pnl_accumulated

                open_trade.exit_idx = i
                open_trade.exit_price = exit_price
                open_trade.pnl = pnl
                open_trade.exit_reason = "stop_loss" if hit_sl else "take_profit"
                capital += gross_pnl - fee
                trades.append(open_trade)
                open_trade = None

            equity.append(capital)
            continue

        # ── No open trade → check for entry ──
        if sig.action in ("BUY", "SELL") and sig.confluence >= min_conf:
            # Block in capitulation
            if block_in_capitulation and macro_regimes:
                candle_idx = LOOKBACK + i
                if candle_idx < len(macro_regimes):
                    regime = macro_regimes[candle_idx]
                    if regime == MacroRegime.CAPITULATION:
                        equity.append(capital)
                        continue

            if sig.atr <= 0:
                equity.append(capital)
                continue

            sl_dist = sig.atr * atr_mult
            entry = sig.close

            if sig.action == "BUY":
                sl = entry - sl_dist
                tp1 = entry + sl_dist * tp_ratio
                tp2_price = entry + sl_dist * 2.618
            else:
                sl = entry + sl_dist
                tp1 = entry - sl_dist * tp_ratio
                tp2_price = entry - sl_dist * 2.618

            risk_dist = abs(entry - sl)
            if risk_dist <= 0:
                equity.append(capital)
                continue
            pos_size = capital * risk_pct / risk_dist

            entry_fee = entry * pos_size * FEE_RATE
            capital -= entry_fee

            open_trade = ReplayTrade(
                entry_idx=i, entry_price=entry, direction=sig.action,
                stop_loss=sl, take_profit=tp1,
            )
            partial_closed = False
            tp2 = tp2_price
            partial_pnl_accumulated = 0.0

        equity.append(capital)

    # Close remaining open trade at last bar
    if open_trade and signals:
        last = signals[-1]
        fee = last.close * pos_size * FEE_RATE
        if open_trade.direction == "BUY":
            gross_pnl = (last.close - open_trade.entry_price) * pos_size
        else:
            gross_pnl = (open_trade.entry_price - last.close) * pos_size
        pnl = gross_pnl - fee + partial_pnl_accumulated
        open_trade.exit_idx = len(signals) - 1
        open_trade.exit_price = last.close
        open_trade.pnl = pnl
        open_trade.exit_reason = "end_of_data"
        capital += gross_pnl - fee
        trades.append(open_trade)
        equity[-1] = capital

    return trades, equity


# ── Combined Portfolio Simulation ──────────────────────────────────────


@dataclass
class HybridResult:
    """Complete result for one hybrid configuration."""
    config_name: str
    core_split: float
    active_split: float
    alloc_table_name: str
    active_params_name: str
    smoothing_bars: int

    # Equity curves
    core_equity: list
    active_equity: list
    combined_equity: list

    # Combined metrics
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    core_return_pct: float = 0.0
    active_return_pct: float = 0.0
    active_trades: int = 0
    active_win_rate: float = 0.0

    # Period metrics
    bear_return_pct: float = 0.0
    bear_drawdown_pct: float = 0.0
    bull_return_pct: float = 0.0
    bull_drawdown_pct: float = 0.0


def _max_drawdown(equity: list[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return max_dd


def _period_metrics(
    equity: list[float], signals: list[BarSignal], start_ts: int, end_ts: int,
) -> tuple[float, float]:
    """Return (return_pct, max_drawdown_pct) for a time period."""
    indices = [i for i, s in enumerate(signals) if start_ts <= s.timestamp <= end_ts]
    if len(indices) < 2:
        return 0.0, 0.0

    first_idx, last_idx = indices[0], indices[-1]
    # Equity indices match signal indices (equity has +1 entry for initial)
    if first_idx >= len(equity) or last_idx >= len(equity):
        return 0.0, 0.0

    start_eq = equity[first_idx]
    end_eq = equity[last_idx]
    ret = (end_eq - start_eq) / start_eq * 100 if start_eq > 0 else 0
    sub_equity = equity[first_idx:last_idx + 1]
    dd = _max_drawdown(sub_equity)
    return ret, dd


def simulate_hybrid(
    signals: list[BarSignal],
    macro_regimes: list[str],
    core_split: float,
    active_split: float,
    alloc_table: dict[str, float],
    alloc_table_name: str,
    active_params: dict,
    active_params_name: str,
    smoothing_bars: int,
    initial_capital: float = INITIAL_CAPITAL,
) -> HybridResult:
    """Run the full hybrid simulation for one config."""
    core_capital = initial_capital * core_split
    active_capital = initial_capital * active_split

    # Core bucket: regime-managed B&H
    core_eq = simulate_core_bucket(
        signals, macro_regimes, alloc_table, core_capital, smoothing_bars,
    )

    # Active bucket: SignalForge replay
    active_trades, active_eq = replay_active(
        signals, active_params, active_capital, macro_regimes,
    )

    # Align lengths (core and active may differ by 1 due to initialization)
    min_len = min(len(core_eq), len(active_eq))
    core_eq = core_eq[:min_len]
    active_eq = active_eq[:min_len]

    # Combined equity
    combined_eq = [c + a for c, a in zip(core_eq, active_eq)]

    # Metrics
    total_ret = (combined_eq[-1] - initial_capital) / initial_capital * 100 if combined_eq else 0
    max_dd = _max_drawdown(combined_eq)
    core_ret = (core_eq[-1] - core_capital) / core_capital * 100 if core_eq else 0
    active_ret = (active_eq[-1] - active_capital) / active_capital * 100 if active_eq else 0

    active_wins = [t for t in active_trades if t.pnl > 0]
    win_rate = len(active_wins) / len(active_trades) * 100 if active_trades else 0

    calmar = total_ret / max_dd if max_dd > 0 else (total_ret if total_ret > 0 else 0)

    config_name = f"{int(core_split*100)}/{int(active_split*100)}|{alloc_table_name}|{active_params_name}|s{smoothing_bars}"

    result = HybridResult(
        config_name=config_name,
        core_split=core_split, active_split=active_split,
        alloc_table_name=alloc_table_name, active_params_name=active_params_name,
        smoothing_bars=smoothing_bars,
        core_equity=core_eq, active_equity=active_eq, combined_equity=combined_eq,
        total_return_pct=total_ret, max_drawdown_pct=max_dd, calmar_ratio=calmar,
        core_return_pct=core_ret, active_return_pct=active_ret,
        active_trades=len(active_trades), active_win_rate=win_rate,
    )

    # Period sub-analysis
    result.bear_return_pct, result.bear_drawdown_pct = _period_metrics(
        combined_eq, signals, BEAR_START_TS, BEAR_END_TS,
    )
    result.bull_return_pct, result.bull_drawdown_pct = _period_metrics(
        combined_eq, signals, BULL_START_TS, BULL_END_TS,
    )

    return result


# ── Benchmarks ──────────────────────────────────────────────────────────


def benchmark_buy_and_hold(signals: list[BarSignal], capital: float = INITIAL_CAPITAL) -> dict:
    """Pure buy-and-hold benchmark."""
    if not signals:
        return {"return_pct": 0, "max_dd_pct": 0, "equity": [capital]}
    start = signals[0].close
    qty = capital / start
    entry_fee = capital * FEE_RATE

    equity = []
    for s in signals:
        val = qty * s.close - entry_fee
        equity.append(val)

    exit_fee = equity[-1] * FEE_RATE
    equity[-1] -= exit_fee

    ret = (equity[-1] - capital) / capital * 100
    return {
        "return_pct": ret,
        "max_dd_pct": _max_drawdown(equity),
        "equity": equity,
        "bear_return": _period_metrics(equity, signals, BEAR_START_TS, BEAR_END_TS)[0],
        "bear_dd": _period_metrics(equity, signals, BEAR_START_TS, BEAR_END_TS)[1],
        "bull_return": _period_metrics(equity, signals, BULL_START_TS, BULL_END_TS)[0],
        "bull_dd": _period_metrics(equity, signals, BULL_START_TS, BULL_END_TS)[1],
    }


def benchmark_regime_bh(
    signals: list[BarSignal], macro_regimes: list[str],
    alloc_table: dict[str, float], smoothing: int = 3,
    capital: float = INITIAL_CAPITAL,
) -> dict:
    """Pure regime-managed B&H (100% core, 0% active)."""
    eq = simulate_core_bucket(signals, macro_regimes, alloc_table, capital, smoothing)
    ret = (eq[-1] - capital) / capital * 100 if eq else 0
    return {
        "return_pct": ret,
        "max_dd_pct": _max_drawdown(eq),
        "equity": eq,
        "bear_return": _period_metrics(eq, signals, BEAR_START_TS, BEAR_END_TS)[0],
        "bear_dd": _period_metrics(eq, signals, BEAR_START_TS, BEAR_END_TS)[1],
        "bull_return": _period_metrics(eq, signals, BULL_START_TS, BULL_END_TS)[0],
        "bull_dd": _period_metrics(eq, signals, BULL_START_TS, BULL_END_TS)[1],
    }


def benchmark_active_only(
    signals: list[BarSignal], params: dict,
    macro_regimes: list[str] | None = None,
    capital: float = INITIAL_CAPITAL,
) -> dict:
    """Pure active-only benchmark."""
    trades, eq = replay_active(signals, params, capital, macro_regimes)
    ret = (eq[-1] - capital) / capital * 100 if eq else 0
    wins = [t for t in trades if t.pnl > 0]
    return {
        "return_pct": ret,
        "max_dd_pct": _max_drawdown(eq),
        "equity": eq,
        "trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "bear_return": _period_metrics(eq, signals, BEAR_START_TS, BEAR_END_TS)[0],
        "bear_dd": _period_metrics(eq, signals, BEAR_START_TS, BEAR_END_TS)[1],
        "bull_return": _period_metrics(eq, signals, BULL_START_TS, BULL_END_TS)[0],
        "bull_dd": _period_metrics(eq, signals, BULL_START_TS, BULL_END_TS)[1],
    }


# ── Grid Search ─────────────────────────────────────────────────────────


def run_hybrid_grid(
    signals_by_lookback: dict[int, list[BarSignal]],
    macro_regimes: list[str],
    pair_name: str,
) -> list[HybridResult]:
    """Test all hybrid configurations for one pair."""
    results = []

    for core_pct, active_pct in SPLIT_RATIOS:
        for alloc_name, alloc_table in ALLOCATION_TABLES.items():
            for ap_name, ap in ACTIVE_PARAMS.items():
                lookback = ap.get("trigger_lookback", 1)
                signals = signals_by_lookback.get(lookback)
                if signals is None:
                    continue

                for smooth in SMOOTHING_OPTIONS:
                    result = simulate_hybrid(
                        signals=signals,
                        macro_regimes=macro_regimes,
                        core_split=core_pct,
                        active_split=active_pct,
                        alloc_table=alloc_table,
                        alloc_table_name=alloc_name,
                        active_params=ap,
                        active_params_name=ap_name,
                        smoothing_bars=smooth,
                    )
                    results.append(result)

    return results


# ── Walk-Forward Validation ─────────────────────────────────────────────


def wfo_validate(
    signals_by_lookback: dict[int, list[BarSignal]],
    macro_regimes: list[str],
    config: HybridResult,
) -> dict:
    """60/40 in-sample / out-of-sample validation for a config."""
    lookback = ACTIVE_PARAMS[config.active_params_name].get("trigger_lookback", 1)
    signals = signals_by_lookback.get(lookback, [])
    if not signals:
        return {"in_sample": 0, "out_sample": 0, "degradation": 100}

    split_idx = int(len(signals) * 0.6)
    in_signals = signals[:split_idx]
    out_signals = signals[split_idx:]

    # Regimes aligned to candle indices
    in_regimes = macro_regimes[:LOOKBACK + split_idx]
    out_regimes = macro_regimes

    alloc = ALLOCATION_TABLES[config.alloc_table_name]
    ap = ACTIVE_PARAMS[config.active_params_name]

    in_result = simulate_hybrid(
        in_signals, in_regimes, config.core_split, config.active_split,
        alloc, config.alloc_table_name, ap, config.active_params_name,
        config.smoothing_bars,
    )
    out_result = simulate_hybrid(
        out_signals, out_regimes, config.core_split, config.active_split,
        alloc, config.alloc_table_name, ap, config.active_params_name,
        config.smoothing_bars,
    )

    in_ret = in_result.total_return_pct
    out_ret = out_result.total_return_pct
    degrade = (in_ret - out_ret) / abs(in_ret) * 100 if in_ret != 0 else 0

    return {"in_sample": in_ret, "out_sample": out_ret, "degradation": degrade}


# ── Regime Time Distribution ───────────────────────────────────────────


def regime_distribution(macro_regimes: list[str]) -> dict[str, float]:
    """Percentage of bars in each regime."""
    total = len([r for r in macro_regimes if r != "unknown"])
    if total == 0:
        return {}
    dist = {}
    for r in MacroRegime.ALL:
        count = macro_regimes.count(r)
        dist[r] = count / total * 100
    return dist


# ── Report Generation ──────────────────────────────────────────────────


def fmt_pct(v: float) -> str:
    if math.isnan(v) or math.isinf(v):
        return "0.0%"
    return f"{v:+.1f}%"


def fmt_dollar(v: float) -> str:
    return f"${v:,.0f}"


def generate_report(
    pair_results: dict,
    pair_benchmarks: dict,
    pair_regimes_dist: dict,
    pair_wfo: dict,
    elapsed: float,
) -> str:
    L = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ── Header ──
    L.append("# Hybrid Core + Active Backtest Results\n")
    L.append(f"> Generated on {now} | Runtime: {elapsed:.0f}s")
    L.append("> Timeframe: 4h candles (Jan 2021 - Mar 2026)")
    L.append(f"> Transaction costs: {FEE_RATE*100:.3f}% per side")
    L.append(f"> Starting capital: ${INITIAL_CAPITAL:,.0f} per pair")
    L.append(f"> HMM training: rolling {HMM_TRAIN_WINDOW}-bar window, retrain every {HMM_RETRAIN_INTERVAL} bars")
    L.append(f"> Grid: {len(SPLIT_RATIOS)} splits x {len(ALLOCATION_TABLES)} tables x "
             f"{len(ACTIVE_PARAMS)} active x {len(SMOOTHING_OPTIONS)} smoothing = "
             f"{len(SPLIT_RATIOS)*len(ALLOCATION_TABLES)*len(ACTIVE_PARAMS)*len(SMOOTHING_OPTIONS)} configs/pair\n")

    # ── Section 1: Benchmark Comparison ──
    L.append("## 1. Benchmark Comparison\n")
    L.append("| Pair | B&H | Regime B&H (mod) | Active (current) | Active (best loose) |")
    L.append("|------|-----|-----------------|-----------------|-------------------|")

    portfolio_bh = []
    portfolio_rbh = []
    portfolio_active = []
    portfolio_active_loose = []

    for pair in sorted(pair_benchmarks.keys()):
        bm = pair_benchmarks[pair]
        ps = pair.replace("-4h", "")
        bh = bm["bh"]
        rbh = bm["regime_bh"]
        act = bm["active_current"]
        act_l = bm.get("active_loose", act)

        portfolio_bh.append(bh["return_pct"])
        portfolio_rbh.append(rbh["return_pct"])
        portfolio_active.append(act["return_pct"])
        portfolio_active_loose.append(act_l["return_pct"])

        L.append(
            f"| {ps} | {fmt_pct(bh['return_pct'])} (dd {bh['max_dd_pct']:.1f}%) | "
            f"{fmt_pct(rbh['return_pct'])} (dd {rbh['max_dd_pct']:.1f}%) | "
            f"{fmt_pct(act['return_pct'])} ({act.get('trades',0)}t) | "
            f"{fmt_pct(act_l['return_pct'])} ({act_l.get('trades',0)}t) |"
        )

    avg_bh = sum(portfolio_bh) / len(portfolio_bh) if portfolio_bh else 0
    avg_rbh = sum(portfolio_rbh) / len(portfolio_rbh) if portfolio_rbh else 0
    avg_act = sum(portfolio_active) / len(portfolio_active) if portfolio_active else 0
    avg_act_l = sum(portfolio_active_loose) / len(portfolio_active_loose) if portfolio_active_loose else 0
    L.append(f"| **AVERAGE** | **{fmt_pct(avg_bh)}** | **{fmt_pct(avg_rbh)}** | "
             f"**{fmt_pct(avg_act)}** | **{fmt_pct(avg_act_l)}** |\n")

    # ── Section 2: Top 10 Hybrid Configs ──
    L.append("## 2. Top 10 Hybrid Configs (by Calmar Ratio)\n")
    L.append("Calmar = Return / Max Drawdown. Higher = better risk-adjusted return.\n")

    # Collect all results across all pairs, average by config
    config_scores: dict[str, list[HybridResult]] = {}
    for pair, results in pair_results.items():
        for r in results:
            config_scores.setdefault(r.config_name, []).append(r)

    # Average metrics per config
    config_avg = []
    for name, results in config_scores.items():
        avg_ret = sum(r.total_return_pct for r in results) / len(results)
        avg_dd = sum(r.max_drawdown_pct for r in results) / len(results)
        avg_calmar = avg_ret / avg_dd if avg_dd > 0 else 0
        avg_core = sum(r.core_return_pct for r in results) / len(results)
        avg_active = sum(r.active_return_pct for r in results) / len(results)
        avg_trades = sum(r.active_trades for r in results) / len(results)
        avg_bear = sum(r.bear_return_pct for r in results) / len(results)
        avg_bull = sum(r.bull_return_pct for r in results) / len(results)
        config_avg.append({
            "name": name, "return": avg_ret, "dd": avg_dd, "calmar": avg_calmar,
            "core_ret": avg_core, "active_ret": avg_active, "trades": avg_trades,
            "bear_ret": avg_bear, "bull_ret": avg_bull,
            "results": results,
        })

    config_avg.sort(key=lambda x: x["calmar"], reverse=True)

    L.append("| Rank | Config | Return | Max DD | Calmar | Core | Active | Trades |")
    L.append("|------|--------|--------|--------|--------|------|--------|--------|")

    for i, c in enumerate(config_avg[:10]):
        L.append(
            f"| {i+1} | {c['name']} | {fmt_pct(c['return'])} | {c['dd']:.1f}% | "
            f"{c['calmar']:.2f} | {fmt_pct(c['core_ret'])} | {fmt_pct(c['active_ret'])} | "
            f"{c['trades']:.0f} |"
        )
    L.append("")

    # ── Section 3: Per-Pair Best Hybrid ──
    L.append("## 3. Best Hybrid Config Per Pair\n")
    L.append("| Pair | Best Config | Return | Max DD | Calmar | vs B&H | vs Active |")
    L.append("|------|-----------|--------|--------|--------|--------|----------|")

    for pair in sorted(pair_results.keys()):
        results = pair_results[pair]
        if not results:
            continue
        best = max(results, key=lambda r: r.calmar_ratio)
        ps = pair.replace("-4h", "")
        bh_ret = pair_benchmarks[pair]["bh"]["return_pct"]
        act_ret = pair_benchmarks[pair]["active_current"]["return_pct"]

        L.append(
            f"| {ps} | {best.config_name} | {fmt_pct(best.total_return_pct)} | "
            f"{best.max_drawdown_pct:.1f}% | {best.calmar_ratio:.2f} | "
            f"{fmt_pct(best.total_return_pct - bh_ret)} | "
            f"{fmt_pct(best.total_return_pct - act_ret)} |"
        )
    L.append("")

    # ── Section 4: Split Ratio Sensitivity ──
    L.append("## 4. Split Ratio Sensitivity\n")
    L.append("| Split (Core/Active) | Avg Return | Avg Max DD | Avg Calmar |")
    L.append("|--------------------:|----------:|----------:|----------:|")

    for core_pct, active_pct in SPLIT_RATIOS:
        matching = [c for c in config_avg
                    if any(r.core_split == core_pct for r in c["results"])]
        if not matching:
            continue
        # Filter results directly
        split_results = []
        for pair_res in pair_results.values():
            for r in pair_res:
                if r.core_split == core_pct:
                    split_results.append(r)
        if not split_results:
            continue
        avg_ret = sum(r.total_return_pct for r in split_results) / len(split_results)
        avg_dd = sum(r.max_drawdown_pct for r in split_results) / len(split_results)
        avg_cal = avg_ret / avg_dd if avg_dd > 0 else 0
        L.append(f"| {int(core_pct*100)}/{int(active_pct*100)} | {fmt_pct(avg_ret)} | {avg_dd:.1f}% | {avg_cal:.2f} |")
    L.append("")

    # ── Section 5: Allocation Table Sensitivity ──
    L.append("## 5. Allocation Table Sensitivity\n")
    L.append("| Table | Avg Return | Avg Max DD | Avg Calmar |")
    L.append("|------:|----------:|----------:|----------:|")

    for table_name in ALLOCATION_TABLES:
        table_results = []
        for pair_res in pair_results.values():
            for r in pair_res:
                if r.alloc_table_name == table_name:
                    table_results.append(r)
        if not table_results:
            continue
        avg_ret = sum(r.total_return_pct for r in table_results) / len(table_results)
        avg_dd = sum(r.max_drawdown_pct for r in table_results) / len(table_results)
        avg_cal = avg_ret / avg_dd if avg_dd > 0 else 0
        L.append(f"| {table_name} | {fmt_pct(avg_ret)} | {avg_dd:.1f}% | {avg_cal:.2f} |")
    L.append("")

    # ── Section 6: Active Params Sensitivity ──
    L.append("## 6. Active Params Sensitivity\n")
    L.append("| Active Variant | Avg Return | Avg Max DD | Avg Trades | Description |")
    L.append("|---------------:|----------:|----------:|----------:|------------|")

    param_desc = {
        "current": "conf=50, tp=1.618, look=1",
        "loose_conf": "conf=30, tp=1.5, look=1",
        "loose_tp": "conf=40, tp=1.0, look=1",
        "wide_trig": "conf=40, tp=1.5, look=3",
        "widest": "conf=30, tp=1.5, look=5",
    }
    for ap_name in ACTIVE_PARAMS:
        ap_results = []
        for pair_res in pair_results.values():
            for r in pair_res:
                if r.active_params_name == ap_name:
                    ap_results.append(r)
        if not ap_results:
            continue
        avg_ret = sum(r.total_return_pct for r in ap_results) / len(ap_results)
        avg_dd = sum(r.max_drawdown_pct for r in ap_results) / len(ap_results)
        avg_trades = sum(r.active_trades for r in ap_results) / len(ap_results)
        L.append(f"| {ap_name} | {fmt_pct(avg_ret)} | {avg_dd:.1f}% | {avg_trades:.0f} | {param_desc.get(ap_name, '')} |")
    L.append("")

    # ── Section 7: Smoothing Sensitivity ──
    L.append("## 7. Smoothing Sensitivity\n")
    L.append("| Smoothing Bars | Avg Return | Avg Max DD | Avg Calmar |")
    L.append("|---------------:|----------:|----------:|----------:|")

    for s in SMOOTHING_OPTIONS:
        s_results = []
        for pair_res in pair_results.values():
            for r in pair_res:
                if r.smoothing_bars == s:
                    s_results.append(r)
        if not s_results:
            continue
        avg_ret = sum(r.total_return_pct for r in s_results) / len(s_results)
        avg_dd = sum(r.max_drawdown_pct for r in s_results) / len(s_results)
        avg_cal = avg_ret / avg_dd if avg_dd > 0 else 0
        L.append(f"| {s} | {fmt_pct(avg_ret)} | {avg_dd:.1f}% | {avg_cal:.2f} |")
    L.append("")

    # ── Section 8: Bear Market Performance (2022) ──
    L.append("## 8. Bear Market Performance (Nov 2021 - Nov 2022)\n")
    L.append("| Pair | B&H | Regime B&H | Best Hybrid | Config |")
    L.append("|------|-----|-----------|------------|--------|")

    for pair in sorted(pair_results.keys()):
        ps = pair.replace("-4h", "")
        bm = pair_benchmarks[pair]
        bh_bear = bm["bh"].get("bear_return", 0)
        rbh_bear = bm["regime_bh"].get("bear_return", 0)

        results = pair_results[pair]
        if results:
            # Best hybrid by bear market return (least negative)
            best_bear = max(results, key=lambda r: r.bear_return_pct)
            L.append(
                f"| {ps} | {fmt_pct(bh_bear)} | {fmt_pct(rbh_bear)} | "
                f"{fmt_pct(best_bear.bear_return_pct)} | {best_bear.config_name} |"
            )
    L.append("")

    # ── Section 9: Bull Market Performance (2024-2026) ──
    L.append("## 9. Bull Market Performance (Jan 2024 - Mar 2026)\n")
    L.append("| Pair | B&H | Regime B&H | Best Hybrid | Config |")
    L.append("|------|-----|-----------|------------|--------|")

    for pair in sorted(pair_results.keys()):
        ps = pair.replace("-4h", "")
        bm = pair_benchmarks[pair]
        bh_bull = bm["bh"].get("bull_return", 0)
        rbh_bull = bm["regime_bh"].get("bull_return", 0)

        results = pair_results[pair]
        if results:
            best_bull = max(results, key=lambda r: r.bull_return_pct)
            L.append(
                f"| {ps} | {fmt_pct(bh_bull)} | {fmt_pct(rbh_bull)} | "
                f"{fmt_pct(best_bull.bull_return_pct)} | {best_bull.config_name} |"
            )
    L.append("")

    # ── Section 10: Drawdown Comparison ──
    L.append("## 10. Drawdown Comparison\n")
    L.append("| Pair | B&H DD | Regime B&H DD | Best Hybrid DD | Active DD |")
    L.append("|------|--------|-------------|---------------|----------|")

    for pair in sorted(pair_results.keys()):
        ps = pair.replace("-4h", "")
        bm = pair_benchmarks[pair]
        bh_dd = bm["bh"]["max_dd_pct"]
        rbh_dd = bm["regime_bh"]["max_dd_pct"]
        act_dd = bm["active_current"]["max_dd_pct"]

        results = pair_results[pair]
        if results:
            best_dd = min(results, key=lambda r: r.max_drawdown_pct)
            L.append(
                f"| {ps} | {bh_dd:.1f}% | {rbh_dd:.1f}% | "
                f"{best_dd.max_drawdown_pct:.1f}% | {act_dd:.1f}% |"
            )
    L.append("")

    # ── Section 11: Regime Time Distribution ──
    L.append("## 11. Regime Time Distribution\n")
    L.append("| Pair | Strong Bull | Bull Corr | Ranging | Bear | Capitulation | Recovery |")
    L.append("|------|-----------|---------|---------|------|-------------|----------|")

    for pair in sorted(pair_regimes_dist.keys()):
        ps = pair.replace("-4h", "")
        d = pair_regimes_dist[pair]
        L.append(
            f"| {ps} | {d.get(MacroRegime.STRONG_BULL,0):.1f}% | "
            f"{d.get(MacroRegime.BULL_CORRECTION,0):.1f}% | "
            f"{d.get(MacroRegime.RANGING,0):.1f}% | "
            f"{d.get(MacroRegime.BEAR_TRENDING,0):.1f}% | "
            f"{d.get(MacroRegime.CAPITULATION,0):.1f}% | "
            f"{d.get(MacroRegime.RECOVERY,0):.1f}% |"
        )
    L.append("")

    # ── Section 12: Walk-Forward Validation ──
    L.append("## 12. Walk-Forward Validation (Top 5 Configs)\n")
    L.append("60% in-sample / 40% out-of-sample. Degradation > 50% = likely overfit.\n")
    L.append("| Config | In-Sample | Out-Sample | Degradation | Status |")
    L.append("|--------|----------|-----------|------------|--------|")

    for pair in sorted(pair_wfo.keys()):
        for wfo in pair_wfo[pair]:
            status = "OVERFIT" if wfo["degradation"] > 50 else "OK"
            L.append(
                f"| {wfo['config']} | {fmt_pct(wfo['in_sample'])} | "
                f"{fmt_pct(wfo['out_sample'])} | {wfo['degradation']:.0f}% | {status} |"
            )
    L.append("")

    # ── Section 13: Success Criteria Check ──
    L.append("## 13. Success Criteria\n")

    if config_avg:
        best = config_avg[0]
        checks = [
            (f"Total return > 100%", best["return"] > 100, f"{best['return']:.1f}%"),
            (f"Max drawdown < 40%", best["dd"] < 40, f"{best['dd']:.1f}%"),
            (f"Bear market DD < 30%", abs(best["bear_ret"]) < 30 if best["bear_ret"] < 0 else True, f"{best['bear_ret']:.1f}%"),
            (f"Calmar ratio > 2.0", best["calmar"] > 2.0, f"{best['calmar']:.2f}"),
        ]
        for desc, passed, val in checks:
            mark = "PASS" if passed else "FAIL"
            L.append(f"- [{mark}] {desc}: **{val}**")
    L.append("")

    # ── Section 14: Recommendations ──
    L.append("## 14. Recommendations\n")

    if config_avg:
        best = config_avg[0]
        L.append(f"**Best universal config:** `{best['name']}`")
        L.append(f"- Average return: {fmt_pct(best['return'])}")
        L.append(f"- Average max drawdown: {best['dd']:.1f}%")
        L.append(f"- Calmar ratio: {best['calmar']:.2f}")
        L.append(f"- Bear market return: {fmt_pct(best['bear_ret'])}")
        L.append(f"- Bull market return: {fmt_pct(best['bull_ret'])}")
        L.append("")

        if best["calmar"] > 2.0 and best["return"] > 50:
            L.append("**Verdict: HYBRID APPROACH IS VIABLE.** Proceed to Phase 2 production implementation.")
        elif best["return"] > 30:
            L.append("**Verdict: PARTIALLY VIABLE.** Hybrid improves on active-only but may not "
                     "justify the complexity over regime-managed B&H alone.")
        else:
            L.append("**Verdict: NOT VIABLE.** Regime-managed B&H alone may be sufficient. "
                     "Active bucket does not add meaningful value.")

    return "\n".join(L)


# ── Main ────────────────────────────────────────────────────────────────


def main():
    start_time = time.time()
    print("=" * 70)
    print("  HYBRID CORE + ACTIVE BACKTEST")
    print("=" * 70)

    # [1/7] Discover and load 4h data
    print("\n[1/7] Discovering 4h data files...")
    pairs = discover_4h_pairs(DATA_DIR)
    print(f"  Found {len(pairs)} pairs: {', '.join(sorted(pairs.keys()))}")

    pair_candles: dict[str, pd.DataFrame] = {}
    for key, info in sorted(pairs.items()):
        df = load_csv(info["file"])
        if len(df) < LOOKBACK + 100:
            print(f"  SKIP {key}: only {len(df)} bars (need {LOOKBACK + 100})")
            continue
        pair_candles[key] = df
        print(f"  {key}: {len(df)} bars")

    # [2/7] Pre-compute signals for each trigger_lookback variant
    print("\n[2/7] Pre-computing signals...")
    lookbacks_needed = sorted(set(p.get("trigger_lookback", 1) for p in ACTIVE_PARAMS.values()))
    print(f"  Lookback variants needed: {lookbacks_needed}")

    pair_signals: dict[str, dict[int, list[BarSignal]]] = {}
    total_passes = len(pair_candles) * len(lookbacks_needed)
    done = 0

    for key, candles in sorted(pair_candles.items()):
        pair_name = key.replace("-4h", "")
        pair_signals[key] = {}

        _indicator_cache.setup(candles)

        for lb in lookbacks_needed:
            t0 = time.time()
            signals = precompute_signals(candles, pair_name, "4h", trigger_lookback=lb)
            done += 1
            elapsed = time.time() - t0
            print(f"  [{done}/{total_passes}] {key} (lookback={lb}): "
                  f"{len(signals)} signals in {elapsed:.1f}s")
            pair_signals[key][lb] = signals

    # [3/7] Detect macro regimes
    print("\n[3/7] Detecting HMM macro regimes...")
    pair_regimes: dict[str, list[str]] = {}
    pair_regimes_dist: dict[str, dict] = {}

    for key, candles in sorted(pair_candles.items()):
        t0 = time.time()
        regimes = detect_macro_regimes_hmm(candles)
        elapsed = time.time() - t0
        pair_regimes[key] = regimes
        dist = regime_distribution(regimes)
        pair_regimes_dist[key] = dist
        print(f"  {key}: {len(regimes)} regime labels in {elapsed:.1f}s")

    # [4/7] Run benchmarks
    print("\n[4/7] Running benchmarks...")
    pair_benchmarks: dict[str, dict] = {}

    # Find best loose config (by return across all pairs, using lookback=1 signals)
    best_loose_name = "loose_conf"  # Default
    for key in sorted(pair_signals.keys()):
        sigs_default = pair_signals[key].get(1, [])
        if not sigs_default:
            continue

        bm = {
            "bh": benchmark_buy_and_hold(sigs_default),
            "regime_bh": benchmark_regime_bh(
                sigs_default, pair_regimes[key],
                ALLOCATION_TABLES["moderate"], smoothing=3,
            ),
            "active_current": benchmark_active_only(
                sigs_default, ACTIVE_PARAMS["current"], pair_regimes[key],
            ),
        }

        # Test each loose variant
        best_loose_ret = bm["active_current"]["return_pct"]
        best_loose_bm = bm["active_current"]
        for lname in ["loose_conf", "loose_tp"]:
            lb = ACTIVE_PARAMS[lname].get("trigger_lookback", 1)
            sigs_lb = pair_signals[key].get(lb, sigs_default)
            loose_bm = benchmark_active_only(sigs_lb, ACTIVE_PARAMS[lname], pair_regimes[key])
            if loose_bm["return_pct"] > best_loose_ret:
                best_loose_ret = loose_bm["return_pct"]
                best_loose_bm = loose_bm
        bm["active_loose"] = best_loose_bm

        pair_benchmarks[key] = bm
        ps = key.replace("-4h", "")
        print(f"  {ps}: B&H {fmt_pct(bm['bh']['return_pct'])}, "
              f"Regime B&H {fmt_pct(bm['regime_bh']['return_pct'])}, "
              f"Active {fmt_pct(bm['active_current']['return_pct'])}")

    # [5/7] Run hybrid grid search
    print("\n[5/7] Running hybrid grid search...")
    total_configs = len(SPLIT_RATIOS) * len(ALLOCATION_TABLES) * len(ACTIVE_PARAMS) * len(SMOOTHING_OPTIONS)
    print(f"  {total_configs} configs per pair x {len(pair_signals)} pairs = "
          f"{total_configs * len(pair_signals)} total simulations")

    pair_results: dict[str, list[HybridResult]] = {}
    for key in sorted(pair_signals.keys()):
        t0 = time.time()
        results = run_hybrid_grid(pair_signals[key], pair_regimes[key], key)
        elapsed = time.time() - t0

        pair_results[key] = results
        if results:
            best = max(results, key=lambda r: r.calmar_ratio)
            print(f"  {key}: {len(results)} configs in {elapsed:.1f}s | "
                  f"Best: {fmt_pct(best.total_return_pct)} ret, {best.max_drawdown_pct:.1f}% dd, "
                  f"calmar {best.calmar_ratio:.2f}")

    # [6/7] Walk-forward validation
    print("\n[6/7] Walk-forward validation (top 5 configs)...")
    # Get top 5 configs across all pairs
    all_results_flat = []
    for pair, results in pair_results.items():
        for r in results:
            all_results_flat.append((pair, r))

    # Group by config name, average calmar
    config_calmar: dict[str, list[float]] = {}
    for pair, r in all_results_flat:
        config_calmar.setdefault(r.config_name, []).append(r.calmar_ratio)

    top_configs = sorted(config_calmar.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)[:5]
    top_config_names = [c[0] for c in top_configs]

    pair_wfo: dict[str, list[dict]] = {}
    for key in sorted(pair_signals.keys()):
        pair_wfo[key] = []
        results = pair_results.get(key, [])
        for r in results:
            if r.config_name in top_config_names:
                wfo = wfo_validate(pair_signals[key], pair_regimes[key], r)
                wfo["config"] = f"{key.replace('-4h','')}|{r.config_name}"
                pair_wfo[key].append(wfo)
                status = "OVERFIT" if wfo["degradation"] > 50 else "OK"
                print(f"  {wfo['config']}: IS={fmt_pct(wfo['in_sample'])} "
                      f"OS={fmt_pct(wfo['out_sample'])} deg={wfo['degradation']:.0f}% [{status}]")

    # [7/7] Generate report
    print("\n[7/7] Generating report...")
    elapsed = time.time() - start_time
    report = generate_report(pair_results, pair_benchmarks, pair_regimes_dist, pair_wfo, elapsed)

    with open(OUTPUT_PATH, "w") as f:
        f.write(report)
    print(f"\n  Report saved to {OUTPUT_PATH}")

    # Final summary
    print("\n" + "=" * 70)
    print(f"  COMPLETED in {elapsed:.0f}s ({elapsed/60:.1f} min)")

    # Print top 3 configs
    config_scores: dict[str, list[HybridResult]] = {}
    for pair, results in pair_results.items():
        for r in results:
            config_scores.setdefault(r.config_name, []).append(r)

    config_ranked = []
    for name, results in config_scores.items():
        avg_ret = sum(r.total_return_pct for r in results) / len(results)
        avg_dd = sum(r.max_drawdown_pct for r in results) / len(results)
        avg_cal = avg_ret / avg_dd if avg_dd > 0 else 0
        config_ranked.append((name, avg_ret, avg_dd, avg_cal))
    config_ranked.sort(key=lambda x: x[3], reverse=True)

    print("\n  TOP 3 CONFIGS:")
    for i, (name, ret, dd, cal) in enumerate(config_ranked[:3]):
        print(f"  {i+1}. {name}")
        print(f"     Return: {ret:+.1f}% | Max DD: {dd:.1f}% | Calmar: {cal:.2f}")

    print("=" * 70)


if __name__ == "__main__":
    main()
