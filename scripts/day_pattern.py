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
import argparse
import yfinance as yf


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
    if last_ret < -3:
        similar = h[h["ret"] <= -3].dropna(subset=["next_1d", "next_3d", "next_5d"])
        label = "<= -3%"
    elif last_ret < -1:
        similar = h[h["ret"] <= -1].dropna(subset=["next_1d", "next_3d", "next_5d"])
        label = "<= -1%"
    elif last_ret > 3:
        similar = h[h["ret"] >= 3].dropna(subset=["next_1d", "next_3d", "next_5d"])
        label = ">= +3%"
    elif last_ret > 1:
        similar = h[h["ret"] >= 1].dropna(subset=["next_1d", "next_3d", "next_5d"])
        label = ">= +1%"
    else:
        similar = h[(h["ret"] > -1) & (h["ret"] < 1)].dropna(subset=["next_1d", "next_3d", "next_5d"])
        label = "flat (-1% to +1%)"

    print(f"\n=== AFTER DAYS WITH {label} (n={len(similar)}) ===")
    if len(similar) > 0:
        print(f"Next day:  avg {similar['next_1d'].mean():+.2f}% | green {(similar['next_1d']>0).mean()*100:.0f}%")
        print(f"After 3d:  avg {similar['next_3d'].mean():+.2f}% | green {(similar['next_3d']>0).mean()*100:.0f}%")
        print(f"After 5d:  avg {similar['next_5d'].mean():+.2f}% | green {(similar['next_5d']>0).mean()*100:.0f}%")

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
