#!/usr/bin/env python3
"""
Earnings Window Pattern Analysis
=================================
Automatically analyzes how a symbol has historically moved around earnings.

Usage:
    python3 earnings_pattern.py SYMBOL [--days-threshold N]

Behavior:
    - Fetches next earnings date from yfinance
    - If earnings are >N days away (default 30): exits with code 0, prints "NOT NEAR"
    - If earnings are <=N days away: fetches last 10 earnings, analyzes price action
      around each event (T-5d, T-3d, T-1d, T+1d, T+3d, T+5d), prints stats

Exit codes:
    0 = success (analysis done OR earnings not near)
    1 = symbol or data fetch error
    2 = no earnings data available
"""
import sys
import argparse
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd

# Allow `from lib.X` when invoked as `python3 scripts/earnings_pattern.py`
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))

from lib.indicators import sigmoid_adjust


def fetch_earnings_dates(symbol: str) -> pd.DataFrame | None:
    t = yf.Ticker(symbol)
    try:
        ed = t.get_earnings_dates(limit=40)
    except Exception:
        try:
            ed = t.earnings_dates
        except Exception as e:
            print(f"ERROR: yfinance earnings_dates failed for {symbol}: {e}", file=sys.stderr)
            return None
    if ed is None or len(ed) == 0:
        return None
    return ed


def get_next_earnings(ed: pd.DataFrame) -> pd.Timestamp | None:
    now = pd.Timestamp.now(tz="America/New_York")
    future = ed[ed.index > now]
    if len(future) == 0:
        return None
    return future.index.min()


def get_historical_dates(ed: pd.DataFrame, limit: int = 10) -> list[pd.Timestamp]:
    now = pd.Timestamp.now(tz="America/New_York")
    past = ed[ed.index < now].sort_index(ascending=False)
    return list(past.index[:limit])


def compute_window_stats(symbol: str, earnings_dates: list[pd.Timestamp],
                         trade_entry_day: int | None = None,
                         trade_exit_day: int | None = None) -> dict:
    """
    Compute pre/post-earnings price action.

    Legacy (backward) mode: T-X to T0 returns (how far was price X days before earnings).
    Trade-Window mode: if trade_entry_day/trade_exit_day are set, also compute
      interval returns T-entry_day → T-exit_day (actual trade P&L if held).
    """
    t = yf.Ticker(symbol)
    h = t.history(period="10y")
    if len(h) == 0:
        return {}

    results = {"T-5d": [], "T-3d": [], "T-1d": [], "T+1d": [], "T+3d": [], "T+5d": []}
    trade_returns: list[float] = []
    trade_returns_by_month: dict[int, list[float]] = {}
    per_event: list[dict] = []

    for ed_date in earnings_dates:
        # Find trading day at or after earnings
        idx_candidates = h.index[h.index >= ed_date]
        if len(idx_candidates) == 0:
            continue
        idx = idx_candidates[0]
        pos = h.index.get_loc(idx)

        def pct(fp, tp):
            if fp < 0 or tp >= len(h):
                return None
            return (h["Close"].iloc[tp] / h["Close"].iloc[fp] - 1) * 100

        row = {
            "date": ed_date.strftime("%Y-%m-%d"),
            "month": ed_date.month,
            "T-5d": pct(max(0, pos - 5), pos),
            "T-3d": pct(max(0, pos - 3), pos),
            "T-1d": pct(max(0, pos - 1), pos),
            "T+1d": pct(pos, min(len(h) - 1, pos + 1)),
            "T+3d": pct(pos, min(len(h) - 1, pos + 3)),
            "T+5d": pct(pos, min(len(h) - 1, pos + 5)),
        }

        # Trade-Window mode: interval return from entry_day to exit_day
        if trade_entry_day is not None and trade_exit_day is not None:
            entry_pos = pos - trade_entry_day
            exit_pos = pos - trade_exit_day
            if entry_pos >= 0 and exit_pos >= 0 and exit_pos < len(h):
                interval = pct(entry_pos, exit_pos)
                row["trade_window"] = interval
                if interval is not None:
                    trade_returns.append(interval)
                    trade_returns_by_month.setdefault(ed_date.month, []).append(interval)

        per_event.append(row)
        for k in ["T-5d", "T-3d", "T-1d", "T+1d", "T+3d", "T+5d"]:
            if row[k] is not None:
                results[k].append(row[k])

    stats = {}
    for k, vals in results.items():
        if vals:
            stats[k] = {
                "avg": sum(vals) / len(vals),
                "green_pct": sum(1 for v in vals if v > 0) / len(vals) * 100,
                "n": len(vals),
                "min": min(vals),
                "max": max(vals),
            }

    trade_stats = None
    if trade_returns:
        trade_stats = {
            "avg": sum(trade_returns) / len(trade_returns),
            "median": sorted(trade_returns)[len(trade_returns) // 2],
            "green_pct": sum(1 for v in trade_returns if v > 0) / len(trade_returns) * 100,
            "n": len(trade_returns),
            "min": min(trade_returns),
            "max": max(trade_returns),
            "entry_day": trade_entry_day,
            "exit_day": trade_exit_day,
            "by_month": {m: {
                "avg": sum(v) / len(v),
                "green_pct": sum(1 for x in v if x > 0) / len(v) * 100,
                "n": len(v),
            } for m, v in trade_returns_by_month.items()},
        }

    return {"per_event": per_event, "stats": stats, "trade_stats": trade_stats}


def classify_phase(days_to_earnings: int) -> str:
    if days_to_earnings < 0:
        return "POST-EARNINGS"
    if days_to_earnings <= 1:
        return "T-1d (day before earnings)"
    if days_to_earnings <= 3:
        return "T-3d to T-1d"
    if days_to_earnings <= 5:
        return "T-5d to T-3d"
    if days_to_earnings <= 10:
        return "T-10d to T-5d"
    if days_to_earnings <= 20:
        return "T-20d to T-10d (early)"
    return f"T-{days_to_earnings}d (very early)"


def print_banner(symbol: str):
    line = "=" * 72
    print(line)
    print(f"  EARNINGS WINDOW PATTERN — {symbol}")
    print(line)


def print_trade_window(result: dict, target_month: int | None = None):
    ts = result.get("trade_stats")
    if not ts:
        return
    print()
    print("  === TRADE-WINDOW MODE ===")
    print(f"  Entry: T-{ts['entry_day']}d  ->  Exit: T-{ts['exit_day']}d  (Interval held, n={ts['n']})")
    print()
    print(f"  {'Date':12} {'Month':6} {'Trade-Window Return':>22}")
    print("  " + "-" * 44)
    for row in result.get("per_event", []):
        tw = row.get("trade_window")
        tw_str = f"{tw:+7.2f}%" if tw is not None else "    n/a"
        month_str = pd.Timestamp(row["date"]).strftime("%b")
        mark = " ←" if target_month is not None and row.get("month") == target_month else ""
        print(f"  {row['date']}  {month_str:6} {tw_str:>22}{mark}")
    print("  " + "-" * 44)
    print(f"  Summary (all quarters): Ø {ts['avg']:+.2f}% | median {ts['median']:+.2f}% | green {ts['green_pct']:.0f}% | n={ts['n']}")
    print(f"                          range [{ts['min']:+.1f}% .. {ts['max']:+.1f}%]")

    if target_month is not None and target_month in ts["by_month"]:
        mb = ts["by_month"][target_month]
        month_name = pd.Timestamp(f"2020-{target_month:02d}-01").strftime("%B")
        print(f"  Same-month ({month_name}) quarters: Ø {mb['avg']:+.2f}% | green {mb['green_pct']:.0f}% | n={mb['n']}")
        if mb["n"] < 3:
            print(f"                          (THIN n<3 — directional hint, not hard signal)")

    print()
    print("  === CONFIDENCE-ADJUST (Trade-Window, sigmoid) ===")
    g = ts["green_pct"]
    avg = ts["avg"]
    n = ts["n"]
    # Earnings sample is structurally small (~10 quarters max).
    # SOLID at n>=8, WEAK at n=4-7, THIN below.
    long_adjust = sigmoid_adjust(g / 100.0, n, solid_n=8, weak_n=4)
    if abs(avg) < 0.3:
        long_adjust = 0.0
        note = " (gated: |avg|<0.3% -> no directional edge)"
    elif n < 4:
        note = " (THIN n<4: weight 0 - no adjust)"
    elif n < 8:
        note = " (WEAK n=4-7: half weight applied)"
    else:
        note = ""
    print(
        f"  Green-Rate {g:.0f}% | Avg {avg:+.2f}% | n={n}  ->  "
        f"LONG {long_adjust:+.2f}% / SHORT {-long_adjust:+.2f}%{note}"
    )


def print_near(symbol: str, next_ed: pd.Timestamp, days: int, result: dict):
    print(f"\n  Next Earnings: {next_ed.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"  Days to Earnings: {days}")
    print(f"  Phase: {classify_phase(days)}")
    print()

    per_event = result.get("per_event", [])
    stats = result.get("stats", {})

    if not per_event:
        print("  NO HISTORICAL DATA — not enough earnings events in price history.")
        return

    print("  === PER EVENT ===")
    print(f"  {'Date':12} {'T-5d':>8} {'T-3d':>8} {'T-1d':>8} {'T+1d':>8} {'T+3d':>8} {'T+5d':>8}")
    print("  " + "-" * 68)
    for row in per_event:
        vals = []
        for k in ["T-5d", "T-3d", "T-1d", "T+1d", "T+3d", "T+5d"]:
            v = row.get(k)
            vals.append(f"{v:+7.2f}%" if v is not None else "    n/a")
        print(f"  {row['date']}  {'  '.join(vals)}")

    print("  " + "-" * 68)
    print("  === AVERAGES ===")
    for k in ["T-5d", "T-3d", "T-1d", "T+1d", "T+3d", "T+5d"]:
        if k in stats:
            s = stats[k]
            print(f"  {k}: avg {s['avg']:+6.2f}% | green {s['green_pct']:3.0f}% | n={s['n']} | range [{s['min']:+.1f}% .. {s['max']:+.1f}%]")

    # Interpretation
    print()
    print("  === INTERPRETATION ===")
    pre = [stats[k]["avg"] for k in ["T-5d", "T-3d", "T-1d"] if k in stats]
    post = [stats[k]["avg"] for k in ["T+1d", "T+3d", "T+5d"] if k in stats]
    pre_green = [stats[k]["green_pct"] for k in ["T-5d", "T-3d", "T-1d"] if k in stats]
    post_green = [stats[k]["green_pct"] for k in ["T+1d", "T+3d", "T+5d"] if k in stats]

    if pre and post:
        pre_avg = sum(pre) / len(pre)
        post_avg = sum(post) / len(post)
        pre_green_avg = sum(pre_green) / len(pre_green)
        post_green_avg = sum(post_green) / len(post_green)

        print(f"  Pre-Earnings  (T-5d..T-1d): avg {pre_avg:+.2f}% | green {pre_green_avg:.0f}%")
        print(f"  Post-Earnings (T+1d..T+5d): avg {post_avg:+.2f}% | green {post_green_avg:.0f}%")
        print()

        if post_avg > pre_avg + 0.5 and post_green_avg > 60:
            print("  EDGE: Post-Earnings (move happens at/after earnings day)")
            print("        -> LONG BEFORE earnings is historically WEAK")
        elif pre_avg > post_avg + 0.5 and pre_green_avg > 60:
            print("  EDGE: Pre-Earnings drift (classic run-up)")
            print("        -> LONG in last days before earnings is bullish")
        else:
            print("  EDGE: NO clear pattern (coin-flip)")
            print("        -> Pre/Post-earnings indeterminate")

    # Warning for current phase
    print()
    current_bucket = None
    if 5 < days <= 10:
        current_bucket = None  # Zwischen T-10 und T-5, kein direkter Bucket
        relevant = ["T-5d"]
    elif 3 < days <= 5:
        relevant = ["T-5d", "T-3d"]
    elif 1 < days <= 3:
        relevant = ["T-3d", "T-1d"]
    elif 0 <= days <= 1:
        relevant = ["T-1d"]
    else:
        relevant = []

    if relevant:
        avgs = [stats[k]["avg"] for k in relevant if k in stats]
        greens = [stats[k]["green_pct"] for k in relevant if k in stats]
        if avgs:
            avg = sum(avgs) / len(avgs)
            green = sum(greens) / len(greens)
            print(f"  CURRENT PHASE ({classify_phase(days)}):")
            print(f"  -> Historically {avg:+.2f}% / {green:.0f}% green in this window")
            if avg < 0 or green < 50:
                print("  WARNING: current phase is historically WEAK for LONG")
                print("     (Backward-mode signal - SECONDARY context only when Trade-Window mode is also run)")


def print_not_near(symbol: str, next_ed: pd.Timestamp | None, days: int | None, threshold: int):
    print()
    if next_ed is None:
        print(f"  NO FUTURE EARNINGS DATE found for {symbol}")
        print(f"  -> Earnings window pattern check: SKIPPED")
    else:
        print(f"  Next Earnings: {next_ed.strftime('%Y-%m-%d')}")
        print(f"  Days to Earnings: {days}")
        print(f"  Threshold: {threshold} days")
        print(f"  -> Earnings not near (>{threshold}d) - pattern check SKIPPED")
        print(f"  -> Standard day-pattern analysis (Step 1.8) is sufficient")
    print()


def main():
    parser = argparse.ArgumentParser(description="Earnings window pattern analysis")
    parser.add_argument("symbol", help="Ticker symbol")
    parser.add_argument("--days-threshold", type=int, default=30,
                        help="Only run full analysis if earnings within N days (default 30)")
    parser.add_argument("--force", action="store_true",
                        help="Run full analysis even if earnings not near")
    parser.add_argument("--trade-entry", type=int, default=None,
                        help="Trade-window mode: entry day (e.g. 8 for T-8d). Pair with --trade-exit.")
    parser.add_argument("--trade-exit", type=int, default=None,
                        help="Trade-window mode: exit day (e.g. 3 for T-3d). Must be < --trade-entry.")
    parser.add_argument("--same-month", action="store_true",
                        help="Highlight historical quarters in same calendar month as next earnings.")
    args = parser.parse_args()

    if (args.trade_entry is None) != (args.trade_exit is None):
        print("ERROR: --trade-entry and --trade-exit must be used together", file=sys.stderr)
        sys.exit(1)
    if args.trade_entry is not None and args.trade_exit >= args.trade_entry:
        print("ERROR: --trade-exit must be < --trade-entry (entry is further from earnings)", file=sys.stderr)
        sys.exit(1)

    symbol = args.symbol.upper()
    print_banner(symbol)

    ed = fetch_earnings_dates(symbol)
    if ed is None or len(ed) == 0:
        print(f"\n  NO EARNINGS DATA available for {symbol}")
        print(f"  -> Skipping (most likely: index, commodity, futures)")
        sys.exit(0)

    next_ed = get_next_earnings(ed)
    days = None
    if next_ed is not None:
        now = pd.Timestamp.now(tz="America/New_York")
        days = (next_ed - now).days

    near = days is not None and days <= args.days_threshold

    if not near and not args.force:
        print_not_near(symbol, next_ed, days, args.days_threshold)
        sys.exit(0)

    # Run full analysis
    historical = get_historical_dates(ed, limit=10)
    if len(historical) == 0:
        print("\n  NO HISTORICAL EARNINGS DATES in yfinance data")
        sys.exit(2)

    result = compute_window_stats(symbol, historical,
                                  trade_entry_day=args.trade_entry,
                                  trade_exit_day=args.trade_exit)
    if not result.get("per_event"):
        print("\n  COULD NOT COMPUTE pattern (price history insufficient)")
        sys.exit(2)

    print_near(symbol, next_ed, days, result)

    target_month = next_ed.month if args.same_month else None
    print_trade_window(result, target_month=target_month)
    print()


if __name__ == "__main__":
    main()
