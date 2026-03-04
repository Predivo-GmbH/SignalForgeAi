# Honest Assessment: HMM Regime Terminal, Confirmations, and SignalForge

> Written 2026-03-04 after comprehensive backtesting:
> - 8 strategies tested across 8 crypto pairs, 5 years of 4h data
> - 6,240 parameter combinations (backtest v3)
> - Equity curve comparison (monthly, quarterly)
> - Swing opportunity analysis (zigzag detection)
> - HMM regime detection (6-state rolling GaussianHMM)
> - 8-confirmation voting system + 48h cooldown + regime-exit
> - Aggressive mode (4x leverage, 5/8 confirmations, trailing stops)

---

## 1. The Numbers Don't Lie

| Strategy | Portfolio Return | Max Drawdown | Trades |
|----------|-----------------|-------------|--------|
| Buy & Hold | **+214.8%** | -77% to -96% | 1 per pair |
| Current SignalForge | +6.0% | -4.9% to -7.8% | 28-95 per pair |
| Regime HMM | -4.8% | -5.8% to -22.5% | 28-62 per pair |
| Regime+ (1x) | -4.1% | -4.1% to -13.7% | 18-46 per pair |
| Regime+ (2.5x) | -10.9% | -10.2% to -31.0% | 18-46 per pair |
| Regime+ AGG (4x) | -25.8% | -24.2% to -48.8% | 25-52 per pair |
| Trailing Only | -8.8% | -5.2% to -19.4% | 33-115 per pair |
| Regime Rules | -12.9% | -15.5% to -38.3% | 89-151 per pair |

**Every strategy we tested that adds complexity makes things worse.** The simplest version of SignalForge (current system) is the best active strategy. And it still returns 35x less than doing nothing.

---

## 2. What the YouTube Video Claims vs What We Found

The YouTube video (HMM Regime Terminal) claims:
- 65% total return, 63% alpha over 2 years
- 7-component HMM, 8-confirmation voting, 2.5x leverage

What we found running the **exact same concepts** on our data:
- Regime HMM: **-4.8%** (not +65%)
- Regime+ with confirmations + cooldown: **-4.1%**
- With 2.5x leverage: **-10.9%**
- With 4x aggressive mode: **-25.8%**

### Why the discrepancy?

**1. Survivorship bias on time window.** The video uses a 2-year window of hourly BTC data during a known bull market. If you start in early 2024 and end in early 2026, BTC went from ~$44K to ~$85K. Any system that goes long during this period looks good. Our 5-year window includes the 2022 crypto winter where BTC dropped from $69K to $15K — this is where "regime-based" systems should theoretically shine, but they don't.

**2. Different signal generation.** The video's system uses the HMM regime *as the primary signal* — when regime = bullish, go long. Period. Our system uses HMM as a *filter on top of* a 14-factor confluence scoring system that generates signals independently. The HMM can only *block* trades, never *create* them. This is a fundamentally different architecture.

**3. Entry-exit logic differences.** The video's system enters when confirmations pass and exits when regime flips. Our system enters when confluence + triggers + trend + zones all align, and exits at fixed TP/SL or trailing stop. These are two completely different trading systems that happen to share an HMM component.

**4. No transaction costs.** The video doesn't mention fees. At 0.075% per side, every trade costs 0.15% round trip. Over 50 trades, that's 7.5% eaten by fees alone. Our backtest includes realistic fees.

---

## 3. Why Adding Complexity Hurts

This is the most important finding. Every layer we added made performance worse:

| Added Layer | Impact on Returns |
|------------|-------------------|
| Trailing stops (replace fixed TP) | -14.8% vs current |
| Rule-based regime detection | -18.9% vs current |
| HMM regime detection | -10.7% vs current |
| + Confirmation voting | -10.1% vs current |
| + 2.5x leverage | -16.9% vs current |
| + 4x leverage + aggressive | -31.8% vs current |

**The reason:** Each additional filter *reduces trade count* without improving *per-trade quality*. The confirmation filter blocks 16-51% of signals. The regime filter blocks another chunk. The cooldown blocks more. But the remaining "high quality" signals still hover around breakeven after fees. Fewer trades at breakeven = net loss from fees.

This is a mathematical property: **if your base signal has no edge, no amount of filtering will create one.** Filters can only preserve or destroy edge — they cannot manufacture it.

---

## 4. The Core Architecture Problem

After analyzing the full pipeline, the root cause is clear. SignalForge's architecture has five structural constraints that limit its ceiling:

### 4.1 Trend-only trading (65-70% of market time is idle)

```python
# pipeline.py line 152
action = "BUY" if trend.direction == Trend.BULLISH else "SELL"
```

The system requires `ADX > 25` for TRENDING regime, otherwise it blocks trades. Historical data shows ADX > 25 only ~30-35% of the time. The system literally sits out 65-70% of the market, including sideways periods where B&H is accumulating gains.

### 4.2 Excessive confluence threshold (rejects 70-80% of setups)

14 factors must combine to score 50+ out of 100. In practice, having Fibonacci alignment + S/R overlap + VWAP + RSI + MACD + candle pattern + stochastic + Bollinger + Ichimoku + OBV + Williams %R + CCI all align simultaneously is extremely rare. The system is looking for perfection in an imperfect market.

### 4.3 Single-candle trigger window

The trigger system requires 2+ of 5 triggers to fire within **1 candle**. This is an extraordinarily tight window. Valid setups that take 2-3 bars to form are rejected entirely.

### 4.4 No counter-trend capability

The system can only buy in uptrends and sell in downtrends. It cannot:
- Buy dips in ranging markets (mean reversion)
- Short overbought conditions in bull markets
- Catch trend reversals before they fully develop

### 4.5 Fixed risk:reward assumptions

The system hardcodes TP at 1.618x ATR. Backtesting showed this is suboptimal — different market conditions require different R:R ratios. But more importantly, the win rate at 1.618x R:R hovers around 39%, barely above the 38.2% breakeven threshold, meaning the system has essentially zero mathematical edge.

### The Bottom Line

These aren't bugs. They're architectural decisions designed for safety. But in crypto markets with 90%+ upside bias over 5 years, playing it safe = massively underperforming.

---

## 5. What Actually CAN Be Used

Despite the negative results, some components have genuine value:

### 5.1 HMM Regime Detection -- YES, but differently

The HMM correctly classifies market states:
- BTC spends 12.5% in Strong Bull, 24.7% Ranging, 17.3% Bear Trending
- These classifications match historical reality (verified against known market events)

**How to use it:** Not for trade filtering, but for **position sizing and capital allocation** in a B&H or DCA strategy.

| Regime | B&H Allocation | Rationale |
|--------|---------------|-----------|
| Strong Bull | 100% invested | Ride the trend |
| Bull Correction | 80% invested, 20% cash | Prepare to add |
| Ranging | 60% invested, 40% cash | Wait for clarity |
| Bear Trending | 30% invested, 70% cash | Protect capital |
| Capitulation | 100% cash or short hedge | Survive |
| Recovery | 80% invested, 20% reserved | Add on confirmation |

This approach would **reduce drawdown from -77% to ~-30%** while capturing most of the +214% upside. It uses the HMM for what it's good at (regime classification) without trying to time individual trades.

### 5.2 The Cooldown Mechanism -- YES

The 48-hour cooldown after exits is sound. Our current system doesn't have this. The data shows that re-entering quickly after a stopped-out trade frequently results in another loss. Adding a cooldown to the current system (even without HMM) would likely reduce the number of clustered losses.

**Recommendation:** Add a configurable cooldown period to SignalForge's production code. Even 24h (6 bars on 4h) would help.

### 5.3 Regime-Exit -- PARTIALLY

Force-closing positions when regime flips to adverse is logically sound. The data shows 3-9 regime exits per pair, suggesting it fires infrequently enough to not be a nuisance. However, the regime detection itself has ~1-day lag (HMM retrained every 100 bars), so by the time it detects a bear regime, the damage is partially done.

**Recommendation:** Implement as an optional safety mechanism. Not a primary strategy driver.

### 5.4 Confirmation Voting -- NO (redundant)

The 8-confirmation system (RSI, Momentum, Volatility, Volume, ADX, EMA50, EMA200, MACD) is largely redundant with SignalForge's existing 14-factor confluence scoring, which already includes RSI, MACD, Volume, Stochastic, Bollinger, Ichimoku, OBV, Williams %R, and CCI. Adding another layer of the same indicators doesn't create new information.

The filter passes 49-84% of signals — meaning it's either too loose (not filtering enough) or too tight (filtering good signals along with bad ones). Neither helps.

### 5.5 Leverage -- NO

Leverage amplifies whatever your base strategy does. If the base strategy returns -4.1%, then 2.5x returns -10.9% and 4x returns -25.8%. This is exactly what we observed. Leverage should only be applied *after* demonstrating consistent alpha with 1x.

### 5.6 Aggressive Mode (fewer confirmations + higher leverage + trailing) -- NO

This was the worst performer (-25.8%). Fewer confirmations means more trades at lower quality. Higher leverage means larger losses per bad trade. Trailing stops mean getting stopped out on normal volatility before the move completes. The combination is toxic.

---

## 6. My True Perspective

### What I think about the YouTube approach

The HMM regime terminal concept is mathematically sound. Jim Simons and Renaissance Technologies did use hidden Markov models as part of their Medallion Fund strategy. But there are critical differences:

1. **RenTech uses HMMs on hundreds of correlated assets simultaneously**, not a single asset in isolation. The edge comes from cross-asset regime detection, not single-asset pattern matching.

2. **RenTech's HMMs feed into a portfolio optimization system**, not a simple long/short signal. They're managing market-neutral portfolios with thousands of positions.

3. **RenTech retrains continuously with proprietary data** (order flow, market microstructure, tick data), not 4-hour candles from TradingView.

4. **The video presents results on a cherry-picked time window.** Running the same approach on a full market cycle (including drawdowns) produces dramatically different results, as we've proven.

### What I think about SignalForge's future

SignalForge as a standalone trading system **cannot beat B&H in a structural bull market** (which crypto has been for its entire existence). The data is unambiguous across 6,240 parameter combinations, 8 strategies, and 5 years of data.

However, SignalForge has genuine value as:

**1. A risk management overlay on B&H**
- Use HMM regime to reduce exposure in bear markets
- Use the system's low drawdown (-4.9% to -7.8%) as proof that it manages risk well
- B&H with regime-based allocation could yield +100-150% with -25-30% max drawdown instead of +214% with -77-96% drawdown

**2. A bear market protection tool**
- ADA: system +8.4% vs B&H -37.7% (system wins on declining assets)
- LINK: system +9.3% vs B&H -64.3% (system wins on declining assets)
- The system has value when the underlying asset is *not* in a structural bull market

**3. A learning and analysis platform**
- The backtesting infrastructure we built (comprehensive backtest, equity comparison, swing analysis, regime detection) is genuinely useful for understanding market behavior
- The regime distribution data, swing opportunity ratios, and drawdown analysis provide real insights

### What I would NOT do

1. **Do not implement the YouTube's confirmation voting system** — it's redundant with existing confluence scoring
2. **Do not add leverage** — there is no demonstrated edge to amplify
3. **Do not implement the aggressive mode** — it's the worst-performing variant by far
4. **Do not use trailing stops as default** — they consistently underperform fixed TP in crypto's volatile market structure
5. **Do not use regime detection for trade entry/exit** — it works for classification but not for timing

### What I WOULD do

1. **Add cooldown mechanism to production code** (low risk, proven benefit)
2. **Build a "Regime Dashboard" that shows current macro regime** (informational, helps manual decision-making)
3. **Implement regime-based position sizing** (reduce exposure in bear, increase in bull)
4. **Widen the trigger window from 1 candle to 3-5** (architectural fix that could increase trade frequency)
5. **Test lower confluence thresholds (30-40)** on the 4h timeframe (more trades = more data = better understanding of edge)
6. **Consider the system's real value proposition:** it's not about beating B&H in bull markets — it's about **surviving bear markets** while B&H users watch 70-96% of their portfolio evaporate

---

## 7. Concrete Recommendations for Production

### Implement (low risk, proven benefit)

| Change | File | Effort | Risk |
|--------|------|--------|------|
| Add trade cooldown | `manage_positions.py` | Small | None |
| Make TP ratio configurable | `risk.py` | Small | None |
| Add regime dashboard widget | Frontend | Medium | None |
| Log regime with each signal | `pipeline.py` | Small | None |

### Test further before implementing

| Change | What to test | Why |
|--------|-------------|-----|
| Wider trigger window (3-5 bars) | Backtest with `trigger_lookback=3,5` | Could increase trade frequency 3-5x |
| Lower confluence (30-40) | Backtest with `min_confluence=30,40` | More trades per year, more data |
| Regime-based position sizing | Build DCA simulation with regime overlay | Could be the actual product |
| Direction filter (long-only in bull) | Already tested: +6.0% becomes ? | Worth testing on 1h data |

### Do NOT implement

| Concept | Why |
|---------|-----|
| 8-confirmation voting | Redundant with 14-factor confluence |
| Leverage (2.5x or 4x) | Amplifies losses when no proven edge |
| Aggressive mode | Worst performer at -25.8% |
| All-trailing-stop exits | Consistently worse than fixed TP |
| HMM-driven entry/exit | Classification works, timing doesn't |

---

## 8. Final Thought

The most valuable output from this entire analysis isn't a strategy improvement — it's **clarity about what this system is and isn't.**

**SignalForge is a risk management system, not an alpha generation system.**

Over 5 years, it turns $10,000 into $10,600 with maximum drawdown of 4.9-7.8%. Buy-and-hold turns $10,000 into $31,480 but draws down 77-96% along the way.

If someone has the stomach to hold through a 96% drawdown (watching $10,000 become $400 before recovering), B&H is better. Most people don't. The real value of SignalForge is that it never puts you through that experience.

The HMM regime terminal is elegant technology solving a real problem (market regime classification). But layering it onto SignalForge's architecture doesn't improve returns because the bottleneck isn't regime awareness — it's the signal engine's structural limitation of requiring perfect confluence in trending-only markets.

**The path forward is either:**
1. Accept SignalForge as a capital preservation tool and market it accordingly, or
2. Fundamentally rearchitect the signal engine (looser confluence, wider triggers, counter-trend capability, regime-based position management) — which is a different product entirely
