# ============================================================
# Cell 1 — Install Libraries
# ============================================================
# !pip install yfinance hmmlearn matplotlib pandas numpy scikit-learn

# ============================================================
# Cell 2 — Imports
# ============================================================
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

# ============================================================
# Cell 3 — Download Data
# ============================================================
print("Downloading BTC-USD hourly data (730d) ...")
raw = yf.download("BTC-USD", period="730d", interval="1h", auto_adjust=True, progress=False)

# Flatten MultiIndex columns if present (use level 0, not last level)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)

# Keep only the required columns
data = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
print(f"Downloaded {len(data):,} rows  |  columns: {list(data.columns)}")

# ============================================================
# Cell 4 — Feature Engineering
# ============================================================
data["Returns"]    = data["Close"].pct_change()
data["Range"]      = (data["High"] - data["Low"]) / data["Close"]
data["Vol_Change"] = data["Volume"].pct_change()

# Drop NaNs
data.dropna(inplace=True)

# Replace inf / -inf with NaN, then drop again
data.replace([np.inf, -np.inf], np.nan, inplace=True)
data.dropna(inplace=True)

print(f"Clean dataset: {len(data):,} rows")

# ============================================================
# Cell 5 — Train HMM
# ============================================================
X = data[["Returns", "Range", "Vol_Change"]].values

model = GaussianHMM(
    n_components=7,
    covariance_type="full",
    n_iter=1000,
    random_state=42
)
model.fit(X)

data["State"] = model.predict(X)
print("Model trained. Hidden states assigned.")

# ============================================================
# Cell 6 — Analyze
# ============================================================
summary = (
    data.groupby("State")
    .agg(
        Mean_Return=("Returns", "mean"),
        Volatility=("Returns",  "std"),
        Count=("Returns",       "count"),
    )
    .sort_values("Mean_Return", ascending=False)
)

print("\n=== Market Regime Summary ===")
print(summary.to_string())

# ============================================================
# Cell 7 — Visualize
# ============================================================
last_500 = data.tail(500).copy()

n_states  = 7
colors    = cm.get_cmap("tab10", n_states)

fig, ax = plt.subplots(figsize=(16, 6))

# Line: Close price
ax.plot(last_500.index, last_500["Close"], color="black", linewidth=0.8,
        alpha=0.6, label="_nolegend_", zorder=1)

# Scatter: colored by regime
for state in range(n_states):
    mask = last_500["State"] == state
    ax.scatter(
        last_500.index[mask],
        last_500["Close"][mask],
        color=colors(state),
        s=12,
        label=f"Regime {state}",
        zorder=2,
    )

ax.set_title("Bitcoin Close Price — Last 500 Hours\nColored by HMM Market Regime", fontsize=14)
ax.set_xlabel("Time")
ax.set_ylabel("BTC-USD Close Price")
ax.legend(loc="upper left", fontsize=9, markerscale=1.5)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("btc_market_regimes.png", dpi=150)
plt.show()
print("Plot saved as btc_market_regimes.png")
