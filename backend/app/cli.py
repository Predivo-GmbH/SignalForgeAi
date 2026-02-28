"""
CLI for running backtests.
Usage: python -m app.cli backtest --symbol BTC/USDT --timeframe 1h --days 90
"""

import argparse
from datetime import datetime, timedelta, timezone

from app.backtest.engine import BacktestEngine
from app.data.ingestion import CCXTIngestion


def cmd_backtest(args):
    print(f"Fetching {args.symbol} {args.timeframe} candles ({args.days} days)...")

    ingestion = CCXTIngestion(exchange_id=args.exchange)
    since = int(
        (datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp() * 1000
    )
    candles = ingestion.fetch_candles(args.symbol, args.timeframe, limit=1000, since=since)

    if candles.empty:
        print("No candles fetched. Check symbol and exchange.")
        return

    print(f"Fetched {len(candles)} candles.")
    print(f"Running backtest with ${args.capital} initial capital...")

    engine = BacktestEngine()
    result = engine.run(
        candles=candles,
        symbol=args.symbol,
        timeframe=args.timeframe,
        initial_capital=args.capital,
    )

    print("\n=== BACKTEST RESULTS ===")
    print(f"Symbol:          {args.symbol}")
    print(f"Timeframe:       {args.timeframe}")
    print(f"Period:          {args.days} days ({len(candles)} candles)")
    print(f"Initial Capital: ${args.capital:,.2f}")
    print(f"Final Capital:   ${result.equity_curve[-1]:,.2f}")
    print("---")
    for key, val in result.metrics.items():
        if isinstance(val, float):
            print(f"{key:20s}: {val:.2f}")
        else:
            print(f"{key:20s}: {val}")


def main():
    parser = argparse.ArgumentParser(description="SignalForge CLI")
    subparsers = parser.add_subparsers()

    bt = subparsers.add_parser("backtest", help="Run a backtest")
    bt.add_argument("--symbol", required=True, help="Trading pair (e.g., BTC/USDT)")
    bt.add_argument("--timeframe", default="1h", help="Candle timeframe")
    bt.add_argument("--days", type=int, default=90, help="Days of history")
    bt.add_argument(
        "--capital", type=float, default=10000.0, help="Initial capital"
    )
    bt.add_argument("--exchange", default="binance", help="Exchange via CCXT")
    bt.set_defaults(func=cmd_backtest)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
