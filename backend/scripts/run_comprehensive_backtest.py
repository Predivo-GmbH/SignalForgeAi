"""
Comprehensive backtest of SignalForgeAI on real data (v3 — enhanced).

Architecture:
  1. Indicator caching: pre-compute all indicators once per pair (eliminates O(N²))
  2. Signal pre-computation: run the real pipeline once with relaxed thresholds
  3. Fast replay: simulate trades from pre-computed signals with different params

Enhancements over v2:
  - Auto-detects all CSV files in docs/chart-data/
  - Transaction costs (0.075% per side)
  - BUY vs SELL breakdown metrics
  - Buy-and-hold benchmark comparison
  - Direction filter (long-only, short-only)
  - Regime filter (trending-only)
  - Partial take-profit variant
  - Timeframe comparison analysis

Usage:
    cd backend
    .venv/Scripts/python.exe -u scripts/run_comprehensive_backtest.py

Output:
    docs/BACKTEST-RESULTS.md
"""

from __future__ import annotations

import glob as globmod
import itertools
import logging
import math
import os
import re
import sys
import time
from dataclasses import dataclass

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

logging.basicConfig(level=logging.WARNING)
logging.getLogger("hmmlearn").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "docs", "chart-data")
OUTPUT_PATH = os.path.join(BASE_DIR, "docs", "BACKTEST-RESULTS.md")

FEE_RATE = 0.00075  # 0.075% per side (Binance + BNB discount)

PARAM_GRID = {
    "min_confluence": [40, 50, 60, 70],
    "atr_sl_multiplier": [1.5, 2.0, 2.5, 3.0],
    "max_risk_per_trade": [0.01, 0.02],
    "tp_ratio": [1.0, 1.5, 2.0, 2.618],
}

VARIANTS = ["baseline", "partial_tp"]
INITIAL_CAPITAL = 10_000.0
LOOKBACK = 200
WFO_TOP_N = 5


# ── Auto-detect data files ─────────────────────────────────────────────


def discover_pairs(data_dir: str) -> dict[str, dict]:
    """Scan chart-data/ for CSV files and build PAIRS dict automatically."""
    pairs = {}
    tf_map = {"1D": "1D", "240": "4h", "60": "1h"}

    for filepath in sorted(globmod.glob(os.path.join(data_dir, "*.csv"))):
        filename = os.path.basename(filepath)
        # Parse: SOURCE_PAIRUSD, TF.csv or SOURCE_PAIRUSDT, TF.csv
        match = re.match(
            r"^([A-Z]+)_([A-Z]+(?:USD|USDT)),\s*(\w+)\.csv$", filename
        )
        if not match:
            continue
        source, symbol, tf_raw = match.groups()

        tf = tf_map.get(tf_raw, tf_raw)
        # Normalize symbol: BTCUSD → BTC/USD, ADAUSDT → ADA/USDT
        if symbol.endswith("USDT"):
            pair_name = symbol[:-4] + "/USDT"
        elif symbol.endswith("USD"):
            pair_name = symbol[:-3] + "/USD"
        else:
            pair_name = symbol

        key = f"{pair_name}-{tf}"

        # Prefer longer files if duplicates exist (e.g., BINANCE and INDEX)
        if key in pairs:
            existing_size = os.path.getsize(pairs[key]["file"])
            new_size = os.path.getsize(filepath)
            if new_size <= existing_size:
                continue  # Keep the larger file

        pairs[key] = {"file": filepath, "tf": tf, "source": source}

    return pairs


# ── CSV Loader ──────────────────────────────────────────────────────────


def load_csv(filepath: str) -> pd.DataFrame:
    """Load TradingView CSV export into pipeline-compatible DataFrame."""
    df = pd.read_csv(filepath)
    df = df.rename(columns={"Volume": "volume"})
    keep = [c for c in ["time", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].copy()
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


# ── Indicator Caching ───────────────────────────────────────────────────


class IndicatorCache:
    """Pre-compute all indicators once and monkey-patch module references."""

    def __init__(self):
        self._cache: dict = {}
        self._originals: dict = {}
        self._patched = False

    def setup(self, candles: pd.DataFrame):
        """Pre-compute all indicators on full dataset and install patches."""
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
        """Monkey-patch indicator functions in all pipeline modules."""
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

        # Patch each module's imported references
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

        self._patched = True


_indicator_cache = IndicatorCache()


# ── Signal Pre-Computation ─────────────────────────────────────────────


@dataclass
class BarSignal:
    """Pre-computed pipeline signal for a single bar."""
    action: str  # "BUY", "SELL", or "NO_TRADE"
    confluence: int
    atr: float
    close: float
    high: float
    low: float
    regime: str = ""  # "trending", "ranging", "transitioning", "chaotic"


def precompute_signals(
    candles: pd.DataFrame, pair: str, tf: str,
) -> list[BarSignal]:
    """Run the actual pipeline once per pair with min_confluence=1."""
    pipeline = SignalPipeline(
        risk_config=RiskConfig(
            max_risk_per_trade=0.02,
            atr_sl_multiplier=2.0,
            min_risk_reward=0.1,
        ),
        min_confluence=1,
    )

    atr_full = _indicator_cache._cache[("atr", 14)]
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
        ))

    return signals


# ── Replay Engine ──────────────────────────────────────────────────────


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


def replay(
    signals: list[BarSignal],
    params: dict,
    variant: str,
    initial_capital: float = 10_000.0,
    direction_filter: str | None = None,
    regime_filter: list[str] | None = None,
) -> tuple[list[ReplayTrade], list[float], dict]:
    """Simulate trades from pre-computed signals with given parameters."""
    min_conf = params["min_confluence"]
    atr_mult = params["atr_sl_multiplier"]
    risk_pct = params["max_risk_per_trade"]
    tp_ratio = params.get("tp_ratio", 1.618)
    enable_partial_tp = variant == "partial_tp"

    trades: list[ReplayTrade] = []
    equity = [initial_capital]
    capital = initial_capital

    open_trade: ReplayTrade | None = None
    original_sl: float = 0.0
    partial_closed = False
    tp2: float = 0.0  # Second take-profit for partial TP
    partial_pnl_accumulated: float = 0.0  # PnL from partial close
    pos_size: float = 0.0  # Track position size for partial TP

    for i, sig in enumerate(signals):
        if open_trade is not None:
            h, l = sig.high, sig.low

            # Check SL/TP
            hit_sl = hit_tp = False
            if open_trade.direction == "BUY":
                hit_sl = l <= open_trade.stop_loss
                hit_tp = h >= open_trade.take_profit
            else:
                hit_sl = h >= open_trade.stop_loss
                hit_tp = l <= open_trade.take_profit

            # Partial TP: check TP1 first (before full exit)
            if enable_partial_tp and not partial_closed and hit_tp:
                # Close 50% at TP1
                exit_price = open_trade.take_profit
                half_size = pos_size * 0.5
                fee = exit_price * half_size * FEE_RATE
                if open_trade.direction == "BUY":
                    partial_pnl = (exit_price - open_trade.entry_price) * half_size - fee
                else:
                    partial_pnl = (open_trade.entry_price - exit_price) * half_size - fee
                partial_pnl_accumulated = partial_pnl
                capital += partial_pnl

                # Move SL to break-even, target TP2
                open_trade.stop_loss = open_trade.entry_price
                open_trade.take_profit = tp2
                partial_closed = True
                pos_size = half_size  # Remaining half
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
                capital += gross_pnl - fee  # partial_pnl already added
                trades.append(open_trade)
                open_trade = None

            equity.append(capital)
            continue

        # ── No open trade → check for entry ──
        if sig.action in ("BUY", "SELL") and sig.confluence >= min_conf:
            # Direction filter
            if direction_filter and sig.action != direction_filter:
                equity.append(capital)
                continue
            # Regime filter
            if regime_filter and sig.regime not in regime_filter:
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

            # Position sizing: risk-based
            risk_dist = abs(entry - sl)
            if risk_dist <= 0:
                equity.append(capital)
                continue
            pos_size = capital * risk_pct / risk_dist

            # Entry fee
            entry_fee = entry * pos_size * FEE_RATE
            capital -= entry_fee

            open_trade = ReplayTrade(
                entry_idx=i,
                entry_price=entry,
                direction=sig.action,
                stop_loss=sl,
                take_profit=tp1,
            )
            original_sl = sl
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

    metrics = calculate_metrics(trades, equity, initial_capital)
    return trades, equity, metrics


# ── Metrics ─────────────────────────────────────────────────────────────


def calculate_metrics(
    trades: list[ReplayTrade], equity_curve: list[float], initial_capital: float,
) -> dict:
    if not trades:
        return {
            "total_trades": 0, "win_rate": 0, "profit_factor": 0,
            "total_return_pct": 0, "max_drawdown_pct": 0, "sharpe_ratio": 0,
            "avg_risk_reward": 0, "net_pnl": 0,
            "buy_trades": 0, "buy_win_rate": 0, "buy_pnl": 0,
            "sell_trades": 0, "sell_win_rate": 0, "sell_pnl": 0,
        }

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    total_win = sum(t.pnl for t in wins) if wins else 0
    total_loss = abs(sum(t.pnl for t in losses)) if losses else 0

    # BUY vs SELL breakdown
    buy_trades = [t for t in trades if t.direction == "BUY"]
    sell_trades = [t for t in trades if t.direction == "SELL"]
    buy_wins = [t for t in buy_trades if t.pnl > 0]
    sell_wins = [t for t in sell_trades if t.pnl > 0]

    # Max drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # Sharpe
    eq = np.array(equity_curve)
    returns = np.diff(eq) / eq[:-1] if len(eq) > 1 else np.array([])
    sharpe = (
        float(np.mean(returns) / np.std(returns) * np.sqrt(252))
        if len(returns) > 0 and np.std(returns) > 0 else 0.0
    )

    total_ret = (equity_curve[-1] - initial_capital) / initial_capital * 100

    return {
        "total_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "profit_factor": total_win / total_loss if total_loss > 0 else (10.0 if total_win > 0 else 0),
        "total_return_pct": total_ret,
        "max_drawdown_pct": max_dd,
        "sharpe_ratio": sharpe,
        "avg_risk_reward": 0,
        "net_pnl": equity_curve[-1] - initial_capital,
        "buy_trades": len(buy_trades),
        "buy_win_rate": len(buy_wins) / len(buy_trades) * 100 if buy_trades else 0,
        "buy_pnl": sum(t.pnl for t in buy_trades),
        "sell_trades": len(sell_trades),
        "sell_win_rate": len(sell_wins) / len(sell_trades) * 100 if sell_trades else 0,
        "sell_pnl": sum(t.pnl for t in sell_trades),
    }


# ── Buy-and-Hold Benchmark ────────────────────────────────────────────


def buy_and_hold(signals: list[BarSignal], capital: float = 10_000.0) -> dict:
    """Calculate buy-and-hold return (with entry/exit fees)."""
    if not signals:
        return {"return_pct": 0, "start_price": 0, "end_price": 0, "net_pnl": 0}
    start = signals[0].close
    end = signals[-1].close
    # Buy at start, sell at end — pay fees both ways
    qty = capital / start
    entry_fee = capital * FEE_RATE
    exit_value = qty * end
    exit_fee = exit_value * FEE_RATE
    net = exit_value - entry_fee - exit_fee - capital
    return {
        "return_pct": net / capital * 100,
        "start_price": start,
        "end_price": end,
        "net_pnl": net,
    }


# ── Scoring ─────────────────────────────────────────────────────────────


def composite_score(metrics: dict) -> float:
    pf = metrics.get("profit_factor", 0)
    dd = metrics.get("max_drawdown_pct", 0)
    n = metrics.get("total_trades", 0)
    if isinstance(pf, float) and (math.isinf(pf) or math.isnan(pf)):
        pf = 10.0
    if isinstance(dd, float) and math.isnan(dd):
        dd = 100.0
    base = pf * max(0, 1 - dd / 100)
    trade_factor = min(n / 10, 1.0)
    return base * trade_factor


def sanitize(v):
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return 0.0
    return v


# ── Grid Search ─────────────────────────────────────────────────────────


def generate_param_combos() -> list[dict]:
    names = list(PARAM_GRID.keys())
    values = list(PARAM_GRID.values())
    return [dict(zip(names, vals)) for vals in itertools.product(*values)]


def run_grid_search(
    pairs_signals: dict[str, list[BarSignal]],
) -> list[dict]:
    """Replay all param combos × variants × pairs."""
    combos = generate_param_combos()
    total = len(combos) * len(VARIANTS) * len(pairs_signals)
    print(f"  {len(combos)} param combos x {len(VARIANTS)} variants x "
          f"{len(pairs_signals)} pairs = {total} replays")

    results = []
    done = 0
    start = time.time()

    for pair, signals in pairs_signals.items():
        for variant in VARIANTS:
            for params in combos:
                trades, eq, metrics = replay(signals, params, variant)
                score = composite_score(metrics)
                results.append({
                    "pair": pair, "params": params.copy(), "variant": variant,
                    "metrics": {k: sanitize(v) for k, v in metrics.items()},
                    "score": score, "trades": trades,
                })
                done += 1
                if done % 1000 == 0 or done == total:
                    elapsed = time.time() - start
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (total - done) / rate if rate > 0 else 0
                    print(f"  [{done}/{total}] {elapsed:.1f}s elapsed, ~{eta:.0f}s ETA")

    return results


# ── Ranking & Analysis ──────────────────────────────────────────────────


def rank_configs(results: list[dict]) -> list[dict]:
    config_scores: dict[str, dict] = {}
    for r in results:
        key = f"{r['params']}|{r['variant']}"
        if key not in config_scores:
            config_scores[key] = {
                "params": r["params"], "variant": r["variant"],
                "scores": {}, "metrics": {}, "total_trades": 0,
            }
        config_scores[key]["scores"][r["pair"]] = r["score"]
        config_scores[key]["metrics"][r["pair"]] = r["metrics"]
        config_scores[key]["total_trades"] += r["metrics"].get("total_trades", 0)

    ranked = []
    for data in config_scores.values():
        scores = list(data["scores"].values())
        avg = sum(scores) / len(scores) if scores else 0
        mn = min(scores) if scores else 0
        consistency = mn / (avg + 0.001) if avg > 0 else 0
        data["avg_score"] = avg
        data["consistency"] = consistency
        data["combined_score"] = avg * (0.7 + 0.3 * consistency)
        ranked.append(data)

    ranked.sort(key=lambda x: x["combined_score"], reverse=True)
    return ranked


def parameter_sensitivity(results: list[dict]) -> dict:
    sensitivity = {}
    for param_name in PARAM_GRID:
        sensitivity[param_name] = {}
        for val in PARAM_GRID[param_name]:
            matching = [r for r in results if r["params"][param_name] == val]
            if not matching:
                continue
            sensitivity[param_name][val] = {
                "avg_score": sum(r["score"] for r in matching) / len(matching),
                "avg_trades": sum(r["metrics"].get("total_trades", 0) for r in matching) / len(matching),
                "avg_win_rate": sum(r["metrics"].get("win_rate", 0) for r in matching) / len(matching),
                "avg_return": sum(r["metrics"].get("total_return_pct", 0) for r in matching) / len(matching),
            }
    return sensitivity


def variant_comparison(results: list[dict]) -> dict:
    comparison = {}
    for variant in VARIANTS:
        matching = [r for r in results if r["variant"] == variant]
        if not matching:
            continue
        n = len(matching)
        pfs = [r["metrics"].get("profit_factor", 0) for r in matching
               if r["metrics"].get("profit_factor", 0) < 100]
        comparison[variant] = {
            "avg_score": sum(r["score"] for r in matching) / n,
            "avg_return": sum(r["metrics"].get("total_return_pct", 0) for r in matching) / n,
            "avg_win_rate": sum(r["metrics"].get("win_rate", 0) for r in matching) / n,
            "avg_drawdown": sum(r["metrics"].get("max_drawdown_pct", 0) for r in matching) / n,
            "avg_profit_factor": sum(pfs) / len(pfs) if pfs else 0,
            "avg_trades": sum(r["metrics"].get("total_trades", 0) for r in matching) / n,
        }
    return comparison


def best_config_per_pair(results: list[dict]) -> dict[str, dict]:
    pair_results: dict[str, list[dict]] = {}
    for r in results:
        pair_results.setdefault(r["pair"], []).append(r)
    best_per_pair = {}
    for pair, pair_r in pair_results.items():
        pair_r.sort(key=lambda x: x["score"], reverse=True)
        if pair_r:
            top = pair_r[0]
            best_per_pair[pair] = {
                "params": top["params"], "variant": top["variant"],
                "score": top["score"], "metrics": top["metrics"],
            }
    return best_per_pair


def timeframe_comparison(results: list[dict], pairs: dict) -> dict:
    """Group results by timeframe and compare performance."""
    tf_results: dict[str, list[dict]] = {}
    for r in results:
        pair_key = r["pair"]
        tf = pairs.get(pair_key, {}).get("tf", "unknown")
        tf_results.setdefault(tf, []).append(r)

    comparison = {}
    for tf, tf_r in sorted(tf_results.items()):
        n = len(tf_r)
        comparison[tf] = {
            "count": n,
            "avg_score": sum(r["score"] for r in tf_r) / n,
            "avg_return": sum(r["metrics"].get("total_return_pct", 0) for r in tf_r) / n,
            "avg_win_rate": sum(r["metrics"].get("win_rate", 0) for r in tf_r) / n,
            "avg_drawdown": sum(r["metrics"].get("max_drawdown_pct", 0) for r in tf_r) / n,
            "avg_trades": sum(r["metrics"].get("total_trades", 0) for r in tf_r) / n,
        }
    return comparison


# ── Walk-Forward Validation ─────────────────────────────────────────────


def run_wfo_validation(
    top_configs: list[dict],
    pairs_signals: dict[str, list[BarSignal]],
) -> list[dict]:
    wfo_results = []
    for idx, cfg in enumerate(top_configs[:WFO_TOP_N]):
        params = cfg["params"]
        variant = cfg["variant"]
        print(f"  WFO [{idx+1}/{min(len(top_configs), WFO_TOP_N)}]: "
              f"conf={params['min_confluence']} atr={params['atr_sl_multiplier']} "
              f"tp={params.get('tp_ratio', 1.618)} risk={params['max_risk_per_trade']} ({variant})")

        is_scores, oos_scores = [], []
        for pair, signals in pairs_signals.items():
            if len(signals) < 100:
                continue
            mid = int(len(signals) * 0.6)
            _, _, m_is = replay(signals[:mid], params, variant)
            is_scores.append(composite_score(m_is))
            _, _, m_oos = replay(signals[mid:], params, variant)
            oos_scores.append(composite_score(m_oos))

        avg_is = sum(is_scores) / len(is_scores) if is_scores else 0
        avg_oos = sum(oos_scores) / len(oos_scores) if oos_scores else 0
        deg = (avg_is - avg_oos) / avg_is * 100 if avg_is > 0 else 0

        wfo_results.append({
            "params": params, "variant": variant,
            "in_sample_score": avg_is, "out_of_sample_score": avg_oos,
            "degradation_pct": deg, "likely_overfit": deg > 50,
            "combined_score": cfg.get("combined_score", 0),
        })

    return wfo_results


# ── Utility ─────────────────────────────────────────────────────────────


def fmt(v, kind="float") -> str:
    if v is None or (isinstance(v, float) and (math.isinf(v) or math.isnan(v))):
        return "N/A"
    if kind == "pct":
        return f"{v:.1f}%"
    if kind == "int":
        return str(int(v))
    if kind == "dollar":
        return f"${v:,.0f}"
    return f"{v:.2f}"


# ── Report Generation ──────────────────────────────────────────────────


def generate_report(
    all_data: dict,
) -> str:
    """Generate comprehensive markdown report from all analysis data."""
    L = []  # lines
    pair_names = all_data["pair_names"]
    pairs_info = all_data["pairs_info"]

    L.append("# SignalForgeAI Comprehensive Backtest Results (v3)\n")
    L.append(f"> Generated on 2026-03-04 | Runtime: {all_data['elapsed']:.0f}s")
    L.append("> Engine: Full 6-layer SignalPipeline with indicator caching")
    L.append(f"> Transaction costs: {FEE_RATE*100:.3f}% per side ({FEE_RATE*2*100:.3f}% round trip)")
    L.append("> Data: Real Binance/Coinbase/Index candles\n")

    # ── Test Environment ──
    L.append("## Test Environment\n")
    L.append("| Pair | Timeframe | Source | Bars |")
    L.append("|------|-----------|--------|------|")
    for pair in pair_names:
        info = pairs_info.get(pair, {})
        L.append(f"| {pair} | {info.get('tf', '?')} | {info.get('source', '?')} | {info.get('bars', 0):,} |")
    L.append("")
    total_combos = len(generate_param_combos())
    total_tests = total_combos * len(VARIANTS) * len(pair_names)
    L.append(f"- **Pairs tested:** {len(pair_names)}")
    L.append(f"- **Parameter combinations:** {total_combos}")
    L.append(f"- **Variants:** {len(VARIANTS)} ({', '.join(VARIANTS)})")
    L.append(f"- **Total backtests:** {total_tests:,}")
    L.append(f"- **Initial capital:** ${INITIAL_CAPITAL:,.0f}\n")

    # ── 1. Buy-and-Hold Benchmark ──
    L.append("---\n")
    L.append("## 1. Buy-and-Hold Benchmark\n")
    L.append("What you'd get by simply buying and holding each asset.\n")
    L.append("| Pair | TF | Start Price | End Price | B&H Return | B&H P&L |")
    L.append("|------|----|------------|----------|-----------|---------|")
    bh = all_data["buy_hold"]
    for pair in pair_names:
        b = bh.get(pair, {})
        tf = pairs_info.get(pair, {}).get("tf", "?")
        L.append(f"| {pair} | {tf} | ${b.get('start_price', 0):,.2f} | ${b.get('end_price', 0):,.2f} | "
                 f"{b.get('return_pct', 0):.1f}% | {fmt(b.get('net_pnl', 0), 'dollar')} |")
    L.append("")

    # ── 2. BUY vs SELL Breakdown (Baseline) ──
    L.append("---\n")
    L.append("## 2. BUY vs SELL Breakdown (Baseline)\n")
    L.append("Default params, both directions. Shows whether SELL trades drag performance.\n")
    L.append("| Pair | TF | BUY Trades | BUY Win% | BUY P&L | SELL Trades | SELL Win% | SELL P&L | Net P&L | B&H Return |")
    L.append("|------|----|-----------|---------|---------|------------|----------|---------|---------|-----------|")
    baseline = all_data["baseline"]
    for pair in pair_names:
        bl = next((b for b in baseline if b["pair"] == pair), None)
        if not bl:
            continue
        m = bl["metrics"]
        b = bh.get(pair, {})
        tf = pairs_info.get(pair, {}).get("tf", "?")
        L.append(
            f"| {pair} | {tf} | {m.get('buy_trades', 0)} | {m.get('buy_win_rate', 0):.0f}% | "
            f"{fmt(m.get('buy_pnl', 0), 'dollar')} | {m.get('sell_trades', 0)} | "
            f"{m.get('sell_win_rate', 0):.0f}% | {fmt(m.get('sell_pnl', 0), 'dollar')} | "
            f"{fmt(m.get('net_pnl', 0), 'dollar')} | {b.get('return_pct', 0):.1f}% |"
        )
    # Totals
    total_buy_pnl = sum(next((b for b in baseline if b["pair"] == p), {"metrics": {}})
                         .get("metrics", {}).get("buy_pnl", 0) for p in pair_names)
    total_sell_pnl = sum(next((b for b in baseline if b["pair"] == p), {"metrics": {}})
                          .get("metrics", {}).get("sell_pnl", 0) for p in pair_names)
    L.append(f"| **TOTAL** | | | | **{fmt(total_buy_pnl, 'dollar')}** | | | "
             f"**{fmt(total_sell_pnl, 'dollar')}** | **{fmt(total_buy_pnl + total_sell_pnl, 'dollar')}** | |")
    L.append("")

    # ── 3. Long-Only vs Both Directions ──
    L.append("---\n")
    L.append("## 3. Long-Only vs Both Directions\n")
    L.append("Same params, but filtering out all SELL signals.\n")
    L.append("| Pair | TF | Both Return | Both Trades | Long-Only Return | Long-Only Trades | Improvement |")
    L.append("|------|----|-----------|------------|-----------------|----------------|------------|")
    long_only = all_data["long_only"]
    for pair in pair_names:
        bl = next((b for b in baseline if b["pair"] == pair), None)
        lo = next((b for b in long_only if b["pair"] == pair), None)
        if not bl or not lo:
            continue
        tf = pairs_info.get(pair, {}).get("tf", "?")
        both_ret = bl["metrics"].get("total_return_pct", 0)
        lo_ret = lo["metrics"].get("total_return_pct", 0)
        improvement = lo_ret - both_ret
        L.append(
            f"| {pair} | {tf} | {both_ret:.1f}% | {bl['metrics'].get('total_trades', 0)} | "
            f"{lo_ret:.1f}% | {lo['metrics'].get('total_trades', 0)} | "
            f"{'**+' if improvement > 0 else ''}{improvement:.1f}%{'**' if improvement > 0 else ''} |"
        )
    L.append("")

    # ── 4. Trending-Only vs All Regimes ──
    L.append("---\n")
    L.append("## 4. Trending-Only vs All Regimes\n")
    L.append("Filtering out signals generated during RANGING/TRANSITIONING regimes.\n")
    L.append("| Pair | TF | All Regimes Return | Trending-Only Return | Trades (All) | Trades (Trending) |")
    L.append("|------|----|-------------------|---------------------|-------------|------------------|")
    trending_only = all_data["trending_only"]
    for pair in pair_names:
        bl = next((b for b in baseline if b["pair"] == pair), None)
        tr = next((b for b in trending_only if b["pair"] == pair), None)
        if not bl or not tr:
            continue
        tf = pairs_info.get(pair, {}).get("tf", "?")
        L.append(
            f"| {pair} | {tf} | {bl['metrics'].get('total_return_pct', 0):.1f}% | "
            f"{tr['metrics'].get('total_return_pct', 0):.1f}% | "
            f"{bl['metrics'].get('total_trades', 0)} | {tr['metrics'].get('total_trades', 0)} |"
        )
    L.append("")

    # ── 5. Timeframe Comparison ──
    L.append("---\n")
    L.append("## 5. Timeframe Comparison\n")
    L.append("Averaged across all parameter combinations.\n")
    L.append("| Timeframe | Avg Score | Avg Return | Avg Win Rate | Avg Drawdown | Avg Trades |")
    L.append("|-----------|----------|-----------|-------------|-------------|-----------|")
    tf_comp = all_data["tf_comparison"]
    for tf, data in sorted(tf_comp.items()):
        L.append(
            f"| {tf} | {data['avg_score']:.3f} | {data['avg_return']:.1f}% | "
            f"{data['avg_win_rate']:.1f}% | {data['avg_drawdown']:.1f}% | {data['avg_trades']:.0f} |"
        )
    L.append("")

    # ── 6. Baseline vs Partial TP ──
    L.append("---\n")
    L.append("## 6. Baseline vs Partial Take-Profit\n")
    L.append("Partial TP: close 50% at TP1, trail remaining 50% to TP2 (2.618x).\n")
    L.append("| Variant | Avg Score | Avg Return | Avg Win Rate | Avg Drawdown | Avg PF |")
    L.append("|---------|----------|-----------|-------------|-------------|--------|")
    var_comp = all_data["variant_comparison"]
    for variant in VARIANTS:
        d = var_comp.get(variant, {})
        L.append(
            f"| {variant} | {fmt(d.get('avg_score', 0))} | {fmt(d.get('avg_return', 0), 'pct')} | "
            f"{fmt(d.get('avg_win_rate', 0), 'pct')} | {fmt(d.get('avg_drawdown', 0), 'pct')} | "
            f"{fmt(d.get('avg_profit_factor', 0))} |"
        )
    L.append("")

    # ── 7. Top 10 Configurations ──
    L.append("---\n")
    L.append("## 7. Top 10 Universal Configurations\n")
    L.append(f"Ranked by combined score (profit_factor × (1-drawdown/100) × min(trades/10,1)), averaged across {len(pair_names)} pairs.\n")
    L.append("| Rank | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Avg Return | Avg Win Rate |")
    L.append("|------|-----------|----------|------|---------|---------|-------|-----------|-------------|")
    ranked = all_data["ranked"]
    for i, cfg in enumerate(ranked[:10]):
        p = cfg["params"]
        all_m = list(cfg["metrics"].values())
        avg_ret = sum(m.get("total_return_pct", 0) for m in all_m) / len(all_m) if all_m else 0
        avg_wr = sum(m.get("win_rate", 0) for m in all_m) / len(all_m) if all_m else 0
        L.append(
            f"| {i+1} | {p['min_confluence']} | {p['atr_sl_multiplier']} | "
            f"{p['max_risk_per_trade']:.0%} | {p.get('tp_ratio', 1.618)} | {cfg['variant']} | "
            f"{cfg['combined_score']:.3f} | {avg_ret:.1f}% | {avg_wr:.1f}% |"
        )
    L.append("")

    # ── 8. Parameter Sensitivity ──
    L.append("---\n")
    L.append("## 8. Parameter Sensitivity\n")
    sensitivity = all_data["sensitivity"]
    for param_name, values in sensitivity.items():
        display_name = param_name.replace("_", " ").title()
        L.append(f"### {display_name}\n")
        L.append(f"| {display_name} | Avg Score | Avg Win Rate | Avg Return | Avg Trades |")
        L.append("|" + "---|" * 5)
        for val, data in sorted(values.items()):
            L.append(
                f"| {val} | {data['avg_score']:.3f} | "
                f"{data['avg_win_rate']:.1f}% | {data['avg_return']:.1f}% | "
                f"{data['avg_trades']:.1f} |"
            )
        L.append("")

    # ── 9. Walk-Forward Validation ──
    L.append("---\n")
    L.append("## 9. Walk-Forward Validation (Top 5)\n")
    L.append("60% in-sample / 40% out-of-sample.\n")
    L.append("| # | Confluence | ATR Mult | Risk | TP Ratio | Variant | In-Sample | OOS | Degradation | Overfit? |")
    L.append("|---|-----------|----------|------|---------|---------|----------|-----|------------|---------|")
    for i, wfo in enumerate(all_data["wfo_results"]):
        p = wfo["params"]
        overfit = "YES" if wfo["likely_overfit"] else "No"
        L.append(
            f"| {i+1} | {p['min_confluence']} | {p['atr_sl_multiplier']} | "
            f"{p['max_risk_per_trade']:.0%} | {p.get('tp_ratio', 1.618)} | {wfo['variant']} | "
            f"{wfo['in_sample_score']:.3f} | {wfo['out_of_sample_score']:.3f} | "
            f"{wfo['degradation_pct']:.0f}% | {overfit} |"
        )
    L.append("")

    # ── 10. Per-Pair Best Configs ──
    L.append("---\n")
    L.append("## 10. Best Configuration Per Pair\n")
    L.append("| Pair | TF | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Return | Win Rate |")
    L.append("|------|----|-----------|----------|------|---------|---------|-------|--------|---------|")
    per_pair = all_data["per_pair_best"]
    for pair in pair_names:
        if pair in per_pair:
            cfg = per_pair[pair]
            p = cfg["params"]
            m = cfg["metrics"]
            tf = pairs_info.get(pair, {}).get("tf", "?")
            L.append(
                f"| {pair} | {tf} | {p['min_confluence']} | {p['atr_sl_multiplier']} | "
                f"{p['max_risk_per_trade']:.0%} | {p.get('tp_ratio', 1.618)} | "
                f"{cfg['variant']} | {cfg['score']:.2f} | "
                f"{m.get('total_return_pct', 0):.1f}% | {m.get('win_rate', 0):.1f}% |"
            )
    L.append("")

    # ── 11. Recommendations ──
    L.append("---\n")
    L.append("## 11. Recommendations\n")

    if ranked:
        best = ranked[0]
        bp = best["params"]
        L.append("### Best Universal Configuration\n")
        L.append("```json")
        L.append("{")
        L.append(f'  "min_confluence": {bp["min_confluence"]},')
        L.append(f'  "atr_sl_multiplier": {bp["atr_sl_multiplier"]},')
        L.append(f'  "max_risk_per_trade": {bp["max_risk_per_trade"]},')
        L.append(f'  "tp1_ratio": {bp.get("tp_ratio", 1.618)}')
        L.append("}")
        L.append("```\n")

    # Key findings
    L.append("### Key Findings\n")

    # BUY vs SELL summary
    if total_buy_pnl != 0 or total_sell_pnl != 0:
        L.append(f"- **BUY trades total P&L:** {fmt(total_buy_pnl, 'dollar')} | "
                 f"**SELL trades total P&L:** {fmt(total_sell_pnl, 'dollar')}")
        if total_sell_pnl < 0 and total_buy_pnl > 0:
            L.append(f"  - SELL trades are destroying {fmt(abs(total_sell_pnl), 'dollar')} of value. "
                     f"**Recommend: long-only mode.**")

    # Sensitivity findings
    for param_name, values in sensitivity.items():
        if values:
            best_val = max(values.items(), key=lambda x: x[1]["avg_score"])
            worst_val = min(values.items(), key=lambda x: x[1]["avg_score"])
            display_name = param_name.replace("_", " ").title()
            L.append(
                f"- **{display_name}:** Best at `{best_val[0]}` "
                f"(score {best_val[1]['avg_score']:.3f}), worst at `{worst_val[0]}` "
                f"(score {worst_val[1]['avg_score']:.3f})"
            )

    # Variant finding
    if var_comp:
        best_var = max(var_comp.items(), key=lambda x: x[1].get("avg_score", 0))
        L.append(f"- **Exit strategy:** `{best_var[0]}` performed best (avg score {best_var[1]['avg_score']:.3f})")

    # Timeframe finding
    if tf_comp:
        best_tf = max(tf_comp.items(), key=lambda x: x[1].get("avg_score", 0))
        L.append(f"- **Best timeframe:** `{best_tf[0]}` (avg score {best_tf[1]['avg_score']:.3f}, "
                 f"avg return {best_tf[1]['avg_return']:.1f}%)")

    L.append("")
    L.append("### Production Recommendations\n")
    L.append("1. **Make TP ratio configurable** — hardcoded 1.618 is suboptimal")
    L.append("2. **Add direction_filter option** — `long_only` for crypto in bull markets")
    L.append("3. **Add regime filtering** — skip RANGING regime if data supports it")
    L.append("4. **Implement partial take-profit** — if partial_tp variant outperforms")
    L.append("5. **Fix Fibonacci swing detection** — use recent N-bar window, not all-time high/low")
    L.append("6. **Enable per-pair configs** — leverage existing FeedbackFilter infrastructure")
    L.append("")

    return "\n".join(L)


# ── Main ────────────────────────────────────────────────────────────────


def main():
    overall_start = time.time()

    print("=" * 70)
    print("  SignalForgeAI Comprehensive Backtest v3 (enhanced)")
    print("=" * 70)

    # ── Discover and load data ──
    print("\n[1/8] Discovering and loading CSV data...")
    PAIRS = discover_pairs(DATA_DIR)
    if not PAIRS:
        print("ERROR: No CSV files found in", DATA_DIR)
        return

    pairs_candles: dict[str, pd.DataFrame] = {}
    for pair, info in sorted(PAIRS.items()):
        df = load_csv(info["file"])
        if len(df) < 300:
            print(f"  {pair}: only {len(df)} bars (need 300+) — skipping")
            continue
        pairs_candles[pair] = df
        info["bars"] = len(df)
        print(f"  {pair} ({info['tf']}, {info['source']}): {len(df):,} bars")

    if not pairs_candles:
        print("ERROR: No valid data loaded.")
        return

    # ── Pre-compute signals ──
    print(f"\n[2/8] Pre-computing signals ({len(pairs_candles)} pairs)...")
    pairs_signals: dict[str, list[BarSignal]] = {}

    for pair, candles in pairs_candles.items():
        t0 = time.time()
        tf = PAIRS[pair]["tf"]
        _indicator_cache.setup(candles)
        signals = precompute_signals(candles, pair, tf)
        pairs_signals[pair] = signals
        elapsed = time.time() - t0
        n_signals = sum(1 for s in signals if s.action in ("BUY", "SELL"))
        print(f"  {pair}: {len(signals)} bars, {n_signals} raw signals, {elapsed:.1f}s")

    # ── Buy-and-hold benchmark ──
    print("\n[3/8] Computing buy-and-hold benchmarks...")
    bh_results = {}
    for pair, signals in pairs_signals.items():
        bh_results[pair] = buy_and_hold(signals)
        print(f"  {pair}: B&H return {bh_results[pair]['return_pct']:.1f}%")

    # ── Baseline (default params, both directions) ──
    print("\n[4/8] Running baseline backtests...")
    baseline_params = {
        "min_confluence": 50,
        "atr_sl_multiplier": 2.0,
        "max_risk_per_trade": 0.02,
        "tp_ratio": 1.618,
    }
    baseline_results = []
    for pair, signals in pairs_signals.items():
        trades, eq, metrics = replay(signals, baseline_params, "baseline")
        baseline_results.append({"pair": pair, "metrics": metrics})
        m = metrics
        print(f"  {pair}: {m['total_trades']} trades (BUY:{m['buy_trades']} SELL:{m['sell_trades']}), "
              f"return {m['total_return_pct']:.1f}%, "
              f"BUY P&L: ${m['buy_pnl']:.0f}, SELL P&L: ${m['sell_pnl']:.0f}")

    # ── Long-only comparison ──
    print("\n[5/8] Running long-only comparison...")
    long_only_results = []
    for pair, signals in pairs_signals.items():
        trades, eq, metrics = replay(signals, baseline_params, "baseline", direction_filter="BUY")
        long_only_results.append({"pair": pair, "metrics": metrics})
        print(f"  {pair}: {metrics['total_trades']} trades, return {metrics['total_return_pct']:.1f}%")

    # ── Trending-only comparison ──
    print("\n[6/8] Running trending-only comparison...")
    trending_only_results = []
    for pair, signals in pairs_signals.items():
        trades, eq, metrics = replay(signals, baseline_params, "baseline", regime_filter=["trending"])
        trending_only_results.append({"pair": pair, "metrics": metrics})
        print(f"  {pair}: {metrics['total_trades']} trades, return {metrics['total_return_pct']:.1f}%")

    # ── Grid search ──
    print("\n[7/8] Running grid search...")
    grid_results = run_grid_search(pairs_signals)

    # ── Analysis ──
    print("\n[8/8] Analyzing results...")
    ranked = rank_configs(grid_results)
    sensitivity = parameter_sensitivity(grid_results)
    var_comp = variant_comparison(grid_results)
    per_pair = best_config_per_pair(grid_results)
    tf_comp = timeframe_comparison(grid_results, PAIRS)

    if ranked:
        best = ranked[0]
        bp = best["params"]
        print(f"  Best universal: conf={bp['min_confluence']} atr={bp['atr_sl_multiplier']} "
              f"tp={bp.get('tp_ratio', 1.618)} risk={bp['max_risk_per_trade']} "
              f"({best['variant']}) score={best['combined_score']:.3f}")

    # Walk-forward validation
    print("\n  Walk-forward validation...")
    wfo_results = run_wfo_validation(ranked, pairs_signals)

    # ── Generate report ──
    elapsed = time.time() - overall_start
    print(f"\nGenerating report... (total runtime: {elapsed:.0f}s)")

    report = generate_report({
        "pair_names": list(pairs_signals.keys()),
        "pairs_info": {k: {**PAIRS[k], "bars": len(pairs_candles.get(k, []))} for k in pairs_signals},
        "buy_hold": bh_results,
        "baseline": baseline_results,
        "long_only": long_only_results,
        "trending_only": trending_only_results,
        "ranked": ranked,
        "sensitivity": sensitivity,
        "variant_comparison": var_comp,
        "tf_comparison": tf_comp,
        "per_pair_best": per_pair,
        "wfo_results": wfo_results,
        "elapsed": elapsed,
    })

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport: {os.path.abspath(OUTPUT_PATH)}")

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
