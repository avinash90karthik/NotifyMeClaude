#!/usr/bin/env python3
"""Place Rule 26 exit orders + take-profit alarm after a buy fill.

What this script does (idempotent, safe to re-run):
  1. Cancel any existing TR price alarms on this ISIN (optional, --keep-alarms)
  2. Cancel any existing sell orders on this ISIN (always, to avoid
     "not enough shares" rejections)
  3. Place 2 stop-market sell orders on the cert:
       Tier 2:  stop = buy × 0.85   size = 50% of position
       Tier 3:  stop = buy × 0.75   size = 50% of position
  4. Place 1 price alarm for take-profit:
       TP-1:    price = buy × 1.20  (push notification, NOT an order)
     Reason: TR reserves shares for any open sell order, so a TP limit
     order would block the stop orders. Alarm + manual sell is the
     correct pattern here.

The script is generic — it works for ANY cert ISIN. Defaults assume
HSBC turbo certs traded on TUB. Override with --exchange.

Usage:
  # ENR cert, 159 shares filled at €1.83
  python3 scripts/tr/place_exits.py --isin DE000HM4F8P6 --buy 1.83 --shares 159

  # AMD cert, 301 shares at average €5.54
  python3 scripts/tr/place_exits.py --isin DE000VY2JHM1 --buy 5.54 --shares 301

  # Dry-run: print plan, no API calls that mutate
  python3 scripts/tr/place_exits.py --isin DE000HM4F8P6 --buy 1.83 --shares 159 --dry-run

Safety:
  - Every mutation requires explicit confirm unless --yes is passed.
  - --dry-run prints the full plan without touching TR.
  - The script ALWAYS cancels existing sell orders on the ISIN first
    (otherwise TR rejects new orders due to share reservation).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running both as a script and as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tr.client import (
    drain_until,
    fetch_active_orders,
    fetch_position,
    fetch_price_alarms,
    parse_order_response,
    tr_session,
)


# Rule 26 v2 (Tier-1 removed 2026-04-28)
TIERS = [
    ("Tier 2 (-15%)", 0.85, 0.50),  # (label, multiplier, fraction of position)
    ("Tier 3 (-25%)", 0.75, 0.50),
]
TP_MULTIPLIER = 1.20  # +20% take-profit alarm


def round_price(p: float) -> float:
    """TR accepts 4dp on sub-EUR, 2dp above."""
    return round(p, 3) if p < 1.0 else round(p, 2)


def split_shares(total: int) -> list[int]:
    """Split position into Tier-2 (50%) and Tier-3 (50%) chunks.
    First tier gets ceil(half), second gets the remainder, ensuring sum == total."""
    half = total // 2
    rest = total - half
    return [rest, half]  # Tier 2 gets the larger half if odd


async def cancel_open_sell_orders(tr, isin: str, dry_run: bool) -> int:
    """Cancel every active SELL order on this ISIN. Returns count cancelled.
    Required because TR reserves shares for open sell orders, blocking new ones."""
    orders = await fetch_active_orders(tr)
    sell_orders = [o for o in orders if o.get("instrumentId") == isin and o.get("type") == "sell"]
    if not sell_orders:
        return 0
    print(f"  Found {len(sell_orders)} existing sell order(s) on {isin}:")
    for o in sell_orders:
        mode = o.get("mode")
        price = o.get("stop") or o.get("limit") or "?"
        print(f"    [{o['id'][:8]}] {mode} {o.get('size'):.0f}× @ €{price}")
    if dry_run:
        print(f"  DRY-RUN — would cancel {len(sell_orders)} order(s)")
        return len(sell_orders)
    for o in sell_orders:
        await tr.cancel_order(o["id"])
        print(f"    → cancelled {o['id'][:8]}")
    # drain confirmation messages
    for _ in range(len(sell_orders) + 2):
        try:
            await asyncio.wait_for(tr.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            break
    return len(sell_orders)


async def cancel_existing_alarms(tr, isin: str, dry_run: bool) -> int:
    """Cancel all price alarms on this ISIN. Returns count cancelled."""
    alarms = await fetch_price_alarms(tr)
    on_isin = [a for a in alarms if a.get("instrumentId") == isin]
    if not on_isin:
        return 0
    print(f"  Found {len(on_isin)} existing alarm(s) on {isin}:")
    for a in on_isin:
        print(f"    [{a['id'][:8]}] €{a.get('targetPrice')}")
    if dry_run:
        print(f"  DRY-RUN — would cancel {len(on_isin)} alarm(s)")
        return len(on_isin)
    for a in on_isin:
        await tr.cancel_price_alarm(a["id"])
    for _ in range(len(on_isin) + 2):
        try:
            await asyncio.wait_for(tr.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            break
    return len(on_isin)


async def place_stop_order(tr, isin: str, exchange: str, size: int, stop: float,
                            expiry_type: str, expiry_date: str | None,
                            label: str, dry_run: bool) -> str | None:
    print(f"  → {label}: stop-sell {size}× @ €{stop:.4f}")
    if dry_run:
        print(f"    DRY-RUN — would place order")
        return None
    await tr.stop_market_order(
        isin=isin, exchange=exchange, order_type="sell", size=size,
        stop=stop, expiry=expiry_type, expiry_date=expiry_date,
        warnings_shown=["targetMarket"],
    )
    # drain
    for _ in range(5):
        try:
            msg = await asyncio.wait_for(tr.recv(), timeout=4.0)
            r = parse_order_response(msg)
            if r["error"]:
                print(f"    ✗ ERROR: {r['error']}")
                return None
            if r["order_id"]:
                print(f"    ✓ orderId: {r['order_id']}")
                return r["order_id"]
        except asyncio.TimeoutError:
            break
    return None


async def place_alarm(tr, isin: str, price: float, label: str, dry_run: bool) -> bool:
    print(f"  → {label}: alarm @ €{price:.4f}")
    if dry_run:
        print(f"    DRY-RUN — would create alarm")
        return True
    await tr.create_price_alarm(isin, float(price))
    for _ in range(3):
        try:
            await asyncio.wait_for(tr.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            break
    print(f"    ✓ alarm created")
    return True


async def run(args) -> int:
    async with tr_session() as tr:
        # 1. Verify position exists with enough shares
        pos = await fetch_position(tr, args.isin)
        if pos is None:
            print(f"  ⚠ No position on {args.isin} — proceeding anyway (--shares is authoritative)")
        else:
            held = int(float(pos.get("netSize", 0)))
            if held < args.shares:
                print(f"  ✗ Held {held} shares but --shares={args.shares}. Aborting.", file=sys.stderr)
                return 1

        # 2. Compute levels
        tier_levels = [
            (label, round_price(args.buy * mult), int(args.shares * frac))
            for (label, mult, frac) in TIERS
        ]
        # Ensure size sum == total (handle rounding)
        total_assigned = sum(s for _, _, s in tier_levels)
        if total_assigned != args.shares:
            # Add the diff to the first tier
            label, price, size = tier_levels[0]
            tier_levels[0] = (label, price, size + (args.shares - total_assigned))

        tp_price = round_price(args.buy * TP_MULTIPLIER)

        print("=" * 70)
        print(f"  PLACE EXITS — {args.isin}")
        print("=" * 70)
        print(f"  Buy price:  €{args.buy:.4f}  ({args.shares} shares)")
        print(f"  Exchange:   {args.exchange}")
        print()
        print("  Plan:")
        for label, price, size in tier_levels:
            print(f"    {label:18}  stop  {size:>4}× @ €{price:.4f}")
        if not args.skip_tp:
            print(f"    {'TP-1 (+20%)':18}  alarm     @ €{tp_price:.4f}  (push, not order)")
        print()

        if args.dry_run:
            print("  DRY-RUN — no mutations.")
            await cancel_open_sell_orders(tr, args.isin, dry_run=True)
            await cancel_existing_alarms(tr, args.isin, dry_run=True)
            return 0

        if not args.yes:
            ans = input("Proceed? [yes/NO]: ").strip().lower()
            if ans != "yes":
                print("Aborted.")
                return 0

        # 3. Cancel existing sell orders + alarms on this ISIN
        print("\n  [1/3] Cancelling existing sells + alarms on this ISIN...")
        await cancel_open_sell_orders(tr, args.isin, dry_run=False)
        if not args.keep_alarms:
            await cancel_existing_alarms(tr, args.isin, dry_run=False)

        # 4. Place stop orders
        print("\n  [2/3] Placing stop orders...")
        for label, price, size in tier_levels:
            await place_stop_order(
                tr, args.isin, args.exchange, size, price,
                expiry_type="gtd", expiry_date=args.expiry_date,
                label=label, dry_run=False,
            )

        # 5. Place TP alarm (not order — see module docstring)
        if not args.skip_tp:
            print("\n  [3/3] Placing take-profit alarm...")
            await place_alarm(tr, args.isin, tp_price, "TP-1 (+20%)", dry_run=False)

        print("\n  ✓ Done. Verify with: python3 scripts/tr/list_orders.py")
    return 0


def main():
    p = argparse.ArgumentParser(description="Place Rule 26 exits + TP alarm after a buy fill")
    p.add_argument("--isin", required=True, help="Cert ISIN")
    p.add_argument("--buy", type=float, required=True, help="Fill price (EUR)")
    p.add_argument("--shares", type=int, required=True, help="Position size (shares)")
    p.add_argument("--exchange", default="TUB", help="TR exchange code (default: TUB for HSBC turbos)")
    p.add_argument("--expiry-date", default="2026-12-31",
                   help="GTD expiry date YYYY-MM-DD (default: 2026-12-31; "
                        "must be within 1 year — SocGen rejects longer)")
    p.add_argument("--skip-tp", action="store_true", help="Don't create the +20%% TP alarm")
    p.add_argument("--keep-alarms", action="store_true",
                   help="Don't cancel existing price alarms on this ISIN")
    p.add_argument("--dry-run", action="store_true", help="Print plan, no mutation")
    p.add_argument("--yes", action="store_true", help="Skip interactive confirm")
    args = p.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
