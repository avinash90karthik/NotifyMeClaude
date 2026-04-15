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
from datetime import timedelta
import numpy as np
import pandas as pd
import yfinance as yf


LOOKBACK_YEARS = 3
MIN_ANALOG_COUNT = 10
CORR_THRESHOLD = 0.70
RSI_WINDOW = 7
ATR_RATIO_LOW = 0.7
ATR_RATIO_HIGH = 1.4
WINDOW_DAYS = 7
FWD_HORIZON = 5


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1 / period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period).mean()


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
    h = h.copy()
    h["ret"] = h["Close"].pct_change() * 100
    h["RSI"] = calc_rsi(h["Close"], 14)
    h["ATR"] = calc_atr(h["High"], h["Low"], h["Close"], 14)
    h["ATR_pct"] = h["ATR"] / h["Close"] * 100
    return h


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


def similar_day_forecast(h: pd.DataFrame, ref_ret: float) -> dict:
    """Classify ref_ret into a band and compute fwd-return distribution."""
    if ref_ret >= 3:
        band_label = ">= +3%"
        mask = h["ret"] >= 3
    elif ref_ret >= 1:
        band_label = ">= +1%"
        mask = h["ret"] >= 1
    elif ref_ret > -1:
        band_label = "flat (-1% to +1%)"
        mask = (h["ret"] > -1) & (h["ret"] < 1)
    elif ref_ret > -3:
        band_label = "<= -1%"
        mask = h["ret"] <= -1
    else:
        band_label = "<= -3%"
        mask = h["ret"] <= -3

    hist = h[mask]

    out = {"band": band_label, "n": 0, "by_day": {}}
    for day in range(1, FWD_HORIZON + 1):
        fwd = h["Close"].pct_change(day).shift(-day) * 100
        subset = fwd.loc[hist.index].dropna()
        if len(subset) == 0:
            continue
        out["n"] = max(out["n"], len(subset))
        out["by_day"][day] = {
            "n": len(subset),
            "mean": float(subset.mean()),
            "std": float(subset.std()),
            "median": float(subset.median()),
            "green": float((subset > 0).mean() * 100),
        }
    return out


def mode1_forecast(h: pd.DataFrame) -> dict:
    """Aggregate forecasts by asking: given today's return, what comes next?"""
    today_ret = float(h["ret"].iloc[-1])
    return similar_day_forecast(h, today_ret)


def mode2_analog_match(h: pd.DataFrame) -> dict:
    """Find historical 7-day windows that match today's state."""
    if len(h) < WINDOW_DAYS + FWD_HORIZON + 30:
        return {"ok": False, "reason": "insufficient history for analog search"}

    today_window = h["ret"].iloc[-WINDOW_DAYS:].values
    today_rsi = float(h["RSI"].iloc[-1])
    today_atr = float(h["ATR_pct"].iloc[-1])

    if np.isnan(today_rsi) or np.isnan(today_atr):
        return {"ok": False, "reason": "today's RSI/ATR not computable"}

    matches = []
    for i in range(WINDOW_DAYS, len(h) - FWD_HORIZON - 1):
        hist_window = h["ret"].iloc[i - WINDOW_DAYS : i].values
        if len(hist_window) != WINDOW_DAYS or np.isnan(hist_window).any():
            continue
        hist_rsi = h["RSI"].iloc[i - 1]
        hist_atr = h["ATR_pct"].iloc[i - 1]
        if np.isnan(hist_rsi) or np.isnan(hist_atr):
            continue

        if abs(hist_rsi - today_rsi) > RSI_WINDOW:
            continue
        atr_ratio = hist_atr / today_atr if today_atr > 0 else 0
        if atr_ratio < ATR_RATIO_LOW or atr_ratio > ATR_RATIO_HIGH:
            continue

        if np.std(hist_window) < 0.01 or np.std(today_window) < 0.01:
            continue
        corr = float(np.corrcoef(hist_window, today_window)[0, 1])
        if np.isnan(corr) or corr < CORR_THRESHOLD:
            continue

        base_close = float(h["Close"].iloc[i - 1])
        fwd_returns = {}
        for d in range(1, FWD_HORIZON + 1):
            if i - 1 + d >= len(h):
                break
            fwd_close = float(h["Close"].iloc[i - 1 + d])
            fwd_returns[d] = (fwd_close / base_close - 1) * 100

        if len(fwd_returns) < FWD_HORIZON:
            continue

        matches.append({
            "date": h.index[i - 1].date(),
            "corr": corr,
            "rsi_diff": hist_rsi - today_rsi,
            "atr_ratio": atr_ratio,
            "fwd": fwd_returns,
        })

    if len(matches) < MIN_ANALOG_COUNT:
        return {
            "ok": False,
            "reason": f"only {len(matches)} qualified analogs (need >= {MIN_ANALOG_COUNT})",
            "best_corr": max((m["corr"] for m in matches), default=0.0),
        }

    by_day = {}
    for d in range(1, FWD_HORIZON + 1):
        vals = np.array([m["fwd"][d] for m in matches if d in m["fwd"]])
        if len(vals) == 0:
            continue
        by_day[d] = {
            "n": len(vals),
            "mean": float(vals.mean()),
            "std": float(vals.std()),
            "median": float(np.median(vals)),
            "green": float((vals > 0).mean() * 100),
        }

    top_matches = sorted(matches, key=lambda m: -m["corr"])[:5]

    return {
        "ok": True,
        "n": len(matches),
        "by_day": by_day,
        "top_matches": top_matches,
    }


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
