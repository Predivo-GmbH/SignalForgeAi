# SignalForge Trading System — Complete Deep Dive

> **Purpose:** This document provides a comprehensive, plain-language explanation of everything
> the SignalForge trading system does — how it decides to buy, how it decides to sell, what
> signals it uses, how they combine, how risk is managed, and where improvements can be made.
>
> **Last updated:** 2026-03-03

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [The 6-Layer Signal Pipeline](#3-the-6-layer-signal-pipeline)
   - 3.1 [Layer 0: Regime Detection](#31-layer-0-regime-detection--is-the-market-safe-to-trade)
   - 3.2 [Layer 1: Trend Filter](#32-layer-1-trend-filter--which-direction-is-the-market-moving)
   - 3.3 [Layer 2: Zone Identification (Fibonacci)](#33-layer-2-zone-identification--where-should-we-enter)
   - 3.4 [Layer 3: Confluence Scoring](#34-layer-3-confluence-scoring--how-strong-is-this-setup)
   - 3.5 [Layer 4: Trigger Detection](#35-layer-4-trigger-detection--is-it-the-right-moment)
   - 3.6 [Layer 5: Risk Management](#36-layer-5-risk-management--how-much-can-we-risk)
4. [Post-Pipeline Filters](#4-post-pipeline-filters)
5. [AI Quality Gate (Claude)](#5-ai-quality-gate-claude)
6. [What Triggers a BUY — Complete Checklist](#6-what-triggers-a-buy--complete-checklist)
7. [What Triggers a SELL — Complete Checklist](#7-what-triggers-a-sell--complete-checklist)
8. [Stop Losses Explained](#8-stop-losses-explained)
   - 8.1 [What Is a Stop Loss?](#81-what-is-a-stop-loss)
   - 8.2 [How SignalForge Calculates Stop Losses](#82-how-signalforge-calculates-stop-losses)
   - 8.3 [When Stop Losses Trigger](#83-when-stop-losses-trigger)
   - 8.4 [Why a Stop Loss Can Cause a Bigger Loss Than Expected](#84-why-a-stop-loss-can-cause-a-bigger-loss-than-expected)
9. [Take Profit Logic](#9-take-profit-logic)
10. [Trailing Stops](#10-trailing-stops)
11. [Break-Even Stop](#11-break-even-stop)
12. [Time-Based Stop](#12-time-based-stop)
13. [Position Sizing — How Much to Buy](#13-position-sizing--how-much-to-buy)
14. [Portfolio-Level Risk Protection](#14-portfolio-level-risk-protection)
15. [The Fibonacci System — Deep Dive](#15-the-fibonacci-system--deep-dive)
16. [All 14 Confluence Factors Explained](#16-all-14-confluence-factors-explained)
17. [The 5 Entry Triggers Explained](#17-the-5-entry-triggers-explained)
18. [The AI Advisor and Self-Learning Loop](#18-the-ai-advisor-and-self-learning-loop)
19. [Why the System May Be Selling at a Loss](#19-why-the-system-may-be-selling-at-a-loss)
20. [Recommendations for Better Performance](#20-recommendations-for-better-performance)
21. [Strategy Configuration Reference](#21-strategy-configuration-reference)
22. [Complete Signal Lifecycle Diagram](#22-complete-signal-lifecycle-diagram)

---

## 1. Executive Summary

SignalForge is a **fully automated crypto day trading system** that uses a 6-layer signal
pipeline, 14 technical indicators, and AI-powered quality control (Claude) to generate and
execute trades.

**The core philosophy:**
- The system identifies the market direction (trend), finds optimal entry zones using
  **Fibonacci retracement** levels, confirms the setup with multiple technical indicators
  (confluence), waits for a precise entry trigger, calculates risk/reward, and then asks
  Claude AI for a final quality check before executing.

**The problem you're experiencing (selling at a loss) can happen because:**
1. Stop losses are hit before take-profit is reached — this is normal for any system, but
   the *frequency* suggests parameter tuning issues or unfavorable market conditions
2. Time-based stops force-close positions that haven't reached their target
3. The AI may be approving trades that look technically sound but are in poor market
   conditions
4. Several powerful protection features (trailing stops, break-even stops, CPPI, drawdown
   breaker) are **disabled by default** and must be explicitly enabled

---

## 2. System Architecture Overview

The system runs as a series of **periodic background tasks** (Celery Beat):

```
Every 60 seconds:   Ingest candle data from Binance
Every 5 minutes:    Run the signal pipeline (generate BUY/SELL signals)
Every 30 seconds:   Execute pending signals (place orders)
Every 15 seconds:   Poll order status (check if orders filled)
Every 60 seconds:   Manage open positions (check SL/TP/trailing/time stops)
```

**Data flow:**

```
Market Data (Binance)
    │
    ▼
Candle Storage (TimescaleDB)
    │
    ▼
┌──────────────────────────────────┐
│     6-LAYER SIGNAL PIPELINE       │
│                                   │
│  L0: Is the market safe?          │ ─── CHAOTIC? → NO TRADE
│  L1: What direction?              │ ─── UNCLEAR? → NO TRADE
│  L2: Where to enter? (Fibonacci)  │ ─── NO ZONE? → NO TRADE
│  L3: How strong? (14 indicators)  │ ─── WEAK?    → NO TRADE
│  L4: Right moment? (5 triggers)   │ ─── NO TRIGGER? → NO TRADE
│  L5: Risk acceptable?             │ ─── BAD R:R? → NO TRADE
└──────────────┬───────────────────┘
               │
               ▼
     Post-Pipeline Filters
  (feedback, positions, MTF)
               │
               ▼
     AI Quality Gate (Claude)
  ─── REJECT? → NO TRADE ───
               │
               ▼
     Order Execution (Paper/Live)
               │
               ▼
     Position Management
  (SL, TP, trailing, time stop)
               │
               ▼
     Trade Closed → PnL recorded
```

**Key principle:** Every layer is a gate. A trade only happens when ALL gates pass. This
means the system is conservative by design — it will miss opportunities rather than take
bad trades. If the market doesn't clearly match the strategy parameters, zero trades is
the correct outcome.

---

## 3. The 6-Layer Signal Pipeline

### 3.1 Layer 0: Regime Detection — "Is the market safe to trade?"

**What it does:** Classifies the current market into one of four states before allowing any
trading activity.

**How it works:**
- Calculates **ADX (Average Directional Index)** — measures trend strength (0-100)
- Calculates **ATR (Average True Range) percentile** — measures how volatile current
  conditions are compared to the last 100 bars

**Market classifications:**

| Market State | Condition | What Happens |
|-------------|-----------|--------------|
| **TRENDING** | ADX > 25 | Trading allowed — market has clear direction |
| **RANGING** | ADX < 20 | Trading allowed — market is sideways/consolidating |
| **TRANSITIONING** | ADX 20-25 | Trading allowed — market may be changing direction |
| **CHAOTIC** | ATR > 90th percentile AND ATR > 3% of price | **ALL TRADING BLOCKED** |

**Why CHAOTIC blocks trading:** When the market is extremely volatile (big, erratic price
swings), technical analysis becomes unreliable. The system protects you by refusing to
trade until volatility subsides.

**Optional enhancement:** An HMM (Hidden Markov Model) can provide a secondary opinion, but
the rule-based system always has final authority.

**File:** `backend/app/engine/layers/regime.py`

---

### 3.2 Layer 1: Trend Filter — "Which direction is the market moving?"

**What it does:** Determines if the market has a clear bullish (upward) or bearish (downward)
trend using three Exponential Moving Averages (EMAs).

**How it works:**

For a **BULLISH** (upward) trend, ALL conditions must be true:
1. EMA(50) > EMA(100) > EMA(200) — short-term average above medium above long-term
2. The slope of the 200-period EMA over the last 20 bars must be positive (> 0.001)

For a **BEARISH** (downward) trend, the reverse:
1. EMA(50) < EMA(100) < EMA(200)
2. The slope of the 200-period EMA must be negative (< -0.001)

If neither condition is met → **UNDETERMINED** → **NO TRADE**

**What this means in practice:** The system only trades when there is a clear, established
trend. If the moving averages are tangled or the trend is flat, it sits on the sidelines.
This requires at least 200 candles of historical data.

**Also checks:** Whether the current price is above or below VWAP (Volume Weighted Average
Price) for additional confirmation.

**File:** `backend/app/engine/layers/trend.py`

---

### 3.3 Layer 2: Zone Identification — "Where should we enter?"

**What it does:** Finds the optimal price levels to enter a trade. This is where
**Fibonacci retracement** plays its central role.

**Method 1 — Fibonacci Golden Pocket (Primary):**

The system finds the recent swing high (highest price) and swing low (lowest price) in the
candle data, then calculates **Fibonacci retracement levels**:

```
                    Swing High ──── 100.0% (1.000)
                         │
                         │ ──────── 78.6% (0.786)
                         │
                         │ ──────── 61.8% (0.618)  ┐
                         │                           │ ← GOLDEN POCKET
                         │ ──────── 50.0% (0.500)   │   (Entry Zone)
                         │                           │
                         │ ──────── 38.2% (0.382)  ┘
                         │
                         │ ──────── 23.6% (0.236)
                         │
                    Swing Low ───── 0.0%   (0.000)
```

The **Golden Pocket** (38.2% - 61.8%) is the primary entry zone. This is the area where
price is most likely to find support (in an uptrend) or resistance (in a downtrend) before
continuing in the trend direction.

**For a BULLISH trend:** Fibonacci levels are calculated from swing low up to swing high. The
system looks for price to pull back INTO the golden pocket before bouncing upward.

**For a BEARISH trend:** Fibonacci levels are calculated from swing high down to swing low.
The system looks for price to rally INTO the golden pocket before falling further.

**Method 2 — VWAP Deviation Bands (Secondary):**

The system also creates two zones based on VWAP (Volume Weighted Average Price):
- **1-sigma zone:** VWAP ± 1 standard deviation (moderate significance)
- **2-sigma zone:** VWAP ± 2 standard deviations (high significance)

**If no zones are found → NO TRADE**

Typically, 3 zones are generated (1 Fibonacci + 2 VWAP). Each zone is then evaluated
through the remaining pipeline layers, and the best-scoring one wins.

**File:** `backend/app/engine/layers/zones.py`

---

### 3.4 Layer 3: Confluence Scoring — "How strong is this setup?"

**What it does:** Scores each entry zone from 0 to 100 using **14 different technical
indicators**. The higher the score, the more indicators agree that this is a good trade.

This is the heart of the system — it doesn't rely on any single indicator but combines
multiple independent signals to build conviction.

**The 14 factors and their weights:**

| # | Factor | Weight | What It Checks |
|---|--------|--------|----------------|
| 1 | Fibonacci Alignment | **12** | Is this a Fibonacci zone? (highest weight) |
| 2 | Support/Resistance Overlap | **12** | Have 3+ candles touched this zone? (highest weight) |
| 3 | Multi-TF Fibonacci | **10** | Is the zone strong (>= 0.7 strength)? |
| 4 | VWAP Proximity | **8** | Is VWAP within this zone? |
| 5 | Volume Node | **8** | Is volume 20%+ above average when price is in this zone? |
| 6 | RSI Confirmation | **8** | Is RSI(14) between 35-65? (not overbought or oversold) |
| 7 | MACD Momentum | **8** | Is the MACD histogram positive/rising (BUY) or negative/falling (SELL)? |
| 8 | Candlestick Pattern | **7** | Hammer, bullish engulfing, or bearish engulfing detected? |
| 9 | Stochastic Cross | **5** | Has %K crossed %D in the trend direction? |
| 10 | Bollinger Position | **5** | Price at lower 30% of bands (BUY) or upper 30% (SELL)? |
| 11 | Ichimoku Cloud | **5** | Price above cloud (BUY) or below cloud (SELL)? |
| 12 | OBV Trend | **5** | On-Balance Volume confirms accumulation/distribution? |
| 13 | Williams %R | **4** | Room to run in the trade direction? |
| 14 | CCI Momentum | **3** | Commodity Channel Index supports the direction? |

**Total possible: 100 points**

**Minimum required: 50 points** (configurable via `min_confluence`)

Each factor is binary — it either scores its full weight or zero. The total is a simple sum
of all factors that pass. A score of 50 means at least 5-7 different indicators agree.

**If the score is below 50 → this zone is skipped** (another zone may still qualify)

See [Section 16](#16-all-14-confluence-factors-explained) for detailed explanations of each
factor.

**File:** `backend/app/engine/layers/confluence.py`

---

### 3.5 Layer 4: Trigger Detection — "Is it the right moment?"

**What it does:** Even after finding a strong zone with high confluence, the system waits for
a specific **timing signal** before entering. This prevents entering too early.

**5 independent triggers are checked:**

| Trigger | What It Looks For |
|---------|-------------------|
| **A. MACD Crossover** | MACD line crosses the signal line in the trend direction |
| **B. RSI Midline Cross** | RSI crosses above 50 (BUY) or below 50 (SELL) |
| **C. Stochastic Exit Extreme** | Stochastic %K exits oversold (<20→>20 for BUY) or overbought (>80→<80 for SELL) |
| **D. Engulfing Candle** | A bullish or bearish engulfing candlestick pattern forms |
| **E. Zone Reclaim** | Price moves back into the entry zone from outside it |

**Minimum required: 2 out of 5** (configurable via `min_trigger_count`)

These triggers are checked within a **1-candle lookback window** (configurable), meaning
they must have fired very recently.

**If fewer than 2 triggers fire → this zone is skipped**

See [Section 17](#17-the-5-entry-triggers-explained) for detailed explanations.

**File:** `backend/app/engine/layers/triggers.py`

---

### 3.6 Layer 5: Risk Management — "How much can we risk?"

**What it does:** Calculates the stop loss, take profit, position size, and risk/reward
ratio. Rejects the trade if the risk/reward is unfavorable.

**Stop Loss calculation:**
```
Stop Loss Distance = ATR(14) × atr_sl_multiplier (default 2.0)

BUY:  Stop Loss = Entry Price - Stop Loss Distance
SELL: Stop Loss = Entry Price + Stop Loss Distance
```

**Take Profit calculation (using Fibonacci extensions):**
```
TP1 = Entry Price ± (Stop Loss Distance × 1.618)    → R:R = 1.618:1
TP2 = Entry Price ± (Stop Loss Distance × 2.618)    → R:R = 2.618:1
```

**Position Size calculation:**
```
Score Multiplier = Confluence Score / 100 (e.g., 70 → 0.7)
Risk Amount = Account Equity × 2% × Score Multiplier
Position Size = Risk Amount / Stop Loss Distance
```

**Risk/Reward check:**
```
If R:R < min_risk_reward (default 1.5) → REJECTED
```

Since the Fibonacci extension naturally produces a 1.618 R:R, the default minimum of 1.5
will almost always pass. But if market conditions compress the take-profit zone or expand
the stop-loss distance, the signal may be rejected.

**File:** `backend/app/engine/layers/risk.py`

---

## 4. Post-Pipeline Filters

After the pipeline produces a BUY or SELL signal, these additional checks are applied:

1. **Feedback Filter** — The self-learning loop may have learned rules like "avoid BTC in
   RANGING markets" based on past losing trades. These rules can block signals or require
   a higher confluence threshold.

2. **Position Filter** — Only ONE open position per symbol is allowed. A BUY is blocked if
   there's already an open BUY for that symbol. A SELL is blocked if there's no BUY to
   close.

3. **Multi-Timeframe Alignment** — For 1-hour signals, the system checks the 4-hour trend.
   For 4-hour signals, it checks the daily trend. If the higher timeframe explicitly
   contradicts (e.g., BUY signal but 4h trend is BEARISH), the signal is **blocked**.

4. **Deduplication** — Prevents the same signal from being created twice.

5. **CPPI Scaling** — If enabled, reduces position size based on how close equity is to the
   protection floor (see [Section 14](#14-portfolio-level-risk-protection)).

**File:** `backend/app/tasks/run_pipeline.py`

---

## 5. AI Quality Gate (Claude)

Every signal must pass Claude AI's quality evaluation before execution. **If AI is
unavailable, the signal is automatically REJECTED — the system does not trade without AI
oversight.**

**What Claude receives:**
- All 14 confluence factor details (which passed, which failed)
- The last 5 candles of price data
- Signal direction, entry, stop loss, take profit
- Market regime and trend information

**What Claude returns:**

| Recommendation | Quality Score | Effect |
|---------------|---------------|--------|
| `strong_confirm` | >= 75 | Trade proceeds, size may increase (up to 1.5x) |
| `confirm` | 50-74 | Trade proceeds normally |
| `caution` | 30-49 | Trade proceeds with reduced size |
| **`reject`** | < 30 | **Trade is killed — no execution** |

**Additionally:** Claude performs a **multi-timeframe analysis** where it:
- Analyzes 4h and 1d candle data alongside the primary timeframe
- Assesses timeframe alignment (aligned / mixed / conflicting)
- Provides a multi-timeframe confidence score (0-100)

**File:** `backend/app/advisor/signal_quality.py`, `backend/app/advisor/multi_tf_analyzer.py`

---

## 6. What Triggers a BUY — Complete Checklist

For a BUY trade to execute, **every single one** of these conditions must pass:

| # | Gate | Condition | Configured Default |
|---|------|-----------|-------------------|
| 1 | Market Regime | Not CHAOTIC | ADX + ATR based |
| 2 | Trend Direction | BULLISH (EMA 50 > 100 > 200, positive slope) | Slope > 0.001 |
| 3 | Entry Zone Found | At least 1 Fibonacci or VWAP zone exists | — |
| 4 | Confluence Score | Score >= minimum | >= 50/100 |
| 5 | Entry Triggers | >= minimum triggers fired recently | >= 2 of 5 |
| 6 | Risk/Reward | R:R ratio >= minimum | >= 1.5 |
| 7 | Feedback Filter | No "avoid" rule matches from self-learning | — |
| 8 | Position Filter | No existing open BUY for this symbol | 1 position per symbol |
| 9 | MTF Alignment | Higher timeframe not BEARISH | — |
| 10 | AI Quality | Claude does not reject | Score >= 30 |
| 11 | Daily Loss | Today's losses < maximum | < 6% of equity |
| 12 | Open Positions | Below maximum | < 5 positions |
| 13 | Per-Trade Risk | Risk amount within limit | < 2% of equity |
| 14 | Drawdown Breaker | Not at Level 2+ (if enabled) | < 75% of limit consumed |
| 15 | Correlation | Position size after penalty > 0 (if enabled) | — |

**If ANY gate fails, the trade does not happen.**

---

## 7. What Triggers a SELL — Complete Checklist

A position can be closed (SELL) by any of these mechanisms:

| # | Exit Type | Trigger | When |
|---|-----------|---------|------|
| 1 | **Stop Loss** | Price drops to/below stop loss level | Checked every 60s |
| 2 | **Take Profit** | Price rises to/above take profit level | Checked every 60s |
| 3 | **Trailing Stop** | Price drops to/below the trailed stop | Checked every 60s (if enabled) |
| 4 | **Break-Even Stop** | Price returns to entry after having been profitable | After SL moved to entry |
| 5 | **Time Stop** | Position held too long | After max_hold_hours (default 24h) |
| 6 | **Sell Signal** | Pipeline generates a SELL signal for this symbol | Every 5 min pipeline run |
| 7 | **Drawdown Breaker** | Portfolio drawdown exceeds emergency limit | Level 3: force-close ALL |
| 8 | **Manual Close** | You close the position via the UI | Anytime |

**The Sell Signal (item 6) requires passing many of the same gates as a BUY, but in reverse:**
- Trend must be BEARISH
- Fibonacci zone must exist for a short entry
- Confluence score must be >= 50
- At least 2 triggers must fire
- AI must approve
- There must be an existing open BUY position to close

---

## 8. Stop Losses Explained

### 8.1 What Is a Stop Loss?

A **stop loss** is a pre-set price level where a losing trade is automatically closed to
prevent further losses. It's your safety net.

**Example:** You buy BTC at $60,000. You set a stop loss at $58,800. If BTC drops to
$58,800, the system automatically sells to limit your loss to $1,200 per unit.

Without a stop loss, a trade could lose your entire position value if the market moves
against you indefinitely.

### 8.2 How SignalForge Calculates Stop Losses

SignalForge uses **ATR-based stop losses**, which means the stop distance adapts to current
market volatility:

```
ATR = Average True Range over 14 periods
Stop Distance = ATR × 2.0 (the atr_sl_multiplier)

BUY trade:  Stop Loss = Entry Price - Stop Distance
SELL trade: Stop Loss = Entry Price + Stop Distance
```

**Why ATR-based?** A fixed dollar amount (e.g., "always stop $100 below entry") doesn't
account for how volatile the market is. ATR measures the average price range per candle.
A 2x ATR stop means "place the stop about 2 average candle ranges away from entry."

**Example with real numbers:**
- BTC price: $60,000
- ATR(14): $600 (average candle range is $600)
- Stop Distance: $600 × 2.0 = $1,200
- Stop Loss: $60,000 - $1,200 = **$58,800**
- This means you're risking $1,200 per unit on this trade

### 8.3 When Stop Losses Trigger

Stop losses are checked by the `manage_positions` task which runs **every ~60 seconds**.
It fetches the latest candle close price and compares:

- **BUY position:** Closes if `current_price <= stop_loss`
- **SELL position:** Closes if `current_price >= stop_loss`

### 8.4 Why a Stop Loss Can Cause a Bigger Loss Than Expected

**Important limitation: Stop losses in SignalForge are NOT real-time.** They are checked
periodically (every ~60 seconds) using the latest candle close price. This means:

1. **Gap risk:** If the price drops sharply between checks (e.g., a flash crash), the
   position closes at the current price, which may be significantly below the stop loss.
   Example: Stop at $58,800, but price drops to $57,500 between checks → loss is $2,500
   instead of $1,200.

2. **Candle-close vs. intraday:** The check uses the candle's close price, not the lowest
   price during the candle. Price could have dipped below your stop during the candle but
   recovered by close — or vice versa.

3. **Paper trading slippage:** The paper adapter applies 0.1% slippage on all fills,
   slightly worsening your exit price.

---

## 9. Take Profit Logic

Take profits use **Fibonacci extension ratios** applied to the risk distance:

```
Risk Distance = ATR × 2.0 (same as stop loss distance)

TP1 = Entry + Risk Distance × 1.618    (R:R = 1.618:1)
TP2 = Entry + Risk Distance × 2.618    (R:R = 2.618:1)
```

**Currently, only TP1 is used** as the active take-profit order. TP2 is calculated and
stored but not actively traded against.

**Example:**
- Entry: $60,000
- Risk Distance: $1,200
- TP1: $60,000 + ($1,200 × 1.618) = **$61,942** → Profit: $1,942 (R:R = 1.62:1)
- TP2: $60,000 + ($1,200 × 2.618) = **$63,142** → Profit: $3,142 (R:R = 2.62:1)

**The 1.618 Fibonacci ratio** is the golden ratio — this means for every $1 you risk, you
target approximately $1.62 in profit.

---

## 10. Trailing Stops

### What Is a Trailing Stop?

A **trailing stop** is a stop loss that follows the price as it moves in your favor. It
"trails" behind the price by a fixed distance. When the price reverses, the stop stays
where it is — it never moves backward. This locks in profits as the trade goes well.

### How SignalForge Implements Trailing Stops

**Status: IMPLEMENTED but DISABLED by default** (`trailing_stop_enabled = False`)

When enabled, the trailing stop is ATR-based:

```
Trail Distance = ATR(14) × atr_trail_multiplier (default 2.0)

BUY position:
  New Stop = Current Price - Trail Distance
  → Only applied if New Stop > Current Stop Loss (ratchets UP only)

SELL position:
  New Stop = Current Price + Trail Distance
  → Only applied if New Stop < Current Stop Loss (ratchets DOWN only)
```

**Example:**
- You buy BTC at $60,000, stop loss at $58,800
- Price rises to $62,000 → Trail stop moves to $62,000 - $1,200 = **$60,800**
- Price rises to $63,000 → Trail stop moves to $63,000 - $1,200 = **$61,800**
- Price drops to $61,800 → **Trail stop triggers, profit locked at $1,800**
- Without trailing: stop would still be at $58,800, potentially losing the entire move

### To Enable

Set in your strategy config:
```json
{
  "trailing_stop_enabled": true,
  "atr_trail_multiplier": 2.0
}
```

**File:** `backend/app/tasks/manage_positions.py` (lines 213-256)

---

## 11. Break-Even Stop

### What Is a Break-Even Stop?

A **break-even stop** moves your stop loss to your entry price once the trade reaches a
certain profit threshold. This means that once activated, the worst-case scenario is
breaking even (no profit, no loss) instead of a loss.

### How SignalForge Implements Break-Even Stops

**Status: IMPLEMENTED but DISABLED by default** (`break_even_enabled = False`)

When enabled:

```
Initial Risk = |Entry Price - Original Stop Loss|
Current Profit = Current Price - Entry Price (for BUY)

If Current Profit >= Initial Risk × break_even_r_multiple (default 1.0):
    → Move Stop Loss to Entry Price
    → Mark break_even_applied = True
```

**Example:**
- Entry: $60,000, Stop: $58,800, Initial Risk: $1,200
- At 1.0 R-multiple (default), break-even activates when profit >= $1,200
- Price reaches $61,200 → Stop Loss moves from $58,800 to **$60,000**
- If price then drops back to $60,000 → trade closes at break-even (zero loss)

**Break-even runs BEFORE trailing stops**, so the sequence is:
1. Check if break-even should activate
2. Then check if trailing stop should improve the stop further

### To Enable

```json
{
  "break_even_enabled": true,
  "break_even_r_multiple": 1.0
}
```

**File:** `backend/app/tasks/manage_positions.py` (lines 185-208)

---

## 12. Time-Based Stop

### What Is a Time-Based Stop?

A **time-based stop** force-closes positions that have been open too long. This prevents
capital from being tied up in stale, directionless trades.

### How SignalForge Implements Time Stops

**Always active.** Default `max_hold_hours = 24`.

Three tiers:

| Condition | Action |
|-----------|--------|
| Held `max_hold_hours` (24h) AND PnL% <= 1.0% | **CLOSE** — trade isn't working |
| Held `max_hold_hours × 1.5` (36h) AND profitable | **CLOSE** — even winning trades have a limit |
| Held `max_hold_hours × 2` (48h) | **CLOSE UNCONDITIONALLY** — hard maximum |

**Why this matters for losses:** If a trade is slightly underwater (e.g., -0.5%) after 24
hours, the time stop closes it even though the stop loss hasn't been hit. This is a
**deliberate design choice** — a trade that hasn't moved in your favor after a full day is
unlikely to do so, and the capital is better used elsewhere.

**File:** `backend/app/tasks/manage_positions.py` (lines 142-180)

---

## 13. Position Sizing — How Much to Buy

Position sizing determines **how many units** to buy/sell. It's a multi-layer calculation:

### Base Calculation

```
Score Multiplier = Confluence Score / 100       (e.g., 70 → 0.7, range: 0.1-1.0)
Risk Amount = Equity × 2% × Score Multiplier    (e.g., $10,000 × 0.02 × 0.7 = $140)
Position Size = Risk Amount / Stop Distance      (e.g., $140 / $1,200 = 0.1167 BTC)
```

Higher confluence = larger position. A 50-score trade risks 1% of equity; a 100-score trade
risks the full 2%.

### Optional Scaling Modifiers (applied multiplicatively)

| Modifier | Default | Effect |
|----------|---------|--------|
| **Kelly Criterion** | Disabled | Replaces 2% risk with a statistically optimal fraction based on win rate |
| **CPPI Exposure** | Disabled | Reduces size as equity approaches the protection floor |
| **AI Quality Factor** | Active | Claude can scale size 0.0x - 1.5x based on conviction |
| **Drawdown Breaker** | Disabled | Level 1: halves size. Level 2+: blocks trading |
| **Correlation Penalty** | Disabled | Reduces size if trading correlated assets (e.g., BTC + ETH) |

**These stack multiplicatively.** In the worst case, a position could be scaled down to a
tiny fraction of the base size.

---

## 14. Portfolio-Level Risk Protection

### Pre-Trade Checks (Always Active)

Before any trade, three hard limits are checked:

| Check | Limit | Action if Exceeded |
|-------|-------|--------------------|
| Daily loss | 6% of equity | Block all new trades for the day |
| Open positions | 5 maximum | Block new trades until one closes |
| Per-trade risk | 2% of equity | Reject the signal |

### Drawdown Circuit Breaker (Disabled by Default)

A graduated system that activates as portfolio drawdown increases:

| Level | Drawdown | Action |
|-------|----------|--------|
| 0 — Normal | < 7.5% | Full trading |
| 1 — Warning | 7.5% - 11.25% | **Reduce all new position sizes by 50%** |
| 2 — Halt | 11.25% - 15% | **Block ALL new trades** |
| 3 — Emergency | > 15% | **Force-close ALL open positions immediately** |

### CPPI — Constant Proportion Portfolio Insurance (Disabled by Default)

A dynamic exposure system that automatically reduces your market exposure as losses mount:

```
Floor = max(Previous Floor, Peak Equity × (1 - 15%))
Cushion = Equity - Floor
Exposure = min(1.0, 3.0 × Cushion / Equity)
Position Size × = Exposure
```

The floor **ratchets up** — once you make gains, the floor rises to protect them. If equity
drops toward the floor, exposure approaches zero.

### Correlation Monitor (Disabled by Default)

Monitors pairwise correlation between symbols. If BTC and ETH are highly correlated (>0.7),
taking positions in both is essentially doubling your risk. The system can automatically
reduce position sizes for correlated assets.

---

## 15. The Fibonacci System — Deep Dive

### What Is Fibonacci in Trading?

Fibonacci retracement is based on the mathematical Fibonacci sequence (0, 1, 1, 2, 3, 5,
8, 13, 21...) where each number is the sum of the two before it. The key ratios derived
from this sequence — particularly **0.382 (38.2%)**, **0.500 (50%)**, and **0.618 (61.8%)**
— appear frequently in financial markets as natural support and resistance levels.

**The core idea:** After a significant price move (up or down), the price tends to retrace
(pull back) to one of these Fibonacci levels before continuing in the original direction.

### How Fibonacci Is Used in SignalForge

Fibonacci is **deeply integrated** at three critical points in the system:

#### 1. Entry Zone Definition (Layer 2)

The system identifies the recent swing high and swing low, then creates a **golden pocket
zone** between the 38.2% and 61.8% retracement levels:

```
Example — BULLISH trend:
  Swing Low:  $55,000
  Swing High: $65,000
  Price Range: $10,000

  Fibonacci Levels:
    0.0%  = $55,000 (swing low)
    23.6% = $57,360
    38.2% = $58,820  ← Golden Pocket bottom
    50.0% = $60,000
    61.8% = $61,180  ← Golden Pocket top
    78.6% = $62,860
    100%  = $65,000 (swing high)

  Golden Pocket Zone: $58,820 - $61,180

  The system waits for price to pull back INTO this zone ($58,820 - $61,180)
  before looking for a buy entry. The theory: this is where buyers are most
  likely to step in and push price back toward the highs.
```

#### 2. Confluence Scoring (Layer 3)

Two of the 14 confluence factors directly reward Fibonacci zones:
- **`fibonacci_alignment`** (weight 12/100) — fires if the zone is a Fibonacci zone
- **`multi_tf_fib`** (weight 10/100) — fires if the zone has high strength (>= 0.7)

This means a Fibonacci zone starts with a **22-point head start** in the confluence score
compared to a non-Fibonacci zone, making it significantly more likely to reach the
50-point minimum.

#### 3. Take Profit Targets (Layer 5)

Take profits use **Fibonacci extension ratios**:
- TP1 at **1.618x** the risk distance (the golden ratio)
- TP2 at **2.618x** the risk distance

This creates a mathematically harmonious system where entry, stop, and target are all
based on Fibonacci relationships.

### Is Fibonacci Reasoning Visible in Trade Decisions?

**Current state: No.** While Fibonacci is used to define entry zones and is a top-weighted
confluence factor, the system does **not** surface Fibonacci-specific reasoning in the trade
output. You cannot see:
- Which swing high/low were used
- The exact Fibonacci levels calculated
- Whether the entry was specifically at the 38.2%, 50%, or 61.8% level
- How much of the confluence score came from Fibonacci factors

**Recommendation:** Add Fibonacci-specific metadata to the signal output (see
[Section 20.6](#206-make-fibonacci-reasoning-visible)).

### Fibonacci Implementation Details

**File:** `backend/app/engine/indicators.py` (lines 109-120)

```python
def calculate_fib_levels(swing_low: float, swing_high: float) -> dict:
    diff = swing_high - swing_low
    return {
        "0.0":   swing_low,
        "0.236": swing_low + diff * 0.236,
        "0.382": swing_low + diff * 0.382,
        "0.5":   swing_low + diff * 0.5,
        "0.618": swing_low + diff * 0.618,
        "0.786": swing_low + diff * 0.786,
        "1.0":   swing_high,
    }
```

**File:** `backend/app/engine/layers/zones.py` (Fibonacci golden pocket zone creation)

---

## 16. All 14 Confluence Factors Explained

Each factor checks a specific technical condition. If it passes, its weight is added to the
total score.

### Factor 1: Fibonacci Alignment (Weight: 12)
**What:** Is the entry zone a Fibonacci zone?
**Condition:** Zone type starts with "fibonacci"
**Why:** Fibonacci zones have the highest historical probability of producing reversals.

### Factor 2: Support/Resistance Overlap (Weight: 12)
**What:** Has this price zone acted as support or resistance recently?
**Condition:** 3 or more candles (out of the last 20) touched the zone boundaries
**Why:** Zones tested multiple times are more significant — institutions place orders there.

### Factor 3: Multi-Timeframe Fibonacci (Weight: 10)
**What:** Is this zone significant across multiple timeframes?
**Condition:** Zone strength >= 0.7
**Why:** Fibonacci zones that align across timeframes are much stronger.

### Factor 4: VWAP Proximity (Weight: 8)
**What:** Is VWAP (Volume Weighted Average Price) within this zone?
**Condition:** VWAP value falls between zone.lower and zone.upper
**Why:** VWAP is a key institutional benchmark — overlap with Fibonacci adds significance.

### Factor 5: Volume Node (Weight: 8)
**What:** Is there high volume activity in this zone?
**Condition:** Average volume when price was in this zone is > 120% of overall average
**Why:** High volume at a price level indicates strong institutional interest.

### Factor 6: RSI Confirmation (Weight: 8)
**What:** Is RSI in a healthy range (not overextended)?
**Condition:** RSI(14) between 35 and 65
**Why:** An RSI between 35-65 means there's room for the trade to move. An RSI above 70
(overbought) or below 30 (oversold) suggests the move may already be exhausted.

### Factor 7: MACD Momentum (Weight: 8)
**What:** Is the MACD histogram supporting the trade direction?
**Condition:** BUY: histogram > 0 or rising. SELL: histogram < 0 or falling.
**Why:** MACD measures momentum — a positive/rising histogram confirms buying pressure.

### Factor 8: Candlestick Pattern (Weight: 7)
**What:** Has a recognizable reversal pattern formed at the zone?
**Condition:** Detects hammer (small body, long lower wick), bullish engulfing (current
candle body completely engulfs previous), or bearish engulfing
**Why:** Candlestick patterns at key zones are powerful reversal signals.

### Factor 9: Stochastic Cross (Weight: 5)
**What:** Has the Stochastic oscillator given a directional signal?
**Condition:** BUY: %K crosses above %D or %K rising while below 50.
SELL: %K crosses below %D or %K falling while above 50.
**Why:** Stochastic measures overbought/oversold conditions with a momentum twist.

### Factor 10: Bollinger Position (Weight: 5)
**What:** Is price at an extreme within the Bollinger Bands?
**Condition:** BUY: price in lower 30% of bands (bb_pct < 0.3).
SELL: price in upper 30% of bands (bb_pct > 0.7).
**Why:** Price at Bollinger extremes tends to revert toward the mean.

### Factor 11: Ichimoku Cloud (Weight: 5)
**What:** Is price above or below the Ichimoku cloud?
**Condition:** BUY: price > cloud top (senkou_a or senkou_b, whichever is higher).
SELL: price < cloud bottom.
**Why:** The Ichimoku cloud provides dynamic support/resistance — being on the right side
confirms trend direction.

### Factor 12: OBV Trend (Weight: 5)
**What:** Is On-Balance Volume (OBV) confirming accumulation or distribution?
**Condition:** BUY: OBV 20-bar moving average slope is positive.
SELL: slope is negative.
**Why:** Rising OBV in an uptrend confirms that volume supports the move (institutional
buying). Divergence warns of weakness.

### Factor 13: Williams %R (Weight: 4)
**What:** Does the trade have room to run?
**Condition:** BUY: Williams %R < -30 (not overbought).
SELL: Williams %R > -70 (not oversold).
**Why:** Similar to RSI but checks specifically that the move isn't exhausted.

### Factor 14: CCI Momentum (Weight: 3)
**What:** Does the Commodity Channel Index support the direction?
**Condition:** BUY: CCI > -50. SELL: CCI < 50.
**Why:** CCI measures deviation from the statistical mean — a mild positive reading for
a BUY confirms upward momentum without overextension.

---

## 17. The 5 Entry Triggers Explained

Entry triggers are **timing signals** — they confirm that the optimal moment to enter has
arrived.

### Trigger A: MACD Crossover
**What:** The MACD line crosses the signal line in the trend direction.
**For BUY:** MACD line crosses ABOVE the signal line (bullish crossover).
**For SELL:** MACD line crosses BELOW the signal line (bearish crossover).
**Why:** A MACD crossover is one of the most widely followed momentum signals. It indicates
a shift in short-term vs. medium-term momentum.

### Trigger B: RSI Midline Cross
**What:** RSI crosses the 50 level.
**For BUY:** RSI crosses above 50 (momentum turning bullish).
**For SELL:** RSI crosses below 50 (momentum turning bearish).
**Why:** RSI 50 is the dividing line between bullish and bearish territory. Crossing it
confirms a momentum shift.

### Trigger C: Stochastic Exit Extreme
**What:** The Stochastic %K exits an extreme zone.
**For BUY:** %K was below 20 (oversold) and rises above 20.
**For SELL:** %K was above 80 (overbought) and falls below 80.
**Why:** Exiting overbought/oversold zones indicates the short-term extreme is reversing.

### Trigger D: Engulfing Candle
**What:** A candlestick pattern where the current candle's body completely engulfs the
previous candle's body.
**For BUY:** Green candle engulfs previous red candle (bullish engulfing).
**For SELL:** Red candle engulfs previous green candle (bearish engulfing).
**Why:** Engulfing patterns represent a decisive shift in market control from sellers to
buyers (or vice versa).

### Trigger E: Zone Reclaim
**What:** Price moves back into the entry zone from outside it.
**For BUY:** Price crosses up from below the zone's lower boundary.
**For SELL:** Price crosses down from above the zone's upper boundary.
**Why:** A zone reclaim indicates the level is holding — price tested it, was repelled, and
is now bouncing back into the zone.

---

## 18. The AI Advisor and Self-Learning Loop

### How the AI Advisor Works

The AI Advisor is a Claude-powered system that provides multiple layers of intelligence:

#### 1. Signal Quality Evaluation (Real-time, per signal)
Every generated signal is sent to Claude for quality assessment. Claude sees the full
technical picture and returns a quality score + recommendation. Signals scoring below 30
are rejected.

#### 2. Multi-Timeframe Analysis (Real-time, per signal)
Claude analyzes the signal in the context of higher timeframes (4h, 1d) to ensure
alignment.

#### 3. Strategy Recommendation (On-demand)
When you create a new strategy, Claude analyzes recent market data and recommends optimal
parameters.

#### 4. Self-Learning Loop (Daily, automated via Celery Beat)

The self-learning loop runs overnight and consists of four stages:

| Time | Task | What It Does |
|------|------|--------------|
| 02:30 | **Pattern Analysis** | Claude analyzes the last 50 trades to find winning/losing patterns |
| 03:00 | **Risk Tuner** | Claude recommends risk parameter adjustments based on performance |
| 04:00 | **Feedback Synthesis** | Claude creates specific rules (e.g., "skip BTC in RANGING markets") |
| Continuous | **Feedback Filter** | Applies the synthesized rules to incoming signals |

**What the Risk Tuner can adjust:**
- `min_confluence` (10-100)
- `max_risk_per_trade` (0.5% - 10%)
- `max_daily_loss` (1% - 20%)
- `atr_sl_multiplier` (0.5 - 5.0)
- `min_risk_reward` (0.5 - 5.0, capped at 1.6)

**What the Risk Tuner CANNOT adjust:**
- `min_trigger_count` — how many triggers are required
- `trigger_lookback_candles` — how far back to look for triggers
- `ema_slope_threshold` — how steep the trend must be

**Safety:** Changes are limited to 20% per parameter per adjustment cycle. If Claude is
unavailable, no changes are made.

---

## 19. Why the System May Be Selling at a Loss

Based on the complete codebase analysis, here are the specific reasons your trades may be
closing at a loss:

### 19.1 Stop Losses Being Hit (Most Likely)

The stop loss is set at **2x ATR** below entry. In volatile crypto markets, this distance
can be insufficient:

- **Problem:** ATR measures *average* volatility. A sudden spike (news event, liquidation
  cascade) can blow through 2x ATR easily.
- **Problem:** The stop is checked every ~60 seconds using candle close, not real-time.
  Price can gap well below the stop between checks.
- **Mitigation:** Increase `atr_sl_multiplier` (e.g., 2.5 or 3.0) to give trades more room.

### 19.2 Time Stops Closing Losing Positions

The default `max_hold_hours = 24` means any position that hasn't profited 1%+ after 24
hours gets closed. If the trade is at -0.3% after 24 hours, the time stop closes it at a
loss — even though the stop loss hasn't been hit.

### 19.3 Key Protection Features Are DISABLED

Several features designed to protect winning trades and limit losses are **off by default**:

| Feature | Status | Impact When Disabled |
|---------|--------|----------------------|
| Trailing Stop | **DISABLED** | Winning trades can reverse all the way back to the stop loss |
| Break-Even Stop | **DISABLED** | Trades that were profitable can still close at a loss |
| Drawdown Breaker | **DISABLED** | No emergency protection if losses compound |
| CPPI | **DISABLED** | Position sizes don't decrease as losses mount |
| Kelly Criterion | **DISABLED** | Position sizes don't adapt to actual win rate |
| Correlation Monitor | **DISABLED** | Correlated positions (BTC + ETH) can double your risk |

### 19.4 Buying at Poor Entries

The system may be generating BUY signals that are technically valid (pass all gates) but
are in poor market conditions:

- **Confluence minimum of 50 may be too low** — this means only half the indicators need to
  agree. A threshold of 60-65 would require stronger setups.
- **Only 2 triggers required** — increasing to 3 would require more timing confirmation.
- **The Fibonacci zone is wide** — the golden pocket (38.2%-61.8%) covers a large price
  range. Entries at the top of this zone (near 61.8%) have less room for error.

### 19.5 The AI May Be Too Permissive

The AI quality gate rejects signals below score 30 — this is quite lenient. A "caution"
rating (30-49) still allows execution with reduced size. If the AI is approving marginal
trades, they may end up as losers.

### 19.6 Reversal Monitor Not Wired for Auto-Close

The **Reversal Monitor** (Layer 6) detects reversal signals for open positions (EMA crosses,
volume divergence, MACD divergence) and recommends actions (CLOSE, TIGHTEN_STOP,
PARTIAL_CLOSE, HOLD). However, while the code exists to monitor reversals, the automatic
close action based on reversal recommendations may not be fully wired into the
`manage_positions` flow, meaning reversal warnings could go unacted upon.

---

## 20. Recommendations for Better Performance

### 20.1 Enable Trailing Stops (HIGH PRIORITY)

**Why:** Without trailing stops, a trade that goes +$2,000 can reverse all the way back to
the stop loss at -$1,200. Trailing stops would have locked in profit.

```json
{
  "trailing_stop_enabled": true,
  "atr_trail_multiplier": 2.0
}
```

Consider a tighter trail multiplier (1.5) for scalping or a wider one (2.5) for swing
trades.

### 20.2 Enable Break-Even Stops (HIGH PRIORITY)

**Why:** Once a trade is 1R in profit ($1,200 in the example), the stop should move to
entry. This ensures profitable trades never turn into losses.

```json
{
  "break_even_enabled": true,
  "break_even_r_multiple": 1.0
}
```

### 20.3 Enable the Drawdown Circuit Breaker (HIGH PRIORITY)

**Why:** Without this, a losing streak has no emergency brake. The circuit breaker
progressively reduces exposure and ultimately halts trading before catastrophic losses.

```json
{
  "drawdown_breaker_enabled": true,
  "max_drawdown_pct": 0.15
}
```

### 20.4 Raise the Confluence Minimum (MEDIUM PRIORITY)

**Why:** A minimum of 50 means trades can execute with relatively weak confirmation. Raising
to 60-65 would filter out marginal setups.

```json
{
  "min_confluence": 60
}
```

### 20.5 Raise the Trigger Minimum (MEDIUM PRIORITY)

**Why:** Requiring only 2 of 5 triggers means the entry timing may not be precise. Raising
to 3 would require stronger confirmation.

```json
{
  "min_trigger_count": 3
}
```

### 20.6 Make Fibonacci Reasoning Visible (MEDIUM PRIORITY)

**Current issue:** You cannot see why the system chose a specific entry or how Fibonacci
influenced the decision.

**Recommendation:** Add the following metadata to each signal:
- Swing high and swing low used for Fibonacci calculation
- All 7 Fibonacci levels
- Which specific level price is nearest
- The exact golden pocket zone boundaries
- What percentage of the confluence score came from Fibonacci factors

This could be added as a `fibonacci_detail` JSON field on the Signal model.

### 20.7 Enable CPPI Portfolio Insurance (MEDIUM PRIORITY)

**Why:** CPPI dynamically reduces your exposure as losses mount and increases it as you win.
It's like an automatic risk throttle.

```json
{
  "cppi_enabled": true,
  "cppi_multiplier": 3.0,
  "cppi_max_drawdown_pct": 0.15
}
```

### 20.8 Enable Correlation Monitoring (LOW-MEDIUM PRIORITY)

**Why:** BTC and ETH (and many altcoins) are highly correlated. Holding BUY positions in
both is effectively doubling your exposure to crypto risk.

```json
{
  "correlation_monitor_enabled": true,
  "correlation_auto_reduce": true,
  "correlation_threshold": 0.7
}
```

### 20.9 Consider Wider Stop Losses (LOW PRIORITY)

**Why:** A 2x ATR stop may be too tight for crypto, which is inherently volatile. Widening
to 2.5x or 3x gives trades more room to breathe, at the cost of larger individual losses
but fewer stops being hit.

```json
{
  "atr_sl_multiplier": 2.5
}
```

**Trade-off:** Wider stops = fewer stop-outs but larger losses when they do trigger. The
position size automatically adjusts (smaller positions when stops are wider) to maintain
the same dollar risk per trade.

### 20.10 Add Partial Take Profit (NOT IMPLEMENTED)

**What:** Instead of a single TP, close 50% of the position at TP1 and let the remaining
50% run toward TP2 with a trailing stop.

**Why:** This locks in profit while keeping upside potential. Currently, the system
calculates TP2 but only uses TP1 — implementing partial take-profit would make better use
of both levels.

**Recommendation:** Implement a `partial_tp_enabled` feature that:
1. Closes 50% at TP1 (1.618x risk)
2. Moves stop to break-even for the remaining 50%
3. Uses a trailing stop to capture the move toward TP2 (2.618x risk)

### 20.11 Improve the Reversal Monitor Integration (NOT FULLY WIRED)

**What:** The Reversal Monitor exists and detects EMA crosses, volume divergence, and MACD
divergence on open positions. It produces recommendations (CLOSE_POSITION, TIGHTEN_STOP,
PARTIAL_CLOSE, HOLD).

**Current issue:** These recommendations may not be automatically acted upon in the
`manage_positions` task.

**Recommendation:** Wire the reversal monitor recommendations into automatic actions:
- `CLOSE_POSITION` → close immediately
- `TIGHTEN_STOP` → move stop to the tighter level suggested
- `PARTIAL_CLOSE` → close 50% of the position
- `HOLD` → no action

### 20.12 Add Real-Time Stop Loss Monitoring (FUTURE ENHANCEMENT)

**Current limitation:** Stops are checked on periodic intervals (~60s), not in real-time.
In fast-moving crypto markets, this can lead to significant slippage.

**Options:**
- Use exchange-side stop-loss orders (the exchange executes the stop regardless of your
  system's uptime)
- Implement a WebSocket price stream that checks stops on every tick
- Use OCO (One-Cancels-Other) orders that combine stop-loss and take-profit at the
  exchange level

### 20.13 Add Fibonacci Cluster Detection (FUTURE ENHANCEMENT)

**What:** Currently the system uses a single timeframe to calculate Fibonacci levels. A
**Fibonacci cluster** is where multiple timeframe's Fibonacci levels converge at the same
price — these are extremely strong zones.

**Example:** If the 1h golden pocket is at $59,000-$61,000, the 4h 38.2% level is at
$59,500, and the daily 50% level is at $60,200 — that cluster around $59,500-$60,200 is
an exceptional entry zone.

**Recommendation:** Calculate Fibonacci levels for 1h, 4h, and 1d, then identify clusters
where levels from different timeframes overlap within a small tolerance (e.g., 0.5% of
price).

### 20.14 Recommended Priority Configuration

If you want to start improving performance immediately, apply these settings to your
strategy config:

```json
{
  "trailing_stop_enabled": true,
  "atr_trail_multiplier": 2.0,
  "break_even_enabled": true,
  "break_even_r_multiple": 1.0,
  "drawdown_breaker_enabled": true,
  "max_drawdown_pct": 0.15,
  "min_confluence": 60,
  "min_trigger_count": 2,
  "atr_sl_multiplier": 2.5,
  "correlation_monitor_enabled": true,
  "correlation_auto_reduce": true,
  "cppi_enabled": true,
  "cppi_multiplier": 3.0,
  "cppi_max_drawdown_pct": 0.15
}
```

---

## 21. Strategy Configuration Reference

Complete list of all configurable parameters:

### Signal Pipeline Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `symbols` | ["BTC/USDT", "ETH/USDT", "SOL/USDT"] | Any CCXT pair | Trading pairs to scan |
| `timeframes` | ["1h"] | 1m, 5m, 15m, 1h, 4h, 1d | Candle timeframes |
| `account_equity` | 10000 | Any positive | Starting equity for sizing |
| `min_confluence` | 50 | 10-100 | Minimum confluence score |
| `min_trigger_count` | 2 | 1-5 | Minimum entry triggers required |
| `trigger_lookback_candles` | 1 | 1+ | Candles to look back for triggers |
| `ema_slope_threshold` | 0.001 | 0+ | EMA(200) slope for trend confirmation |

### Risk Management Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `max_risk_per_trade` | 0.02 (2%) | 0.005-0.10 | Max equity risked per trade |
| `max_daily_loss` | 0.06 (6%) | 0.01-0.20 | Daily loss circuit breaker |
| `atr_sl_multiplier` | 2.0 | 0.5-5.0 | ATR multiple for stop loss |
| `min_risk_reward` | 1.5 | 0.5-5.0 | Minimum risk/reward ratio |

### Stop Management Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `trailing_stop_enabled` | false | bool | Enable trailing stops |
| `atr_trail_multiplier` | 2.0 | 0.5+ | ATR multiple for trail distance |
| `break_even_enabled` | false | bool | Enable break-even stop |
| `break_even_r_multiple` | 1.0 | 0.5+ | R-multiple to trigger break-even |
| `max_hold_hours` | 24.0 | 1+ | Max hours before time stop |
| `time_stop_profit_threshold_pct` | 1.0 | 0+ | PnL% threshold for time extension |

### Portfolio Protection Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `drawdown_breaker_enabled` | false | bool | Enable drawdown circuit breaker |
| `max_drawdown_pct` | 0.15 (15%) | 0.01-1.0 | Max drawdown before emergency |
| `cppi_enabled` | false | bool | Enable CPPI portfolio insurance |
| `cppi_multiplier` | 3.0 | 1+ | CPPI risky exposure multiplier |
| `cppi_max_drawdown_pct` | 0.15 | 0.01-1.0 | CPPI floor calculation param |
| `correlation_monitor_enabled` | false | bool | Enable correlation monitoring |
| `correlation_auto_reduce` | false | bool | Auto-reduce correlated positions |
| `correlation_threshold` | 0.7 | 0-1 | Correlation warning threshold |

### Kelly Criterion Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `kelly_enabled` | false | bool | Enable Kelly Criterion sizing |
| `kelly_fraction` | 0.5 | 0-1 | Kelly fraction (0.5 = half-Kelly) |
| `kelly_min_trades` | 20 | 1+ | Min trades before Kelly activates |
| `kelly_lookback` | 50 | 1+ | Recent trades for Kelly calculation |

---

## 22. Complete Signal Lifecycle Diagram

```
                        ┌─────────────────────┐
                        │   Binance Market     │
                        │   (OHLCV candles)    │
                        └──────────┬──────────┘
                                   │ every 60s
                                   ▼
                        ┌─────────────────────┐
                        │  Candle Ingestion    │
                        │  (TimescaleDB)       │
                        └──────────┬──────────┘
                                   │ every 5min
                                   ▼
               ┌───────────────────────────────────────┐
               │         6-LAYER PIPELINE               │
               │                                        │
               │  L0 Regime ──── CHAOTIC? ──── NO TRADE │
               │       │                                │
               │  L1 Trend ──── UNCLEAR? ──── NO TRADE  │
               │       │                                │
               │  L2 Zones ──── NONE? ────── NO TRADE   │
               │       │                                │
               │  For each zone:                        │
               │    L3 Confluence ── < 50? ── skip zone │
               │         │                              │
               │    L4 Triggers ──── < 2? ── skip zone  │
               │         │                              │
               │    L5 Risk ──── R:R < 1.5? ─ skip zone │
               │                                        │
               │  → Best qualifying zone wins           │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │       POST-PIPELINE FILTERS            │
               │                                        │
               │  Feedback Filter (self-learning rules) │
               │  Position Filter (1 per symbol)        │
               │  MTF Alignment (higher TF check)       │
               │  CPPI Scaling (if enabled)             │
               │  Deduplication                         │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │       AI QUALITY GATE (Claude)         │
               │                                        │
               │  Signal Quality: 0-100                 │
               │  strong_confirm / confirm / caution    │
               │  → reject? ─────────────── NO TRADE    │
               │                                        │
               │  Multi-TF Analysis: aligned/conflicting│
               │  → conflicting? ────────── NO TRADE    │
               │                                        │
               │  AI unavailable? ───────── NO TRADE    │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Signal persisted    │
                        │  (status: "pending") │
                        └──────────┬──────────┘
                                   │ every 30s
                                   ▼
               ┌───────────────────────────────────────┐
               │       EXECUTION CHECKS                 │
               │                                        │
               │  Drawdown breaker (if enabled)         │
               │  Correlation penalty (if enabled)      │
               │  Position safety check (defense)       │
               │  Idempotency check (no duplicates)     │
               │  Pre-trade risk checks:                │
               │    - Daily loss < 6%                   │
               │    - Open positions < 5                │
               │    - Per-trade risk < 2%               │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │       ORDER PLACEMENT                  │
               │                                        │
               │  BrokerRouter → PaperAdapter (default) │
               │              → CCXTAdapter (live)      │
               │                                        │
               │  Paper: instant fill + 0.1% slippage   │
               │  Live: real exchange execution          │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │       POSITION OPENED                  │
               │                                        │
               │  Entry price, SL, TP1, TP2 recorded    │
               │  is_open = True                        │
               └───────────────────┬───────────────────┘
                                   │ every 60s
                                   ▼
               ┌───────────────────────────────────────┐
               │       POSITION MANAGEMENT              │
               │                                        │
               │  1. Update price from latest candle    │
               │  2. Time stop check                    │
               │     → held too long? CLOSE             │
               │  3. Break-even check (if enabled)      │
               │     → profit >= 1R? Move SL to entry   │
               │  4. Trailing stop check (if enabled)   │
               │     → ratchet stop in profit direction │
               │  5. Stop loss check                    │
               │     → price <= SL? CLOSE at loss       │
               │  6. Take profit check                  │
               │     → price >= TP? CLOSE at profit     │
               │  7. Drawdown emergency (if enabled)    │
               │     → portfolio DD > limit? CLOSE ALL  │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │       TRADE RECORDED                   │
               │                                        │
               │  Entry/exit prices, PnL, duration,     │
               │  exit_reason: stop_loss / take_profit / │
               │  time_stop / sell_signal / manual /    │
               │  drawdown_breaker                      │
               │                                        │
               │  Fed into self-learning loop nightly   │
               └───────────────────────────────────────┘

      ┌─────────────── SELF-LEARNING LOOP ───────────────┐
      │                                                    │
      │  02:30  Pattern Analysis (Claude reviews trades)   │
      │  03:00  Risk Tuner (Claude adjusts parameters)     │
      │  04:00  Feedback Synthesis (Claude creates rules)  │
      │    ↓                                               │
      │  Feedback Filter → applied to next pipeline run    │
      │                                                    │
      └────────────────────────────────────────────────────┘
```

---

*This document was generated from a complete code review of the SignalForge backend. All
file references, thresholds, defaults, and logic flows were verified against the actual
codebase.*
