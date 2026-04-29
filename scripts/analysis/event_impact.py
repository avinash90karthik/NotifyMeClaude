#!/usr/bin/env python3
"""
Event Impact — Big Moves Reaction
=================================
For a given symbol, list all days with |return| > threshold over the
past 6 months and the next-day reaction. Used in Step 1.9 to estimate
how this stock typically behaves around catalysts.

Usage:
    python3 event_impact.py SYMBOL [--threshold 3.0]

Exit codes:
    0 = success
    1 = symbol or data fetch error
"""
import sys
import argparse
import yfinance as yf


def main():
    parser = argparse.ArgumentParser(description="Event Impact — Big Moves Reaction")
    parser.add_argument("symbol", type=str)
    parser.add_argument("--threshold", type=float, default=3.0, help="Absolute return %% threshold for 'big move'")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="6mo")
    except Exception as e:
        print(f"ERROR: yfinance history failed for {symbol}: {e}", file=sys.stderr)
        sys.exit(1)

    if h is None or len(h) < 20:
        print(f"ERROR: insufficient history for {symbol}", file=sys.stderr)
        sys.exit(1)

    h = h.copy()
    h["ret"] = h["Close"].pct_change() * 100
    big = h[h["ret"].abs() > args.threshold]

    print(f"=== BIG MOVES (|{args.threshold:.1f}%|+) for {symbol} ===")
    bounce = 0
    for i in range(len(big)):
        idx = big.index[i]
        pos = h.index.get_loc(idx)
        r = float(big["ret"].iloc[i])
        d = idx.strftime("%d.%m.%y")
        if pos + 1 < len(h):
            nxt = float(h["ret"].iloc[pos + 1])
            print(f"  {d}: {r:+.2f}% -> next day: {nxt:+.2f}%")
            if r < 0 and nxt > 0:
                bounce += 1

    print()
    down_moves = big[big["ret"] < 0]
    if len(down_moves) > 0:
        print(f"Bounce rate after big drops: {bounce}/{len(down_moves)}")

    sys.exit(0)


if __name__ == "__main__":
    main()
