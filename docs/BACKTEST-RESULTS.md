# SignalForge Comprehensive Backtest Results

> Generated on 2026-03-04 | Runtime: 251s
> Engine: Full 6-layer SignalPipeline with indicator caching
> Data: Real Binance candles

## Test Environment

| Pair | Timeframe | Bars |
|------|-----------|------|
| BTC/USD-1D | 1D | 2,252 |
| ETH/USD-1D | 1D | 3,539 |
| SOL/USD-1D | 1D | 2,154 |
| ADA/USDT-1D | 1D | 2,878 |
| BNB/USD-1D | 1D | 3,155 |
| DOGE/USDT-1D | 1D | 2,434 |
| LINK/USDT-1D | 1D | 2,604 |
| XRP/USDT-1D | 1D | 2,861 |
| XMR/USDT-1D | 1D | 1,806 |
| HYPE/USDT-4h | 4h | 1,619 |
| BTC/USD-1h | 1h | 4,689 |
| ETH/USDT-1h | 1h | 4,713 |
| SOL/USDT-1h | 1h | 4,761 |

- **Pairs tested:** 13
- **Parameter combinations:** 48
- **Exit variants:** 3 (baseline, break-even, trailing)
- **Total backtests run:** 1872
- **Initial capital:** $10,000
- **Lookback:** 200 bars

### Key Discovery: R:R Is Always 1.618

The take-profit is calculated as `entry ± SL_distance × 1.618` (Fibonacci extension). This means R:R is always exactly 1.618 regardless of ATR multiplier. The `min_risk_reward` parameter only acts as a binary gate — values ≤1.618 always pass, values >1.618 always reject (0 trades). This was confirmed during backtesting.

---

## 1. Baseline Results (Default Parameters)

Default: `min_confluence=50, atr_sl_mult=2.0, risk/trade=2%, no trailing, no break-even`

| Metric | BTC/USD-1D | ETH/USD-1D | SOL/USD-1D | ADA/USDT-1D | BNB/USD-1D | DOGE/USDT-1D | LINK/USDT-1D | XRP/USDT-1D | XMR/USDT-1D | HYPE/USDT-4h | BTC/USD-1h | ETH/USDT-1h | SOL/USDT-1h |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| Total Trades | 25 | 33 | 25 | 34 | 40 | 32 | 35 | 37 | 19 | 19 | 58 | 68 | 73 |
| Win Rate | 32.0% | 39.4% | 52.0% | 38.2% | 50.0% | 37.5% | 31.4% | 29.7% | 42.1% | 36.8% | 36.2% | 41.2% | 46.6% |
| Profit Factor | 0.75 | 1.02 | 1.73 | 0.98 | 1.59 | 0.95 | 0.72 | 0.66 | 1.15 | 0.92 | 0.85 | 1.08 | 1.34 |
| Total Return | -8.5% | 1.0% | 18.7% | -1.0% | 26.2% | -2.2% | -12.6% | -16.0% | 3.3% | -1.9% | -10.4% | 6.2% | 32.2% |
| Max Drawdown | 17.3% | 11.4% | 5.9% | 8.8% | 9.6% | 18.7% | 15.3% | 20.4% | 8.5% | 7.5% | 21.3% | 16.6% | 11.9% |
| Sharpe Ratio | -0.23 | 0.04 | 0.48 | 0.00 | 0.42 | -0.03 | -0.28 | -0.34 | 0.14 | -0.05 | -0.11 | 0.09 | 0.32 |
| Avg R:R (winners) | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.54 | 1.58 | 1.59 |

---

## 2. Top 10 Configurations (by Combined Score)

Score = `profit_factor × (1 - max_drawdown/100) × min(trades/10, 1.0)`, averaged across 13 pairs, weighted by consistency.

| Rank | Confluence | ATR Mult | Risk/Trade | Variant | Combined Score | Avg Return | Avg Win Rate |
|------|-----------|----------|-----------|---------|---------------|-----------|-------------|
| 1 | 60 | 2.0 | 1% | baseline | 0.948 | 2.3% | 41.4% |
| 2 | 50 | 1.5 | 1% | baseline | 0.914 | 2.2% | 40.2% |
| 3 | 60 | 3.0 | 1% | breakeven | 0.912 | 0.8% | 32.1% |
| 4 | 60 | 2.5 | 1% | baseline | 0.906 | 0.5% | 39.6% |
| 5 | 60 | 1.5 | 1% | baseline | 0.904 | 2.1% | 40.4% |
| 6 | 40 | 1.5 | 1% | baseline | 0.902 | 1.7% | 40.0% |
| 7 | 60 | 2.0 | 2% | baseline | 0.885 | 4.5% | 41.4% |
| 8 | 40 | 2.0 | 1% | baseline | 0.885 | 1.5% | 39.7% |
| 9 | 50 | 2.0 | 1% | baseline | 0.882 | 1.4% | 39.5% |
| 10 | 60 | 3.0 | 2% | breakeven | 0.858 | 1.6% | 32.1% |

### Best Configuration — Detailed Metrics

**Parameters:** `min_confluence=60, atr_sl_mult=2.0, risk/trade=1%, variant=baseline`

| Metric | BTC/USD-1D | ETH/USD-1D | SOL/USD-1D | ADA/USDT-1D | BNB/USD-1D | DOGE/USDT-1D | LINK/USDT-1D | XRP/USDT-1D | XMR/USDT-1D | HYPE/USDT-4h | BTC/USD-1h | ETH/USDT-1h | SOL/USDT-1h |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| Total Trades | 19 | 21 | 14 | 22 | 26 | 28 | 23 | 23 | 13 | 13 | 41 | 53 | 54 |
| Win Rate | 31.6% | 47.6% | 64.3% | 45.5% | 50.0% | 42.9% | 30.4% | 30.4% | 46.2% | 23.1% | 36.6% | 39.6% | 50.0% |
| Profit Factor | 0.74 | 1.45 | 2.84 | 1.33 | 1.60 | 1.19 | 0.70 | 0.70 | 1.37 | 0.48 | 0.92 | 1.00 | 1.58 |
| Total Return | -3.4% | 5.1% | 9.9% | 4.1% | 8.1% | 3.2% | -4.7% | -4.7% | 2.6% | -5.1% | -2.0% | -0.0% | 16.7% |
| Max Drawdown | 9.0% | 3.9% | 3.0% | 4.3% | 3.9% | 7.0% | 4.9% | 9.6% | 3.9% | 5.1% | 11.2% | 6.2% | 4.1% |
| Sharpe Ratio | -0.22 | 0.23 | 0.64 | 0.21 | 0.34 | 0.17 | -0.26 | -0.25 | 0.23 | -0.51 | -0.05 | 0.01 | 0.38 |
| Avg R:R (winners) | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.62 | 1.54 | 1.59 |

---

## 3. Parameter Sensitivity Analysis

Average score when each parameter is set to a given value (other params averaged out).

### Min Confluence

| Min Confluence | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 40 | 0.815 | 39.3% | -3.2% | 38.6 |
| 50 | 0.824 | 39.2% | -2.6% | 37.6 |
| 60 | 0.951 | 40.1% | -0.9% | 26.7 |
| 70 | 0.869 | 37.5% | -0.9% | 10.7 |

### Atr Sl Multiplier

| Atr Sl Multiplier | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 1.5 | 0.759 | 36.6% | -5.1% | 33.2 |
| 2.0 | 0.907 | 39.9% | -0.8% | 30.0 |
| 2.5 | 0.878 | 39.2% | -1.4% | 26.5 |
| 3.0 | 0.915 | 40.4% | -0.4% | 24.0 |

### Max Risk Per Trade

| Max Risk Per Trade | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 0.01 | 0.923 | 39.0% | -1.0% | 28.4 |
| 0.02 | 0.863 | 39.0% | -1.9% | 28.4 |
| 0.03 | 0.808 | 39.0% | -2.9% | 28.4 |

---

## 4. Exit Strategy Comparison

Averaged across ALL parameter combinations and ALL pairs.

| Variant | Avg Score | Avg Return | Avg Win Rate | Avg Drawdown | Avg PF | Avg Trades |
|---------|----------|-----------|-------------|-------------|--------|-----------|
| baseline | 0.94 | 1.5% | 39.1% | 11.4% | 1.10 | 27.13 |
| breakeven | 0.89 | -1.8% | 28.4% | 11.8% | 1.03 | 28.72 |
| trailing | 0.76 | -5.5% | 49.6% | 11.8% | 0.88 | 29.37 |

---

## 5. Walk-Forward Validation (Top 5 Configs)

60% in-sample / 40% out-of-sample split across all pairs.

| # | Confluence | ATR Mult | Risk | Variant | In-Sample | Out-of-Sample | Degradation | Overfit? |
|---|-----------|----------|------|---------|----------|--------------|------------|---------|
| 1 | 60 | 2.0 | 1% | baseline | 1.206 | 0.946 | 22% | No |
| 2 | 50 | 1.5 | 1% | baseline | 1.088 | 1.015 | 7% | No |
| 3 | 60 | 3.0 | 1% | breakeven | 1.273 | 0.834 | 35% | No |
| 4 | 60 | 2.5 | 1% | baseline | 1.189 | 0.850 | 29% | No |
| 5 | 60 | 1.5 | 1% | baseline | 1.133 | 0.981 | 13% | No |

---

## 6. Per-Trade Statistics (Best Config)

| Pair | Total | Wins | Losses | Avg Win | Avg Loss | Largest Win | Largest Loss | Avg Duration | Avg R:R |
|------|-------|------|--------|---------|----------|-------------|-------------|-------------|---------|
| BTC/USD-1D | 19 | 6 | 13 | $157.57 | $-98.70 | $164.42 | $-103.26 | 16.5 bars | 1.62 |
| ETH/USD-1D | 21 | 10 | 11 | $166.32 | $-104.63 | $173.91 | $-109.22 | 24.2 bars | 1.62 |
| SOL/USD-1D | 14 | 9 | 5 | $169.55 | $-107.63 | $177.44 | $-111.44 | 15.4 bars | 1.62 |
| ADA/USDT-1D | 22 | 10 | 12 | $163.42 | $-102.26 | $166.40 | $-104.51 | 24.9 bars | 1.62 |
| BNB/USD-1D | 26 | 13 | 13 | $166.02 | $-103.62 | $175.64 | $-110.31 | 23.4 bars | 1.62 |
| DOGE/USDT-1D | 28 | 12 | 16 | $166.02 | $-104.32 | $172.87 | $-108.57 | 14.2 bars | 1.62 |
| LINK/USDT-1D | 23 | 7 | 16 | $155.55 | $-97.61 | $157.30 | $-100.00 | 11.3 bars | 1.62 |
| XRP/USDT-1D | 23 | 7 | 16 | $159.91 | $-99.52 | $165.73 | $-104.09 | 17.7 bars | 1.62 |
| XMR/USDT-1D | 13 | 6 | 7 | $161.52 | $-100.89 | $163.75 | $-102.84 | 19.4 bars | 1.62 |
| HYPE/USDT-4h | 13 | 3 | 10 | $155.84 | $-97.76 | $157.30 | $-100.00 | 14.2 bars | 1.62 |
| BTC/USD-1h | 41 | 15 | 26 | $160.11 | $-100.19 | $168.06 | $-105.55 | 12.7 bars | 1.62 |
| ETH/USDT-1h | 53 | 21 | 32 | $149.45 | $-98.10 | $161.39 | $-101.36 | 16.7 bars | 1.54 |
| SOL/USDT-1h | 54 | 27 | 27 | $168.50 | $-106.82 | $184.24 | $-115.02 | 15.0 bars | 1.59 |

---

## 7. Recommendations

### Best Configuration Found

```json
{
  "min_confluence": 60,
  "atr_sl_multiplier": 2.0,
  "max_risk_per_trade": 0.01,
}
```

### Most Robust Config (WFO-validated, not overfit)

```json
{
  "min_confluence": 50,
  "atr_sl_multiplier": 1.5,
  "max_risk_per_trade": 0.01,
}
```

### Key Findings

- **Min Confluence:** Best at `60` (score 0.951), worst at `40` (score 0.815)
- **Atr Sl Multiplier:** Best at `3.0` (score 0.915), worst at `1.5` (score 0.759)
- **Max Risk Per Trade:** Best at `0.01` (score 0.923), worst at `0.03` (score 0.808)
- **Exit strategy:** `baseline` performed best (avg score 0.942)

### Production Recommendations

1. **Enable trailing stops + break-even** — protects winners from reversing to losses
2. **Enable drawdown circuit breaker** (`max_drawdown_pct: 15%`) — prevents catastrophic streaks
3. **Enable correlation monitoring** — BTC/ETH/SOL are correlated; multiple positions multiply risk
4. **Consider partial take-profit** — close 50% at TP1, trail remaining to TP2
5. **R:R is fixed at 1.618** — consider making TP ratio configurable for different market conditions

### Stop-Loss on Profitable Trades

A `stop_loss` exit reason with positive P&L occurs when **trailing stop or break-even stop** is active. The SL gets moved in the profit direction (e.g., to entry for break-even, or higher for trailing). When price retraces and hits this moved SL, the trade closes profitably — but the exit mechanism is still technically the stop loss, hence `exit_reason: stop_loss`.

Example: SELL at $0.0500 → price drops to $0.0490 → trailing SL moves to $0.0495 → price retraces to $0.0495 → exit at SL = +1% profit.
