#!/usr/bin/env python3
"""Cancel all active orders + alarms for one ISIN. Useful before manual
re-entry or when closing a position cleanly."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tr.client import fetch_active_orders, fetch_price_alarms, tr_session


async def run(args) -> int:
    async with tr_session() as tr:
        orders = await fetch_active_orders(tr)
        alarms = await fetch_price_alarms(tr)
        my_orders = [o for o in orders if o.get("instrumentId") == args.isin]
        my_alarms = [a for a in alarms if a.get("instrumentId") == args.isin]

        print(f"=== Will cancel for {args.isin} ===")
        print(f"  Orders: {len(my_orders)}")
        for o in my_orders:
            mode = o.get("mode")
            price = o.get("stop") or o.get("limit") or "?"
            print(f"    [{o['id'][:8]}] {o.get('type')} {mode} {o.get('size')}× @ €{price}")
        print(f"  Alarms: {len(my_alarms)}")
        for a in my_alarms:
            print(f"    [{a['id'][:8]}] €{a.get('targetPrice')}")

        if not my_orders and not my_alarms:
            print("  Nothing to cancel.")
            return 0

        if args.dry_run:
            print("  DRY-RUN — no mutation.")
            return 0
        if not args.yes:
            ans = input("Proceed? [yes/NO]: ").strip().lower()
            if ans != "yes":
                print("Aborted.")
                return 0

        for o in my_orders:
            await tr.cancel_order(o["id"])
            print(f"  → cancelled order {o['id'][:8]}")
        for a in my_alarms:
            await tr.cancel_price_alarm(a["id"])
            print(f"  → cancelled alarm {a['id'][:8]}")
        # drain
        for _ in range(len(my_orders) + len(my_alarms) + 2):
            try:
                await asyncio.wait_for(tr.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                break
        print("  ✓ Done.")
    return 0


def main():
    p = argparse.ArgumentParser(description="Cancel all orders + alarms for an ISIN")
    p.add_argument("--isin", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")
    args = p.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
