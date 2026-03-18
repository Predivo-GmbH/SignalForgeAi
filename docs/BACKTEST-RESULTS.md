# SignalForgeAI Comprehensive Backtest Results (v3)

> Generated on 2026-03-04 | Runtime: 1398s
> Engine: Full 6-layer SignalPipeline with indicator caching
> Transaction costs: 0.075% per side (0.150% round trip)
> Data: Real Binance/Coinbase/Index candles

## Test Environment

| Pair | Timeframe | Source | Bars |
|------|-----------|--------|------|
| ADA/USD-1h | 1h | BINANCE | 10,256 |
| ADA/USD-4h | 4h | BINANCE | 11,330 |
| ADA/USDT-1D | 1D | BINANCE | 2,878 |
| BNB/USD-1D | 1D | BINANCE | 3,155 |
| BNB/USD-1h | 1h | CRYPTO | 10,256 |
| BNB/USD-4h | 4h | CRYPTO | 11,330 |
| BTC/USD-1D | 1D | BINANCE | 2,252 |
| BTC/USD-1h | 1h | INDEX | 10,256 |
| BTC/USD-4h | 4h | INDEX | 11,330 |
| DOGE/USD-1h | 1h | CRYPTO | 10,256 |
| DOGE/USD-4h | 4h | CRYPTO | 11,330 |
| DOGE/USDT-1D | 1D | BINANCE | 2,434 |
| ETH/USD-1D | 1D | BINANCE | 3,539 |
| ETH/USD-1h | 1h | COINBASE | 10,251 |
| ETH/USD-4h | 4h | COINBASE | 11,329 |
| ETH/USDT-1h | 1h | BINANCE | 4,713 |
| HYPE/USDT-4h | 4h | BINANCEUS | 1,619 |
| LINK/USD-1h | 1h | COINBASE | 10,251 |
| LINK/USD-4h | 4h | COINBASE | 11,329 |
| LINK/USDT-1D | 1D | BINANCE | 2,604 |
| SOL/USD-1D | 1D | BINANCE | 2,154 |
| SOL/USD-1h | 1h | COINBASE | 10,251 |
| SOL/USD-4h | 4h | COINBASE | 10,323 |
| SOL/USDT-1h | 1h | BINANCE | 4,761 |
| XMR/USDT-1D | 1D | KUCOIN | 1,806 |
| XRP/USD-1h | 1h | COINBASE | 10,251 |
| XRP/USD-4h | 4h | COINBASE | 5,786 |
| XRP/USDT-1D | 1D | BINANCE | 2,861 |

- **Pairs tested:** 28
- **Parameter combinations:** 128
- **Variants:** 2 (baseline, partial_tp)
- **Total backtests:** 7,168
- **Initial capital:** $10,000

---

## 1. Buy-and-Hold Benchmark

What you'd get by simply buying and holding each asset.

| Pair | TF | Start Price | End Price | B&H Return | B&H P&L |
|------|----|------------|----------|-----------|---------|
| ADA/USD-1h | 1h | $0.92 | $0.26 | -71.7% | $-7,170 |
| ADA/USD-4h | 4h | $0.42 | $0.26 | -37.7% | $-3,773 |
| ADA/USDT-1D | 1D | $0.07 | $0.26 | 267.1% | $26,707 |
| BNB/USD-1D | 1D | $11.21 | $632.76 | 5542.4% | $554,237 |
| BNB/USD-1h | 1h | $694.96 | $635.56 | -8.7% | $-869 |
| BNB/USD-4h | 4h | $51.11 | $635.28 | 1142.0% | $114,195 |
| BTC/USD-1D | 1D | $9,441.36 | $68,353.03 | 623.4% | $62,336 |
| BTC/USD-1h | 1h | $93,020.74 | $68,415.39 | -26.6% | $-2,658 |
| BTC/USD-4h | 4h | $36,000.79 | $68,367.83 | 89.7% | $8,969 |
| DOGE/USD-1h | 1h | $0.33 | $0.09 | -73.3% | $-7,332 |
| DOGE/USD-4h | 4h | $0.03 | $0.09 | 177.9% | $17,795 |
| DOGE/USDT-1D | 1D | $0.00 | $0.09 | 3709.4% | $370,943 |
| ETH/USD-1D | 1D | $9.76 | $1,962.49 | 19999.8% | $1,999,978 |
| ETH/USD-1h | 1h | $3,308.43 | $1,978.06 | -40.3% | $-4,033 |
| ETH/USD-4h | 4h | $1,539.67 | $1,977.48 | 28.3% | $2,826 |
| ETH/USDT-1h | 1h | $4,506.71 | $1,991.40 | -55.9% | $-5,592 |
| HYPE/USDT-4h | 4h | $41.80 | $31.28 | -25.3% | $-2,530 |
| LINK/USD-1h | 1h | $19.97 | $8.81 | -56.0% | $-5,600 |
| LINK/USD-4h | 4h | $24.55 | $8.80 | -64.3% | $-6,425 |
| LINK/USDT-1D | 1D | $2.51 | $8.80 | 250.3% | $25,027 |
| SOL/USD-1D | 1D | $1.71 | $85.65 | 4903.2% | $490,323 |
| SOL/USD-1h | 1h | $191.07 | $85.90 | -55.2% | $-5,515 |
| SOL/USD-4h | 4h | $24.08 | $85.94 | 256.5% | $25,652 |
| SOL/USDT-1h | 1h | $187.20 | $86.94 | -53.7% | $-5,367 |
| XMR/USDT-1D | 1D | $270.06 | $341.90 | 26.4% | $2,643 |
| XRP/USD-1h | 1h | $2.32 | $1.36 | -41.3% | $-4,134 |
| XRP/USD-4h | 4h | $0.60 | $1.36 | 126.1% | $12,610 |
| XRP/USDT-1D | 1D | $0.44 | $1.36 | 207.2% | $20,716 |

---

## 2. BUY vs SELL Breakdown (Baseline)

Default params, both directions. Shows whether SELL trades drag performance.

| Pair | TF | BUY Trades | BUY Win% | BUY P&L | SELL Trades | SELL Win% | SELL P&L | Net P&L | B&H Return |
|------|----|-----------|---------|---------|------------|----------|---------|---------|-----------|
| ADA/USD-1h | 1h | 49 | 33% | $-1,570 | 92 | 42% | $720 | $-1,614 | -71.7% |
| ADA/USD-4h | 4h | 54 | 35% | $-1,515 | 83 | 53% | $7,119 | $5,092 | -37.7% |
| ADA/USDT-1D | 1D | 15 | 40% | $79 | 19 | 37% | $-216 | $-173 | 267.1% |
| BNB/USD-1D | 1D | 22 | 59% | $2,496 | 18 | 39% | $29 | $2,451 | 5542.4% |
| BNB/USD-1h | 1h | 66 | 45% | $1,035 | 64 | 30% | $-3,155 | $-3,575 | -8.7% |
| BNB/USD-4h | 4h | 62 | 47% | $2,578 | 62 | 47% | $3,066 | $4,897 | 1142.0% |
| BTC/USD-1D | 1D | 19 | 37% | $-196 | 6 | 17% | $-701 | $-952 | 623.4% |
| BTC/USD-1h | 1h | 39 | 36% | $-1,174 | 74 | 43% | $749 | $-1,963 | -26.6% |
| BTC/USD-4h | 4h | 57 | 44% | $1,242 | 73 | 37% | $-1,227 | $-634 | 89.7% |
| DOGE/USD-1h | 1h | 48 | 33% | $-1,250 | 79 | 39% | $-602 | $-2,500 | -73.3% |
| DOGE/USD-4h | 4h | 54 | 44% | $1,712 | 69 | 52% | $6,064 | $7,269 | 177.9% |
| DOGE/USDT-1D | 1D | 12 | 42% | $153 | 20 | 35% | $-407 | $-295 | 3709.4% |
| ETH/USD-1D | 1D | 15 | 60% | $1,662 | 18 | 22% | $-1,611 | $1 | 19999.8% |
| ETH/USD-1h | 1h | 46 | 35% | $-1,173 | 68 | 38% | $-655 | $-2,607 | -40.3% |
| ETH/USD-4h | 4h | 59 | 44% | $1,571 | 82 | 40% | $190 | $1,111 | 28.3% |
| ETH/USDT-1h | 1h | 19 | 42% | $-87 | 49 | 41% | $8 | $-626 | -55.9% |
| HYPE/USDT-4h | 4h | 8 | 38% | $-76 | 11 | 36% | $-167 | $-292 | -25.3% |
| LINK/USD-1h | 1h | 60 | 30% | $-2,143 | 76 | 38% | $-1,000 | $-3,773 | -56.0% |
| LINK/USD-4h | 4h | 74 | 39% | $-24 | 71 | 48% | $3,515 | $3,038 | -64.3% |
| LINK/USDT-1D | 1D | 16 | 31% | $-601 | 19 | 32% | $-690 | $-1,327 | 250.3% |
| SOL/USD-1D | 1D | 11 | 64% | $1,540 | 14 | 43% | $297 | $1,808 | 4903.2% |
| SOL/USD-1h | 1h | 61 | 34% | $-1,088 | 94 | 36% | $-2,106 | $-3,935 | -55.2% |
| SOL/USD-4h | 4h | 63 | 46% | $2,881 | 69 | 42% | $755 | $3,169 | 256.5% |
| SOL/USDT-1h | 1h | 28 | 43% | $192 | 45 | 49% | $2,257 | $1,813 | -53.7% |
| XMR/USDT-1D | 1D | 7 | 43% | $138 | 12 | 42% | $164 | $276 | 26.4% |
| XRP/USD-1h | 1h | 58 | 26% | $-3,686 | 83 | 43% | $1,157 | $-3,399 | -41.3% |
| XRP/USD-4h | 4h | 34 | 26% | $-1,934 | 54 | 41% | $245 | $-2,009 | 126.1% |
| XRP/USDT-1D | 1D | 20 | 25% | $-1,279 | 17 | 35% | $-365 | $-1,691 | 207.2% |
| **TOTAL** | | | | **$-516** | | | **$13,432** | **$12,916** | |

---

## 3. Long-Only vs Both Directions

Same params, but filtering out all SELL signals.

| Pair | TF | Both Return | Both Trades | Long-Only Return | Long-Only Trades | Improvement |
|------|----|-----------|------------|-----------------|----------------|------------|
| ADA/USD-1h | 1h | -16.1% | 141 | -19.5% | 49 | -3.3% |
| ADA/USD-4h | 4h | 50.9% | 137 | -12.3% | 54 | -63.2% |
| ADA/USDT-1D | 1D | -1.7% | 34 | 0.6% | 15 | **+2.4%** |
| BNB/USD-1D | 1D | 24.5% | 40 | 25.3% | 22 | **+0.8%** |
| BNB/USD-1h | 1h | -35.7% | 130 | 1.7% | 66 | **+37.4%** |
| BNB/USD-4h | 4h | 49.0% | 124 | 21.5% | 62 | -27.5% |
| BTC/USD-1D | 1D | -9.5% | 25 | -2.8% | 19 | **+6.7%** |
| BTC/USD-1h | 1h | -19.6% | 113 | -17.6% | 39 | **+2.0%** |
| BTC/USD-4h | 4h | -6.3% | 130 | 9.1% | 57 | **+15.4%** |
| DOGE/USD-1h | 1h | -25.0% | 127 | -17.5% | 48 | **+7.6%** |
| DOGE/USD-4h | 4h | 72.7% | 123 | 14.0% | 54 | -58.7% |
| DOGE/USDT-1D | 1D | -3.0% | 32 | 1.6% | 12 | **+4.5%** |
| ETH/USD-1D | 1D | 0.0% | 33 | 17.5% | 15 | **+17.5%** |
| ETH/USD-1h | 1h | -26.1% | 114 | -15.9% | 46 | **+10.2%** |
| ETH/USD-4h | 4h | 11.1% | 141 | 11.8% | 59 | **+0.7%** |
| ETH/USDT-1h | 1h | -6.3% | 68 | -3.4% | 19 | **+2.9%** |
| HYPE/USDT-4h | 4h | -2.9% | 19 | -0.9% | 8 | **+2.0%** |
| LINK/USD-1h | 1h | -37.7% | 136 | -29.6% | 60 | **+8.1%** |
| LINK/USD-4h | 4h | 30.4% | 145 | -2.7% | 74 | -33.0% |
| LINK/USDT-1D | 1D | -13.3% | 35 | -6.4% | 16 | **+6.9%** |
| SOL/USD-1D | 1D | 18.1% | 25 | 15.0% | 11 | -3.1% |
| SOL/USD-1h | 1h | -39.4% | 155 | -21.7% | 61 | **+17.7%** |
| SOL/USD-4h | 4h | 31.7% | 132 | 22.3% | 63 | -9.4% |
| SOL/USDT-1h | 1h | 18.1% | 73 | -0.2% | 28 | -18.3% |
| XMR/USDT-1D | 1D | 2.8% | 19 | 1.3% | 7 | -1.5% |
| XRP/USD-1h | 1h | -34.0% | 141 | -38.0% | 58 | -4.1% |
| XRP/USD-4h | 4h | -20.1% | 88 | -21.6% | 34 | -1.5% |
| XRP/USDT-1D | 1D | -16.9% | 37 | -13.9% | 20 | **+3.1%** |

---

## 4. Trending-Only vs All Regimes

Filtering out signals generated during RANGING/TRANSITIONING regimes.

| Pair | TF | All Regimes Return | Trending-Only Return | Trades (All) | Trades (Trending) |
|------|----|-------------------|---------------------|-------------|------------------|
| ADA/USD-1h | 1h | -16.1% | -10.2% | 141 | 83 |
| ADA/USD-4h | 4h | 50.9% | 42.1% | 137 | 80 |
| ADA/USDT-1D | 1D | -1.7% | -12.8% | 34 | 22 |
| BNB/USD-1D | 1D | 24.5% | 12.8% | 40 | 17 |
| BNB/USD-1h | 1h | -35.7% | -13.3% | 130 | 72 |
| BNB/USD-4h | 4h | 49.0% | 18.1% | 124 | 67 |
| BTC/USD-1D | 1D | -9.5% | 1.3% | 25 | 12 |
| BTC/USD-1h | 1h | -19.6% | -10.2% | 113 | 71 |
| BTC/USD-4h | 4h | -6.3% | -10.4% | 130 | 62 |
| DOGE/USD-1h | 1h | -25.0% | -24.8% | 127 | 67 |
| DOGE/USD-4h | 4h | 72.7% | 44.3% | 123 | 62 |
| DOGE/USDT-1D | 1D | -3.0% | 14.0% | 32 | 14 |
| ETH/USD-1D | 1D | 0.0% | -10.2% | 33 | 18 |
| ETH/USD-1h | 1h | -26.1% | -10.2% | 114 | 65 |
| ETH/USD-4h | 4h | 11.1% | -4.9% | 141 | 72 |
| ETH/USDT-1h | 1h | -6.3% | -15.2% | 68 | 35 |
| HYPE/USDT-4h | 4h | -2.9% | 6.6% | 19 | 7 |
| LINK/USD-1h | 1h | -37.7% | -24.8% | 136 | 72 |
| LINK/USD-4h | 4h | 30.4% | 39.0% | 145 | 82 |
| LINK/USDT-1D | 1D | -13.3% | -14.9% | 35 | 13 |
| SOL/USD-1D | 1D | 18.1% | 2.5% | 25 | 9 |
| SOL/USD-1h | 1h | -39.4% | -28.8% | 155 | 90 |
| SOL/USD-4h | 4h | 31.7% | -2.4% | 132 | 69 |
| SOL/USDT-1h | 1h | 18.1% | 12.6% | 73 | 42 |
| XMR/USDT-1D | 1D | 2.8% | 0.4% | 19 | 10 |
| XRP/USD-1h | 1h | -34.0% | -23.9% | 141 | 80 |
| XRP/USD-4h | 4h | -20.1% | 21.9% | 88 | 41 |
| XRP/USDT-1D | 1D | -16.9% | -7.3% | 37 | 19 |

---

## 5. Timeframe Comparison

Averaged across all parameter combinations.

| Timeframe | Avg Score | Avg Return | Avg Win Rate | Avg Drawdown | Avg Trades |
|-----------|----------|-----------|-------------|-------------|-----------|
| 1D | 1.098 | 2.2% | 41.2% | 8.0% | 20 |
| 1h | 0.694 | -12.1% | 36.3% | 22.3% | 85 |
| 4h | 0.983 | 8.0% | 40.6% | 13.3% | 77 |

---

## 6. Baseline vs Partial Take-Profit

Partial TP: close 50% at TP1, trail remaining 50% to TP2 (2.618x).

| Variant | Avg Score | Avg Return | Avg Win Rate | Avg Drawdown | Avg PF |
|---------|----------|-----------|-------------|-------------|--------|
| baseline | 0.90 | -1.8% | 39.0% | 15.0% | 1.10 |
| partial_tp | 0.94 | -0.4% | 39.5% | 14.6% | 1.14 |

---

## 7. Top 10 Universal Configurations

Ranked by combined score (profit_factor × (1-drawdown/100) × min(trades/10,1)), averaged across 28 pairs.

| Rank | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Avg Return | Avg Win Rate |
|------|-----------|----------|------|---------|---------|-------|-----------|-------------|
| 1 | 60 | 2.0 | 1% | 1.0 | partial_tp | 0.919 | -0.6% | 51.8% |
| 2 | 60 | 2.0 | 1% | 2.0 | baseline | 0.902 | -0.4% | 36.5% |
| 3 | 60 | 2.0 | 1% | 2.0 | partial_tp | 0.893 | 0.1% | 36.8% |
| 4 | 50 | 3.0 | 1% | 2.0 | partial_tp | 0.885 | 2.5% | 36.6% |
| 5 | 50 | 2.0 | 1% | 1.0 | partial_tp | 0.879 | 0.5% | 52.0% |
| 6 | 60 | 2.0 | 1% | 1.5 | partial_tp | 0.879 | -0.8% | 42.3% |
| 7 | 40 | 2.0 | 1% | 1.0 | partial_tp | 0.879 | 0.9% | 52.0% |
| 8 | 50 | 3.0 | 1% | 2.0 | baseline | 0.864 | 1.6% | 35.8% |
| 9 | 40 | 3.0 | 1% | 2.0 | partial_tp | 0.863 | 2.0% | 36.2% |
| 10 | 50 | 3.0 | 1% | 2.618 | baseline | 0.860 | 2.8% | 30.7% |

---

## 8. Parameter Sensitivity

### Min Confluence

| Min Confluence | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 40 | 0.872 | 39.6% | -0.9% | 88.8 |
| 50 | 0.886 | 39.7% | -0.4% | 80.9 |
| 60 | 0.964 | 39.7% | -1.0% | 53.5 |
| 70 | 0.945 | 38.1% | -2.0% | 22.8 |

### Atr Sl Multiplier

| Atr Sl Multiplier | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 1.5 | 0.873 | 39.1% | -3.0% | 75.2 |
| 2.0 | 0.933 | 39.5% | -0.8% | 65.1 |
| 2.5 | 0.909 | 38.8% | -0.7% | 56.6 |
| 3.0 | 0.951 | 39.7% | 0.2% | 49.2 |

### Max Risk Per Trade

| Max Risk Per Trade | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 0.01 | 0.966 | 39.3% | -0.8% | 61.5 |
| 0.02 | 0.867 | 39.3% | -1.4% | 61.5 |

### Tp Ratio

| Tp Ratio | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 1.0 | 0.925 | 50.1% | -3.2% | 67.5 |
| 1.5 | 0.913 | 41.1% | -1.8% | 62.7 |
| 2.0 | 0.917 | 35.5% | -0.1% | 59.5 |
| 2.618 | 0.912 | 30.4% | 0.8% | 56.4 |

---

## 9. Walk-Forward Validation (Top 5)

60% in-sample / 40% out-of-sample.

| # | Confluence | ATR Mult | Risk | TP Ratio | Variant | In-Sample | OOS | Degradation | Overfit? |
|---|-----------|----------|------|---------|---------|----------|-----|------------|---------|
| 1 | 60 | 2.0 | 1% | 1.0 | partial_tp | 1.166 | 1.280 | -10% | No |
| 2 | 60 | 2.0 | 1% | 2.0 | baseline | 1.121 | 1.075 | 4% | No |
| 3 | 60 | 2.0 | 1% | 2.0 | partial_tp | 1.155 | 1.132 | 2% | No |
| 4 | 50 | 3.0 | 1% | 2.0 | partial_tp | 1.114 | 1.067 | 4% | No |
| 5 | 50 | 2.0 | 1% | 1.0 | partial_tp | 0.978 | 1.124 | -15% | No |

---

## 10. Best Configuration Per Pair

| Pair | TF | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Return | Win Rate |
|------|----|-----------|----------|------|---------|---------|-------|--------|---------|
| ADA/USD-1h | 1h | 70 | 3.0 | 1% | 2.0 | partial_tp | 1.14 | 4.5% | 40.0% |
| ADA/USD-4h | 4h | 60 | 3.0 | 1% | 1.5 | partial_tp | 1.42 | 18.6% | 48.6% |
| ADA/USDT-1D | 1D | 70 | 3.0 | 1% | 1.5 | partial_tp | 2.02 | 4.9% | 66.7% |
| BNB/USD-1D | 1D | 70 | 2.5 | 1% | 2.618 | baseline | 3.42 | 10.3% | 62.5% |
| BNB/USD-1h | 1h | 70 | 3.0 | 1% | 2.618 | baseline | 1.43 | 3.7% | 38.5% |
| BNB/USD-4h | 4h | 70 | 1.5 | 1% | 1.0 | partial_tp | 3.14 | 6.5% | 76.9% |
| BTC/USD-1D | 1D | 40 | 1.5 | 1% | 1.0 | baseline | 2.58 | 11.7% | 73.1% |
| BTC/USD-1h | 1h | 60 | 3.0 | 1% | 1.0 | partial_tp | 1.08 | 3.2% | 54.8% |
| BTC/USD-4h | 4h | 70 | 3.0 | 1% | 1.0 | partial_tp | 1.85 | 6.9% | 61.9% |
| DOGE/USD-1h | 1h | 40 | 2.0 | 1% | 1.0 | partial_tp | 1.07 | 10.9% | 55.8% |
| DOGE/USD-4h | 4h | 70 | 3.0 | 1% | 1.0 | baseline | 4.00 | 4.0% | 100.0% |
| DOGE/USDT-1D | 1D | 40 | 3.0 | 1% | 1.0 | partial_tp | 1.83 | 5.6% | 68.4% |
| ETH/USD-1D | 1D | 70 | 1.5 | 1% | 1.5 | baseline | 3.38 | 7.4% | 70.0% |
| ETH/USD-1h | 1h | 70 | 1.5 | 1% | 1.0 | baseline | 1.45 | 11.2% | 63.4% |
| ETH/USD-4h | 4h | 70 | 2.0 | 1% | 2.618 | partial_tp | 1.80 | 19.1% | 42.9% |
| ETH/USDT-1h | 1h | 60 | 1.5 | 1% | 2.618 | baseline | 1.09 | 4.3% | 34.5% |
| HYPE/USDT-4h | 4h | 40 | 1.5 | 1% | 2.0 | baseline | 1.13 | 2.1% | 38.1% |
| LINK/USD-1h | 1h | 60 | 1.5 | 1% | 1.0 | baseline | 1.01 | 1.3% | 55.2% |
| LINK/USD-4h | 4h | 60 | 2.5 | 1% | 2.618 | baseline | 1.47 | 26.4% | 38.2% |
| LINK/USDT-1D | 1D | 40 | 3.0 | 1% | 1.0 | partial_tp | 1.36 | 4.9% | 57.1% |
| SOL/USD-1D | 1D | 60 | 2.5 | 1% | 1.5 | baseline | 4.27 | 10.8% | 75.0% |
| SOL/USD-1h | 1h | 70 | 1.5 | 1% | 2.0 | baseline | 1.21 | 7.3% | 41.7% |
| SOL/USD-4h | 4h | 50 | 2.5 | 1% | 2.618 | baseline | 1.48 | 46.8% | 40.0% |
| SOL/USDT-1h | 1h | 70 | 3.0 | 1% | 2.0 | partial_tp | 2.16 | 11.1% | 57.1% |
| XMR/USDT-1D | 1D | 60 | 2.0 | 1% | 2.618 | partial_tp | 1.85 | 5.6% | 45.5% |
| XRP/USD-1h | 1h | 50 | 3.0 | 1% | 2.0 | partial_tp | 0.77 | -8.5% | 32.2% |
| XRP/USD-4h | 4h | 70 | 3.0 | 1% | 1.5 | partial_tp | 1.02 | 0.9% | 42.9% |
| XRP/USDT-1D | 1D | 60 | 3.0 | 1% | 1.0 | baseline | 1.28 | 2.7% | 57.1% |

---

## 11. Recommendations

### Best Universal Configuration

```json
{
  "min_confluence": 60,
  "atr_sl_multiplier": 2.0,
  "max_risk_per_trade": 0.01,
  "tp1_ratio": 1.0
}
```

### Key Findings

- **BUY trades total P&L:** $-516 | **SELL trades total P&L:** $13,432
- **Min Confluence:** Best at `60` (score 0.964), worst at `40` (score 0.872)
- **Atr Sl Multiplier:** Best at `3.0` (score 0.951), worst at `1.5` (score 0.873)
- **Max Risk Per Trade:** Best at `0.01` (score 0.966), worst at `0.02` (score 0.867)
- **Tp Ratio:** Best at `1.0` (score 0.925), worst at `2.618` (score 0.912)
- **Exit strategy:** `partial_tp` performed best (avg score 0.937)
- **Best timeframe:** `1D` (avg score 1.098, avg return 2.2%)

### Production Recommendations

1. **Make TP ratio configurable** — hardcoded 1.618 is suboptimal
2. **Add direction_filter option** — `long_only` for crypto in bull markets
3. **Add regime filtering** — skip RANGING regime if data supports it
4. **Implement partial take-profit** — if partial_tp variant outperforms
5. **Fix Fibonacci swing detection** — use recent N-bar window, not all-time high/low
6. **Enable per-pair configs** — leverage existing FeedbackFilter infrastructure
