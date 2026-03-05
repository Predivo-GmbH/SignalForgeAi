"""Seed the portfolio with CoinGecko cost basis data.

Two distinct operations:
1. Manual holdings — only coins NOT already on a connected exchange
   (hardware wallets, external platforms, obscure tokens)
2. Cost basis overrides — for ALL 15 coins from CoinGecko snapshot,
   so exchange holdings also get P&L tracking.

Cost basis derived from CoinGecko PNL$ snapshot (March 2026):
  cost_per_unit = (current_value - pnl_dollar) / quantity

Usage:
    python -m scripts.seed_portfolio            # dry-run (prints data)
    python -m scripts.seed_portfolio --apply     # inserts via API
    python -m scripts.seed_portfolio --apply --clear  # clears existing first
"""

import argparse
import json
import sys

import httpx

# ---------- Manual holdings (coins NOT on connected exchanges) ----------
# Original holdings: ALPH (Ledger), BTC (Ledger), BTC (Crypto.com),
# CRO (Crypto.com wallet), ETH (Crypto.com dust)
# Plus obscure tokens not on Binance/MEXC/Kraken/Crypto.com/KuCoin:
# QUBIC, ABX, APAD, EX, AYIN

MANUAL_HOLDINGS: list[dict] = [
    {
        "symbol": "ALPH",
        "quantity": 18811.78,
        "purchase_price": 1.0888,  # PNL$-derived
        "notes": "Ledger",
    },
    {
        "symbol": "BTC",
        "quantity": 0.90207,
        "purchase_price": 33110.69,  # PNL$-derived
        "notes": "Ledger",
    },
    {
        "symbol": "BTC",
        "quantity": 0.00951335,
        "purchase_price": 33110.69,
        "notes": "Crypto.com",
    },
    {
        "symbol": "CRO",
        "quantity": 59203.31,
        "purchase_price": 0.08892,  # -12.3% PNL
        "notes": "Crypto.com wallet",
    },
    {
        "symbol": "ETH",
        "quantity": 0.0045138,
        "purchase_price": None,
        "notes": "Crypto.com dust",
    },
    {
        "symbol": "QUBIC",
        "quantity": 1166127000,
        "purchase_price": 0.00000437,  # PNL$-derived
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
        "purchase_price": None,  # airdrop — no cost basis
        "notes": "Airdrop",
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
        "purchase_price": 18.08,  # PNL$-derived
        "notes": "CoinGecko import",
    },
]

# ---------- Cost basis overrides (ALL coins, including exchange ones) ----------
# Applied to any holding (manual or exchange) that lacks its own avg_price.
# This lets exchange-sourced coins (RENDER on Binance, RIO on MEXC, etc.)
# show correct P&L without duplicating quantities.

COST_BASIS_OVERRIDES: list[dict] = [
    {"symbol": "BTC", "purchase_price": 33110.69, "notes": "PNL$-derived"},
    {"symbol": "RENDER", "purchase_price": 0.9510, "notes": "CoinGecko ~+50.4%"},
    {"symbol": "CRO", "purchase_price": 0.08892, "notes": "CoinGecko -12.3%"},
    {"symbol": "TAO", "purchase_price": 280.85, "notes": "CoinGecko -32.9%"},
    {"symbol": "ALPH", "purchase_price": 1.0888, "notes": "PNL$-derived"},
    {"symbol": "INJ", "purchase_price": 30.60, "notes": "PNL$-derived"},
    {"symbol": "QUBIC", "purchase_price": 0.00000437, "notes": "PNL$-derived"},
    {"symbol": "RIO", "purchase_price": 1.4990, "notes": "CoinGecko -95.1%"},
    {"symbol": "ORAI", "purchase_price": 12.42, "notes": "PNL$-derived"},
    {"symbol": "ZEPH", "purchase_price": 43.22, "notes": "PNL$-derived"},
    {"symbol": "USDT", "purchase_price": 8.59, "notes": "PNL$-derived"},
    {"symbol": "ABX", "purchase_price": 0.1602, "notes": "CoinGecko -90.3%"},
    # APAD excluded — airdrop, no cost basis
    {"symbol": "EX", "purchase_price": 0.01127, "notes": "CoinGecko +4.3%"},
    {"symbol": "AYIN", "purchase_price": 18.08, "notes": "PNL$-derived"},
]


def print_summary() -> None:
    """Print the portfolio in a human-readable table."""
    print(f"\n{'='*60}")
    print("MANUAL HOLDINGS (coins not on connected exchanges)")
    print(f"{'='*60}")
    print(f"{'Symbol':<8} {'Qty':>16} {'Cost/Unit':>14} {'Notes':<20}")
    print("-" * 62)
    for h in MANUAL_HOLDINGS:
        pp = h["purchase_price"]
        pp_str = f"${pp:,.6f}" if pp else "n/a"
        print(f"{h['symbol']:<8} {h['quantity']:>16,.4f} {pp_str:>14} {h.get('notes', ''):<20}")

    print(f"\n{'='*60}")
    print("COST BASIS OVERRIDES (all coins, for P&L tracking)")
    print(f"{'='*60}")
    print(f"{'Symbol':<8} {'Cost/Unit':>14} {'Notes':<30}")
    print("-" * 55)
    for cb in COST_BASIS_OVERRIDES:
        print(f"{cb['symbol']:<8} ${cb['purchase_price']:>12,.6f} {cb.get('notes', ''):<30}")
    print()


def apply(api_url: str, token: str, clear: bool = False) -> None:
    """Send portfolio data via API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Step 1: Import manual holdings
    holdings_url = f"{api_url}/api/holdings/manual/bulk"
    # Filter out entries with None purchase_price for the API (Field(gt=0) validation)
    api_holdings = []
    for h in MANUAL_HOLDINGS:
        entry = {
            "symbol": h["symbol"],
            "quantity": h["quantity"],
            "notes": h.get("notes"),
        }
        if h.get("purchase_price") is not None:
            entry["purchase_price"] = h["purchase_price"]
        api_holdings.append(entry)

    payload = {"holdings": api_holdings, "clear_existing": clear}
    resp = httpx.post(holdings_url, json=payload, headers=headers, timeout=30)
    if resp.status_code == 201:
        data = resp.json()
        print(f"Imported {len(data)} manual holdings.")
    else:
        print(f"Error importing holdings {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Import cost basis overrides
    cb_url = f"{api_url}/api/holdings/cost-basis/bulk"
    cb_payload = {"overrides": COST_BASIS_OVERRIDES, "clear_existing": clear}
    resp = httpx.post(cb_url, json=cb_payload, headers=headers, timeout=30)
    if resp.status_code == 201:
        data = resp.json()
        print(f"Imported {len(data)} cost basis overrides.")
    else:
        print(f"Error importing cost basis {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    print("\nDone! Portfolio seeded successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed portfolio with CoinGecko data")
    parser.add_argument("--apply", action="store_true", help="Actually insert via API")
    parser.add_argument("--clear", action="store_true", help="Clear existing holdings/overrides first")
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


if __name__ == "__main__":
    main()
