"""
Analyze swing/volatility opportunities in the 4h data.

Quantifies:
1. Total absolute price movement vs net movement (swing opportunity ratio)
2. Major swings (10%+ moves) with dates
3. Drawdown-from-ATH timeline (when system should activate)
4. Regime breakdown per quarter (trending vs ranging vs correction)
5. Theoretical max capture vs system actual capture

Output: JSON to stdout for use in report generation.
"""
from __future__ import annotations

import glob as globmod
import json
import os
import re
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "docs", "chart-data")


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


def detect_swings(closes: np.ndarray, timestamps: np.ndarray, threshold: float = 0.10):
    """Detect significant price swings (zigzag) above threshold."""
    swings = []
    if len(closes) < 2:
        return swings

    # Simple zigzag: track direction, record swing when reversal > threshold
    direction = 0  # 0=undetermined, 1=up, -1=down
    swing_start_idx = 0
    swing_start_price = closes[0]
    extreme_idx = 0
    extreme_price = closes[0]

    for i in range(1, len(closes)):
        price = closes[i]

        if direction == 0:
            if price > swing_start_price * (1 + threshold):
                direction = 1
                extreme_idx = i
                extreme_price = price
            elif price < swing_start_price * (1 - threshold):
                direction = -1
                extreme_idx = i
                extreme_price = price
        elif direction == 1:
            if price > extreme_price:
                extreme_idx = i
                extreme_price = price
            elif price < extreme_price * (1 - threshold):
                # Reversal: record the up-swing
                swings.append({
                    "start_idx": swing_start_idx,
                    "end_idx": extreme_idx,
                    "start_price": float(swing_start_price),
                    "end_price": float(extreme_price),
                    "change_pct": float((extreme_price - swing_start_price) / swing_start_price * 100),
                    "direction": "UP",
                    "start_date": datetime.fromtimestamp(int(timestamps[swing_start_idx]), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "end_date": datetime.fromtimestamp(int(timestamps[extreme_idx]), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "bars": int(extreme_idx - swing_start_idx),
                })
                swing_start_idx = extreme_idx
                swing_start_price = extreme_price
                direction = -1
                extreme_idx = i
                extreme_price = price
        elif direction == -1:
            if price < extreme_price:
                extreme_idx = i
                extreme_price = price
            elif price > extreme_price * (1 + threshold):
                # Reversal: record the down-swing
                swings.append({
                    "start_idx": swing_start_idx,
                    "end_idx": extreme_idx,
                    "start_price": float(swing_start_price),
                    "end_price": float(extreme_price),
                    "change_pct": float((extreme_price - swing_start_price) / swing_start_price * 100),
                    "direction": "DOWN",
                    "start_date": datetime.fromtimestamp(int(timestamps[swing_start_idx]), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "end_date": datetime.fromtimestamp(int(timestamps[extreme_idx]), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "bars": int(extreme_idx - swing_start_idx),
                })
                swing_start_idx = extreme_idx
                swing_start_price = extreme_price
                direction = 1
                extreme_idx = i
                extreme_price = price

    # Record final swing
    if direction != 0 and extreme_idx != swing_start_idx:
        swings.append({
            "start_idx": swing_start_idx,
            "end_idx": extreme_idx,
            "start_price": float(swing_start_price),
            "end_price": float(extreme_price),
            "change_pct": float((extreme_price - swing_start_price) / swing_start_price * 100),
            "direction": "UP" if direction == 1 else "DOWN",
            "start_date": datetime.fromtimestamp(int(timestamps[swing_start_idx]), tz=timezone.utc).strftime("%Y-%m-%d"),
            "end_date": datetime.fromtimestamp(int(timestamps[extreme_idx]), tz=timezone.utc).strftime("%Y-%m-%d"),
            "bars": int(extreme_idx - swing_start_idx),
        })

    return swings


def calculate_drawdown_from_ath(closes: np.ndarray, timestamps: np.ndarray):
    """Calculate drawdown from all-time-high at each point."""
    ath = closes[0]
    dd_timeline = []

    for i in range(len(closes)):
        if closes[i] > ath:
            ath = closes[i]
        dd = (ath - closes[i]) / ath * 100
        dt = datetime.fromtimestamp(int(timestamps[i]), tz=timezone.utc)
        q = (dt.month - 1) // 3 + 1
        dd_timeline.append({
            "date": dt.strftime("%Y-%m-%d"),
            "quarter": f"{dt.year}-Q{q}",
            "close": float(closes[i]),
            "ath": float(ath),
            "drawdown_pct": float(dd),
        })

    return dd_timeline


def quarterly_volatility(closes: np.ndarray, timestamps: np.ndarray):
    """Calculate per-quarter volatility metrics."""
    quarters = {}
    for i in range(len(closes)):
        dt = datetime.fromtimestamp(int(timestamps[i]), tz=timezone.utc)
        q = (dt.month - 1) // 3 + 1
        qkey = f"{dt.year}-Q{q}"
        if qkey not in quarters:
            quarters[qkey] = {"closes": [], "highs": [], "lows": []}
        quarters[qkey]["closes"].append(closes[i])

    results = {}
    for qkey in sorted(quarters.keys()):
        c = np.array(quarters[qkey]["closes"])
        if len(c) < 2:
            continue

        # Total absolute movement (sum of |bar-to-bar changes|)
        abs_moves = np.sum(np.abs(np.diff(c)))
        # Net movement
        net_move = c[-1] - c[0]
        net_pct = (c[-1] - c[0]) / c[0] * 100

        # Volatility (annualized std of returns)
        returns = np.diff(c) / c[:-1]
        vol = float(np.std(returns) * np.sqrt(252 * 6))  # 6 bars per day on 4h

        # Max intra-quarter range
        max_range = (np.max(c) - np.min(c)) / np.min(c) * 100

        results[qkey] = {
            "start_price": float(c[0]),
            "end_price": float(c[-1]),
            "net_return_pct": float(net_pct),
            "total_absolute_movement": float(abs_moves),
            "swing_opportunity_ratio": float(abs_moves / abs(net_move)) if abs(net_move) > 0 else float('inf'),
            "annualized_volatility": float(vol),
            "max_intra_quarter_range_pct": float(max_range),
            "bars": len(c),
        }

    return results


def main():
    pairs = discover_4h_pairs(DATA_DIR)
    target = ["BTC/USD-4h", "ETH/USD-4h", "SOL/USD-4h", "BNB/USD-4h",
              "ADA/USD-4h", "DOGE/USD-4h", "LINK/USD-4h", "XRP/USD-4h"]

    all_results = {}

    for pair_key in target:
        if pair_key not in pairs:
            continue
        info = pairs[pair_key]
        df = load_csv(info["file"])
        closes = df["close"].values
        timestamps = df["time"].values

        pair_short = pair_key.replace("-4h", "")

        # 1. Overall movement stats
        total_abs_move = float(np.sum(np.abs(np.diff(closes))))
        net_move = float(closes[-1] - closes[0])
        net_pct = float((closes[-1] - closes[0]) / closes[0] * 100)

        # Swing opportunity ratio: how much total movement vs net
        sor = total_abs_move / abs(net_move) if abs(net_move) > 0 else float('inf')

        # Theoretical perfect trading: capture every bar-to-bar move
        bar_returns = np.abs(np.diff(closes))
        fee_per_trade = closes[:-1] * 0.00075 * 2  # round trip
        # Can't trade every bar, but shows total available movement
        theoretical_gross = float(np.sum(bar_returns))

        # 2. Major swings (10%+ moves)
        swings_10 = detect_swings(closes, timestamps, threshold=0.10)
        swings_20 = detect_swings(closes, timestamps, threshold=0.20)

        # Sum of absolute swing magnitudes (capturable movement)
        total_swing_magnitude_10 = sum(abs(s["change_pct"]) for s in swings_10)
        total_swing_magnitude_20 = sum(abs(s["change_pct"]) for s in swings_20)

        # 3. Drawdown from ATH
        dd_timeline = calculate_drawdown_from_ath(closes, timestamps)

        # Time spent in different DD ranges
        dd_values = [d["drawdown_pct"] for d in dd_timeline]
        total_bars = len(dd_values)
        dd_ranges = {
            "0-10% (near ATH)": sum(1 for d in dd_values if d < 10) / total_bars * 100,
            "10-20% (mild correction)": sum(1 for d in dd_values if 10 <= d < 20) / total_bars * 100,
            "20-40% (correction)": sum(1 for d in dd_values if 20 <= d < 40) / total_bars * 100,
            "40-60% (bear market)": sum(1 for d in dd_values if 40 <= d < 60) / total_bars * 100,
            "60%+ (deep bear)": sum(1 for d in dd_values if d >= 60) / total_bars * 100,
        }

        # 4. Quarterly volatility
        qvol = quarterly_volatility(closes, timestamps)

        # Average swing opportunity ratio across quarters
        sors = [q["swing_opportunity_ratio"] for q in qvol.values()
                if q["swing_opportunity_ratio"] < 1000]
        avg_sor = sum(sors) / len(sors) if sors else 0

        # Quarters where market declined
        declining_quarters = {k: v for k, v in qvol.items() if v["net_return_pct"] < -5}
        rising_quarters = {k: v for k, v in qvol.items() if v["net_return_pct"] > 20}

        start_date = datetime.fromtimestamp(int(timestamps[0]), tz=timezone.utc).strftime("%Y-%m-%d")
        end_date = datetime.fromtimestamp(int(timestamps[-1]), tz=timezone.utc).strftime("%Y-%m-%d")

        all_results[pair_short] = {
            "period": f"{start_date} to {end_date}",
            "bars": len(closes),
            "start_price": float(closes[0]),
            "end_price": float(closes[-1]),
            "net_return_pct": net_pct,
            "total_absolute_movement_usd": total_abs_move,
            "swing_opportunity_ratio": sor,
            "avg_quarterly_sor": avg_sor,
            "swings_10pct": len(swings_10),
            "total_swing_magnitude_10pct": total_swing_magnitude_10,
            "swings_20pct": len(swings_20),
            "total_swing_magnitude_20pct": total_swing_magnitude_20,
            "top_swings": sorted(swings_10, key=lambda s: abs(s["change_pct"]), reverse=True)[:10],
            "dd_time_distribution": dd_ranges,
            "declining_quarters": len(declining_quarters),
            "rising_quarters": len(rising_quarters),
            "total_quarters": len(qvol),
            "quarterly_volatility": qvol,
        }

        print(f"{pair_short}: {len(swings_10)} swings >10%, SOR={sor:.1f}x, "
              f"net {net_pct:+.1f}%, total swing magnitude {total_swing_magnitude_10:.0f}%", file=sys.stderr)

    # Output JSON
    print(json.dumps(all_results, indent=2, default=str))


if __name__ == "__main__":
    main()
