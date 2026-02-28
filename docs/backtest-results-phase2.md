# Phase 2 Backtest Results

## Summary

| Metric | EUR/USD (Forex) | BTC/USDT (Crypto) | SPY (Equity) |
|--------|--------|--------|--------|
| total_trades | 3 | 4 | 5 |
| win_rate | 33.33 | 50.00 | 20.00 |
| profit_factor | 0.78 | 1.58 | 0.40 |
| total_return_pct | -0.85 | 2.36 | -4.78 |
| max_drawdown_pct | 3.96 | 3.96 | 5.88 |
| sharpe_ratio | -0.07 | 0.17 | -0.35 |
| avg_risk_reward | 1.62 | 1.62 | 1.62 |

## Parameters

- Lookback: 200 bars
- Risk per trade: 2%
- ATR SL multiplier: 2.0
- Min confluence: 50
- Min risk:reward: 1.5

## Notes

- Data is synthetic (2000 bars each) to demonstrate pipeline functionality
- Real market data will be used once CCXT ingestion is live (Phase 3)
- All 6 layers active: Regime -> Trend -> Zones -> Confluence -> Triggers -> Risk