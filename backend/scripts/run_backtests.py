"""
Run backtests across multiple synthetic market scenarios.
Since we don't have live exchange connections in CI, we generate
realistic synthetic data for each market type.

Usage:
    cd backend && .venv/Scripts/python.exe scripts/run_backtests.py
"""

import os
import sys

import numpy as np
import pandas as pd

# Ensure the backend package is importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.backtest.engine import BacktestEngine


def generate_forex_like(n=2000, seed=42):
    """EUR/USD-like: low volatility, mean-reverting with trends."""
    rng = np.random.default_rng(seed)
    close = 1.1000 + np.cumsum(rng.normal(0, 0.0005, n))
    # Add trends
    for i in range(0, n, 200):
        end = min(i + 200, n)
        close[i:end] += np.arange(end - i) * rng.choice([-0.0001, 0.0001])
    high = close + rng.uniform(0.001, 0.003, n)
    low = close - rng.uniform(0.001, 0.003, n)
    return pd.DataFrame({
        "open": close + 0.0001,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(10000, 50000, n),
    })


def generate_crypto_like(n=2000, seed=42):
    """BTC/USDT-like: high volatility, strong trends, volume spikes."""
    rng = np.random.default_rng(seed)
    close = 40000 + np.cumsum(rng.normal(0, 100, n))
    high = close + rng.uniform(50, 500, n)
    low = close - rng.uniform(50, 500, n)
    return pd.DataFrame({
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(100, 5000, n),
    })


def generate_equity_like(n=2000, seed=42):
    """SPY-like: moderate volatility, upward bias."""
    rng = np.random.default_rng(seed)
    close = 450 + np.cumsum(rng.normal(0.02, 1.5, n))
    high = close + rng.uniform(0.5, 3, n)
    low = close - rng.uniform(0.5, 3, n)
    return pd.DataFrame({
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(5000, 50000, n),
    })


def run_all():
    markets = {
        "EUR/USD (Forex)": ("EUR/USD", "1h", generate_forex_like()),
        "BTC/USDT (Crypto)": ("BTC/USDT", "1h", generate_crypto_like()),
        "SPY (Equity)": ("SPY", "1h", generate_equity_like()),
    }

    results = {}
    for name, (symbol, tf, candles) in markets.items():
        print(f"\n{'=' * 60}")
        print(f"Backtesting: {name}")
        print(f"{'=' * 60}")

        engine = BacktestEngine()
        result = engine.run(candles, symbol, tf)
        results[name] = result.metrics

        for k, v in result.metrics.items():
            print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    # Write markdown report
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_path = os.path.join(docs_dir, "backtest-results-phase2.md")
    write_report(results, report_path)
    print(f"\nReport written to {os.path.abspath(report_path)}")


def write_report(results: dict, report_path: str):
    lines = ["# Phase 2 Backtest Results\n"]
    lines.append("## Summary\n")
    lines.append("| Metric | " + " | ".join(results.keys()) + " |")
    lines.append("|--------|" + "|".join(["--------"] * len(results)) + "|")

    metric_keys = list(next(iter(results.values())).keys())
    for key in metric_keys:
        vals = []
        for name in results:
            v = results[name][key]
            vals.append(f"{v:.2f}" if isinstance(v, float) else str(v))
        lines.append(f"| {key} | " + " | ".join(vals) + " |")

    lines.append("\n## Parameters\n")
    lines.append("- Lookback: 200 bars")
    lines.append("- Risk per trade: 2%")
    lines.append("- ATR SL multiplier: 2.0")
    lines.append("- Min confluence: 50")
    lines.append("- Min risk:reward: 1.5")
    lines.append("\n## Notes\n")
    lines.append("- Data is synthetic (2000 bars each) to demonstrate pipeline functionality")
    lines.append("- Real market data will be used once CCXT ingestion is live (Phase 3)")
    lines.append(
        "- All 6 layers active: Regime -> Trend -> Zones -> Confluence -> Triggers -> Risk"
    )

    with open(report_path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_all()
