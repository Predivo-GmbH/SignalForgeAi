# Hybrid Core + Active Backtest Results

> Generated on 2026-03-04 | Runtime: 2828s
> Timeframe: 4h candles (Jan 2021 - Mar 2026)
> Transaction costs: 0.075% per side
> Starting capital: $10,000 per pair
> HMM training: rolling 500-bar window, retrain every 100 bars
> Grid: 3 splits x 3 tables x 5 active x 3 smoothing = 135 configs/pair

## 1. Benchmark Comparison

| Pair | B&H | Regime B&H (mod) | Active (current) | Active (best loose) |
|------|-----|-----------------|-----------------|-------------------|
| ADA/USD | -37.7% (dd 92.2%) | -15.5% (dd 84.6%) | +36.3% (123t) | +54.8% (141t) |
| BNB/USD | +1142.0% (dd 71.9%) | +321.0% (dd 61.3%) | +55.5% (97t) | +55.5% (97t) |
| BTC/USD | +89.7% (dd 77.1%) | +136.8% (dd 55.3%) | +6.4% (114t) | +19.9% (131t) |
| DOGE/USD | +177.9% (dd 93.0%) | +203.6% (dd 80.6%) | +47.1% (102t) | +47.1% (102t) |
| ETH/USD | +28.3% (dd 81.2%) | +55.4% (dd 66.9%) | +30.0% (124t) | +58.0% (145t) |
| HYPE/USDT | -25.3% (dd 65.4%) | -9.3% (dd 51.0%) | -6.2% (19t) | -6.0% (21t) |
| LINK/USD | -64.3% (dd 90.4%) | +17.3% (dd 60.6%) | +23.6% (131t) | +23.6% (131t) |
| SOL/USD | +256.5% (dd 96.6%) | +262.5% (dd 88.2%) | +45.7% (115t) | +45.7% (115t) |
| XRP/USD | +126.1% (dd 66.5%) | +60.4% (dd 55.7%) | -9.8% (81t) | -9.8% (81t) |
| **AVERAGE** | **+188.1%** | **+114.7%** | **+25.4%** | **+32.1%** |

## 2. Top 10 Hybrid Configs (by Calmar Ratio)

Calmar = Return / Max Drawdown. Higher = better risk-adjusted return.

| Rank | Config | Return | Max DD | Calmar | Core | Active | Trades |
|------|--------|--------|--------|--------|------|--------|--------|
| 1 | 80/20|conservative|current|s5 | +101.8% | 57.2% | 1.78 | +121.1% | +25.0% | 101 |
| 2 | 80/20|conservative|loose_conf|s5 | +100.6% | 57.0% | 1.76 | +121.1% | +18.8% | 115 |
| 3 | 80/20|conservative|loose_tp|s5 | +100.6% | 57.0% | 1.76 | +121.1% | +18.7% | 123 |
| 4 | 80/20|conservative|wide_trig|s5 | +99.7% | 57.0% | 1.75 | +121.1% | +14.3% | 165 |
| 5 | 70/30|conservative|current|s5 | +92.2% | 54.1% | 1.70 | +121.0% | +25.0% | 101 |
| 6 | 70/30|conservative|loose_conf|s5 | +90.3% | 53.8% | 1.68 | +121.0% | +18.8% | 115 |
| 7 | 70/30|conservative|loose_tp|s5 | +90.3% | 53.8% | 1.68 | +121.0% | +18.7% | 123 |
| 8 | 80/20|moderate|current|s5 | +103.5% | 61.8% | 1.68 | +123.2% | +25.0% | 101 |
| 9 | 80/20|conservative|widest|s5 | +96.2% | 57.4% | 1.68 | +121.1% | -3.2% | 143 |
| 10 | 80/20|moderate|loose_conf|s5 | +102.3% | 61.6% | 1.66 | +123.2% | +18.8% | 115 |

## 3. Best Hybrid Config Per Pair

| Pair | Best Config | Return | Max DD | Calmar | vs B&H | vs Active |
|------|-----------|--------|--------|--------|--------|----------|
| ADA/USD | 60/40|conservative|loose_tp|s5 | +32.4% | 66.5% | 0.49 | +70.1% | -3.9% |
| BNB/USD | 80/20|aggressive|current|s5 | +359.9% | 59.7% | 6.02 | -782.1% | +304.4% |
| BTC/USD | 80/20|conservative|loose_conf|s5 | +110.1% | 42.8% | 2.57 | +20.5% | +103.7% |
| DOGE/USD | 80/20|moderate|current|s5 | +173.4% | 78.3% | 2.21 | -4.6% | +126.2% |
| ETH/USD | 60/40|conservative|loose_tp|s5 | +61.3% | 43.8% | 1.40 | +33.0% | +31.3% |
| HYPE/USDT | 80/20|conservative|wide_trig|s1 | +0.6% | 35.7% | 0.02 | +25.9% | +6.8% |
| LINK/USD | 60/40|conservative|current|s3 | +31.0% | 37.9% | 0.82 | +95.3% | +7.5% |
| SOL/USD | 80/20|conservative|current|s5 | +276.4% | 79.5% | 3.48 | +19.9% | +230.7% |
| XRP/USD | 80/20|aggressive|current|s1 | +68.0% | 56.2% | 1.21 | -58.1% | +77.8% |

## 4. Split Ratio Sensitivity

| Split (Core/Active) | Avg Return | Avg Max DD | Avg Calmar |
|--------------------:|----------:|----------:|----------:|
| 60/40 | +69.7% | 55.7% | 1.25 |
| 70/30 | +78.9% | 59.2% | 1.33 |
| 80/20 | +88.1% | 62.4% | 1.41 |

## 5. Allocation Table Sensitivity

| Table | Avg Return | Avg Max DD | Avg Calmar |
|------:|----------:|----------:|----------:|
| conservative | +76.8% | 54.7% | 1.40 |
| moderate | +78.9% | 59.2% | 1.33 |
| aggressive | +81.2% | 63.4% | 1.28 |

## 6. Active Params Sensitivity

| Active Variant | Avg Return | Avg Max DD | Avg Trades | Description |
|---------------:|----------:|----------:|----------:|------------|
| current | +82.0% | 59.1% | 101 | conf=50, tp=1.618, look=1 |
| loose_conf | +80.1% | 58.9% | 115 | conf=30, tp=1.5, look=1 |
| loose_tp | +80.1% | 59.0% | 123 | conf=40, tp=1.0, look=1 |
| wide_trig | +78.8% | 58.7% | 165 | conf=40, tp=1.5, look=3 |
| widest | +73.5% | 59.6% | 143 | conf=30, tp=1.5, look=5 |

## 7. Smoothing Sensitivity

| Smoothing Bars | Avg Return | Avg Max DD | Avg Calmar |
|---------------:|----------:|----------:|----------:|
| 1 | +61.5% | 60.3% | 1.02 |
| 3 | +84.8% | 58.5% | 1.45 |
| 5 | +90.5% | 58.4% | 1.55 |

## 8. Bear Market Performance (Nov 2021 - Nov 2022)

| Pair | B&H | Regime B&H | Best Hybrid | Config |
|------|-----|-----------|------------|--------|
| ADA/USD | -84.9% | -68.9% | -46.6% | 60/40|conservative|wide_trig|s5 |
| BNB/USD | -53.5% | -44.2% | -34.9% | 60/40|conservative|loose_tp|s3 |
| BTC/USD | -74.0% | -45.3% | -25.0% | 60/40|conservative|loose_conf|s3 |
| DOGE/USD | -71.3% | -62.9% | -50.8% | 60/40|conservative|loose_tp|s5 |
| ETH/USD | -75.1% | -56.9% | -32.8% | 60/40|conservative|loose_tp|s3 |
| HYPE/USDT | +0.0% | +0.0% | +0.0% | 60/40|conservative|current|s1 |
| LINK/USD | -81.6% | -40.7% | -19.8% | 60/40|conservative|wide_trig|s1 |
| SOL/USD | -95.1% | -85.1% | -70.5% | 60/40|conservative|current|s5 |
| XRP/USD | +0.0% | +0.0% | +0.0% | 60/40|conservative|current|s1 |

## 9. Bull Market Performance (Jan 2024 - Mar 2026)

| Pair | B&H | Regime B&H | Best Hybrid | Config |
|------|-----|-----------|------------|--------|
| ADA/USD | +12.1% | +17.0% | +25.7% | 80/20|conservative|current|s5 |
| BNB/USD | +97.0% | +85.3% | +99.6% | 80/20|aggressive|loose_conf|s5 |
| BTC/USD | +96.0% | +111.1% | +102.7% | 80/20|aggressive|wide_trig|s3 |
| DOGE/USD | +88.9% | +69.3% | +73.4% | 80/20|aggressive|widest|s5 |
| ETH/USD | -19.3% | -21.5% | -3.9% | 60/40|conservative|loose_tp|s5 |
| HYPE/USDT | +0.0% | +0.0% | +0.0% | 60/40|conservative|current|s1 |
| LINK/USD | -8.7% | -1.7% | +12.3% | 60/40|conservative|current|s5 |
| SOL/USD | +22.3% | +46.9% | +45.4% | 80/20|aggressive|wide_trig|s5 |
| XRP/USD | +242.6% | +131.6% | +151.8% | 80/20|aggressive|loose_tp|s1 |

## 10. Drawdown Comparison

| Pair | B&H DD | Regime B&H DD | Best Hybrid DD | Active DD |
|------|--------|-------------|---------------|----------|
| ADA/USD | 92.2% | 84.6% | 65.1% | 20.4% |
| BNB/USD | 71.9% | 61.3% | 51.6% | 11.9% |
| BTC/USD | 77.1% | 55.3% | 33.7% | 25.0% |
| DOGE/USD | 93.0% | 80.6% | 70.1% | 12.6% |
| ETH/USD | 81.2% | 66.9% | 41.9% | 18.6% |
| HYPE/USDT | 65.4% | 51.0% | 25.9% | 10.8% |
| LINK/USD | 90.4% | 60.6% | 36.6% | 23.6% |
| SOL/USD | 96.6% | 88.2% | 73.8% | 22.7% |
| XRP/USD | 66.5% | 55.7% | 40.8% | 23.4% |

## 11. Regime Time Distribution

| Pair | Strong Bull | Bull Corr | Ranging | Bear | Capitulation | Recovery |
|------|-----------|---------|---------|------|-------------|----------|
| ADA/USD | 6.4% | 19.5% | 26.1% | 18.4% | 6.9% | 22.7% |
| BNB/USD | 9.0% | 22.2% | 21.4% | 15.7% | 13.7% | 18.0% |
| BTC/USD | 13.1% | 19.1% | 25.9% | 18.1% | 5.0% | 18.9% |
| DOGE/USD | 7.7% | 11.3% | 30.4% | 16.5% | 10.6% | 23.5% |
| ETH/USD | 12.9% | 24.8% | 29.4% | 14.2% | 5.4% | 13.4% |
| HYPE/USDT | 27.3% | 21.1% | 19.2% | 14.0% | 0.0% | 18.3% |
| LINK/USD | 9.6% | 18.5% | 32.9% | 13.3% | 8.7% | 17.0% |
| SOL/USD | 5.2% | 17.1% | 28.1% | 16.5% | 8.8% | 24.4% |
| XRP/USD | 3.0% | 21.6% | 38.0% | 7.9% | 3.2% | 26.3% |

## 12. Walk-Forward Validation (Top 5 Configs)

60% in-sample / 40% out-of-sample. Degradation > 50% = likely overfit.

| Config | In-Sample | Out-Sample | Degradation | Status |
|--------|----------|-----------|------------|--------|
| ADA/USD|80/20|conservative|current|s5 | +30.4% | +15.1% | 50% | OVERFIT |
| ADA/USD|80/20|conservative|loose_conf|s5 | +34.0% | +13.2% | 61% | OVERFIT |
| ADA/USD|80/20|conservative|loose_tp|s5 | +32.4% | +14.1% | 57% | OVERFIT |
| ADA/USD|80/20|conservative|wide_trig|s5 | +33.8% | +12.7% | 62% | OVERFIT |
| ADA/USD|80/20|moderate|current|s5 | +18.4% | +8.1% | 56% | OVERFIT |
| BNB/USD|80/20|conservative|current|s5 | +150.0% | +76.9% | 49% | OK |
| BNB/USD|80/20|conservative|loose_conf|s5 | +147.8% | +77.2% | 48% | OK |
| BNB/USD|80/20|conservative|loose_tp|s5 | +150.1% | +73.4% | 51% | OVERFIT |
| BNB/USD|80/20|conservative|wide_trig|s5 | +149.9% | +69.9% | 53% | OVERFIT |
| BNB/USD|80/20|moderate|current|s5 | +162.7% | +83.3% | 49% | OK |
| BTC/USD|80/20|conservative|current|s5 | +45.0% | +9.6% | 79% | OVERFIT |
| BTC/USD|80/20|conservative|loose_conf|s5 | +47.7% | +9.8% | 79% | OVERFIT |
| BTC/USD|80/20|conservative|loose_tp|s5 | +46.2% | +8.7% | 81% | OVERFIT |
| BTC/USD|80/20|conservative|wide_trig|s5 | +43.3% | +10.6% | 76% | OVERFIT |
| BTC/USD|80/20|moderate|current|s5 | +44.9% | +8.3% | 82% | OVERFIT |
| DOGE/USD|80/20|conservative|current|s5 | +111.3% | +37.1% | 67% | OVERFIT |
| DOGE/USD|80/20|conservative|loose_conf|s5 | +107.7% | +36.6% | 66% | OVERFIT |
| DOGE/USD|80/20|conservative|loose_tp|s5 | +109.3% | +36.1% | 67% | OVERFIT |
| DOGE/USD|80/20|conservative|wide_trig|s5 | +108.5% | +40.7% | 63% | OVERFIT |
| DOGE/USD|80/20|moderate|current|s5 | +123.1% | +35.1% | 71% | OVERFIT |
| ETH/USD|80/20|conservative|current|s5 | +72.8% | +14.0% | 81% | OVERFIT |
| ETH/USD|80/20|conservative|loose_conf|s5 | +70.4% | +16.1% | 77% | OVERFIT |
| ETH/USD|80/20|conservative|loose_tp|s5 | +76.4% | +15.8% | 79% | OVERFIT |
| ETH/USD|80/20|conservative|wide_trig|s5 | +75.4% | +10.7% | 86% | OVERFIT |
| ETH/USD|80/20|moderate|current|s5 | +75.5% | +5.9% | 92% | OVERFIT |
| HYPE/USDT|80/20|conservative|current|s5 | -5.2% | +5.6% | -208% | OK |
| HYPE/USDT|80/20|conservative|loose_conf|s5 | -5.2% | +5.5% | -205% | OK |
| HYPE/USDT|80/20|conservative|loose_tp|s5 | -4.8% | +5.3% | -209% | OK |
| HYPE/USDT|80/20|conservative|wide_trig|s5 | -5.0% | +6.3% | -226% | OK |
| HYPE/USDT|80/20|moderate|current|s5 | -7.7% | +4.9% | -163% | OK |
| LINK/USD|80/20|conservative|current|s5 | +24.5% | +0.6% | 98% | OVERFIT |
| LINK/USD|80/20|conservative|loose_conf|s5 | +22.9% | -0.0% | 100% | OVERFIT |
| LINK/USD|80/20|conservative|loose_tp|s5 | +22.9% | -0.1% | 101% | OVERFIT |
| LINK/USD|80/20|conservative|wide_trig|s5 | +27.7% | -3.5% | 113% | OVERFIT |
| LINK/USD|80/20|moderate|current|s5 | +16.1% | -4.8% | 130% | OVERFIT |
| SOL/USD|80/20|conservative|current|s5 | +226.2% | -24.8% | 111% | OVERFIT |
| SOL/USD|80/20|conservative|loose_conf|s5 | +225.7% | -25.3% | 111% | OVERFIT |
| SOL/USD|80/20|conservative|loose_tp|s5 | +220.6% | -25.6% | 112% | OVERFIT |
| SOL/USD|80/20|conservative|wide_trig|s5 | +217.5% | -24.7% | 111% | OVERFIT |
| SOL/USD|80/20|moderate|current|s5 | +205.0% | -26.2% | 113% | OVERFIT |
| XRP/USD|80/20|conservative|current|s5 | +94.2% | -22.7% | 124% | OVERFIT |
| XRP/USD|80/20|conservative|loose_conf|s5 | +93.1% | -22.5% | 124% | OVERFIT |
| XRP/USD|80/20|conservative|loose_tp|s5 | +93.7% | -23.6% | 125% | OVERFIT |
| XRP/USD|80/20|conservative|wide_trig|s5 | +92.1% | -22.1% | 124% | OVERFIT |
| XRP/USD|80/20|moderate|current|s5 | +121.0% | -25.7% | 121% | OVERFIT |

## 13. Success Criteria

- [PASS] Total return > 100%: **101.8%**
- [FAIL] Max drawdown < 40%: **57.2%**
- [FAIL] Bear market DD < 30%: **-37.1%**
- [FAIL] Calmar ratio > 2.0: **1.78**

## 14. Recommendations

**Best universal config:** `80/20|conservative|current|s5`
- Average return: +101.8%
- Average max drawdown: 57.2%
- Calmar ratio: 1.78
- Bear market return: -37.1%
- Bull market return: +40.0%

**Verdict: PARTIALLY VIABLE.** Hybrid improves on active-only but may not justify the complexity over regime-managed B&H alone.