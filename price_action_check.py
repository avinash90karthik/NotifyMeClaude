#!/usr/bin/env python3
"""
Price-Action Reality Check (CLAUDE.md Rule 14)
==============================================
MACD/RSI turn signals are not bullish triggers on their own.
Verify with actual green-day counts over the last 5/10/20 trading days
so "bullisch" claims must survive the empirical green-day floor.

Usage:
    python3 price_action_check.py SYMBOL

Exit codes:
    0 = success
    1 = symbol or data fetch error
"""
import sys
import argparse
import yfinance as yf


def main():
    parser = argparse.ArgumentParser(description="Price-Action Reality Check (Rule 14)")
    parser.add_argument("symbol", type=str)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="2mo")
    except Exception as e:
        print(f"ERROR: yfinance history failed for {symbol}: {e}", file=sys.stderr)
        sys.exit(1)

    if h is None or len(h) < 21:
        print(f"ERROR: insufficient history for {symbol}", file=sys.stderr)
        sys.exit(1)

    h = h.copy()
    h["ret"] = h["Close"].pct_change() * 100

    first20 = h["Close"].iloc[-20]
    first10 = h["Close"].iloc[-10]
    first5 = h["Close"].iloc[-5]
    last = h["Close"].iloc[-1]

    trend20 = (last / first20 - 1) * 100
    trend10 = (last / first10 - 1) * 100
    trend5 = (last / first5 - 1) * 100

    greens20 = int(sum(1 for i in range(-20, 0) if h["ret"].iloc[i] > 0))
    greens10 = int(sum(1 for i in range(-10, 0) if h["ret"].iloc[i] > 0))
    greens5 = int(sum(1 for i in range(-5, 0) if h["ret"].iloc[i] > 0))

    print(f"=== Price-Action Reality Check: {symbol} ===")
    print(f"{'Window':<8} {'Trend':>10} {'Greens':>10}")
    print(f"{'20d':<8} {trend20:>+9.2f}% {greens20:>5}/20")
    print(f"{'10d':<8} {trend10:>+9.2f}% {greens10:>5}/10")
    print(f"{'5d':<8} {trend5:>+9.2f}%  {greens5:>5}/5")
    print()

    if greens10 < 4:
        verdict = "RED phase — no turn confirmed"
    elif greens10 < 5:
        verdict = "Mixed — below 5/10 green floor, not a confirmed turn"
    elif trend5 <= 0 and greens5 <= 2:
        verdict = "Stabilization only — MACD may turn positive without price follow-through"
    else:
        verdict = "Confirmed up-flow — green floor met AND recent trend positive"

    print(f"VERDICT: {verdict}")
    print()
    print("Use this in Step 1.4 reality check — if MACD/RSI 'bullish turn' conflicts with")
    print("green-day count < 5/10, weight the indicator signal DOWN (-5% to -10% Confidence).")
    sys.exit(0)


if __name__ == "__main__":
    main()
