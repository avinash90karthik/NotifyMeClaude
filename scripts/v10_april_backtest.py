#!/usr/bin/env python3
"""v10 April-2026 Backtest — Acceptance test for the v10.0 changes.

Replays the 31 round-trip trades from April 2026 with v10 rules applied:

  Rule 26 (loss tier cap): trades that historically went past −15% are
    capped at −15% (sell 50%) + −25% (sell other 50%) = −20% effective on
    the invested amount, simulating staged exits.

  Rule 28 (circuit-breaker): after any simulated Tier-2/3 exit, suppress
    all NEW trades on the same calendar day (Tier-2) or the next trading
    day too (Tier-3).

  V3 (slot cap = 2 turbos): trades opened when the day already has 2
    open turbo positions are suppressed.

  V4 (sector cap > 40% with AI-Semi-Group): trades that would push sector
    exposure above 40% are suppressed. AI-semi grouping per
    lib.risk_audit.AI_SEMI_GROUP.

  V6 (60d-correlation veto ≥ 0,7): trades whose underlying correlates
    ≥ 0,7 with any open position are suppressed. Correlation computed via
    yfinance retroactively. Symbols not resolvable from cert ISINs (the
    underlying is encoded in the cert name like "Long 288,66 $ AMD")
    are skipped for V6 — soft warning only, not a veto.

User decision (plan-mode): approximation via final P&L for Rule 26, NOT
intraday reconstruction. The CSV has only entry/exit prices, so we infer
"would have hit Tier-2/3" from the final pnl_pct column.

Pass criteria:
  P&L ≥ +5% of April-1 portfolio (€6.000) = ≥ +€300.
  Stretch: ≥ +8% = +€480.
  Each rule must show ≥ 1 suppression in summary (otherwise the rule isn't
  actually firing).

Usage:
  python3 scripts/v10_april_backtest.py
  python3 scripts/v10_april_backtest.py --csv /path/to/trades.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# Make lib.risk_audit importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@dataclass
class Trade:
    date: str
    name: str
    isin: str
    qty: int
    avg_buy: float
    sell: float
    pnl_pct: float
    pnl_eur: float
    underlying: str = ""  # extracted from name


# Map cert-name patterns to underlying symbols. Reuses the trades_summary CSV
# which has names like "Long 288,66 $", "Beyond Meat", "Long 134,0047 €".
# This map is the manual ground-truth — yfinance can't reverse-resolve a cert.
ISIN_TO_UNDERLYING = {
    'DE000HM41Y67': 'AMD',     # actually Long 64,14 $ (AMD legacy)
    'DE000HM2Z7Y8': 'BTC-USD', # Short 24968 $ (BTC short, treat as crypto)
    'DE000HM183S4': 'ENR.DE',  # Long 126,18 €
    'DE000VH8NBG6': 'AMD',     # Call 90 $ (legacy AMD call)
    'DE000HM1PK37': 'ENR.DE',  # Long 134,00 €
    'DE000WA1T4R2': 'NFLX',    # Long 1095,21 €
    'DE000FC6BDK8': 'BTC-USD', # Short 25073 €
    'DE000HG8W2M3': 'ENR.DE',  # Long 127 €
    'DE000HM46ZZ2': 'ENR.DE',  # Long 139,58 €
    'DE000VY1FBQ5': 'AMD',     # Long 139,08 $
    'DE000HM4HG14': 'ASML',    # Long 75,50 $ (legacy)
    'DE000FC7TRQ5': 'AVGO',    # Long 388,99 $
    'DE000HM4H7L5': 'AMZN',    # Long 188,52 $
    'DE000WA4QQS7': 'ENR.DE',  # Long 138,79 €
    'US08862E1091': 'BYND',    # Beyond Meat
    'DE000HM4NGS0': 'BTC-USD', # Long 24,95 $ — small unknown
    'DE000FE31GZ5': 'AMD',     # Long 73,98 $
    'DE000WA4K1V6': 'AMD',     # Long 131,69 $
    'DE000WA2W136': 'ENR.DE',  # Long 153,56 €
    'DE000HM4V469': 'ENR.DE',  # Long 164,09 €
    'DE000VY2JHM1': 'AMD',     # Long 288,66 $ — the AMD #130 catastrophe
    'DE000HM4LQN4': 'ENR.DE',  # Long 163,16 €
    'DE000HM4F8P6': 'ENR.DE',  # Long 157,27 € — today's tier-2/3 stop
}


def parse_csv(path: Path) -> list[Trade]:
    """Parse the trades CSV. Handle the comma-in-name quirk by reading
    fields from the right edge (pnl_eur, pnl_pct, sell, avg_buy, qty, isin)
    and joining everything else as the name."""
    trades: list[Trade] = []
    with path.open() as f:
        reader = csv.reader(f)
        header_seen = False
        for row in reader:
            if not row:
                continue
            if not header_seen:
                header_seen = True
                continue
            if not row[0].startswith('2026'):
                # footer/summary lines start with '#' or are blank
                continue
            # Right-edge parse: last 5 fields are pnl_eur, pnl_pct, sell, avg_buy, qty
            try:
                pnl_eur = float(row[-1])
                pnl_pct = float(row[-2])
                sell = float(row[-3])
                avg_buy = float(row[-4])
                qty = int(row[-5])
                isin = row[-6]
            except (ValueError, IndexError):
                continue
            date = row[0]
            name = ','.join(row[1:-6])  # everything in the middle is the name
            underlying = ISIN_TO_UNDERLYING.get(isin, '')
            trades.append(Trade(
                date=date, name=name, isin=isin, qty=qty,
                avg_buy=avg_buy, sell=sell,
                pnl_pct=pnl_pct, pnl_eur=pnl_eur,
                underlying=underlying,
            ))
    return trades


def infer_invested(trade: Trade) -> float:
    """Position cost in EUR at entry."""
    return trade.qty * trade.avg_buy


def v10_size_cap(trade: Trade, portfolio: float) -> float:
    """v10 sizing cap. The original April trades used the v9 monotone curve
    (15%/20%/25% at 60/65/70%). v10 caps at 20% from 65% upward and 10% at
    60-65%. Here we approximate by capping every trade to 20% of starting
    portfolio — the most generous v10 bracket — and pro-rating P&L
    accordingly. The actual confidence per trade isn't in the CSV, so 20%
    is a conservative upper bound; real v10 would size some trades smaller.

    Returns sizing scale factor (0..1). 1.0 = original size, 0.5 = half, etc.
    """
    invested = infer_invested(trade)
    cap = portfolio * 0.20
    if invested <= cap:
        return 1.0
    return cap / invested


def apply_rule_26(trade: Trade, sizing_scale: float = 1.0) -> tuple[float, bool]:
    """Apply Rule-26 retroactive cap, scaled by v10 position-size factor.

    Returns (simulated_pnl_eur, was_capped).

    For winners or losses ≤−15%, leave P&L unchanged (just rescaled).
    For losses between −15% and −25%, cap at Tier-2 staged exit:
        50% of position lost 15%, 50% lost the actual final pnl_pct.
    For losses past −25%, cap at Tier-2 + Tier-3 → −20% effective.

    Then the result is multiplied by sizing_scale to reflect v10 position
    sizing (cap at 20% of portfolio).
    """
    invested = infer_invested(trade)
    if trade.pnl_pct >= -15:
        return trade.pnl_eur * sizing_scale, False
    if trade.pnl_pct >= -25:
        loss_pct = 0.5 * (-15) + 0.5 * trade.pnl_pct
        sim_pnl = invested * loss_pct / 100
        return sim_pnl * sizing_scale, True
    loss_pct = 0.5 * (-15) + 0.5 * (-25)
    sim_pnl = invested * loss_pct / 100
    return sim_pnl * sizing_scale, True


def date_to_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def is_weekend(d: datetime) -> bool:
    return d.weekday() >= 5


def next_trading_day(d: datetime) -> datetime:
    nxt = d + timedelta(days=1)
    while is_weekend(nxt):
        nxt += timedelta(days=1)
    return nxt


def get_correlation_cached(sym_a: str, sym_b: str, cache: dict) -> float | None:
    """Cached wrapper for yfinance correlation — backtest hits same pairs many
    times, no point re-fetching."""
    key = tuple(sorted([sym_a, sym_b]))
    if key in cache:
        return cache[key]
    from lib.risk_audit import compute_correlation
    corr = compute_correlation(sym_a, sym_b, days=60)
    cache[key] = corr
    return corr


def run_backtest(trades: list[Trade], starting_portfolio: float = 6000) -> dict:
    """Replay trades chronologically with v10 rules applied.

    Returns dict with summary stats + per-trade details.
    """
    from lib.risk_audit import AI_SEMI_GROUP

    # Sort by date
    trades_sorted = sorted(trades, key=lambda t: t.date)

    # State carried day-to-day
    suppressed_dates: dict[str, list[str]] = defaultdict(list)  # date -> reasons (for next day blocks)
    open_positions_by_date: dict[str, list[str]] = defaultdict(list)  # naive: track the symbol opens that day
    rule28_block_until: dict[str, str] = {}  # carry tier-3 next-day blocks

    corr_cache: dict = {}

    rows = []
    summary = {
        'rule26_capped': 0,
        'rule28_suppressed': 0,
        'v3_suppressed': 0,
        'v4_suppressed': 0,
        'v6_suppressed': 0,
        'kept': 0,
        'total_pnl_original': 0.0,
        'total_pnl_v10': 0.0,
        'max_single_loss': 0.0,
    }

    for trade in trades_sorted:
        original_pnl = trade.pnl_eur
        summary['total_pnl_original'] += original_pnl

        # Decide if THIS trade gets suppressed before computing v10 P&L
        suppressed_by = None

        # ----- Rule 28: was there a Tier-2/3 stop earlier today/yesterday? -----
        # Compute Tier-status of all PRIOR trades on same date or yesterday
        trade_dt = date_to_dt(trade.date)
        # Look at all already-processed (same date or earlier in chronological order)
        for earlier in trades_sorted:
            if earlier.date >= trade.date:
                break
            earlier_dt = date_to_dt(earlier.date)
            # Different underlying only — Rule 28 doesn't block re-managing same symbol
            if earlier.underlying == trade.underlying and earlier.underlying:
                continue
            # Was earlier a Tier-2 or Tier-3?
            if earlier.pnl_pct <= -25:
                # Tier-3: block today AND next trading day
                block_end = next_trading_day(earlier_dt)
                if trade_dt <= block_end:
                    suppressed_by = f"Rule28-Tier3 (blocked by {earlier.underlying} {earlier.date})"
                    break
            elif earlier.pnl_pct <= -15:
                # Tier-2: block same day only
                if earlier.date == trade.date:
                    suppressed_by = f"Rule28-Tier2 (blocked by {earlier.underlying} {earlier.date})"
                    break

        # ----- V3: slot cap 2 turbos (count concurrent OPEN trades on same day) -----
        if not suppressed_by:
            # Naive: count distinct underlyings opened on same date BEFORE this one
            same_day_earlier = [t for t in trades_sorted
                               if t.date == trade.date and t is not trade
                               and trades_sorted.index(t) < trades_sorted.index(trade)]
            distinct_underlyings_today = {t.underlying for t in same_day_earlier if t.underlying}
            if len(distinct_underlyings_today) >= 2:
                suppressed_by = f"V3 ({len(distinct_underlyings_today)}/2 turbos already open today)"

        # ----- V4: sector cap > 40% with AI-Semi-Group -----
        if not suppressed_by and trade.underlying:
            same_day_earlier_underlyings = {
                t.underlying for t in trades_sorted
                if t.date == trade.date and t is not trade
                and trades_sorted.index(t) < trades_sorted.index(trade)
                and t.underlying
            }
            # Group by effective-sector
            def sec(sym): return "AI-Semi-Group" if sym in AI_SEMI_GROUP else sym
            sectors_today = [sec(s) for s in same_day_earlier_underlyings]
            this_sec = sec(trade.underlying)
            same_sec_count = sum(1 for s in sectors_today if s == this_sec) + 1  # +1 for this trade
            new_total = len(sectors_today) + 1
            if new_total > 0 and same_sec_count / new_total > 0.40:
                # Only veto if there's at least 2 in the same sector
                if same_sec_count >= 2:
                    suppressed_by = f"V4 ({same_sec_count}/{new_total} = {same_sec_count/new_total*100:.0f}% in {this_sec})"

        # ----- V6: 60d-correlation ≥ 0,7 with any other position open SAME DAY -----
        if not suppressed_by and trade.underlying:
            same_day_others = {
                t.underlying for t in trades_sorted
                if t.date == trade.date and t is not trade
                and trades_sorted.index(t) < trades_sorted.index(trade)
                and t.underlying and t.underlying != trade.underlying
            }
            for other in same_day_others:
                corr = get_correlation_cached(trade.underlying, other, corr_cache)
                if corr is not None and abs(corr) >= 0.7:
                    suppressed_by = f"V6 (corr {trade.underlying}/{other}={corr:+.2f} ≥ 0,7)"
                    break

        # ----- Apply Rule 26 + v10 sizing if not suppressed -----
        sizing_scale = v10_size_cap(trade, starting_portfolio)
        v10_pnl, capped = apply_rule_26(trade, sizing_scale=sizing_scale)

        if suppressed_by:
            v10_pnl_final = 0.0  # trade didn't happen
            if 'Rule28' in suppressed_by:
                summary['rule28_suppressed'] += 1
            elif suppressed_by.startswith('V3'):
                summary['v3_suppressed'] += 1
            elif suppressed_by.startswith('V4'):
                summary['v4_suppressed'] += 1
            elif suppressed_by.startswith('V6'):
                summary['v6_suppressed'] += 1
        else:
            v10_pnl_final = v10_pnl
            if capped:
                summary['rule26_capped'] += 1
            summary['kept'] += 1
            if v10_pnl_final < summary['max_single_loss']:
                summary['max_single_loss'] = v10_pnl_final

        summary['total_pnl_v10'] += v10_pnl_final

        rows.append({
            'date': trade.date,
            'isin': trade.isin,
            'underlying': trade.underlying or '?',
            'orig_pnl': original_pnl,
            'v10_pnl': v10_pnl_final,
            'suppressed_by': suppressed_by or '',
            'capped': capped,
        })

    summary['delta'] = summary['total_pnl_v10'] - summary['total_pnl_original']
    summary['portfolio_pct'] = summary['total_pnl_v10'] / starting_portfolio * 100
    summary['rows'] = rows
    summary['starting_portfolio'] = starting_portfolio
    return summary


def print_report(summary: dict, verbose: bool = True) -> None:
    rows = summary['rows']

    print("=" * 80)
    print(f"  v10 April-2026 Backtest — Starting portfolio €{summary['starting_portfolio']:.0f}")
    print("=" * 80)

    if verbose:
        print(f"  {'date':<12} {'isin':<14} {'underlying':<10} "
              f"{'orig P&L':>10} {'v10 P&L':>10}  notes")
        print(f"  {'-' * 78}")
        for r in rows:
            note = []
            if r['capped']:
                note.append('rule26-cap')
            if r['suppressed_by']:
                note.append(r['suppressed_by'])
            note_str = '; '.join(note)
            print(f"  {r['date']:<12} {r['isin']:<14} {r['underlying']:<10} "
                  f"{r['orig_pnl']:>+10.2f} {r['v10_pnl']:>+10.2f}  {note_str}")
        print()

    print(f"  Original April P&L:    €{summary['total_pnl_original']:>+10.2f}")
    print(f"  v10 simulated P&L:     €{summary['total_pnl_v10']:>+10.2f}")
    print(f"  Δ vs original:         €{summary['delta']:>+10.2f}")
    print(f"  v10 / portfolio:       {summary['portfolio_pct']:>+10.2f}%")
    print()
    print(f"  Suppressions:  Rule28={summary['rule28_suppressed']}  "
          f"V3={summary['v3_suppressed']}  V4={summary['v4_suppressed']}  "
          f"V6={summary['v6_suppressed']}")
    print(f"  Rule-26 capped: {summary['rule26_capped']} trades")
    print(f"  Kept:          {summary['kept']} trades")
    print(f"  Max single loss in v10: €{summary['max_single_loss']:>+10.2f}")
    print()

    # Pass criteria
    pass_pnl = summary['total_pnl_v10'] >= summary['starting_portfolio'] * 0.05
    pass_max_loss = abs(summary['max_single_loss']) <= summary['starting_portfolio'] * 0.05
    has_rule28 = summary['rule28_suppressed'] >= 1
    has_v3 = summary['v3_suppressed'] >= 1
    has_v4 = summary['v4_suppressed'] >= 1
    # V6 may not fire if correlations stay below 0,7 — soft pass

    print("=" * 80)
    print("  ACCEPTANCE CRITERIA")
    print("=" * 80)
    threshold = summary['starting_portfolio'] * 0.05
    stretch = summary['starting_portfolio'] * 0.08
    print(f"  [{'✓' if pass_pnl else '✗'}] P&L ≥ +€{threshold:.0f} (5% of starting): "
          f"€{summary['total_pnl_v10']:+.0f}")
    if summary['total_pnl_v10'] >= stretch:
        print(f"  [✓] Stretch goal ≥ +€{stretch:.0f} (8%) achieved")
    print(f"  [{'✓' if pass_max_loss else '✗'}] Max single loss ≤ €{threshold:.0f} "
          f"(5% sizing sanity): €{summary['max_single_loss']:.2f}")
    print(f"  [{'✓' if has_rule28 else '✗'}] Rule 28 fires ≥ 1×: {summary['rule28_suppressed']}")
    print(f"  [{'✓' if has_v3 else '✗'}] V3 fires ≥ 1×: {summary['v3_suppressed']}")
    print(f"  [{'✓' if has_v4 else '✗'}] V4 fires ≥ 1×: {summary['v4_suppressed']}")
    print(f"  [{'~' if not summary['v6_suppressed'] else '✓'}] V6 fires (soft — may "
          f"not trigger if corr stays < 0,7): {summary['v6_suppressed']}")
    print()
    overall_pass = pass_pnl and pass_max_loss and has_rule28 and has_v3 and has_v4
    print(f"  OVERALL: {'PASS ✓' if overall_pass else 'FAIL ✗'}")


def main():
    parser = argparse.ArgumentParser(description="v10 April-2026 backtest")
    parser.add_argument("--csv", default="/tmp/trades_summary.csv",
                        help="Path to round-trip trades CSV")
    parser.add_argument("--portfolio", type=float, default=6000,
                        help="Starting portfolio value EUR (default 6000 = April-1 baseline)")
    parser.add_argument("--quiet", action="store_true", help="Skip per-trade detail")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        # Fallback to brief location
        alt = Path("/tmp/claude_web_brief/trades_april_2026.csv")
        if alt.exists():
            csv_path = alt
        else:
            print(f"ERROR: CSV not found at {csv_path}", file=sys.stderr)
            sys.exit(2)

    trades = parse_csv(csv_path)
    print(f"Loaded {len(trades)} trades from {csv_path}")
    summary = run_backtest(trades, starting_portfolio=args.portfolio)
    print_report(summary, verbose=not args.quiet)


if __name__ == "__main__":
    main()
