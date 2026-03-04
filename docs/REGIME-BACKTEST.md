# Regime-Adaptive Backtest Results

> Generated on 2026-03-04 | Runtime: 972s
> Timeframe: 4h candles (Jan 2021 - Mar 2026)
> Transaction costs: 0.075% per side
> Starting capital: $10,000 per pair
> HMM training: rolling 500-bar window, retrain every 100 bars
> Regime+ confirmations: 6/8 required | Cooldown: 12 bars (48h)

## 1. Strategy Comparison (Return %)

| Pair | Current | Trailing | Rules | HMM | R+ 1x | R+ 2.5x | R+ AGG 4x | B&H |
|------|---------|----------|-------|-----|-------|---------|----------|-----|
| ADA/USD | +8.4% (95t) | -4.5% (115t) | **+14.6%** (151t) | +3.7% (59t) | +6.5% (46t) | +11.1% (46t) | -5.0% (52t) | -37.7% |
| BNB/USD | +1.4% (61t) | -3.8% (69t) | -13.0% (112t) | -1.4% (57t) | -4.6% (26t) | -11.6% (26t) | -24.4% (47t) | +1142.0% |
| BTC/USD | +7.5% (80t) | -13.7% (97t) | -31.9% (143t) | -11.5% (61t) | -5.6% (35t) | -14.8% (35t) | -37.4% (46t) | +89.7% |
| DOGE/USD | +1.0% (28t) | -3.0% (33t) | -9.9% (110t) | -5.6% (45t) | -4.5% (24t) | -11.6% (24t) | -12.0% (37t) | +177.9% |
| ETH/USD | +16.8% (91t) | -11.5% (107t) | -18.6% (146t) | -11.2% (61t) | -11.6% (40t) | -27.0% (40t) | -29.3% (52t) | +28.3% |
| LINK/USD | **+9.3%** (90t) | -9.2% (104t) | -21.5% (141t) | +7.7% (62t) | -2.6% (38t) | -7.3% (38t) | -29.9% (47t) | -64.3% |
| SOL/USD | +4.1% (93t) | -6.7% (108t) | +0.7% (125t) | -15.1% (57t) | -7.4% (43t) | -18.4% (43t) | -45.6% (47t) | +256.5% |
| XRP/USD | -0.7% (67t) | -17.9% (81t) | -23.5% (89t) | -4.6% (28t) | -3.0% (18t) | -7.7% (18t) | -23.0% (25t) | +126.1% |
| **PORTFOLIO** | **+6.0%** | **-8.8%** | **-12.9%** | **-4.8%** | **-4.1%** | **-10.9%** | **-25.8%** | **+214.8%** |

---

## 2. Max Drawdown Comparison

| Pair | Current | Trailing | Rules | HMM | R+ 1x | R+ 2.5x | R+ AGG 4x | B&H |
|------|---------|----------|-------|-----|-------|---------|----------|-----|
| ADA/USD | -7.8% | -15.7% | -15.5% | -15.4% | -12.3% | -28.7% | -46.9% | -92.2% |
| BNB/USD | -4.9% | -7.0% | -21.4% | -7.6% | -5.8% | -14.2% | -25.7% | -71.9% |
| BTC/USD | -7.5% | -16.0% | -38.3% | -22.5% | -13.7% | -31.0% | -48.8% | -77.1% |
| DOGE/USD | -7.6% | -5.2% | -22.3% | -11.3% | -8.0% | -19.2% | -29.8% | -93.0% |
| ETH/USD | -6.5% | -15.2% | -27.1% | -16.4% | -13.2% | -30.1% | -40.7% | -81.2% |
| LINK/USD | -6.1% | -13.7% | -25.8% | -10.7% | -6.8% | -16.8% | -44.6% | -90.4% |
| SOL/USD | -6.1% | -12.6% | -18.6% | -17.0% | -12.3% | -28.5% | -48.0% | -96.6% |
| XRP/USD | -7.4% | -19.4% | -24.7% | -5.8% | -4.1% | -10.2% | -24.2% | -66.5% |

---

## 3. Win Rate Comparison

| Pair | Current | Trailing | Rules | HMM | R+ 1x | R+ 2.5x | R+ AGG 4x |
|------|---------|----------|-------|-----|-------|---------|----------|
| ADA/USD | 53% | 31% | 42% | 36% | 37% | 37% | 35% |
| BNB/USD | 52% | 38% | 37% | 46% | 46% | 46% | 47% |
| BTC/USD | 57% | 32% | 34% | 33% | 34% | 34% | 33% |
| DOGE/USD | 46% | 36% | 39% | 40% | 33% | 33% | 41% |
| ETH/USD | 57% | 35% | 35% | 38% | 32% | 32% | 37% |
| LINK/USD | 53% | 40% | 41% | 47% | 45% | 45% | 40% |
| SOL/USD | 49% | 35% | 36% | 30% | 42% | 42% | 34% |
| XRP/USD | 46% | 28% | 33% | 43% | 39% | 39% | 36% |

---

## 4. Regime+ Strategy Details

The Regime+ strategy adds three key mechanisms on top of HMM regime-adaptive:

- **8-Confirmation Voting:** 6/8 must pass before entry
  (RSI<90, Momentum>1%, Vol<6%, Volume>20-SMA, ADX>25, Price>EMA50, Price>EMA200, MACD>Signal)
- **48h Cooldown:** 12 bars after every exit before re-entry
- **Regime-Exit:** Force close when regime flips to adverse (long->bear, short->bull)

### Variants Tested

| Variant | Leverage | Confirmations | Exit Mode | Description |
|---------|----------|---------------|-----------|-------------|
| **R+ 1x** | 1.0x | 6/8 | Per-regime | Conservative baseline |
| **R+ 2.5x** | 2.5x | 6/8 | Per-regime | Leveraged version |
| **R+ AGG 4x** | 4.0x | 5/8 | All trailing | Aggressive: fewer confirmations, higher leverage, trailing stops |

### Confirmation Filter Impact

| Pair | Signals Checked | Passed Filter | Filter Rate | Regime Exits |
|------|----------------|--------------|------------|-------------|
| ADA/USD | 60 | 46 | 77% | 8 |
| BNB/USD | 53 | 26 | 49% | 3 |
| BTC/USD | 59 | 35 | 59% | 5 |
| DOGE/USD | 41 | 24 | 59% | 0 |
| ETH/USD | 56 | 40 | 71% | 9 |
| LINK/USD | 54 | 38 | 70% | 9 |
| SOL/USD | 51 | 43 | 84% | 9 |
| XRP/USD | 31 | 18 | 58% | 3 |

---

## 5. Regime Breakdown: Regime+ Strategy (1x)

Trades and P&L per detected macro regime.

| Pair | Strong Bull | Bull Correction | Ranging | Bear Trending | Capitulation | Recovery |
|------|-----------|----------------|---------|-------------|-------------|----------|
| ADA/USD | 4t $+137 | 10t $+289 | 5t $-61 | 18t $+1,029 | - | 9t $-645 |
| BNB/USD | 3t $+134 | 6t $-314 | 2t $-95 | 9t $+272 | - | 6t $-358 |
| BTC/USD | 3t $-177 | 6t $-187 | 3t $+4 | 13t $-272 | 1t $+39 | 9t $+145 |
| DOGE/USD | - | 5t $-499 | 1t $+96 | 7t $-217 | - | 11t $+217 |
| ETH/USD | 8t $-302 | 6t $-270 | 8t $-292 | 8t $-130 | 1t $+43 | 9t $-119 |
| LINK/USD | 4t $-176 | 9t $+392 | 6t $-76 | 7t $-27 | - | 12t $-307 |
| SOL/USD | - | 8t $+180 | 8t $-373 | 11t $+289 | 1t $+47 | 13t $-605 |
| XRP/USD | - | 4t $-108 | 8t $-204 | 3t $-86 | - | 2t $+232 |

---

## 6. Regime Time Distribution (HMM)

Percentage of bars classified into each macro regime.

| Pair | Strong Bull | Bull Correction | Ranging | Bear Trending | Capitulation | Recovery |
|------|-----------|----------------|---------|-------------|-------------|----------|
| ADA/USD | 6.1% | 18.6% | 25.0% | 17.6% | 6.6% | 21.7% |
| BNB/USD | 8.6% | 21.3% | 20.5% | 15.0% | 13.1% | 17.2% |
| BTC/USD | 12.5% | 18.3% | 24.7% | 17.3% | 4.8% | 18.0% |
| DOGE/USD | 7.4% | 10.8% | 29.1% | 15.8% | 10.1% | 22.5% |
| ETH/USD | 12.3% | 23.7% | 28.1% | 13.5% | 5.1% | 12.8% |
| LINK/USD | 9.2% | 17.7% | 31.4% | 12.7% | 8.3% | 16.2% |
| SOL/USD | 4.9% | 16.2% | 26.7% | 15.7% | 8.4% | 23.2% |
| XRP/USD | 2.7% | 19.7% | 34.7% | 7.3% | 2.9% | 24.0% |

---

## 7. Key Findings

- **Best overall strategy:** Buy & Hold (+214.8%)
- **Current system:** +6.0%
- **Trailing stops:** -8.8% (-14.8% vs current)
- **Regime HMM:** -4.8% (-10.7% vs current)
- **Regime+ (1x):** -4.1% (-10.1% vs current)
- **Regime+ (2.5x):** -10.9% (-16.9% vs current)
- **Regime+ AGG (4x):** -25.8% (-31.8% vs current)
- **Buy & Hold:** +214.8%

### Insights from HMM Regime Terminal Approach

Based on the Jim Simons / RETech regime terminal model:
- HMM detects hidden market states that drive strategy selection
- Confirmation voting acts as a second-factor authentication for entries
- Signal hysteresis (cooldown) prevents overtrading in choppy transitions
- Regime-exit prevents holding through structural market shifts
- The model is a living algorithm -- retrain and evolve as market structure changes
