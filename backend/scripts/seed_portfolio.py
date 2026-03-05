"""Seed the portfolio with CoinGecko holdings data.

Adds 15 coins as manual holdings with cost basis derived from the
CoinGecko portfolio snapshot (March 2026). Cost basis is calculated from
the PNL% shown on CoinGecko at the time of the snapshot.

Usage:
    python -m scripts.seed_portfolio            # dry-run (prints data)
    python -m scripts.seed_portfolio --apply     # inserts via API
    python -m scripts.seed_portfolio --apply --clear  # clears existing first
"""

import argparse
import json
import sys

import httpx

# ---------- Portfolio data (from CoinGecko snapshot) ----------
# cost_per_unit derived from: current_price / (1 + pnl_pct / 100)
# For USDT: cost set to $1.00 (stablecoin, CoinGecko PNL is artifact)
# For RENDER: cost derived from dollar PNL ($3,191.68)

PORTFOLIO: list[dict] = [
    {
        "symbol": "BTC",
        "quantity": 0.90207,
        "purchase_price": 41841.94,  # +74.7% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "RENDER",
        "quantity": 6632.82725,
        "purchase_price": 0.9510,  # ~+50.4% PNL (from dollar PNL $3,191.68)
        "notes": "CoinGecko import",
    },
    {
        "symbol": "CRO",
        "quantity": 59203.31,
        "purchase_price": 0.08892,  # -12.3% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "TAO",
        "quantity": 21.3533,
        "purchase_price": 280.85,  # -32.9% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "ALPH",
        "quantity": 18811.78,
        "purchase_price": 0.2682,  # -70.7% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "INJ",
        "quantity": 326.79,
        "purchase_price": 27.79,  # -88.7% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "QUBIC",
        "quantity": 115598000,
        "purchase_price": 0.00004420,  # -87.8% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "RIO",
        "quantity": 6468.7,
        "purchase_price": 1.4990,  # -95.1% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "ORAI",
        "quantity": 804.94,
        "purchase_price": 12.567,  # -96.4% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "ZEPH",
        "quantity": 512.82,
        "purchase_price": 0.8193,  # -47.2% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "USDT",
        "quantity": 137.575,
        "purchase_price": 1.00,  # stablecoin — CoinGecko PNL is tracking artifact
        "notes": "CoinGecko import",
    },
    {
        "symbol": "ABX",
        "quantity": 422.747,
        "purchase_price": 0.1602,  # -90.3% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "APAD",
        "quantity": 15000,
        "purchase_price": 0.0003871,  # 0.0% PNL (airdrop / free)
        "notes": "CoinGecko import",
    },
    {
        "symbol": "EX",
        "quantity": 100,
        "purchase_price": 0.01127,  # +4.3% PNL
        "notes": "CoinGecko import",
    },
    {
        "symbol": "AYIN",
        "quantity": 255.847,
        "purchase_price": 19.36,  # -99.9% PNL
        "notes": "CoinGecko import",
    },
]


def print_summary() -> None:
    """Print the portfolio in a human-readable table."""
    print(f"\n{'Symbol':<8} {'Qty':>16} {'Cost/Unit':>14} {'Total Cost':>14}")
    print("-" * 56)
    total_cost = 0.0
    for h in PORTFOLIO:
        cost = h["quantity"] * h["purchase_price"]
        total_cost += cost
        print(f"{h['symbol']:<8} {h['quantity']:>16,.4f} ${h['purchase_price']:>12,.6f} ${cost:>12,.2f}")
    print("-" * 56)
    print(f"{'TOTAL':<8} {'':>16} {'':>14} ${total_cost:>12,.2f}")
    print(f"\n{len(PORTFOLIO)} coins, total cost basis: ${total_cost:,.2f}\n")


def apply(api_url: str, token: str, clear: bool = False) -> None:
    """Send portfolio to the bulk import endpoint."""
    url = f"{api_url}/api/holdings/manual/bulk"
    payload = {
        "holdings": PORTFOLIO,
        "clear_existing": clear,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = httpx.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code == 201:
        data = resp.json()
        print(f"Successfully imported {len(data)} holdings.")
    else:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed portfolio with CoinGecko data")
    parser.add_argument("--apply", action="store_true", help="Actually insert via API")
    parser.add_argument("--clear", action="store_true", help="Clear existing holdings first")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--token", default="", help="JWT auth token")
    args = parser.parse_args()

    print_summary()

    if args.apply:
        if not args.token:
            print("Error: --token is required when using --apply", file=sys.stderr)
            print("Get a token: curl -X POST http://localhost:8000/api/auth/login \\")
            print('  -H "Content-Type: application/json" \\')
            print('  -d \'{"email":"roger@signalforge.dev","password":"SignalForge2026"}\'')
            sys.exit(1)
        apply(args.api_url, args.token, args.clear)
    else:
        print("Dry run. Use --apply --token <JWT> to insert holdings.")
        print(f"\nJSON payload:\n{json.dumps(PORTFOLIO, indent=2)}")


if __name__ == "__main__":
    main()
