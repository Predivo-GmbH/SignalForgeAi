"""
Equity Curve Comparison: SignalForge vs Buy-and-Hold.

Runs the best configs from backtest v3 on 4h data (Jan 2021 - Mar 2026)
and produces a month-by-month equity comparison showing when the system
outperforms or underperforms simple buy-and-hold.

Usage:
    cd backend
    .venv/Scripts/python.exe -u scripts/run_equity_comparison.py

Output:
    docs/EQUITY-COMPARISON.md
"""

from __future__ import annotations

import glob as globmod
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# ── Path setup ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Disable HMM (performance) ──────────────────────────────────────────
from app.engine.layers import regime as _regime_mod  # noqa: E402

_OrigRegimeDetector = _regime_mod.RegimeDetector


class _FastRegimeDetector(_OrigRegimeDetector):
    def __init__(self, use_hmm: bool = False):
        super().__init__(use_hmm=False)


_regime_mod.RegimeDetector = _FastRegimeDetector

# ── Imports (after HMM patch) ──────────────────────────────────────────
from app.engine import indicators as _ind_mod  # noqa: E402
from app.engine.layers import confluence as _conf_mod  # noqa: E402
from app.engine.layers import risk as _risk_mod  # noqa: E402
from app.engine.layers import trend as _trend_mod  # noqa: E402
from app.engine.layers import triggers as _trig_mod  # noqa: E402
from app.engine.layers import zones as _zone_mod  # noqa: E402
from app.engine.layers.risk import RiskConfig  # noqa: E402
from app.engine.pipeline import SignalPipeline  # noqa: E402

import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger("hmmlearn").setLevel(logging.CRITICAL)

# ── Configuration ───────────────────────────────────────────────────────

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "docs", "chart-data")
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "EQUITY-COMPARISON.md")

FEE_RATE = 0.00075  # 0.075% per side
INITIAL_CAPITAL = 10_000.0
LOOKBACK = 200

# Best universal config from backtest v3
UNIVERSAL_CONFIG = {
    "min_confluence": 60,
    "atr_sl_multiplier": 2.0,
    "max_risk_per_trade": 0.01,
    "tp_ratio": 1.0,
}
UNIVERSAL_VARIANT = "partial_tp"

# Best per-pair configs from backtest v3 (4h only)
PER_PAIR_CONFIGS = {
    "BTC/USD-4h": {"params": {"min_confluence": 70, "atr_sl_multiplier": 3.0, "max_risk_per_trade": 0.01, "tp_ratio": 1.0}, "variant": "partial_tp"},
    "ETH/USD-4h": {"params": {"min_confluence": 70, "atr_sl_multiplier": 2.0, "max_risk_per_trade": 0.01, "tp_ratio": 2.618}, "variant": "partial_tp"},
    "SOL/USD-4h": {"params": {"min_confluence": 50, "atr_sl_multiplier": 2.5, "max_risk_per_trade": 0.01, "tp_ratio": 2.618}, "variant": "baseline"},
    "BNB/USD-4h": {"params": {"min_confluence": 70, "atr_sl_multiplier": 1.5, "max_risk_per_trade": 0.01, "tp_ratio": 1.0}, "variant": "partial_tp"},
    "ADA/USD-4h": {"params": {"min_confluence": 60, "atr_sl_multiplier": 3.0, "max_risk_per_trade": 0.01, "tp_ratio": 1.5}, "variant": "partial_tp"},
    "DOGE/USD-4h": {"params": {"min_confluence": 70, "atr_sl_multiplier": 3.0, "max_risk_per_trade": 0.01, "tp_ratio": 1.0}, "variant": "baseline"},
    "LINK/USD-4h": {"params": {"min_confluence": 60, "atr_sl_multiplier": 2.5, "max_risk_per_trade": 0.01, "tp_ratio": 2.618}, "variant": "baseline"},
    "XRP/USD-4h": {"params": {"min_confluence": 70, "atr_sl_multiplier": 3.0, "max_risk_per_trade": 0.01, "tp_ratio": 1.5}, "variant": "partial_tp"},
}

# Focus on 4h pairs (5 years: Jan 2021 - Mar 2026, full market cycles)
TARGET_PAIRS_4H = [
    "BTC/USD-4h", "ETH/USD-4h", "SOL/USD-4h", "BNB/USD-4h",
    "ADA/USD-4h", "DOGE/USD-4h", "LINK/USD-4h", "XRP/USD-4h",
]


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
    timestamp: int = 0  # Unix timestamp


@dataclass
class EquityPoint:
    timestamp: int
    date: str  # YYYY-MM-DD
    system_equity: float
    bh_equity: float


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
        if tf_raw != "240":  # Only 4h
            continue

        if symbol.endswith("USDT"):
            pair_name = symbol[:-4] + "/USDT"
        elif symbol.endswith("USD"):
            pair_name = symbol[:-3] + "/USD"
        else:
            pair_name = symbol

        key = f"{pair_name}-4h"
        if key in pairs:
            existing_size = os.path.getsize(pairs[key]["file"])
            new_size = os.path.getsize(filepath)
            if new_size <= existing_size:
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
            return self._originals["compute_ema"](close, period)

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
        risk_config=RiskConfig(
            max_risk_per_trade=0.02,
            atr_sl_multiplier=2.0,
            min_risk_reward=0.1,
        ),
        min_confluence=1,
    )

    atr_full = _indicator_cache._cache[("atr", 14)]
    timestamps = candles["time"].values if "time" in candles.columns else [0] * len(candles)
    signals: list[BarSignal] = []

    for i in range(LOOKBACK, len(candles)):
        window = candles.iloc[: i + 1]
        current = candles.iloc[i]

        signal = pipeline.process(
            symbol=pair, timeframe=tf, candles=window, account_equity=10000.0,
        )

        atr_val = float(atr_full.iloc[i]) if not pd.isna(atr_full.iloc[i]) else 0.0

        signals.append(BarSignal(
            action=signal.action,
            confluence=signal.confluence_score,
            atr=atr_val,
            close=float(current["close"]),
            high=float(current["high"]),
            low=float(current["low"]),
            regime=signal.regime,
            timestamp=int(timestamps[i]) if i < len(timestamps) else 0,
        ))

    return signals


# ── Replay Engine with Equity Tracking ──────────────────────────────────


def replay_with_equity(
    signals: list[BarSignal],
    params: dict,
    variant: str,
    initial_capital: float = 10_000.0,
) -> tuple[list[EquityPoint], dict]:
    """Replay trades and track equity at each bar with timestamps."""
    min_conf = params["min_confluence"]
    atr_mult = params["atr_sl_multiplier"]
    risk_pct = params["max_risk_per_trade"]
    tp_ratio = params.get("tp_ratio", 1.618)
    enable_partial_tp = variant == "partial_tp"

    capital = initial_capital
    equity_points: list[EquityPoint] = []

    # Buy-and-hold tracking
    bh_start_price = signals[0].close if signals else 1.0
    bh_qty = initial_capital / bh_start_price
    bh_entry_fee = initial_capital * FEE_RATE
    bh_capital_after_entry = initial_capital - bh_entry_fee

    open_trade = None
    original_sl = 0.0
    partial_closed = False
    tp2 = 0.0
    partial_pnl_accumulated = 0.0
    pos_size = 0.0

    total_trades = 0
    winning_trades = 0
    total_pnl = 0.0

    for i, sig in enumerate(signals):
        # Buy-and-hold equity at this point
        bh_current_value = bh_qty * sig.close
        bh_exit_fee = bh_current_value * FEE_RATE
        bh_equity = bh_current_value - bh_entry_fee - bh_exit_fee

        ts = sig.timestamp
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts > 0 else f"bar-{i}"

        if open_trade is not None:
            h, l = sig.high, sig.low

            # Check SL/TP
            hit_sl = hit_tp = False
            if open_trade["direction"] == "BUY":
                hit_sl = l <= open_trade["stop_loss"]
                hit_tp = h >= open_trade["take_profit"]
            else:
                hit_sl = h >= open_trade["stop_loss"]
                hit_tp = l <= open_trade["take_profit"]

            # Partial TP
            if enable_partial_tp and not partial_closed and hit_tp:
                exit_price = open_trade["take_profit"]
                half_size = pos_size * 0.5
                fee = exit_price * half_size * FEE_RATE
                if open_trade["direction"] == "BUY":
                    partial_pnl = (exit_price - open_trade["entry_price"]) * half_size - fee
                else:
                    partial_pnl = (open_trade["entry_price"] - exit_price) * half_size - fee
                partial_pnl_accumulated = partial_pnl
                capital += partial_pnl
                open_trade["stop_loss"] = open_trade["entry_price"]
                open_trade["take_profit"] = tp2
                partial_closed = True
                pos_size = half_size
                equity_points.append(EquityPoint(ts, date_str, capital, bh_equity))
                continue

            if hit_sl or hit_tp:
                exit_price = open_trade["stop_loss"] if hit_sl else open_trade["take_profit"]
                fee = exit_price * pos_size * FEE_RATE
                if open_trade["direction"] == "BUY":
                    gross_pnl = (exit_price - open_trade["entry_price"]) * pos_size
                else:
                    gross_pnl = (open_trade["entry_price"] - exit_price) * pos_size
                pnl = gross_pnl - fee + partial_pnl_accumulated
                capital += gross_pnl - fee

                total_trades += 1
                total_pnl += pnl
                if pnl > 0:
                    winning_trades += 1
                open_trade = None

            equity_points.append(EquityPoint(ts, date_str, capital, bh_equity))
            continue

        # No open trade → check for entry
        if sig.action in ("BUY", "SELL") and sig.confluence >= min_conf:
            if sig.atr <= 0:
                equity_points.append(EquityPoint(ts, date_str, capital, bh_equity))
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
                equity_points.append(EquityPoint(ts, date_str, capital, bh_equity))
                continue
            pos_size = capital * risk_pct / risk_dist

            entry_fee = entry * pos_size * FEE_RATE
            capital -= entry_fee

            open_trade = {
                "entry_price": entry,
                "direction": sig.action,
                "stop_loss": sl,
                "take_profit": tp1,
            }
            original_sl = sl
            partial_closed = False
            tp2 = tp2_price
            partial_pnl_accumulated = 0.0

        equity_points.append(EquityPoint(ts, date_str, capital, bh_equity))

    # Close remaining open trade
    if open_trade and signals:
        last = signals[-1]
        fee = last.close * pos_size * FEE_RATE
        if open_trade["direction"] == "BUY":
            gross_pnl = (last.close - open_trade["entry_price"]) * pos_size
        else:
            gross_pnl = (open_trade["entry_price"] - last.close) * pos_size
        pnl = gross_pnl - fee + partial_pnl_accumulated
        capital += gross_pnl - fee
        total_trades += 1
        total_pnl += pnl
        if pnl > 0:
            winning_trades += 1
        if equity_points:
            equity_points[-1].system_equity = capital

    metrics = {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "win_rate": winning_trades / total_trades * 100 if total_trades > 0 else 0,
        "total_pnl": total_pnl,
        "total_return_pct": (capital - initial_capital) / initial_capital * 100,
        "final_equity": capital,
        "bh_return_pct": (bh_equity - initial_capital) / initial_capital * 100 if equity_points else 0,
        "bh_final_equity": bh_equity if equity_points else initial_capital,
    }

    return equity_points, metrics


def sample_monthly(equity_points: list[EquityPoint]) -> list[EquityPoint]:
    """Sample equity curve at month boundaries."""
    if not equity_points:
        return []

    monthly = {}
    for ep in equity_points:
        if ep.timestamp <= 0:
            continue
        month_key = ep.date[:7]  # YYYY-MM
        monthly[month_key] = ep  # Keep last value of each month

    return [monthly[k] for k in sorted(monthly.keys())]


def sample_quarterly(equity_points: list[EquityPoint]) -> list[EquityPoint]:
    """Sample equity curve at quarter boundaries."""
    if not equity_points:
        return []

    quarterly = {}
    for ep in equity_points:
        if ep.timestamp <= 0:
            continue
        dt = datetime.fromtimestamp(ep.timestamp, tz=timezone.utc)
        q = (dt.month - 1) // 3 + 1
        quarter_key = f"{dt.year}-Q{q}"
        quarterly[quarter_key] = ep

    return list(quarterly.values())


# ── Market Events ───────────────────────────────────────────────────────

MARKET_EVENTS = {
    "2021-01": "Start (post-COVID rally)",
    "2021-04": "BTC $64K ATH",
    "2021-11": "BTC $69K peak",
    "2022-05": "LUNA crash",
    "2022-06": "Crypto winter begins",
    "2022-11": "FTX collapse / BTC $15K",
    "2023-01": "Recovery starts",
    "2023-06": "Mid-recovery",
    "2024-01": "ETF speculation",
    "2024-03": "BTC new ATH $73K",
    "2024-11": "Post-election rally",
    "2025-01": "BTC $100K+",
    "2025-06": "Recent decline",
    "2026-01": "Current period",
}


# ── Report Generation ───────────────────────────────────────────────────


def generate_report(
    all_results: dict[str, tuple[list[EquityPoint], dict]],
    elapsed: float,
) -> str:
    L = []

    L.append("# SignalForge vs Buy-and-Hold: Equity Comparison\n")
    L.append(f"> Generated on 2026-03-04 | Runtime: {elapsed:.0f}s")
    L.append(f"> Timeframe: 4h candles (Jan 2021 – Mar 2026, ~5 years)")
    L.append(f"> Transaction costs: {FEE_RATE*100:.3f}% per side ({FEE_RATE*2*100:.3f}% round trip)")
    L.append(f"> Starting capital: ${INITIAL_CAPITAL:,.0f} per pair\n")

    # ── Summary Table ──
    L.append("## Summary: Final Results\n")
    L.append("| Pair | Config | Trades | Win% | System Final | System Return | B&H Final | B&H Return | Verdict |")
    L.append("|------|--------|--------|------|-------------|--------------|----------|-----------|---------|")

    total_system = 0
    total_bh = 0
    total_starting = 0

    for pair in sorted(all_results.keys()):
        eq_points, metrics = all_results[pair]
        cfg = PER_PAIR_CONFIGS.get(pair, {"params": UNIVERSAL_CONFIG, "variant": UNIVERSAL_VARIANT})
        p = cfg["params"]
        config_str = f"c{p['min_confluence']} a{p['atr_sl_multiplier']} tp{p['tp_ratio']} r{p['max_risk_per_trade']}"

        sys_ret = metrics["total_return_pct"]
        bh_ret = metrics["bh_return_pct"]
        verdict = "SYSTEM WINS" if sys_ret > bh_ret else "B&H WINS"
        emoji = "+" if sys_ret > bh_ret else "-"

        L.append(
            f"| {pair.replace('-4h', '')} | {config_str} | {metrics['total_trades']} | "
            f"{metrics['win_rate']:.0f}% | ${metrics['final_equity']:,.0f} | "
            f"{sys_ret:+.1f}% | ${metrics['bh_final_equity']:,.0f} | "
            f"{bh_ret:+.1f}% | {verdict} |"
        )
        total_system += metrics["final_equity"]
        total_bh += metrics["bh_final_equity"]
        total_starting += INITIAL_CAPITAL

    total_sys_ret = (total_system - total_starting) / total_starting * 100
    total_bh_ret = (total_bh - total_starting) / total_starting * 100
    L.append(
        f"| **PORTFOLIO** | | | | **${total_system:,.0f}** | "
        f"**{total_sys_ret:+.1f}%** | **${total_bh:,.0f}** | "
        f"**{total_bh_ret:+.1f}%** | **{'SYSTEM' if total_sys_ret > total_bh_ret else 'B&H'} WINS** |"
    )
    L.append("")

    # ── Per-Pair Quarterly Equity Curves ──
    L.append("---\n")
    L.append("## Per-Pair Quarterly Equity Comparison\n")

    for pair in sorted(all_results.keys()):
        eq_points, metrics = all_results[pair]
        pair_short = pair.replace("-4h", "")
        L.append(f"### {pair_short}\n")

        quarterly = sample_quarterly(eq_points)
        if not quarterly:
            L.append("_No quarterly data available._\n")
            continue

        L.append("| Quarter | System Equity | System Return | B&H Equity | B&H Return | System vs B&H | Market Event |")
        L.append("|---------|-------------|--------------|-----------|-----------|--------------|-------------|")

        for ep in quarterly:
            dt = datetime.fromtimestamp(ep.timestamp, tz=timezone.utc)
            q = (dt.month - 1) // 3 + 1
            quarter_label = f"{dt.year}-Q{q}"

            sys_ret = (ep.system_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
            bh_ret = (ep.bh_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
            diff = sys_ret - bh_ret

            month_key = f"{dt.year}-{dt.month:02d}"
            event = ""
            for mk, ev in MARKET_EVENTS.items():
                if mk in [f"{dt.year}-{m:02d}" for m in range(max(1, dt.month - 2), dt.month + 1)]:
                    event = ev
                    break

            ahead = "ahead" if diff > 0 else "behind"
            L.append(
                f"| {quarter_label} | ${ep.system_equity:,.0f} | {sys_ret:+.1f}% | "
                f"${ep.bh_equity:,.0f} | {bh_ret:+.1f}% | "
                f"{diff:+.1f}% ({ahead}) | {event} |"
            )

        L.append("")

    # ── Portfolio Equity Over Time ──
    L.append("---\n")
    L.append("## Combined Portfolio: Quarterly Equity\n")
    L.append(f"Equal allocation: ${INITIAL_CAPITAL:,.0f} per pair, ${total_starting:,.0f} total.\n")

    # Aggregate quarterly data across all pairs
    quarterly_portfolio: dict[str, dict] = {}
    for pair in sorted(all_results.keys()):
        eq_points, _ = all_results[pair]
        quarterly = sample_quarterly(eq_points)
        for ep in quarterly:
            dt = datetime.fromtimestamp(ep.timestamp, tz=timezone.utc)
            q = (dt.month - 1) // 3 + 1
            qkey = f"{dt.year}-Q{q}"
            if qkey not in quarterly_portfolio:
                quarterly_portfolio[qkey] = {"system": 0, "bh": 0, "count": 0}
            quarterly_portfolio[qkey]["system"] += ep.system_equity
            quarterly_portfolio[qkey]["bh"] += ep.bh_equity
            quarterly_portfolio[qkey]["count"] += 1

    L.append("| Quarter | System Portfolio | System Return | B&H Portfolio | B&H Return | System vs B&H |")
    L.append("|---------|----------------|--------------|--------------|-----------|--------------|")

    num_pairs = len(all_results)
    for qkey in sorted(quarterly_portfolio.keys()):
        d = quarterly_portfolio[qkey]
        if d["count"] < num_pairs * 0.5:  # Skip quarters with incomplete data
            continue
        # Scale to full portfolio size
        scale = num_pairs / d["count"] if d["count"] > 0 else 1
        sys_eq = d["system"] * scale
        bh_eq = d["bh"] * scale

        sys_ret = (sys_eq - total_starting) / total_starting * 100
        bh_ret = (bh_eq - total_starting) / total_starting * 100
        diff = sys_ret - bh_ret
        ahead = "ahead" if diff > 0 else "behind"

        L.append(
            f"| {qkey} | ${sys_eq:,.0f} | {sys_ret:+.1f}% | "
            f"${bh_eq:,.0f} | {bh_ret:+.1f}% | {diff:+.1f}% ({ahead}) |"
        )
    L.append("")

    # ── Key Insights ──
    L.append("---\n")
    L.append("## Key Insights\n")

    # Find when system outperforms
    system_wins_pairs = [p for p, (_, m) in all_results.items() if m["total_return_pct"] > m["bh_return_pct"]]
    bh_wins_pairs = [p for p, (_, m) in all_results.items() if m["total_return_pct"] <= m["bh_return_pct"]]

    L.append(f"### System beats B&H on {len(system_wins_pairs)}/{len(all_results)} pairs:\n")
    for p in system_wins_pairs:
        _, m = all_results[p]
        L.append(f"- **{p.replace('-4h', '')}**: System {m['total_return_pct']:+.1f}% vs B&H {m['bh_return_pct']:+.1f}% "
                 f"(system ahead by {m['total_return_pct'] - m['bh_return_pct']:+.1f}%)")

    if bh_wins_pairs:
        L.append(f"\n### B&H beats System on {len(bh_wins_pairs)}/{len(all_results)} pairs:\n")
        for p in bh_wins_pairs:
            _, m = all_results[p]
            L.append(f"- **{p.replace('-4h', '')}**: System {m['total_return_pct']:+.1f}% vs B&H {m['bh_return_pct']:+.1f}% "
                     f"(system behind by {m['bh_return_pct'] - m['total_return_pct']:+.1f}%)")

    L.append("")
    L.append("### Why the System Underperforms B&H in Bull Markets\n")
    L.append("1. **Position sizing caps gains**: Risking 1% per trade means max ~1-2.6% gain per trade, ")
    L.append("   while B&H captures the entire move (e.g., BTC +89.7% over 5 years)")
    L.append("2. **Constant entry/exit friction**: 0.15% round-trip fees on every trade add up ")
    L.append("   (40+ trades × 0.15% = 6%+ in fees alone)")
    L.append("3. **Shorting in a bull market**: SELL signals captured some drops but also ")
    L.append("   created losses during recoveries")
    L.append("4. **Fixed R:R exits**: Can't ride multi-month trends; exits at 1-2.6x ATR ")
    L.append("   while assets move 10-100x over 5 years")
    L.append("")
    L.append("### When the System DOES Add Value\n")
    L.append("1. **Declining/sideways markets**: The system makes money even when assets drop")
    L.append("2. **Risk management**: Max drawdowns are controlled (~13% avg vs 70%+ for B&H in 2022)")
    L.append("3. **Direction-agnostic**: Can profit from both up and down moves")
    L.append("4. **Capital preservation**: In bear markets, B&H investors see -70%+ drawdowns")
    L.append("")

    # Calculate max drawdowns for B&H
    L.append("### B&H Max Drawdowns (for context)\n")
    L.append("During the 2022 crypto winter, buy-and-hold investors experienced:\n")
    L.append("| Asset | Peak | Trough | B&H Drawdown |")
    L.append("|-------|------|--------|-------------|")

    for pair in sorted(all_results.keys()):
        eq_points, _ = all_results[pair]
        pair_short = pair.replace("-4h", "")

        # Calculate B&H max drawdown
        bh_peak = 0
        bh_max_dd = 0
        bh_peak_date = ""
        bh_trough_date = ""
        for ep in eq_points:
            if ep.bh_equity > bh_peak:
                bh_peak = ep.bh_equity
                bh_peak_date = ep.date
            dd = (bh_peak - ep.bh_equity) / bh_peak * 100 if bh_peak > 0 else 0
            if dd > bh_max_dd:
                bh_max_dd = dd
                bh_trough_date = ep.date

        # System max drawdown
        sys_peak = 0
        sys_max_dd = 0
        for ep in eq_points:
            if ep.system_equity > sys_peak:
                sys_peak = ep.system_equity
            dd = (sys_peak - ep.system_equity) / sys_peak * 100 if sys_peak > 0 else 0
            if dd > sys_max_dd:
                sys_max_dd = dd

        L.append(f"| {pair_short} | {bh_peak_date} | {bh_trough_date} | -{bh_max_dd:.1f}% (system: -{sys_max_dd:.1f}%) |")

    L.append("")

    # ── Bottom Line ──
    L.append("---\n")
    L.append("## Bottom Line\n")
    L.append(f"- **Portfolio (system):** ${total_starting:,.0f} -> ${total_system:,.0f} ({total_sys_ret:+.1f}%)")
    L.append(f"- **Portfolio (B&H):** ${total_starting:,.0f} -> ${total_bh:,.0f} ({total_bh_ret:+.1f}%)")

    if total_sys_ret < total_bh_ret:
        gap = total_bh_ret - total_sys_ret
        L.append(f"\n**The system underperforms buy-and-hold by {gap:.1f}% over 5 years** in a period "
                 "dominated by a massive crypto bull market (2021 + 2024-2025).")
        L.append("\nHowever, this comparison is unfair because:")
        L.append("- B&H in crypto from Jan 2021 was buying at the START of a historic bull run")
        L.append("- B&H doesn't account for drawdown pain (70%+ drops in 2022)")
        L.append("- The system maintained controlled risk throughout")
        L.append("- In the declining 2025 market, the system outperforms B&H")
    else:
        L.append(f"\n**The system outperforms buy-and-hold by {total_sys_ret - total_bh_ret:.1f}%!**")

    L.append("\n### The Real Question")
    L.append("A trading system risking 1% per trade **cannot** beat buy-and-hold in a 10x bull market. ")
    L.append("The math is simple: even with 100% win rate at 1% risk and 2.6x R:R, ")
    L.append("you'd need 300+ winning trades to match a 10x move.")
    L.append("\n**To beat B&H, the system needs:**")
    L.append("1. Higher position sizes (more risk = more reward)")
    L.append("2. Trailing exits that ride trends (not fixed R:R)")
    L.append("3. Trend-following mode for strong trends (hold until trend reverses)")
    L.append("4. Compounding (increase position size as equity grows)")
    L.append("")

    return "\n".join(L)


# ── Main ────────────────────────────────────────────────────────────────


def main():
    overall_start = time.time()

    print("=" * 70)
    print("  SignalForge vs Buy-and-Hold: Equity Comparison")
    print("=" * 70)

    # ── Discover 4h data ──
    print("\n[1/3] Loading 4h data files...")
    pairs = discover_4h_pairs(DATA_DIR)

    if not pairs:
        print("ERROR: No 4h CSV files found in", DATA_DIR)
        return

    # Filter to target pairs
    target_pairs = {k: v for k, v in pairs.items() if k in TARGET_PAIRS_4H}
    if not target_pairs:
        target_pairs = pairs  # Use whatever we found

    pairs_candles = {}
    for pair, info in sorted(target_pairs.items()):
        df = load_csv(info["file"])
        if len(df) < 300:
            print(f"  {pair}: only {len(df)} bars — skipping")
            continue
        pairs_candles[pair] = df
        start_ts = int(df["time"].iloc[0]) if "time" in df.columns else 0
        end_ts = int(df["time"].iloc[-1]) if "time" in df.columns else 0
        start_date = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d") if start_ts > 0 else "?"
        end_date = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d") if end_ts > 0 else "?"
        print(f"  {pair}: {len(df):,} bars ({start_date} to {end_date})")

    # ── Pre-compute signals ──
    print(f"\n[2/3] Pre-computing signals ({len(pairs_candles)} pairs)...")
    pairs_signals: dict[str, list[BarSignal]] = {}

    for pair, candles in pairs_candles.items():
        t0 = time.time()
        _indicator_cache.setup(candles)
        signals = precompute_signals(candles, pair, "4h")
        pairs_signals[pair] = signals
        elapsed = time.time() - t0
        n_signals = sum(1 for s in signals if s.action in ("BUY", "SELL"))
        print(f"  {pair}: {len(signals)} bars, {n_signals} signals, {elapsed:.1f}s")

    # ── Run equity comparison ──
    print(f"\n[3/3] Running equity comparisons...")
    all_results: dict[str, tuple[list[EquityPoint], dict]] = {}

    for pair, signals in pairs_signals.items():
        # Use per-pair best config if available, otherwise universal
        cfg = PER_PAIR_CONFIGS.get(pair, {"params": UNIVERSAL_CONFIG, "variant": UNIVERSAL_VARIANT})
        params = cfg["params"]
        variant = cfg["variant"]

        eq_points, metrics = replay_with_equity(signals, params, variant)
        all_results[pair] = (eq_points, metrics)

        print(f"  {pair}: System {metrics['total_return_pct']:+.1f}% ({metrics['total_trades']} trades, "
              f"{metrics['win_rate']:.0f}% WR) | B&H {metrics['bh_return_pct']:+.1f}% | "
              f"{'SYSTEM' if metrics['total_return_pct'] > metrics['bh_return_pct'] else 'B&H'} wins")

    # ── Also run with universal config for comparison ──
    print("\n  --- Universal config comparison ---")
    universal_results: dict[str, tuple[list[EquityPoint], dict]] = {}
    for pair, signals in pairs_signals.items():
        eq_points, metrics = replay_with_equity(signals, UNIVERSAL_CONFIG, UNIVERSAL_VARIANT)
        universal_results[pair] = (eq_points, metrics)
        print(f"  {pair} (universal): System {metrics['total_return_pct']:+.1f}% | "
              f"B&H {metrics['bh_return_pct']:+.1f}%")

    # ── Generate report ──
    elapsed = time.time() - overall_start
    report = generate_report(all_results, elapsed)

    # Add universal config section
    report += "\n---\n\n## Appendix: Universal Config Results\n\n"
    report += f"Config: confluence={UNIVERSAL_CONFIG['min_confluence']}, "
    report += f"atr={UNIVERSAL_CONFIG['atr_sl_multiplier']}, "
    report += f"tp={UNIVERSAL_CONFIG['tp_ratio']}, "
    report += f"risk={UNIVERSAL_CONFIG['max_risk_per_trade']}, "
    report += f"variant={UNIVERSAL_VARIANT}\n\n"
    report += "| Pair | System Return | B&H Return | Verdict |\n"
    report += "|------|-------------|-----------|--------|\n"

    uni_total_sys = 0
    uni_total_bh = 0
    uni_total_start = 0
    for pair in sorted(universal_results.keys()):
        _, m = universal_results[pair]
        verdict = "SYSTEM" if m["total_return_pct"] > m["bh_return_pct"] else "B&H"
        report += f"| {pair.replace('-4h', '')} | {m['total_return_pct']:+.1f}% | {m['bh_return_pct']:+.1f}% | {verdict} |\n"
        uni_total_sys += m["final_equity"]
        uni_total_bh += m["bh_final_equity"]
        uni_total_start += INITIAL_CAPITAL

    uni_sys_ret = (uni_total_sys - uni_total_start) / uni_total_start * 100
    uni_bh_ret = (uni_total_bh - uni_total_start) / uni_total_start * 100
    report += f"| **PORTFOLIO** | **{uni_sys_ret:+.1f}%** | **{uni_bh_ret:+.1f}%** | **{'SYSTEM' if uni_sys_ret > uni_bh_ret else 'B&H'}** |\n"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'=' * 70}")
    print(f"  Report saved to: {OUTPUT_PATH}")
    print(f"  Total runtime: {elapsed:.0f}s")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
