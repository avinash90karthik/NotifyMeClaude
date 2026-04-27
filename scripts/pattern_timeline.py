#!/usr/bin/env python3
"""
Pattern Timeline — Day -7 to 0 (actual) + Day +1 to +5 (forecast)
=================================================================
Two modes:

  Mode 1 — Day-Pattern Timeline:
    For each forward day (+1..+5), find historical days with a similar
    recent-return profile and report mean, ±1σ range, and green-rate.

  Mode 2 — Analog Matching:
    Find historical 7-day windows that match today's state on:
      - 7-day return correlation >= 0.7
      - RSI within ±7 points
      - ATR regime ratio in [0.7, 1.4]
    Requires >=10 qualified analogs. If fewer, skip with a clear note.

Usage:
    python3 pattern_timeline.py SYMBOL

Exit codes:
    0 = success
    1 = symbol or data fetch error
"""
import sys
import argparse
import os
from datetime import timedelta
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.conditional_stats import (
    analog_match_green_rate,
    fwd_distribution_per_day,
    prepare_pattern_history,
)


LOOKBACK_YEARS = 3
MIN_ANALOG_COUNT = 10
CORR_THRESHOLD = 0.70
RSI_WINDOW = 7
ATR_RATIO_LOW = 0.7
ATR_RATIO_HIGH = 1.4
WINDOW_DAYS = 7
FWD_HORIZON = 5


def fetch(symbol: str) -> pd.DataFrame | None:
    try:
        t = yf.Ticker(symbol)
        h = t.history(period=f"{LOOKBACK_YEARS}y")
    except Exception as e:
        print(f"ERROR: yfinance fetch failed for {symbol}: {e}", file=sys.stderr)
        return None
    if h is None or len(h) < 60:
        print(f"ERROR: insufficient history for {symbol}", file=sys.stderr)
        return None
    return prepare_pattern_history(h)


def print_actuals(h: pd.DataFrame) -> None:
    tail = h.tail(WINDOW_DAYS + 1)
    print("Day   Date         Return       Close")
    print("──────────────────────────────────────")
    today_idx = len(tail) - 1
    for i, (idx, row) in enumerate(tail.iterrows()):
        day_offset = i - today_idx
        date_str = idx.strftime("%Y-%m-%d")
        ret = row["ret"]
        close = row["Close"]
        tag = " ← TODAY" if day_offset == 0 else ""
        print(f"{day_offset:+3d}    {date_str}   {ret:+6.2f}%   {close:8.2f}{tag}")
    print()


def mode1_forecast(h: pd.DataFrame) -> dict:
    """Aggregate forecasts by asking: given today's return, what comes next?

    Delegates to lib.conditional_stats.fwd_distribution_per_day so the
    bucketing logic is canonical across day_pattern, pattern_timeline,
    and convergence_check.
    """
    today_ret = float(h["ret"].iloc[-1])
    result = fwd_distribution_per_day(h, today_ret, max_horizon=FWD_HORIZON)
    by_day = result["by_day"]
    n_max = max((v["n"] for v in by_day.values()), default=0)
    return {"band": result["band"], "n": n_max, "by_day": by_day}


def mode2_analog_match(h: pd.DataFrame) -> dict:
    """Delegate to lib.conditional_stats.analog_match_green_rate so the
    same logic is shared with convergence_check.py."""
    return analog_match_green_rate(
        h,
        lookback_window=WINDOW_DAYS,
        fwd_horizon=FWD_HORIZON,
        min_analogs=MIN_ANALOG_COUNT,
        corr_threshold=CORR_THRESHOLD,
        rsi_window=RSI_WINDOW,
        atr_ratio_low=ATR_RATIO_LOW,
        atr_ratio_high=ATR_RATIO_HIGH,
    )


def fmt_day_row(day: int, forecast_entry: dict | None) -> str:
    if forecast_entry is None:
        return f"+{day}     n/a"
    mean = forecast_entry["mean"]
    std = forecast_entry["std"]
    green = forecast_entry["green"]
    n = forecast_entry["n"]
    lo = mean - std
    hi = mean + std
    return f"+{day}    {mean:+6.2f}%   [{lo:+6.2f}% .. {hi:+6.2f}%]   green {green:4.0f}%   n={n}"


def main():
    parser = argparse.ArgumentParser(description="Pattern Timeline + Analog Matching")
    parser.add_argument("symbol", type=str)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    h = fetch(symbol)
    if h is None:
        sys.exit(1)

    close_today = float(h["Close"].iloc[-1])
    rsi_today = float(h["RSI"].iloc[-1])
    atr_today = float(h["ATR_pct"].iloc[-1])

    print(f"=== Pattern Timeline: {symbol} ===")
    print(f"Today: Close={close_today:.2f} | RSI={rsi_today:.1f} | ATR%={atr_today:.2f}%")
    print()

    print("── PAST 7 DAYS (actual) ──")
    print_actuals(h)

    print("── MODE 1: Similar-Day Forecast (Day +1..+5) ──")
    m1 = mode1_forecast(h)
    print(f"Reference: today's return classified as '{m1['band']}' (n={m1['n']})")
    print()
    print("Day     Mean          ±1σ Range                Green   Sample")
    print("──────────────────────────────────────────────────────────────")
    for d in range(1, FWD_HORIZON + 1):
        print(fmt_day_row(d, m1["by_day"].get(d)))
    print()

    print("── MODE 2: Analog Matching (7-day window + RSI + ATR regime) ──")
    m2 = mode2_analog_match(h)
    if not m2.get("ok"):
        reason = m2.get("reason", "unknown")
        best = m2.get("best_corr")
        best_str = f" (best corr {best:.2f})" if best is not None else ""
        print(f"SKIP: {reason}{best_str}")
        print("Fallback to Mode 1 only. Analog forecast not reliable today.")
    else:
        print(f"Found {m2['n']} qualified analogs (corr>={CORR_THRESHOLD}, RSI±{RSI_WINDOW}, ATR ratio {ATR_RATIO_LOW}-{ATR_RATIO_HIGH}).")
        print()
        print("Day     Mean          ±1σ Range                Green   Sample")
        print("──────────────────────────────────────────────────────────────")
        for d in range(1, FWD_HORIZON + 1):
            print(fmt_day_row(d, m2["by_day"].get(d)))
        print()
        print("Top-5 Analog Windows (highest correlation):")
        for m in m2["top_matches"]:
            fwd5 = m["fwd"].get(5, float("nan"))
            print(f"  {m['date']}  corr={m['corr']:.3f}  ΔRSI={m['rsi_diff']:+.1f}  ATR-ratio={m['atr_ratio']:.2f}  Fwd-5d={fwd5:+.2f}%")
    print()

    if m2.get("ok"):
        print("── AGREEMENT CHECK ──")
        for d in range(1, FWD_HORIZON + 1):
            e1 = m1["by_day"].get(d)
            e2 = m2["by_day"].get(d)
            if e1 is None or e2 is None:
                continue
            sign1 = "↑" if e1["mean"] > 0 else "↓"
            sign2 = "↑" if e2["mean"] > 0 else "↓"
            agree = sign1 == sign2
            status = "AGREE" if agree else "DIVERGE"
            diff = e2["mean"] - e1["mean"]
            print(f"  Day +{d}: Mode1={e1['mean']:+.2f}% Mode2={e2['mean']:+.2f}%  Δ={diff:+.2f}pp  [{status}]")
        print()

    print("── HINTS ──")
    print("Use ±1σ range as realistic entry-limit boundary.")
    print("If Day+1 mean positive but lower bound < -1.5%, a pullback limit entry is reasonable.")
    print("If Mode1 and Mode2 diverge → lower confidence in the forecast.")
    print("THIN sample (<15) = treat as directional hint, not a hard forecast.")

    sys.exit(0)


if __name__ == "__main__":
    main()
