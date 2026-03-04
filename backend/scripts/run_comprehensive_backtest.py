"""
Comprehensive backtest of SignalForge on real Binance data (v2 — fast).

Architecture:
  1. Indicator caching: pre-compute all indicators once per pair (eliminates O(N²))
  2. Signal pre-computation: run the real pipeline once with relaxed thresholds
  3. Fast replay: simulate trades from pre-computed signals with different params

This reduces runtime from ~5 days (naive approach) to ~2 minutes.

Usage:
    cd backend
    .venv/Scripts/python.exe -u scripts/run_comprehensive_backtest.py

Output:
    docs/BACKTEST-RESULTS.md
"""

from __future__ import annotations

import itertools
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field

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

PAIRS = {
    # Daily (1D)
    "BTC/USD-1D": {"file": os.path.join(DATA_DIR, "BINANCE_BTCUSD, 1D.csv"), "tf": "1D"},
    "ETH/USD-1D": {"file": os.path.join(DATA_DIR, "BINANCE_ETHUSD, 1D.csv"), "tf": "1D"},
    "SOL/USD-1D": {"file": os.path.join(DATA_DIR, "BINANCE_SOLUSD, 1D.csv"), "tf": "1D"},
    "ADA/USDT-1D": {"file": os.path.join(DATA_DIR, "BINANCE_ADAUSDT, 1D.csv"), "tf": "1D"},
    "BNB/USD-1D": {"file": os.path.join(DATA_DIR, "BINANCE_BNBUSD, 1D.csv"), "tf": "1D"},
    "DOGE/USDT-1D": {"file": os.path.join(DATA_DIR, "BINANCE_DOGEUSDT, 1D.csv"), "tf": "1D"},
    "LINK/USDT-1D": {"file": os.path.join(DATA_DIR, "BINANCE_LINKUSDT, 1D.csv"), "tf": "1D"},
    "XRP/USDT-1D": {"file": os.path.join(DATA_DIR, "BINANCE_XRPUSDT, 1D.csv"), "tf": "1D"},
    "XMR/USDT-1D": {"file": os.path.join(DATA_DIR, "KUCOIN_XMRUSDT, 1D.csv"), "tf": "1D"},
    # 4-hour
    "HYPE/USDT-4h": {"file": os.path.join(DATA_DIR, "BINANCEUS_HYPEUSDT, 240.csv"), "tf": "4h"},
    # 1-hour
    "BTC/USD-1h": {"file": os.path.join(DATA_DIR, "BINANCE_BTCUSD, 60.csv"), "tf": "1h"},
    "ETH/USDT-1h": {"file": os.path.join(DATA_DIR, "BINANCE_ETHUSDT, 60.csv"), "tf": "1h"},
    "SOL/USDT-1h": {"file": os.path.join(DATA_DIR, "BINANCE_SOLUSDT, 60.csv"), "tf": "1h"},
}

PARAM_GRID = {
    "min_confluence": [40, 50, 60, 70],
    "atr_sl_multiplier": [1.5, 2.0, 2.5, 3.0],
    "max_risk_per_trade": [0.01, 0.02],
    "tp_ratio": [1.0, 1.2, 1.618, 2.0, 2.618],
}

VARIANTS = ["baseline", "breakeven", "trailing"]
INITIAL_CAPITAL = 10_000.0
LOOKBACK = 200
WFO_TOP_N = 5

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
#
# The pipeline recomputes ALL indicators from scratch on every bar
# (expanding window → O(N²) total work). This cache computes them ONCE
# on the full dataset and returns slices. Indicators are causal (no
# lookahead), so full_result.iloc[:N] == compute_on_first_N_bars.


class IndicatorCache:
    """Pre-compute all indicators once and monkey-patch module references."""

    def __init__(self):
        self._cache: dict = {}
        self._originals: dict = {}
        self._patched = False

    def setup(self, candles: pd.DataFrame):
        """Pre-compute all indicators on full dataset and install patches."""
        close = candles["close"]

        # Save originals (only first time)
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

        # Pre-compute everything
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
        # Pre-compute EMAs for all periods used by the pipeline
        for period in [10, 20, 50, 100, 200]:
            self._cache[("ema", period)] = orig["compute_ema"](close, period)

        self._n = len(candles)
        self._install_patches()

    def _slice_result(self, result, n):
        """Slice a pre-computed result to length n."""
        if isinstance(result, tuple):
            return tuple(r.iloc[:n] if hasattr(r, "iloc") else r for r in result)
        if isinstance(result, dict):
            return {
                k: v.iloc[:n] if hasattr(v, "iloc") else v
                for k, v in result.items()
            }
        return result.iloc[:n]

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
            # Fallback for unexpected periods
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
            return {
                k: v.iloc[:n] if hasattr(v, "iloc") else v
                for k, v in r.items()
            }

        def _cached_obv(candles):
            return cache[("obv",)].iloc[: len(candles)]

        def _cached_williams_r(candles, period=14):
            return cache[("williams_r", 14)].iloc[: len(candles)]

        def _cached_cci(candles, period=20):
            return cache[("cci", 20)].iloc[: len(candles)]

        # Patch each module's imported references
        # regime.py imports: compute_adx, compute_atr
        _regime_mod.compute_adx = _cached_adx
        _regime_mod.compute_atr = _cached_atr
        # risk.py imports: compute_atr
        _risk_mod.compute_atr = _cached_atr
        # confluence.py imports: compute_bollinger_bands, compute_cci,
        #   compute_ichimoku, compute_macd, compute_obv, compute_rsi,
        #   compute_stochastic, compute_vwap, compute_williams_r
        _conf_mod.compute_rsi = _cached_rsi
        _conf_mod.compute_macd = _cached_macd
        _conf_mod.compute_stochastic = _cached_stochastic
        _conf_mod.compute_vwap = _cached_vwap
        _conf_mod.compute_bollinger_bands = _cached_bollinger
        _conf_mod.compute_ichimoku = _cached_ichimoku
        _conf_mod.compute_obv = _cached_obv
        _conf_mod.compute_williams_r = _cached_williams_r
        _conf_mod.compute_cci = _cached_cci
        # triggers.py imports: compute_macd, compute_rsi, compute_stochastic
        _trig_mod.compute_macd = _cached_macd
        _trig_mod.compute_rsi = _cached_rsi
        _trig_mod.compute_stochastic = _cached_stochastic
        # zones.py imports: compute_vwap (calculate_fib_levels takes scalars, no cache needed)
        _zone_mod.compute_vwap = _cached_vwap
        # trend.py imports: compute_ema, compute_vwap
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


def precompute_signals(
    candles: pd.DataFrame, pair: str, tf: str,
) -> list[BarSignal]:
    """Run the actual pipeline once per pair with min_confluence=1.

    Stores per-bar: action, direction, confluence_score, atr, close, high, low.
    The indicator cache MUST be set up before calling this function.
    """
    # Pipeline with very low thresholds to capture all possible signals
    pipeline = SignalPipeline(
        risk_config=RiskConfig(
            max_risk_per_trade=0.02,
            atr_sl_multiplier=2.0,
            min_risk_reward=0.1,  # Below 1.618 → never rejects
        ),
        min_confluence=1,  # Capture all signals with score ≥ 1
    )

    # Pre-computed ATR array for the full dataset
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

    @property
    def risk_reward(self) -> float:
        if self.exit_price == 0:
            return 0
        reward = abs(self.exit_price - self.entry_price)
        risk = abs(self.entry_price - self.stop_loss)
        return reward / risk if risk > 0 else 0


def replay(
    signals: list[BarSignal],
    params: dict,
    variant: str,
    initial_capital: float = 10_000.0,
) -> tuple[list[ReplayTrade], list[float], dict]:
    """Simulate trades from pre-computed signals with given parameters.

    Returns: (trades, equity_curve, metrics)
    """
    min_conf = params["min_confluence"]
    atr_mult = params["atr_sl_multiplier"]
    risk_pct = params["max_risk_per_trade"]
    tp_ratio = params.get("tp_ratio", 1.618)
    enable_breakeven = variant in ("breakeven", "trailing")
    enable_trailing = variant == "trailing"
    trail_atr_mult = 1.5
    max_hold_bars = params.get("max_hold_bars", 0)  # 0 = disabled

    trades: list[ReplayTrade] = []
    equity = [initial_capital]
    capital = initial_capital

    open_trade: ReplayTrade | None = None
    original_sl: float = 0.0
    breakeven_activated = False
    highest_since_entry: float = 0.0
    lowest_since_entry: float = float("inf")

    for i, sig in enumerate(signals):
        if open_trade is not None:
            # ── Manage open trade ──
            h, l = sig.high, sig.low

            # Track extremes
            if open_trade.direction == "BUY":
                highest_since_entry = max(highest_since_entry, h)
            else:
                lowest_since_entry = min(lowest_since_entry, l)

            # Break-even stop: move SL to entry after 1R profit
            if enable_breakeven and not breakeven_activated and original_sl != 0:
                risk_dist = abs(open_trade.entry_price - original_sl)
                if risk_dist > 0:
                    if open_trade.direction == "BUY":
                        if h >= open_trade.entry_price + risk_dist:
                            open_trade.stop_loss = open_trade.entry_price
                            breakeven_activated = True
                    else:
                        if l <= open_trade.entry_price - risk_dist:
                            open_trade.stop_loss = open_trade.entry_price
                            breakeven_activated = True

            # Trailing stop (ATR-based, only after break-even)
            if enable_trailing and breakeven_activated and sig.atr > 0:
                if open_trade.direction == "BUY":
                    trail_sl = highest_since_entry - sig.atr * trail_atr_mult
                    if trail_sl > open_trade.stop_loss:
                        open_trade.stop_loss = trail_sl
                elif open_trade.direction == "SELL":
                    trail_sl = lowest_since_entry + sig.atr * trail_atr_mult
                    if trail_sl < open_trade.stop_loss:
                        open_trade.stop_loss = trail_sl

            # Time-based exit: close if held too long with no significant profit
            if max_hold_bars > 0 and (i - open_trade.entry_idx) >= max_hold_bars:
                exit_price = sig.close
                risk_dist = abs(open_trade.entry_price - original_sl) if original_sl else sl_dist
                if risk_dist > 0:
                    pos_size = capital * risk_pct / risk_dist
                    if open_trade.direction == "BUY":
                        pnl = (exit_price - open_trade.entry_price) * pos_size
                    else:
                        pnl = (open_trade.entry_price - exit_price) * pos_size
                else:
                    pnl = 0.0
                open_trade.exit_idx = i
                open_trade.exit_price = exit_price
                open_trade.pnl = pnl
                capital += pnl
                trades.append(open_trade)
                open_trade = None
                equity.append(capital)
                continue

            # Check SL/TP
            hit_sl = hit_tp = False
            if open_trade.direction == "BUY":
                hit_sl = l <= open_trade.stop_loss
                hit_tp = h >= open_trade.take_profit
            else:
                hit_sl = h >= open_trade.stop_loss
                hit_tp = l <= open_trade.take_profit

            if hit_sl or hit_tp:
                exit_price = open_trade.stop_loss if hit_sl else open_trade.take_profit
                risk_dist = abs(open_trade.entry_price - original_sl) if original_sl else abs(open_trade.entry_price - open_trade.stop_loss)
                if risk_dist > 0:
                    pos_size = capital * risk_pct / risk_dist
                    if open_trade.direction == "BUY":
                        pnl = (exit_price - open_trade.entry_price) * pos_size
                    else:
                        pnl = (open_trade.entry_price - exit_price) * pos_size
                else:
                    pnl = 0.0

                open_trade.exit_idx = i
                open_trade.exit_price = exit_price
                open_trade.pnl = pnl
                capital += pnl
                trades.append(open_trade)
                open_trade = None

            equity.append(capital)
            continue

        # ── No open trade → check for entry ──
        if sig.action in ("BUY", "SELL") and sig.confluence >= min_conf:
            if sig.atr <= 0:
                equity.append(capital)
                continue

            sl_dist = sig.atr * atr_mult
            entry = sig.close

            if sig.action == "BUY":
                sl = entry - sl_dist
                tp = entry + sl_dist * tp_ratio
            else:
                sl = entry + sl_dist
                tp = entry - sl_dist * tp_ratio

            open_trade = ReplayTrade(
                entry_idx=i,
                entry_price=entry,
                direction=sig.action,
                stop_loss=sl,
                take_profit=tp,
            )
            original_sl = sl
            breakeven_activated = False
            highest_since_entry = sig.high
            lowest_since_entry = sig.low

        equity.append(capital)

    # Close remaining open trade at last bar
    if open_trade and signals:
        last = signals[-1]
        risk_dist = abs(open_trade.entry_price - original_sl) if original_sl else abs(open_trade.entry_price - open_trade.stop_loss)
        if risk_dist > 0:
            pos_size = capital * risk_pct / risk_dist
            if open_trade.direction == "BUY":
                pnl = (last.close - open_trade.entry_price) * pos_size
            else:
                pnl = (open_trade.entry_price - last.close) * pos_size
        else:
            pnl = 0.0
        open_trade.exit_idx = len(signals) - 1
        open_trade.exit_price = last.close
        open_trade.pnl = pnl
        capital += pnl
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
            "sortino_ratio": 0, "calmar_ratio": 0, "avg_risk_reward": 0,
        }

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    total_win = sum(t.pnl for t in wins) if wins else 0
    total_loss = abs(sum(t.pnl for t in losses)) if losses else 0

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
    # Sortino
    downside = returns[returns < 0] if len(returns) > 0 else np.array([])
    sortino = (
        float(np.mean(returns) / np.std(downside) * np.sqrt(252))
        if len(downside) > 0 and np.std(downside) > 0 else 0.0
    )
    # Calmar
    total_ret = (equity_curve[-1] - initial_capital) / initial_capital * 100
    calmar = total_ret / max_dd if max_dd > 0 else 0.0

    return {
        "total_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "profit_factor": total_win / total_loss if total_loss > 0 else (10.0 if total_win > 0 else 0),
        "total_return_pct": total_ret,
        "max_drawdown_pct": max_dd,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "avg_risk_reward": float(np.mean([t.risk_reward for t in wins])) if wins else 0,
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
                if done % 500 == 0 or done == total:
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


# ── Per-Pair Best Config ────────────────────────────────────────────────


def best_config_per_pair(results: list[dict]) -> dict[str, dict]:
    """Find the best configuration for each pair individually."""
    pair_results: dict[str, list[dict]] = {}
    for r in results:
        pair_results.setdefault(r["pair"], []).append(r)

    best_per_pair = {}
    for pair, pair_r in pair_results.items():
        # Sort by score descending
        pair_r.sort(key=lambda x: x["score"], reverse=True)
        if pair_r:
            top = pair_r[0]
            best_per_pair[pair] = {
                "params": top["params"],
                "variant": top["variant"],
                "score": top["score"],
                "metrics": top["metrics"],
            }
    return best_per_pair


# ── Walk-Forward Validation ─────────────────────────────────────────────


def run_wfo_validation(
    top_configs: list[dict],
    pairs_signals: dict[str, list[BarSignal]],
) -> list[dict]:
    """Split pre-computed signals into halves; replay on each."""
    wfo_results = []

    for idx, cfg in enumerate(top_configs[:WFO_TOP_N]):
        params = cfg["params"]
        variant = cfg["variant"]
        print(f"  WFO [{idx+1}/{min(len(top_configs), WFO_TOP_N)}]: "
              f"conf={params['min_confluence']} atr={params['atr_sl_multiplier']} "
              f"risk={params['max_risk_per_trade']} ({variant})")

        is_scores, oos_scores = [], []

        for pair, signals in pairs_signals.items():
            if len(signals) < 100:
                continue
            mid = int(len(signals) * 0.6)

            # In-sample: first 60%
            _, _, m_is = replay(signals[:mid], params, variant)
            is_scores.append(composite_score(m_is))

            # Out-of-sample: last 40%
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


# ── Per-Trade Statistics ────────────────────────────────────────────────


def per_trade_stats(results: list[dict], target_params: dict, target_variant: str) -> dict:
    stats = {}
    for r in results:
        if r["params"] == target_params and r["variant"] == target_variant:
            pair = r["pair"]
            trades = r["trades"]
            if not trades:
                stats[pair] = {"total": 0}
                continue
            wins = [t for t in trades if t.pnl > 0]
            losses = [t for t in trades if t.pnl <= 0]
            durations = [(t.exit_idx - t.entry_idx) for t in trades]
            stats[pair] = {
                "total": len(trades),
                "wins": len(wins),
                "losses": len(losses),
                "avg_win": sum(t.pnl for t in wins) / len(wins) if wins else 0,
                "avg_loss": sum(t.pnl for t in losses) / len(losses) if losses else 0,
                "largest_win": max((t.pnl for t in wins), default=0),
                "largest_loss": min((t.pnl for t in losses), default=0),
                "avg_duration_bars": sum(durations) / len(durations) if durations else 0,
                "avg_rr": sum(t.risk_reward for t in wins) / len(wins) if wins else 0,
            }
    return stats


# ── Utility ─────────────────────────────────────────────────────────────


def fmt(v, kind="float") -> str:
    if v is None or (isinstance(v, float) and (math.isinf(v) or math.isnan(v))):
        return "N/A"
    if kind == "pct":
        return f"{v:.1f}%"
    if kind == "int":
        return str(int(v))
    if kind == "dollar":
        return f"${v:,.2f}"
    return f"{v:.2f}"


# ── Report Generation ──────────────────────────────────────────────────


def generate_report(
    baseline_results, grid_results, ranked, sensitivity,
    var_comparison, wfo_results, trade_stats, elapsed_time,
    pair_names, pairs_bar_counts,
):
    lines = []
    lines.append("# SignalForge Comprehensive Backtest Results\n")
    lines.append(f"> Generated on 2026-03-04 | Runtime: {elapsed_time:.0f}s")
    lines.append("> Engine: Full 6-layer SignalPipeline with indicator caching")
    lines.append("> Data: Real Binance candles\n")

    # ── Test Environment ──
    lines.append("## Test Environment\n")
    lines.append("| Pair | Timeframe | Bars |")
    lines.append("|------|-----------|------|")
    for pair in pair_names:
        tf = PAIRS[pair]["tf"]
        bars = pairs_bar_counts.get(pair, 0)
        lines.append(f"| {pair} | {tf} | {bars:,} |")
    lines.append("")
    total_combos = len(generate_param_combos())
    total_tests = total_combos * len(VARIANTS) * len(pair_names)
    lines.append(f"- **Pairs tested:** {len(pair_names)}")
    lines.append(f"- **Parameter combinations:** {total_combos}")
    lines.append(f"- **Exit variants:** {len(VARIANTS)} (baseline, break-even, trailing)")
    lines.append(f"- **Total backtests run:** {total_tests}")
    lines.append(f"- **Initial capital:** ${INITIAL_CAPITAL:,.0f}")
    lines.append(f"- **Lookback:** {LOOKBACK} bars\n")

    lines.append("### Key Parameter: TP Ratio\n")
    lines.append("The take-profit distance is `SL_distance × tp_ratio`. In production this is hardcoded at 1.618 "
                 "(Fibonacci extension). This backtest tests variable TP ratios [1.0, 1.2, 1.618, 2.0, 2.618] "
                 "to find the optimal risk:reward tradeoff.\n")

    # ── 1. Baseline Results ──
    lines.append("---\n")
    lines.append("## 1. Baseline Results (Default Parameters)\n")
    lines.append("Default: `min_confluence=50, atr_sl_mult=2.0, risk/trade=2%, no trailing, no break-even`\n")

    header = "| Metric | " + " | ".join(pair_names) + " |"
    sep = "|--------" + "|--------" * len(pair_names) + "|"
    lines.append(header)
    lines.append(sep)

    baseline_by_pair = {r["pair"]: r["metrics"] for r in baseline_results}
    metric_display = [
        ("Total Trades", "total_trades", "int"),
        ("Win Rate", "win_rate", "pct"),
        ("Profit Factor", "profit_factor", "float"),
        ("Total Return", "total_return_pct", "pct"),
        ("Max Drawdown", "max_drawdown_pct", "pct"),
        ("Sharpe Ratio", "sharpe_ratio", "float"),
        ("Avg R:R (winners)", "avg_risk_reward", "float"),
    ]
    for label, key, kind in metric_display:
        vals = [fmt(baseline_by_pair.get(p, {}).get(key, 0), kind) for p in pair_names]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    lines.append("")

    # ── 2. Top 10 Configurations ──
    lines.append("---\n")
    lines.append("## 2. Top 10 Configurations (by Combined Score)\n")
    lines.append(f"Score = `profit_factor × (1 - max_drawdown/100) × min(trades/10, 1.0)`, "
                 f"averaged across {len(pair_names)} pairs, weighted by consistency.\n")

    lines.append("| Rank | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Avg Return | Avg Win Rate |")
    lines.append("|------|-----------|----------|------|---------|---------|-------|-----------|-------------|")
    for i, cfg in enumerate(ranked[:10]):
        p = cfg["params"]
        all_m = list(cfg["metrics"].values())
        avg_ret = sum(m.get("total_return_pct", 0) for m in all_m) / len(all_m) if all_m else 0
        avg_wr = sum(m.get("win_rate", 0) for m in all_m) / len(all_m) if all_m else 0
        lines.append(
            f"| {i+1} | {p['min_confluence']} | {p['atr_sl_multiplier']} | "
            f"{p['max_risk_per_trade']:.0%} | {p.get('tp_ratio', 1.618)} | {cfg['variant']} | "
            f"{cfg['combined_score']:.3f} | {avg_ret:.1f}% | {avg_wr:.1f}% |"
        )
    lines.append("")

    # Detailed metrics for #1
    if ranked:
        best = ranked[0]
        lines.append("### Best Configuration — Detailed Metrics\n")
        bp = best["params"]
        lines.append(f"**Parameters:** `min_confluence={bp['min_confluence']}, "
                     f"atr_sl_mult={bp['atr_sl_multiplier']}, "
                     f"risk/trade={bp['max_risk_per_trade']:.0%}, "
                     f"variant={best['variant']}`\n")
        header2 = "| Metric | " + " | ".join(pair_names) + " |"
        sep2 = "|--------" + "|--------" * len(pair_names) + "|"
        lines.append(header2)
        lines.append(sep2)
        for label, key, kind in metric_display:
            vals = [fmt(best["metrics"].get(p, {}).get(key, 0), kind) for p in pair_names]
            lines.append(f"| {label} | " + " | ".join(vals) + " |")
        lines.append("")

    # ── 3. Parameter Sensitivity ──
    lines.append("---\n")
    lines.append("## 3. Parameter Sensitivity Analysis\n")
    lines.append("Average score when each parameter is set to a given value (other params averaged out).\n")

    for param_name, values in sensitivity.items():
        display_name = param_name.replace("_", " ").title()
        lines.append(f"### {display_name}\n")
        lines.append(f"| {display_name} | Avg Score | Avg Win Rate | Avg Return | Avg Trades |")
        lines.append("|" + "---|" * 5)
        for val, data in sorted(values.items()):
            lines.append(
                f"| {val} | {data['avg_score']:.3f} | "
                f"{data['avg_win_rate']:.1f}% | "
                f"{data['avg_return']:.1f}% | "
                f"{data['avg_trades']:.1f} |"
            )
        lines.append("")

    # ── 4. Exit Strategy Comparison ──
    lines.append("---\n")
    lines.append("## 4. Exit Strategy Comparison\n")
    lines.append("Averaged across ALL parameter combinations and ALL pairs.\n")
    lines.append("| Variant | Avg Score | Avg Return | Avg Win Rate | Avg Drawdown | Avg PF | Avg Trades |")
    lines.append("|---------|----------|-----------|-------------|-------------|--------|-----------|")
    for variant in VARIANTS:
        d = var_comparison.get(variant, {})
        lines.append(
            f"| {variant} | {fmt(d.get('avg_score', 0))} | "
            f"{fmt(d.get('avg_return', 0), 'pct')} | "
            f"{fmt(d.get('avg_win_rate', 0), 'pct')} | "
            f"{fmt(d.get('avg_drawdown', 0), 'pct')} | "
            f"{fmt(d.get('avg_profit_factor', 0))} | "
            f"{fmt(d.get('avg_trades', 0))} |"
        )
    lines.append("")

    # ── 5. Walk-Forward Validation ──
    lines.append("---\n")
    lines.append("## 5. Walk-Forward Validation (Top 5 Configs)\n")
    lines.append("60% in-sample / 40% out-of-sample split across all pairs.\n")
    lines.append("| # | Confluence | ATR Mult | Risk | Variant | In-Sample | Out-of-Sample | Degradation | Overfit? |")
    lines.append("|---|-----------|----------|------|---------|----------|--------------|------------|---------|")
    for i, wfo in enumerate(wfo_results):
        p = wfo["params"]
        overfit = "YES" if wfo["likely_overfit"] else "No"
        lines.append(
            f"| {i+1} | {p['min_confluence']} | {p['atr_sl_multiplier']} | "
            f"{p['max_risk_per_trade']:.0%} | {wfo['variant']} | "
            f"{wfo['in_sample_score']:.3f} | {wfo['out_of_sample_score']:.3f} | "
            f"{wfo['degradation_pct']:.0f}% | {overfit} |"
        )
    lines.append("")

    # ── 6. Per-Trade Statistics ──
    if trade_stats:
        lines.append("---\n")
        lines.append("## 6. Per-Trade Statistics (Best Config)\n")
        lines.append("| Pair | Total | Wins | Losses | Avg Win | Avg Loss | Largest Win | Largest Loss | Avg Duration | Avg R:R |")
        lines.append("|------|-------|------|--------|---------|----------|-------------|-------------|-------------|---------|")
        for pair in pair_names:
            s = trade_stats.get(pair, {})
            if s.get("total", 0) == 0:
                lines.append(f"| {pair} | 0 | -- | -- | -- | -- | -- | -- | -- | -- |")
            else:
                lines.append(
                    f"| {pair} | {s['total']} | {s['wins']} | {s['losses']} | "
                    f"{fmt(s['avg_win'], 'dollar')} | {fmt(s['avg_loss'], 'dollar')} | "
                    f"{fmt(s['largest_win'], 'dollar')} | {fmt(s['largest_loss'], 'dollar')} | "
                    f"{s['avg_duration_bars']:.1f} bars | {fmt(s['avg_rr'])} |"
                )
        lines.append("")

    # ── 7. Recommendations ──
    lines.append("---\n")
    lines.append("## 7. Recommendations\n")

    if ranked:
        best = ranked[0]
        bp = best["params"]
        lines.append("### Best Configuration Found\n")
        lines.append("```json")
        lines.append("{")
        lines.append(f'  "min_confluence": {bp["min_confluence"]},')
        lines.append(f'  "atr_sl_multiplier": {bp["atr_sl_multiplier"]},')
        lines.append(f'  "max_risk_per_trade": {bp["max_risk_per_trade"]},')
        lines.append(f'  "tp_ratio": {bp.get("tp_ratio", 1.618)},')
        if best["variant"] in ("breakeven", "trailing"):
            lines.append(f'  "break_even_enabled": true,')
        if best["variant"] == "trailing":
            lines.append(f'  "trailing_stop_enabled": true,')
            lines.append(f'  "atr_trail_multiplier": 1.5,')
        lines.append("}")
        lines.append("```\n")

    if wfo_results:
        non_overfit = [w for w in wfo_results if not w["likely_overfit"]]
        if non_overfit:
            best_wfo = max(non_overfit, key=lambda w: w["out_of_sample_score"])
            wp = best_wfo["params"]
            lines.append("### Most Robust Config (WFO-validated, not overfit)\n")
            lines.append("```json")
            lines.append("{")
            lines.append(f'  "min_confluence": {wp["min_confluence"]},')
            lines.append(f'  "atr_sl_multiplier": {wp["atr_sl_multiplier"]},')
            lines.append(f'  "max_risk_per_trade": {wp["max_risk_per_trade"]},')
            lines.append(f'  "tp_ratio": {wp.get("tp_ratio", 1.618)},')
            if best_wfo["variant"] in ("breakeven", "trailing"):
                lines.append(f'  "break_even_enabled": true,')
            if best_wfo["variant"] == "trailing":
                lines.append(f'  "trailing_stop_enabled": true,')
            lines.append("}")
            lines.append("```\n")

    # ── Per-Pair Best Configs ──
    if hasattr(generate_report, '_per_pair') and generate_report._per_pair:
        pp = generate_report._per_pair
        lines.append("### Best Configuration Per Pair\n")
        lines.append("| Pair | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Return | Win Rate |")
        lines.append("|------|-----------|----------|------|---------|---------|-------|--------|---------|")
        for pair in pair_names:
            if pair in pp:
                cfg = pp[pair]
                p = cfg["params"]
                m = cfg["metrics"]
                lines.append(
                    f"| {pair} | {p['min_confluence']} | {p['atr_sl_multiplier']} | "
                    f"{p['max_risk_per_trade']:.0%} | {p.get('tp_ratio', 1.618)} | "
                    f"{cfg['variant']} | {cfg['score']:.2f} | "
                    f"{m.get('total_return_pct', 0):.1f}% | {m.get('win_rate', 0):.1f}% |"
                )
        lines.append("")

    lines.append("### Key Findings\n")
    for param_name, values in sensitivity.items():
        if values:
            best_val = max(values.items(), key=lambda x: x[1]["avg_score"])
            worst_val = min(values.items(), key=lambda x: x[1]["avg_score"])
            display_name = param_name.replace("_", " ").title()
            lines.append(
                f"- **{display_name}:** Best at `{best_val[0]}` "
                f"(score {best_val[1]['avg_score']:.3f}), "
                f"worst at `{worst_val[0]}` "
                f"(score {worst_val[1]['avg_score']:.3f})"
            )
    if var_comparison:
        best_var = max(var_comparison.items(), key=lambda x: x[1].get("avg_score", 0))
        lines.append(f"- **Exit strategy:** `{best_var[0]}` performed best "
                     f"(avg score {best_var[1]['avg_score']:.3f})")

    lines.append("")
    lines.append("### Production Recommendations\n")
    lines.append("1. **Make TP ratio configurable** — the optimal TP ratio varies; 1.618 may not be best for all conditions")
    lines.append("2. **Enable drawdown circuit breaker** (`max_drawdown_pct: 15%`) — prevents catastrophic loss streaks")
    lines.append("3. **Use per-pair optimized configs** — some pairs need different settings than others")
    lines.append("4. **Enable correlation monitoring** — BTC/ETH/SOL are highly correlated; avoid simultaneous positions")
    lines.append("5. **Consider partial take-profit** — close 50% at TP1, trail remaining to TP2")
    lines.append("")

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────────


def main():
    overall_start = time.time()

    print("=" * 70)
    print("  SignalForge Comprehensive Backtest v2 (with indicator caching)")
    print("=" * 70)

    # ── Load data ──
    print("\n[1/6] Loading CSV data...")
    pairs_candles: dict[str, pd.DataFrame] = {}
    for pair, info in PAIRS.items():
        filepath = info["file"]
        if not os.path.exists(filepath):
            print(f"  {pair}: FILE NOT FOUND — skipping")
            continue
        df = load_csv(filepath)
        if len(df) < 300:
            print(f"  {pair}: only {len(df)} bars (need 300+) — skipping")
            continue
        pairs_candles[pair] = df
        print(f"  {pair} ({info['tf']}): {len(df):,} bars loaded")

    if not pairs_candles:
        print("ERROR: No valid data loaded.")
        return

    # ── Pre-compute signals ──
    print("\n[2/6] Pre-computing signals (indicator caching + pipeline)...")
    pairs_signals: dict[str, list[BarSignal]] = {}

    for pair, candles in pairs_candles.items():
        t0 = time.time()
        tf = PAIRS[pair]["tf"]

        # Setup indicator cache for this pair
        _indicator_cache.setup(candles)

        # Run pipeline once with relaxed thresholds
        signals = precompute_signals(candles, pair, tf)
        pairs_signals[pair] = signals

        elapsed = time.time() - t0
        n_signals = sum(1 for s in signals if s.action in ("BUY", "SELL"))
        print(f"  {pair}: {len(signals)} bars, {n_signals} raw signals, {elapsed:.1f}s")

    # ── Baseline ──
    print("\n[3/6] Running baseline backtests (default params)...")
    baseline_params = {
        "min_confluence": 50,
        "atr_sl_multiplier": 2.0,
        "max_risk_per_trade": 0.02,
        "tp_ratio": 1.618,
    }
    baseline_results = []
    for pair, signals in pairs_signals.items():
        trades, eq, metrics = replay(signals, baseline_params, "baseline")
        baseline_results.append({"pair": pair, "metrics": metrics, "score": composite_score(metrics)})
        m = metrics
        print(f"  {pair}: {m['total_trades']} trades, "
              f"win rate {m['win_rate']:.1f}%, "
              f"return {m['total_return_pct']:.1f}%, "
              f"drawdown {m['max_drawdown_pct']:.1f}%")

    # ── Grid search ──
    print("\n[4/6] Running grid search...")
    grid_results = run_grid_search(pairs_signals)

    # ── Analysis ──
    print("\n[5/6] Analyzing results...")
    ranked = rank_configs(grid_results)
    sensitivity = parameter_sensitivity(grid_results)
    var_comp = variant_comparison(grid_results)

    # Per-pair best configs
    per_pair = best_config_per_pair(grid_results)

    if ranked:
        best = ranked[0]
        bp = best["params"]
        print(f"  Best universal: conf={bp['min_confluence']} atr={bp['atr_sl_multiplier']} "
              f"tp={bp.get('tp_ratio', 1.618)} risk={bp['max_risk_per_trade']} "
              f"({best['variant']}) score={best['combined_score']:.3f}")

    print("\n  Per-pair best configs:")
    for pair in per_pair:
        cfg = per_pair[pair]
        p = cfg["params"]
        m = cfg["metrics"]
        print(f"    {pair}: conf={p['min_confluence']} atr={p['atr_sl_multiplier']} "
              f"tp={p.get('tp_ratio', 1.618)} ({cfg['variant']}) "
              f"return={m.get('total_return_pct', 0):.1f}%, wr={m.get('win_rate', 0):.1f}%")

    # ── Walk-Forward Validation ──
    print("\n[6/6] Walk-forward validation...")
    wfo_results = run_wfo_validation(ranked, pairs_signals)

    # Per-trade stats for best config
    trade_stats = {}
    if ranked:
        trade_stats = per_trade_stats(grid_results, ranked[0]["params"], ranked[0]["variant"])

    # ── Generate report ──
    elapsed = time.time() - overall_start
    pair_names = list(pairs_signals.keys())
    pairs_bar_counts = {p: len(c) for p, c in pairs_candles.items()}

    # Attach per-pair data to report function (simple approach)
    generate_report._per_pair = per_pair

    print(f"\nGenerating report... (total runtime: {elapsed:.0f}s)")
    report = generate_report(
        baseline_results, grid_results, ranked, sensitivity,
        var_comp, wfo_results, trade_stats, elapsed,
        pair_names, pairs_bar_counts,
    )

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport: {os.path.abspath(OUTPUT_PATH)}")

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
