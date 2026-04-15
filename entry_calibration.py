#!/usr/bin/env python3
"""
Entry Calibration — Intraday Dip Stats + Realistic Buy Range
============================================================
For a symbol, compute:
  - Median/P25 open-to-low dip over last 60 trading days
  - Frequency of dips >1% and >2%
  - Hour of day the daily low typically forms (last 30 days, 1h bars)
  - Realistic buy range = MIN(median dip, 0.5*ATR) to P25 dip

Output feeds Step 3 Optimal Entry block so Limit levels are set
datengetrieben, not at Close.

Usage:
    python3 entry_calibration.py SYMBOL

Exit codes:
    0 = success
    1 = symbol or data fetch error
"""
import sys
import argparse
from collections import Counter
import numpy as np
import pandas as pd
import yfinance as yf


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period).mean()


def main():
    parser = argparse.ArgumentParser(description="Intraday dip statistics for entry calibration")
    parser.add_argument("symbol", type=str)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    try:
        t = yf.Ticker(symbol)
        daily = t.history(period="3mo")
    except Exception as e:
        print(f"ERROR: yfinance daily history failed for {symbol}: {e}", file=sys.stderr)
        sys.exit(1)

    if daily is None or len(daily) < 20:
        print(f"ERROR: insufficient daily history for {symbol}", file=sys.stderr)
        sys.exit(1)

    daily = daily.copy()
    daily["dip_pct"] = (daily["Open"] - daily["Low"]) / daily["Open"] * 100
    dips = daily["dip_pct"].dropna().tail(60)

    atr_val = float(calc_atr(daily["High"], daily["Low"], daily["Close"], period=14).iloc[-1])
    last_close = float(daily["Close"].iloc[-1])
    atr_pct = atr_val / last_close * 100
    open_today = float(daily["Open"].iloc[-1])
    low_today = float(daily["Low"].iloc[-1])
    dip_today_pct = (open_today - low_today) / open_today * 100 if open_today > 0 else 0.0
    atr_used_pct = dip_today_pct / atr_pct * 100 if atr_pct > 0 else 0.0

    median_dip = float(dips.median())
    p25_dip = float(dips.quantile(0.25))
    p75_dip = float(dips.quantile(0.75))
    n_dip_over_1 = int((dips > 1).sum())
    n_dip_over_2 = int((dips > 2).sum())

    print(f"=== Entry Calibration: {symbol} ===")
    print(f"Close={last_close:.2f} | Open today={open_today:.2f} | Low today={low_today:.2f}")
    print(f"ATR(14)={atr_val:.2f} ({atr_pct:.2f}%)")
    print(f"Today's dip so far: {dip_today_pct:.2f}% ({atr_used_pct:.0f}% of ATR used)")
    print()
    print("Intraday Dip Statistics (last 60 trading days):")
    print(f"  Median dip from open:  {median_dip:.2f}%")
    print(f"  P25 (75% chance):      {p25_dip:.2f}%")
    print(f"  P75 (25% chance):      {p75_dip:.2f}%")
    print(f"  Days with dip >1%:     {n_dip_over_1}/{len(dips)} ({n_dip_over_1/len(dips)*100:.0f}%)")
    print(f"  Days with dip >2%:     {n_dip_over_2}/{len(dips)} ({n_dip_over_2/len(dips)*100:.0f}%)")
    print()

    try:
        intraday = t.history(period="1mo", interval="1h")
    except Exception as e:
        print(f"WARN: hourly history failed: {e}", file=sys.stderr)
        intraday = None

    if intraday is not None and len(intraday) > 0:
        low_hours = []
        for date_key, group in intraday.groupby(intraday.index.date):
            if len(group) > 3:
                low_hours.append(group["Low"].idxmin().hour)
        total = len(low_hours)
        if total > 0:
            morning = sum(1 for h in low_hours if h < 12)
            afternoon = total - morning
            counts = Counter(low_hours)
            peak_hour = max(counts, key=counts.get)
            print("Daily-Low Timing (last ~30 days, 1h bars):")
            print(f"  Before 12:00: {morning}/{total} ({morning/total*100:.0f}%)")
            print(f"  After 12:00:  {afternoon}/{total} ({afternoon/total*100:.0f}%)")
            print(f"  Peak hour:    {peak_hour:02d}:00 ({counts[peak_hour]}x)")
            print()

    half_atr_dip = 0.5 * atr_pct
    upper_range = min(median_dip, half_atr_dip)
    lower_range = p25_dip

    if upper_range > lower_range:
        upper_range, lower_range = lower_range, upper_range

    limit_upper = open_today * (1 - upper_range / 100)
    limit_lower = open_today * (1 - lower_range / 100)

    print("Realistic Buy Range (LONG):")
    print(f"  Upper (sooner fill):  Stock {limit_upper:.2f}  (dip {upper_range:.2f}%)")
    print(f"  Lower (better fill):  Stock {limit_lower:.2f}  (dip {lower_range:.2f}%)")
    print()
    print("Rule: Rule 18 Reversion-Guard decides WHETHER to wait for a dip.")
    print("  If Guard says 'Pullback-Pflicht'  -> Limit = Close - 1xATR (or lower bound above, whichever lower)")
    print("  If Guard says 'Kein Reversion-Edge' -> Limit in buy range (upper bound for faster fill)")
    print("  DB entry_price = Limit level, NEVER the Close.")

    sys.exit(0)


if __name__ == "__main__":
    main()
