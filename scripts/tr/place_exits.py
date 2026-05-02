#!/usr/bin/env python3
"""Place v1.0 exit orders + target alarms after a buy fill.

What this script does (idempotent, safe to re-run):
  1. Cancel any existing TR price alarms on this ISIN (optional, --keep-alarms)
  2. Cancel any existing sell orders on this ISIN (always, to avoid
     "not enough shares" rejections from share reservation)
  3. Place N stop-market sell orders per --stops (cert-% drawdown : size %)
     The default for v1.0 is the staircase 10:33,17:33,25:34
  4. Place price alarms per --targets (cert-% gains, push only — NOT orders)
     Reason: TR reserves shares for any open sell order, so a target
     limit order would block the stop orders. Alarm + manual sell is
     the correct pattern.

Exchange selection:
  Default exchange is derived from the ISIN issuer (TUB=HSBC, SGL=SocGen,
  LSX=stocks/ETFs). Override with --exchange.

Recalibrate mode:
  --recalibrate cancels the existing stops on a (now reduced) position
  and re-places the staircase on the remaining shares with the same
  --stops percentages. Use after a manual Target sell.

Usage:
  # v1.0 default staircase 10:33, 17:33, 25:34 plus +12%/+22% target alarms
  python3 scripts/tr/place_exits.py --isin DE000HM4F8P6 --buy 1.83 --shares 159 \\
      --stops 10:33,17:33,25:34 --targets 12,22

  # After Target 1 manual sell — recalibrate stops on reduced position
  python3 scripts/tr/place_exits.py --isin DE000HM4F8P6 --shares 80 \\
      --buy 1.83 --stops 10:33,17:33,25:34 --recalibrate

  # Dry-run: print plan, no API calls that mutate
  python3 scripts/tr/place_exits.py --isin DE000HM4F8P6 --buy 1.83 --shares 159 \\
      --stops 10:33,17:33,25:34 --dry-run

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


# ISIN issuer prefix → TR exchange code
# Heuristics from observed cert ISINs in this repo.
ISIN_EXCHANGE_MAP = {
    'DE000HM': 'TUB',   # HSBC turbo certs
    'DE000HW': 'TUB',   # HSBC warrants/turbos
    'DE000HC': 'TUB',
    'DE000SF': 'SGL',   # SocGen
    'DE000SG': 'SGL',
    'DE000SY': 'SGL',
    'DE000SU': 'SGL',
    'DE000VY': 'TUB',   # Vontobel — observed on TUB historically
    'DE000VX': 'TUB',
    'DE000UE': 'TUB',   # UBS
    'DE000UB': 'TUB',
}


def derive_exchange(isin: str) -> str:
    """Best-effort: derive TR exchange code from ISIN issuer prefix.

    Falls back to 'TUB' if no prefix matches. The user can always override
    with --exchange.
    """
    for prefix, exchange in ISIN_EXCHANGE_MAP.items():
        if isin.startswith(prefix):
            return exchange
    return 'TUB'


def round_price(p: float) -> float:
    """TR accepts 4dp on sub-EUR, 2dp above."""
    return round(p, 3) if p < 1.0 else round(p, 2)


def parse_stops_spec(spec: str) -> list[tuple[float, float]]:
    """Parse '--stops 10:33,17:33,25:34' into [(0.10, 0.33), (0.17, 0.33), (0.25, 0.34)].

    Each item is `pct:size_pct`, both in percent (positive numbers).
    Stop pct is the cert drawdown from buy price (e.g. 10 = stop at buy * 0.90).
    Size pct is the fraction of total shares (e.g. 33 = 33% of position).
    """
    out = []
    for raw in spec.split(','):
        raw = raw.strip()
        if not raw:
            continue
        if ':' not in raw:
            raise ValueError(f'invalid stop spec {raw!r}: expected "pct:size_pct"')
        pct_str, size_str = raw.split(':', 1)
        pct = float(pct_str.strip())
        size = float(size_str.strip())
        if pct <= 0 or pct >= 100:
            raise ValueError(f'stop pct {pct} not in (0, 100)')
        if size <= 0 or size > 100:
            raise ValueError(f'size pct {size} not in (0, 100]')
        out.append((pct / 100.0, size / 100.0))
    if not out:
        raise ValueError('--stops produced no entries')
    total_size = sum(s for _, s in out)
    if abs(total_size - 1.0) > 0.01:
        raise ValueError(f'--stops sizes sum to {total_size*100:.0f}%, expected ~100%')
    return out


def parse_targets_spec(spec: str | None) -> list[float]:
    """Parse '--targets 12,22' into [0.12, 0.22] (cert-% gains, fractions)."""
    if not spec:
        return []
    out = []
    for raw in spec.split(','):
        raw = raw.strip()
        if not raw:
            continue
        pct = float(raw)
        if pct <= 0 or pct >= 1000:
            raise ValueError(f'target pct {pct} not in (0, 1000)')
        out.append(pct / 100.0)
    return out


def split_share_counts(total: int, fractions: list[float]) -> list[int]:
    """Split `total` shares according to fractions (must sum to ~1.0).

    Adjusts rounding so the integer shares sum exactly to `total`. Any
    leftover from rounding is added to the FIRST chunk (so stop 1 is the
    largest one if there's a remainder — first defense gets the most shares).
    """
    chunks = [int(total * f) for f in fractions]
    deficit = total - sum(chunks)
    if deficit > 0:
        chunks[0] += deficit
    elif deficit < 0:
        # Over-assigned: subtract from last chunks
        for i in range(len(chunks) - 1, -1, -1):
            take = min(chunks[i], -deficit)
            chunks[i] -= take
            deficit += take
            if deficit == 0:
                break
    return chunks


async def cancel_open_sell_orders(tr, isin: str, dry_run: bool) -> int:
    """Cancel every active SELL order on this ISIN."""
    orders = await fetch_active_orders(tr)
    sell_orders = [o for o in orders if o.get('instrumentId') == isin and o.get('type') == 'sell']
    if not sell_orders:
        return 0
    print(f'  Found {len(sell_orders)} existing sell order(s) on {isin}:')
    for o in sell_orders:
        mode = o.get('mode')
        price = o.get('stop') or o.get('limit') or '?'
        print(f"    [{o['id'][:8]}] {mode} {o.get('size'):.0f}× @ €{price}")
    if dry_run:
        print(f'  DRY-RUN — would cancel {len(sell_orders)} order(s)')
        return len(sell_orders)
    for o in sell_orders:
        await tr.cancel_order(o['id'])
        print(f"    → cancelled {o['id'][:8]}")
    for _ in range(len(sell_orders) + 2):
        try:
            await asyncio.wait_for(tr.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            break
    return len(sell_orders)


async def cancel_existing_alarms(tr, isin: str, dry_run: bool) -> int:
    alarms = await fetch_price_alarms(tr)
    on_isin = [a for a in alarms if a.get('instrumentId') == isin]
    if not on_isin:
        return 0
    print(f'  Found {len(on_isin)} existing alarm(s) on {isin}:')
    for a in on_isin:
        print(f"    [{a['id'][:8]}] €{a.get('targetPrice')}")
    if dry_run:
        print(f'  DRY-RUN — would cancel {len(on_isin)} alarm(s)')
        return len(on_isin)
    for a in on_isin:
        await tr.cancel_price_alarm(a['id'])
    for _ in range(len(on_isin) + 2):
        try:
            await asyncio.wait_for(tr.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            break
    return len(on_isin)


async def place_stop_order(tr, isin: str, exchange: str, size: int, stop: float,
                           expiry_type: str, expiry_date: str | None,
                           label: str, dry_run: bool) -> str | None:
    print(f'  → {label}: stop-sell {size}× @ €{stop:.4f}')
    if dry_run:
        print(f'    DRY-RUN — would place order')
        return None
    await tr.stop_market_order(
        isin=isin, exchange=exchange, order_type='sell', size=size,
        stop=stop, expiry=expiry_type, expiry_date=expiry_date,
        warnings_shown=['targetMarket'],
    )
    for _ in range(5):
        try:
            msg = await asyncio.wait_for(tr.recv(), timeout=4.0)
            r = parse_order_response(msg)
            if r['error']:
                print(f"    ✗ ERROR: {r['error']}")
                return None
            if r['order_id']:
                print(f"    ✓ orderId: {r['order_id']}")
                return r['order_id']
        except asyncio.TimeoutError:
            break
    return None


async def place_alarm(tr, isin: str, price: float, label: str, dry_run: bool) -> bool:
    print(f'  → {label}: alarm @ €{price:.4f}')
    if dry_run:
        print(f'    DRY-RUN — would create alarm')
        return True
    await tr.create_price_alarm(isin, float(price))
    for _ in range(3):
        try:
            await asyncio.wait_for(tr.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            break
    print(f'    ✓ alarm created')
    return True


async def run(args) -> int:
    stops = parse_stops_spec(args.stops)
    targets = parse_targets_spec(args.targets)
    exchange = args.exchange or derive_exchange(args.isin)

    async with tr_session() as tr:
        pos = await fetch_position(tr, args.isin)
        if pos is None:
            print(f'  ⚠ No position on {args.isin} — proceeding (--shares is authoritative)')
        else:
            held = int(float(pos.get('netSize', 0)))
            if held < args.shares:
                print(f'  ✗ Held {held} shares but --shares={args.shares}. Aborting.',
                      file=sys.stderr)
                return 1

        # Compute stop levels and share splits
        share_counts = split_share_counts(args.shares, [s for _, s in stops])
        stop_levels = [
            (round_price(args.buy * (1.0 - pct)), share_counts[i])
            for i, (pct, _) in enumerate(stops)
        ]

        target_levels = [round_price(args.buy * (1.0 + pct)) for pct in targets]

        print('=' * 70)
        if args.recalibrate:
            print(f'  RECALIBRATE EXITS — {args.isin}')
        else:
            print(f'  PLACE EXITS — {args.isin}')
        print('=' * 70)
        print(f'  Buy price:  €{args.buy:.4f}  ({args.shares} shares)')
        print(f'  Exchange:   {exchange}{"  (override)" if args.exchange else "  (derived from ISIN)"}')
        print()
        print('  Plan:')
        for i, ((pct, frac), (price, size)) in enumerate(zip(stops, stop_levels), 1):
            label = f'Stop {i} (-{int(pct*100)}%, {int(frac*100)}%)'
            print(f'    {label:30}  stop  {size:>4}× @ €{price:.4f}')
        if args.recalibrate:
            print('    (Recalibrate mode: targets re-applied unless --skip-targets)')
        for pct, price in zip(targets, target_levels):
            label = f'Target (+{int(pct*100)}%)'
            print(f'    {label:30}  alarm     @ €{price:.4f}  (push, not order)')
        print()

        if args.dry_run:
            print('  DRY-RUN — no mutations.')
            await cancel_open_sell_orders(tr, args.isin, dry_run=True)
            if not args.keep_alarms:
                await cancel_existing_alarms(tr, args.isin, dry_run=True)
            return 0

        if not args.yes:
            ans = input('Proceed? [yes/NO]: ').strip().lower()
            if ans != 'yes':
                print('Aborted.')
                return 0

        print('\n  [1/3] Cancelling existing sells + alarms on this ISIN...')
        await cancel_open_sell_orders(tr, args.isin, dry_run=False)
        if not args.keep_alarms:
            await cancel_existing_alarms(tr, args.isin, dry_run=False)

        print('\n  [2/3] Placing stop orders...')
        for i, ((pct, frac), (price, size)) in enumerate(zip(stops, stop_levels), 1):
            if size <= 0:
                continue
            label = f'Stop {i} (-{int(pct*100)}%)'
            await place_stop_order(
                tr, args.isin, exchange, size, price,
                expiry_type='gtd', expiry_date=args.expiry_date,
                label=label, dry_run=False,
            )

        if targets and not args.skip_targets:
            print('\n  [3/3] Placing target alarms...')
            for pct, price in zip(targets, target_levels):
                await place_alarm(tr, args.isin, price,
                                  f'Target (+{int(pct*100)}%)', dry_run=False)
        else:
            print('\n  [3/3] No targets to place.')

        print('\n  ✓ Done. Verify with: python3 scripts/tr/list_orders.py')
    return 0


def main():
    p = argparse.ArgumentParser(
        description='Place v1.0 exit orders + target alarms after a buy fill',
    )
    p.add_argument('--isin', required=True, help='Cert ISIN')
    p.add_argument('--buy', type=float, required=True,
                   help='Fill price (EUR) — anchor for stops + targets')
    p.add_argument('--shares', type=int, required=True, help='Position size (shares)')
    p.add_argument('--stops', required=True,
                   help='Comma-separated stops as pct:size_pct (e.g. 10:33,17:33,25:34)')
    p.add_argument('--targets', default='',
                   help='Comma-separated cert-pct target alarms (e.g. 12,22). '
                        'Empty = no target alarms.')
    p.add_argument('--exchange', default=None,
                   help='TR exchange code; default derived from ISIN issuer prefix.')
    p.add_argument('--expiry-date', default='2026-12-31',
                   help='GTD expiry date YYYY-MM-DD (default 2026-12-31; '
                        'must be within 1 year — SocGen rejects longer)')
    p.add_argument('--recalibrate', action='store_true',
                   help='Re-place stops on a reduced position after manual target sell')
    p.add_argument('--skip-targets', action='store_true',
                   help="Don't (re)place target alarms — useful with --recalibrate "
                        'when you want to keep the existing alarms intact')
    p.add_argument('--keep-alarms', action='store_true',
                   help="Don't cancel existing price alarms on this ISIN")
    p.add_argument('--dry-run', action='store_true', help='Print plan, no mutation')
    p.add_argument('--yes', action='store_true', help='Skip interactive confirm')
    args = p.parse_args()
    return asyncio.run(run(args))


if __name__ == '__main__':
    sys.exit(main())
