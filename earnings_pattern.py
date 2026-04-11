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


def compute_window_stats(symbol: str, earnings_dates: list[pd.Timestamp]) -> dict:
    t = yf.Ticker(symbol)
    h = t.history(period="10y")
    if len(h) == 0:
        return {}

    results = {"T-5d": [], "T-3d": [], "T-1d": [], "T+1d": [], "T+3d": [], "T+5d": []}
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
            "T-5d": pct(max(0, pos - 5), pos),
            "T-3d": pct(max(0, pos - 3), pos),
            "T-1d": pct(max(0, pos - 1), pos),
            "T+1d": pct(pos, min(len(h) - 1, pos + 1)),
            "T+3d": pct(pos, min(len(h) - 1, pos + 3)),
            "T+5d": pct(pos, min(len(h) - 1, pos + 5)),
        }
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
    return {"per_event": per_event, "stats": stats}


def classify_phase(days_to_earnings: int) -> str:
    if days_to_earnings < 0:
        return "POST-EARNINGS"
    if days_to_earnings <= 1:
        return "T-1d (Tag vor Earnings)"
    if days_to_earnings <= 3:
        return "T-3d bis T-1d"
    if days_to_earnings <= 5:
        return "T-5d bis T-3d"
    if days_to_earnings <= 10:
        return "T-10d bis T-5d"
    if days_to_earnings <= 20:
        return "T-20d bis T-10d (frueh)"
    return f"T-{days_to_earnings}d (sehr frueh)"


def print_banner(symbol: str):
    line = "=" * 72
    print(line)
    print(f"  EARNINGS WINDOW PATTERN — {symbol}")
    print(line)


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
            print("  EDGE: Post-Earnings (Action kommt am/nach Earnings-Day)")
            print("        → LONG VOR Earnings ist historisch SCHWACH")
        elif pre_avg > post_avg + 0.5 and pre_green_avg > 60:
            print("  EDGE: Pre-Earnings-Drift (klassischer Run-Up)")
            print("        → LONG in letzten Tagen vor Earnings bullish")
        else:
            print("  EDGE: KEIN klares Muster (Coin-Flip)")
            print("        → Pre/Post-Earnings unbestimmt")

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
            print(f"  AKTUELLE PHASE ({classify_phase(days)}):")
            print(f"  → Historisch {avg:+.2f}% / {green:.0f}% green in diesem Fenster")
            if avg < 0 or green < 50:
                print(f"  ⚠  WARNING: Aktuelle Phase ist historisch SCHWACH für LONG")
                print(f"     → Confidence-Abzug -5% wenn LONG-Trade geplant")


def print_not_near(symbol: str, next_ed: pd.Timestamp | None, days: int | None, threshold: int):
    print()
    if next_ed is None:
        print(f"  NO FUTURE EARNINGS DATE found for {symbol}")
        print(f"  → Earnings-Window-Pattern check: SKIPPED")
    else:
        print(f"  Next Earnings: {next_ed.strftime('%Y-%m-%d')}")
        print(f"  Days to Earnings: {days}")
        print(f"  Threshold: {threshold} days")
        print(f"  → Earnings not near (>{threshold}d) — pattern check SKIPPED")
        print(f"  → Standard day-pattern analysis (Step 1.8) reicht aus")
    print()


def main():
    parser = argparse.ArgumentParser(description="Earnings window pattern analysis")
    parser.add_argument("symbol", help="Ticker symbol")
    parser.add_argument("--days-threshold", type=int, default=30,
                        help="Only run full analysis if earnings within N days (default 30)")
    parser.add_argument("--force", action="store_true",
                        help="Run full analysis even if earnings not near")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    print_banner(symbol)

    ed = fetch_earnings_dates(symbol)
    if ed is None or len(ed) == 0:
        print(f"\n  NO EARNINGS DATA available for {symbol}")
        print(f"  → Skipping (most likely: index, commodity, futures)")
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

    result = compute_window_stats(symbol, historical)
    if not result.get("per_event"):
        print("\n  COULD NOT COMPUTE pattern (price history insufficient)")
        sys.exit(2)

    print_near(symbol, next_ed, days, result)
    print()


if __name__ == "__main__":
    main()
