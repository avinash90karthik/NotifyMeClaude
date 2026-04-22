#!/usr/bin/env python3
"""
Indicator Context Check (CLAUDE.md Rule 16)
===========================================
Before calling any indicator value "bullish" or "bearish" (RSI level,
BB position, distance-to-high), compute this stock's own historical
forward distribution in that band. Range-stock heuristics are
systematically wrong for trend stocks - prove the direction from this
stock's own history.

Reports sample sizes as [SOLID n>=30 / WEAK n=15-29 / THIN n<15] and
Fwd-5d Green-Rate per band. Each axis also gets a sigmoid-derived
Confidence-Adjust (continuous, no bucket cliffs). Aggregation rule:
take the STRONGEST single axis as Rating 1 input - do not sum across
RSI/BB/DistHigh because those axes are positively correlated.

Stock is also classified as TREND vs Range based on SMA200 distance,
1Y gain, max drawdown.

Usage:
    python3 indicator_context.py SYMBOL --expected-price X.XX --expected-date YYYY-MM-DD
    python3 indicator_context.py SYMBOL  (skip sanity check)

The sanity check aborts with exit code 2 if yfinance history is stale
(>2 trading days old) or close diverges >0.5% from expected, so the
analysis can't silently continue on stale data.

Exit codes:
    0 = success
    1 = symbol or data fetch error
    2 = sanity check failed (stale data)
"""
import sys
import argparse
from datetime import date
import numpy as np
import yfinance as yf

# Allow `from lib.X` when invoked as `python3 scripts/indicator_context.py`
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.indicators import sigmoid_adjust


SOLID_N = 30
WEAK_N = 15


def sample_tag(n: int) -> str:
    if n >= SOLID_N:
        return "SOLID"
    if n >= WEAK_N:
        return "WEAK"
    return "THIN"


def report(name: str, subset, total: int) -> dict | None:
    """Print band stats and return a dict with green-rate / sample / sigmoid adjust.

    Returns None when the band has no usable forward data (so the caller can
    skip it during aggregation).
    """
    n = len(subset)
    if n == 0:
        print(f"  {name}: n=0 - no history")
        return None
    tag = sample_tag(n)
    fwd5 = subset["fwd_5d"].dropna()
    if len(fwd5) == 0:
        print(f"  {name}: n={n} [{tag}] - no fwd data")
        return None
    green_rate = (fwd5 > 0).mean() * 100
    avg = fwd5.mean()
    med = fwd5.median()
    pct_time = n / total * 100
    adjust = sigmoid_adjust(green_rate / 100.0, n)
    print(
        f"  {name}: n={n} [{tag}] ({pct_time:.0f}% of time) | "
        f"fwd 5d avg {avg:+.2f}% | median {med:+.2f}% | "
        f"green {green_rate:.0f}% | adjust {adjust:+.2f}%"
    )
    return {
        "name": name,
        "n": n,
        "tag": tag,
        "green_rate": green_rate,
        "avg": avg,
        "adjust": adjust,
    }


def print_aggregation(axes: list[dict | None]) -> None:
    """Print the AGGREGATION block. Strongest axis (max |adjust|) is the Rating-1 input."""
    print("== 6. AGGREGATION (Rating 1 input) ==")
    valid = [a for a in axes if a is not None]
    if not valid:
        print("  No usable axis - Rating 1 defaults to neutral (5/5).")
        return
    for a in valid:
        print(
            f"  {a['name']:38s}  green={a['green_rate']:.0f}% n={a['n']} {a['tag']}  "
            f"adjust={a['adjust']:+.2f}%"
        )
    strongest = max(valid, key=lambda a: abs(a["adjust"]))
    direction = "LONG bullish" if strongest["adjust"] > 0 else (
        "LONG bearish" if strongest["adjust"] < 0 else "neutral"
    )
    print()
    print(
        f"  STRONGEST AXIS: {strongest['name']}  "
        f"adjust={strongest['adjust']:+.2f}%  ({direction})"
    )
    print(
        "  -> Use ONLY this single adjust as Rating 1 input. "
        "Do NOT sum across axes (they are correlated for trend stocks)."
    )


def main():
    parser = argparse.ArgumentParser(description="Indicator Context Check (Rule 16)")
    parser.add_argument("symbol", type=str)
    parser.add_argument("--expected-price", type=float, default=0.0, help="Close from collect_data.py for sanity check")
    parser.add_argument("--expected-date", type=str, default="", help="Last trading day YYYY-MM-DD for sanity check")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="3y")
    except Exception as e:
        print(f"ERROR: yfinance history failed for {symbol}: {e}", file=sys.stderr)
        sys.exit(1)

    if h is None or len(h) < 60:
        print(f"ERROR: insufficient history for {symbol}", file=sys.stderr)
        sys.exit(1)

    last_date = h.index[-1].date()
    last_close = float(h["Close"].iloc[-1])

    if args.expected_date:
        try:
            expected_d = date.fromisoformat(args.expected_date)
            day_gap = abs((last_date - expected_d).days)
            if day_gap > 4:
                print(f"ABORT: history ends {last_date}, expected {args.expected_date} (diff {day_gap}d)")
                print(f"   yfinance cache or delay. STOP - do not continue analysis on stale data.")
                sys.exit(2)
        except ValueError:
            print(f"WARN: --expected-date '{args.expected_date}' unparseable, skipping date sanity", file=sys.stderr)

    if args.expected_price > 0:
        pct_diff = abs(last_close / args.expected_price - 1) * 100
        if pct_diff > 0.5:
            print(f"ABORT: history close {last_close:.2f} vs expected {args.expected_price:.2f} ({pct_diff:.2f}% diff)")
            print(f"   data sources inconsistent. STOP.")
            sys.exit(2)

    print(f"Sanity OK: latest history date {last_date}, close {last_close:.2f}")
    print()

    delta = h["Close"].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1 / 14, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, min_periods=14).mean()
    h["RSI"] = 100 - (100 / (1 + gain / loss))

    h["SMA20"] = h["Close"].rolling(20).mean()
    h["STD20"] = h["Close"].rolling(20).std()
    h["BB_POS"] = (h["Close"] - (h["SMA20"] - 2 * h["STD20"])) / (4 * h["STD20"]) * 100

    h["high_3m"] = h["Close"].rolling(60).max()
    h["dist_high"] = (h["Close"] / h["high_3m"] - 1) * 100

    for d in [1, 3, 5, 10]:
        h[f"fwd_{d}d"] = h["Close"].pct_change(d).shift(-d) * 100

    now = h.iloc[-1].copy()
    h_hist = h.dropna(subset=["RSI", "BB_POS", "dist_high", "fwd_5d", "fwd_10d"])
    total = len(h_hist)

    print(f"NOW ({last_date}): RSI {now['RSI']:.1f} | BB-Pos {now['BB_POS']:.1f}% | DistHigh {now['dist_high']:+.2f}%")
    print(f"History for band stats: {total} days ({h_hist.index[0].date()} to {h_hist.index[-1].date()})")
    print()

    rsi_now = float(now["RSI"])
    bb_now = float(now["BB_POS"])
    d_now = float(now["dist_high"])

    axes: list[dict | None] = []

    print("== 1. RSI BAND (current value +/-5) ==")
    band = h_hist[(h_hist["RSI"] >= rsi_now - 5) & (h_hist["RSI"] <= rsi_now + 5)]
    rsi_axis = report(f"RSI {rsi_now-5:.0f}-{rsi_now+5:.0f}", band, total)
    axes.append(rsi_axis)
    if rsi_now >= 60:
        report("RSI >70 (textbook overbought)", h_hist[h_hist["RSI"] > 70], total)
    if rsi_now <= 40:
        report("RSI <30 (textbook oversold)", h_hist[h_hist["RSI"] < 30], total)
    print()

    print("== 2. BOLLINGER POSITION ==")
    if bb_now > 100:
        bb_axis = report("BB >100% (above upper band)", h_hist[h_hist["BB_POS"] > 100], total)
    elif bb_now > 70:
        bb_axis = report("BB 70-100% (upper third)", h_hist[(h_hist["BB_POS"] > 70) & (h_hist["BB_POS"] <= 100)], total)
    elif bb_now < 0:
        bb_axis = report("BB <0% (below lower band)", h_hist[h_hist["BB_POS"] < 0], total)
    elif bb_now < 30:
        bb_axis = report("BB 0-30% (lower third)", h_hist[(h_hist["BB_POS"] >= 0) & (h_hist["BB_POS"] < 30)], total)
    else:
        bb_axis = report("BB 30-70% (middle)", h_hist[(h_hist["BB_POS"] >= 30) & (h_hist["BB_POS"] <= 70)], total)
    axes.append(bb_axis)
    print()

    print("== 3. DISTANCE TO 3M-HIGH ==")
    dist_axis: dict | None = None
    if d_now > -3:
        near = h_hist[h_hist["dist_high"] > -3]
        dist_axis = report("Within 3% of 3M-high", near, total)
        broken = 0
        n_checked = 0
        for i in range(len(h_hist) - 10):
            if h_hist["dist_high"].iloc[i] > -3:
                n_checked += 1
                if (h_hist["Close"].iloc[i + 1 : i + 11] > h_hist["high_3m"].iloc[i]).any():
                    broken += 1
        if n_checked > 0:
            br = broken / n_checked * 100
            tag = sample_tag(n_checked)
            print(f"  Break-rate 3M-high in 10d: {br:.0f}% (n={n_checked}) [{tag}]")
    elif d_now < -15:
        far = h_hist[h_hist["dist_high"] < -15]
        dist_axis = report("More than -15% from 3M-high (deep drawdown)", far, total)
    else:
        mid = h_hist[(h_hist["dist_high"] >= -15) & (h_hist["dist_high"] <= -3)]
        dist_axis = report("Between -15% and -3% from 3M-high", mid, total)
    axes.append(dist_axis)
    print()

    print("== 4. COMBO ==")
    combo_axis: dict | None = None
    if rsi_now >= 60 and bb_now > 100:
        combo_axis = report("RSI >=60 AND BB >100%", h_hist[(h_hist["RSI"] >= 60) & (h_hist["BB_POS"] > 100)], total)
    elif rsi_now <= 40 and bb_now < 30:
        combo_axis = report("RSI <=40 AND BB <30%", h_hist[(h_hist["RSI"] <= 40) & (h_hist["BB_POS"] < 30)], total)
    else:
        print("  (no extreme combo active - combo check skipped)")
    if combo_axis is not None:
        axes.append(combo_axis)
    print()

    print("== 5. ARCHETYPE ==")
    sma200 = h["Close"].rolling(200).mean().iloc[-1]
    dist_sma200 = (float(now["Close"]) / sma200 - 1) * 100 if sma200 and not np.isnan(sma200) else 0.0
    max_dd_1y = 0.0
    h1y = h.tail(252)
    for i in range(len(h1y)):
        peak = h1y["Close"].iloc[: i + 1].max()
        dd = (h1y["Close"].iloc[i] / peak - 1) * 100
        if dd < max_dd_1y:
            max_dd_1y = dd
    gain_1y = (h.iloc[-1]["Close"] / h.iloc[-252]["Close"] - 1) * 100 if len(h) >= 252 else None
    gain_str = f"{gain_1y:+.1f}%" if gain_1y is not None else "n/a"
    print(f"  Dist SMA200: {dist_sma200:+.1f}% | 1Y gain: {gain_str} | Max DD 1Y: {max_dd_1y:.1f}%")
    is_trend = dist_sma200 > 20 and gain_1y is not None and gain_1y > 100 and max_dd_1y > -25
    if is_trend:
        print("  Classification: TREND-STOCK (range heuristics are historically wrong here)")
    else:
        print("  Classification: Range/Normal-Stock (range heuristics applicable)")
    print()

    print_aggregation(axes)

    sys.exit(0)


if __name__ == "__main__":
    main()
