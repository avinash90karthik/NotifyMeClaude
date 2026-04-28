#!/usr/bin/env python3
"""List all active TR orders + alarms for one or all ISINs."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tr.client import fetch_active_orders, fetch_price_alarms, tr_session


def fmt_order(o: dict) -> str:
    side = o.get("type", "?").upper()
    mode = o.get("mode", "?")
    size = o.get("size", 0)
    isin = o.get("instrumentId", "?")
    name = o.get("instrumentName", "?")
    price = (
        f"limit €{o.get('limit'):.4f}" if mode == "limit"
        else f"stop @ €{o.get('stop'):.4f}" if mode == "stopMarket"
        else mode
    )
    return f"  [{o['id'][:8]}] {side:4}  {size:>5.0f}× {isin}  {name:30}  {price:25}  ({o.get('exchangeId','?')})"


async def run(args):
    async with tr_session() as tr:
        orders = await fetch_active_orders(tr)
        alarms = await fetch_price_alarms(tr)
        if args.isin:
            orders = [o for o in orders if o.get("instrumentId") == args.isin]
            alarms = [a for a in alarms if a.get("instrumentId") == args.isin]

        print(f"=== Active orders ({len(orders)}) ===")
        for o in orders:
            print(fmt_order(o))
        print()
        print(f"=== Price alarms ({len(alarms)}) ===")
        # group by ISIN
        by_isin: dict[str, list] = {}
        for a in alarms:
            by_isin.setdefault(a["instrumentId"], []).append(float(a["targetPrice"]))
        for isin, prices in sorted(by_isin.items()):
            prices.sort()
            print(f"  {isin}  " + "  ".join(f"€{p}" for p in prices))


def main():
    p = argparse.ArgumentParser(description="List TR orders + alarms")
    p.add_argument("--isin", help="Filter to one ISIN")
    args = p.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
