# SignalForge Comprehensive Backtest Results

> Generated on 2026-03-04 | Runtime: 259s
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
- **Parameter combinations:** 160
- **Exit variants:** 3 (baseline, break-even, trailing)
- **Total backtests run:** 6240
- **Initial capital:** $10,000
- **Lookback:** 200 bars

### Key Parameter: TP Ratio

The take-profit distance is `SL_distance × tp_ratio`. In production this is hardcoded at 1.618 (Fibonacci extension). This backtest tests variable TP ratios [1.0, 1.2, 1.618, 2.0, 2.618] to find the optimal risk:reward tradeoff.

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

| Rank | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Avg Return | Avg Win Rate |
|------|-----------|----------|------|---------|---------|-------|-----------|-------------|
| 1 | 60 | 3.0 | 1% | 2.0 | breakeven | 1.041 | 1.8% | 29.2% |
| 2 | 60 | 2.0 | 1% | 2.0 | baseline | 1.017 | 2.0% | 37.2% |
| 3 | 60 | 2.0 | 1% | 2.618 | baseline | 0.990 | 2.9% | 31.6% |
| 4 | 60 | 2.0 | 1% | 2.618 | breakeven | 0.981 | 1.3% | 21.2% |
| 5 | 60 | 3.0 | 2% | 2.0 | breakeven | 0.980 | 3.5% | 29.2% |
| 6 | 40 | 1.5 | 1% | 1.0 | baseline | 0.974 | 1.4% | 52.4% |
| 7 | 50 | 1.5 | 1% | 1.0 | baseline | 0.970 | 1.6% | 52.3% |
| 8 | 60 | 2.0 | 1% | 1.0 | baseline | 0.969 | 1.5% | 52.9% |
| 9 | 60 | 1.5 | 1% | 1.0 | baseline | 0.954 | 1.1% | 52.0% |
| 10 | 70 | 3.0 | 1% | 2.0 | baseline | 0.949 | 2.6% | 41.5% |

### Best Configuration — Detailed Metrics

**Parameters:** `min_confluence=60, atr_sl_mult=3.0, risk/trade=1%, variant=breakeven`

| Metric | BTC/USD-1D | ETH/USD-1D | SOL/USD-1D | ADA/USDT-1D | BNB/USD-1D | DOGE/USDT-1D | LINK/USDT-1D | XRP/USDT-1D | XMR/USDT-1D | HYPE/USDT-4h | BTC/USD-1h | ETH/USDT-1h | SOL/USDT-1h |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| Total Trades | 14 | 18 | 11 | 15 | 22 | 21 | 20 | 19 | 13 | 11 | 36 | 47 | 47 |
| Win Rate | 28.6% | 50.0% | 45.5% | 33.3% | 50.0% | 19.0% | 25.0% | 21.1% | 15.4% | 18.2% | 25.0% | 21.3% | 27.7% |
| Profit Factor | 0.99 | 2.52 | 3.26 | 1.64 | 2.75 | 0.88 | 0.82 | 0.99 | 0.56 | 0.44 | 1.11 | 0.68 | 1.16 |
| Total Return | -0.1% | 11.4% | 7.1% | 3.9% | 14.7% | -1.1% | -2.1% | -0.1% | -3.0% | -5.0% | 1.8% | -7.9% | 3.2% |
| Max Drawdown | 5.9% | 2.0% | 2.0% | 3.9% | 3.9% | 4.9% | 5.0% | 3.9% | 4.9% | 5.0% | 8.6% | 10.7% | 5.9% |
| Sharpe Ratio | 0.00 | 0.46 | 0.52 | 0.24 | 0.57 | -0.07 | -0.11 | 0.00 | -0.31 | -0.51 | 0.07 | -0.24 | 0.10 |
| Avg R:R (winners) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 |

---

## 3. Parameter Sensitivity Analysis

Average score when each parameter is set to a given value (other params averaged out).

### Min Confluence

| Min Confluence | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 40 | 0.864 | 40.3% | -2.0% | 38.6 |
| 50 | 0.870 | 40.2% | -1.7% | 37.5 |
| 60 | 0.995 | 41.0% | -0.6% | 26.7 |
| 70 | 0.903 | 38.6% | -0.6% | 10.7 |

### Atr Sl Multiplier

| Atr Sl Multiplier | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 1.5 | 0.811 | 37.6% | -3.6% | 33.2 |
| 2.0 | 0.944 | 40.7% | -0.7% | 29.8 |
| 2.5 | 0.897 | 39.9% | -1.0% | 26.5 |
| 3.0 | 0.981 | 42.0% | 0.5% | 24.0 |

### Max Risk Per Trade

| Max Risk Per Trade | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 0.01 | 0.938 | 40.1% | -0.8% | 28.4 |
| 0.02 | 0.878 | 40.1% | -1.6% | 28.4 |

### Tp Ratio

| Tp Ratio | Avg Score | Avg Win Rate | Avg Return | Avg Trades |
|---|---|---|---|---|
| 1.0 | 0.890 | 47.6% | -1.7% | 29.4 |
| 1.2 | 0.877 | 43.9% | -1.8% | 29.1 |
| 1.618 | 0.893 | 39.0% | -1.4% | 28.4 |
| 2.0 | 0.929 | 36.5% | -0.8% | 27.8 |
| 2.618 | 0.951 | 33.3% | -0.2% | 27.0 |

---

## 4. Exit Strategy Comparison

Averaged across ALL parameter combinations and ALL pairs.

| Variant | Avg Score | Avg Return | Avg Win Rate | Avg Drawdown | Avg PF | Avg Trades |
|---------|----------|-----------|-------------|-------------|--------|-----------|
| baseline | 1.00 | 1.7% | 40.3% | 8.5% | 1.14 | 27.10 |
| breakeven | 0.93 | -1.3% | 30.3% | 9.0% | 1.05 | 28.59 |
| trailing | 0.79 | -4.0% | 49.6% | 9.0% | 0.89 | 29.39 |

---

## 5. Walk-Forward Validation (Top 5 Configs)

60% in-sample / 40% out-of-sample split across all pairs.

| # | Confluence | ATR Mult | Risk | Variant | In-Sample | Out-of-Sample | Degradation | Overfit? |
|---|-----------|----------|------|---------|----------|--------------|------------|---------|
| 1 | 60 | 3.0 | 1% | breakeven | 1.492 | 0.807 | 46% | No |
| 2 | 60 | 2.0 | 1% | baseline | 1.369 | 0.917 | 33% | No |
| 3 | 60 | 2.0 | 1% | baseline | 1.358 | 0.859 | 37% | No |
| 4 | 60 | 2.0 | 1% | breakeven | 1.511 | 1.234 | 18% | No |
| 5 | 60 | 3.0 | 2% | breakeven | 1.450 | 0.772 | 47% | No |

---

## 6. Per-Trade Statistics (Best Config)

| Pair | Total | Wins | Losses | Avg Win | Avg Loss | Largest Win | Largest Loss | Avg Duration | Avg R:R |
|------|-------|------|--------|---------|----------|-------------|-------------|-------------|---------|
| BTC/USD-1D | 14 | 4 | 10 | $199.93 | $-81.16 | $204.00 | $-104.04 | 36.0 bars | 0.00 |
| ETH/USD-1D | 18 | 9 | 9 | $209.77 | $-83.21 | $222.85 | $-113.65 | 37.8 bars | 0.00 |
| SOL/USD-1D | 11 | 5 | 6 | $205.63 | $-52.54 | $210.12 | $-107.16 | 27.9 bars | 0.00 |
| ADA/USDT-1D | 15 | 5 | 10 | $202.74 | $-61.90 | $208.02 | $-106.09 | 66.9 bars | 0.00 |
| BNB/USD-1D | 22 | 11 | 11 | $210.58 | $-76.66 | $227.24 | $-115.89 | 41.9 bars | 0.00 |
| DOGE/USDT-1D | 21 | 4 | 17 | $201.94 | $-54.09 | $203.94 | $-104.01 | 32.8 bars | 0.00 |
| LINK/USDT-1D | 20 | 5 | 15 | $199.89 | $-80.87 | $201.90 | $-102.97 | 24.1 bars | 0.00 |
| XRP/USDT-1D | 19 | 4 | 15 | $198.92 | $-53.84 | $201.90 | $-102.97 | 47.9 bars | 0.00 |
| XMR/USDT-1D | 13 | 2 | 11 | $193.08 | $-62.63 | $196.02 | $-100.00 | 21.2 bars | 0.00 |
| HYPE/USDT-4h | 11 | 2 | 9 | $192.10 | $-97.77 | $194.00 | $-100.00 | 42.9 bars | 0.00 |
| BTC/USD-1h | 36 | 9 | 27 | $200.69 | $-60.39 | $207.89 | $-106.03 | 24.0 bars | 0.00 |
| ETH/USDT-1h | 47 | 10 | 37 | $166.67 | $-66.51 | $194.06 | $-100.00 | 27.4 bars | 0.00 |
| SOL/USDT-1h | 47 | 13 | 34 | $184.79 | $-61.10 | $203.39 | $-103.73 | 30.5 bars | 0.04 |

---

## 7. Recommendations

### Best Configuration Found

```json
{
  "min_confluence": 60,
  "atr_sl_multiplier": 3.0,
  "max_risk_per_trade": 0.01,
  "tp_ratio": 2.0,
  "break_even_enabled": true,
}
```

### Most Robust Config (WFO-validated, not overfit)

```json
{
  "min_confluence": 60,
  "atr_sl_multiplier": 2.0,
  "max_risk_per_trade": 0.01,
  "tp_ratio": 2.618,
  "break_even_enabled": true,
}
```

### Best Configuration Per Pair

| Pair | Confluence | ATR Mult | Risk | TP Ratio | Variant | Score | Return | Win Rate |
|------|-----------|----------|------|---------|---------|-------|--------|---------|
| BTC/USD-1D | 40 | 1.5 | 1% | 1.0 | baseline | 2.66 | 12.6% | 73.1% |
| ETH/USD-1D | 70 | 2.0 | 1% | 2.618 | breakeven | 3.40 | 7.6% | 40.0% |
| SOL/USD-1D | 60 | 2.5 | 1% | 1.618 | baseline | 4.12 | 10.3% | 72.7% |
| ADA/USDT-1D | 70 | 2.0 | 1% | 2.618 | breakeven | 2.73 | 7.6% | 50.0% |
| BNB/USD-1D | 70 | 2.0 | 1% | 2.618 | breakeven | 4.07 | 8.7% | 50.0% |
| DOGE/USDT-1D | 70 | 3.0 | 1% | 2.618 | baseline | 1.76 | 5.5% | 44.4% |
| LINK/USDT-1D | 70 | 1.5 | 1% | 2.618 | breakeven | 1.43 | 3.4% | 33.3% |
| XRP/USDT-1D | 60 | 3.0 | 1% | 1.2 | breakeven | 1.30 | 2.9% | 50.0% |
| XMR/USDT-1D | 60 | 2.0 | 1% | 2.618 | baseline | 1.78 | 6.1% | 41.7% |
| HYPE/USDT-4h | 40 | 1.5 | 1% | 2.0 | baseline | 1.17 | 2.8% | 38.1% |
| BTC/USD-1h | 70 | 3.0 | 1% | 1.0 | baseline | 2.85 | 6.1% | 75.0% |
| ETH/USDT-1h | 50 | 1.5 | 1% | 2.618 | baseline | 1.22 | 17.3% | 34.7% |
| SOL/USDT-1h | 70 | 3.0 | 1% | 2.0 | baseline | 2.23 | 13.4% | 54.5% |

### Key Findings

- **Min Confluence:** Best at `60` (score 0.995), worst at `40` (score 0.864)
- **Atr Sl Multiplier:** Best at `3.0` (score 0.981), worst at `1.5` (score 0.811)
- **Max Risk Per Trade:** Best at `0.01` (score 0.938), worst at `0.02` (score 0.878)
- **Tp Ratio:** Best at `2.618` (score 0.951), worst at `1.2` (score 0.877)
- **Exit strategy:** `baseline` performed best (avg score 1.002)

### Production Recommendations

1. **Make TP ratio configurable** — the optimal TP ratio varies; 1.618 may not be best for all conditions
2. **Enable drawdown circuit breaker** (`max_drawdown_pct: 15%`) — prevents catastrophic loss streaks
3. **Use per-pair optimized configs** — some pairs need different settings than others
4. **Enable correlation monitoring** — BTC/ETH/SOL are highly correlated; avoid simultaneous positions
5. **Consider partial take-profit** — close 50% at TP1, trail remaining to TP2
