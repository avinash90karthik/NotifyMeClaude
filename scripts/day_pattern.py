#!/usr/bin/env python3
"""
Recent Day Pattern Analysis
===========================
Shows the last 5 trading days and the forward-return distribution
after similar days (same sign/magnitude band) in this stock's own
history. Also reports consecutive red-day streak patterns.

Usage:
    python3 day_pattern.py SYMBOL

Exit codes:
    0 = success
    1 = symbol or data fetch error
"""
import sys
import os
import argparse
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.conditional_stats import fwd_distribution_per_day


def main():
    parser = argparse.ArgumentParser(description="Recent Day Pattern Analysis")
    parser.add_argument("symbol", type=str)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="2y")
    except Exception as e:
        print(f"ERROR: yfinance history failed for {symbol}: {e}", file=sys.stderr)
        sys.exit(1)

    if h is None or len(h) < 30:
        print(f"ERROR: insufficient history for {symbol}", file=sys.stderr)
        sys.exit(1)

    h = h.copy()
    h["ret"] = h["Close"].pct_change() * 100
    h["next_1d"] = h["ret"].shift(-1)
    h["next_3d"] = h["Close"].pct_change(3).shift(-3) * 100
    h["next_5d"] = h["Close"].pct_change(5).shift(-5) * 100

    print(f"=== LAST 5 TRADING DAYS: {symbol} ===")
    for i in range(-5, 0):
        d = h.iloc[i]
        print(f"  {d.name.strftime('%d.%m')} Close: {d['Close']:.2f} Change: {d['ret']:+.2f}%")

    streak = 0
    for i in range(len(h) - 1, -1, -1):
        if h["ret"].iloc[i] < 0:
            streak += 1
        else:
            break
    print(f"\nCurrent red streak: {streak} days")

    last_ret = float(h["ret"].iloc[-1])
    dist = fwd_distribution_per_day(h, last_ret, max_horizon=5)
    label = dist["band"]
    by_day = dist["by_day"]
    n_max = max((v["n"] for v in by_day.values()), default=0)

    print(f"\n=== AFTER DAYS WITH {label} (n={n_max}) ===")
    for d_label, d_key in [("Next day", 1), ("After 3d", 3), ("After 5d", 5)]:
        entry = by_day.get(d_key)
        if entry is None:
            continue
        print(f"{d_label}:  avg {entry['mean']:+.2f}% | green {entry['green']:.0f}%")

    if streak >= 2:
        h["red"] = h["ret"] < 0
        h["red_streak"] = h["red"].groupby((~h["red"]).cumsum()).cumsum()
        multi = h[h["red_streak"] >= streak].dropna(subset=["next_1d"])
        print(f"\n=== AFTER {streak}+ RED DAYS IN A ROW (n={len(multi)}) ===")
        if len(multi) > 0:
            print(f"Next day:  avg {multi['next_1d'].mean():+.2f}% | green {(multi['next_1d']>0).mean()*100:.0f}%")

    sys.exit(0)


if __name__ == "__main__":
    main()
