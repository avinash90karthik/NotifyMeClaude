#!/usr/bin/env python3
"""
Cross-Source Convergence Check (Step 1.8c)
==========================================
Three independent fwd-5d green-rate estimates from different conditional
types are compared side by side. Output is *descriptive* — no automatic
cap, no automatic confidence penalty. The LLM must cite the spread and
the asymmetry-reading explicitly when synthesising Bull/Bear in Step 2/3.

Sources:
    1. Indicator Context strongest-axis    narrow per-stock conditional
                                           (RSI-band, BB-band, or DistHigh
                                           — whichever has max|adjust|;
                                           same value Rating-1 uses)
    2. Pattern Timeline Mode 1             disjoint return-bucket
    3. Pattern Timeline Mode 2             analog window match
                                           (corr + RSI-range + ATR-regime)

Source 3 may SKIP when fewer than the required analogs exist (default
n>=10). On SKIP, convergence runs on Sources 1+2 with explicit visibility
of the limitation rather than silent truncation.

The three conditional types are methodologically independent:
    - Source 1 conditions on the stock's CURRENT indicator state
    - Source 2 conditions on the stock's TODAY return-magnitude
    - Source 3 conditions on the stock's 7-day RETURN SHAPE + RSI + Vol

A large spread between Source 1 (narrow per-stock) and Sources 2/3
(broader conditionals) is *information* about regime-conditionality,
not inconsistency.

Usage:
    python3 convergence_check.py SYMBOL

Exit codes:
    0 = success
    1 = symbol or data fetch error
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.conditional_stats import (
    analog_match_green_rate,
    prepare_indicator_history,
    prepare_pattern_history,
    similar_return_day_green_rate,
    strongest_indicator_axis,
)


HISTORY_PERIOD = "3y"
FWD_HORIZON = 5
HIGH_SPREAD_PP = 20.0
MODERATE_SPREAD_PP = 10.0

ANALOG_LOOKBACK = 7
ANALOG_MIN = 10
ANALOG_CORR = 0.70
ANALOG_RSI_WINDOW = 7.0
ANALOG_ATR_LOW = 0.70
ANALOG_ATR_HIGH = 1.40


def fetch(symbol: str) -> pd.DataFrame | None:
    try:
        h = yf.Ticker(symbol).history(period=HISTORY_PERIOD)
    except Exception as e:
        print(f"ERROR: yfinance fetch failed for {symbol}: {e}", file=sys.stderr)
        return None
    if h is None or len(h) < 60:
        print(f"ERROR: insufficient history for {symbol}", file=sys.stderr)
        return None
    h = h.copy()
    h["ret"] = h["Close"].pct_change() * 100
    return h


def _fmt_row(idx: int, source_name: str, label: str, result: dict) -> str:
    if result["n"] == 0:
        return (
            f"  {idx}. {source_name:38s}  ({label})  "
            f"n=0 — no usable forward data"
        )
    if not result.get("ok", True):
        return (
            f"  {idx}. {source_name:38s}  ({label})  "
            f"SKIP — {result.get('reason', 'unavailable')}"
        )
    return (
        f"  {idx}. {source_name:38s}  ({label})  "
        f"green={result['green_rate']:5.1f}%  "
        f"n={result['n']:<3d} {result['tag']:5s}  "
        f"mean={result['mean']:+.2f}%"
    )


def _spread_verdict(spread_pp: float) -> str:
    if spread_pp >= HIGH_SPREAD_PP:
        return "HIGH SPREAD"
    if spread_pp >= MODERATE_SPREAD_PP:
        return "MODERATE SPREAD"
    return "TIGHT — sources converge"


def _reading(
    narrow_gr: float,
    bucket_gr: float,
    analog_gr: float,
    analog_tag: str,
    analog_n: int,
    analog_axis_name: str,
) -> list[str]:
    """Generate the descriptive reading for the LLM.

    narrow_gr        : Indicator Context strongest-axis green-rate
    bucket_gr        : Pattern Timeline Mode 1 (return-bucket) green-rate
    analog_gr        : Pattern Timeline Mode 2 (analog window) green-rate
                       (NaN if Mode 2 SKIPPED)
    analog_tag       : 'SOLID' / 'WEAK' / 'THIN' for Mode 2
    analog_n         : analog match count (used when emitting THIN warning)
    analog_axis_name : 'Mode 2' or 'analog' — used in messages

    Returns 1-3 reading lines. No cap, no recommendation, just diagnosis.
    """
    lines: list[str] = []

    narrow_ok = not np.isnan(narrow_gr)
    bucket_ok = not np.isnan(bucket_gr)
    analog_ok = not np.isnan(analog_gr)

    if not narrow_ok or not bucket_ok:
        lines.append(
            "Indicator-context strongest-axis or return-bucket source unavailable. "
            "Cite the available source(s) in Step 2/3 and treat the convergence "
            "diagnosis as partial."
        )
        return lines

    if analog_ok and analog_tag == "THIN":
        lines.append(
            f"Mode 2 n={analog_n} THIN — analog matching available but sample below "
            "robustness threshold (THIN<15). Treat as directional hint; weight SOLID "
            "sources higher in synthesis."
        )

    if analog_ok:
        broad_avg = (bucket_gr + analog_gr) / 2.0
        bucket_minus_analog = bucket_gr - analog_gr
        if abs(bucket_minus_analog) >= 15:
            stronger = "return-bucket" if bucket_minus_analog > 0 else "analog-window"
            lines.append(
                f"The two broad conditionals disagree: return-bucket ({bucket_gr:.0f}%) "
                f"vs analog-window ({analog_gr:.0f}%) differ by {abs(bucket_minus_analog):.0f}pp. "
                f"The {stronger} conditional is materially stronger — note both in Step 2/3 "
                "and avoid relying on a single broad source."
            )
        narrow_minus_broad = narrow_gr - broad_avg
        broad_label = "broad conditionals (return-bucket + analog)"
    else:
        narrow_minus_broad = narrow_gr - bucket_gr
        broad_avg = bucket_gr
        broad_label = "broad conditional (return-bucket; analog SKIPPED)"

    if narrow_minus_broad >= 15:
        lines.append(
            f"Narrow per-stock conditional ({narrow_gr:.0f}%) is much stronger than "
            f"{broad_label} ({broad_avg:.0f}%). Signal is regime-conditional — it works "
            "while the regime (this stock's current indicator state) holds. Cite this "
            "asymmetry in Step 2/3 reasoning when stating Bull/Bear confidence."
        )
    elif narrow_minus_broad <= -15:
        lines.append(
            f"Narrow per-stock conditional ({narrow_gr:.0f}%) is much weaker than "
            f"{broad_label} ({broad_avg:.0f}%). The stock historically underperforms in "
            "this exact indicator regime relative to its return-day-shape pattern. "
            "Cite this asymmetry in Step 2/3."
        )
    elif abs(narrow_minus_broad) >= 8:
        direction = "stronger" if narrow_minus_broad > 0 else "weaker"
        lines.append(
            f"Narrow per-stock conditional ({narrow_gr:.0f}%) is moderately {direction} "
            f"than {broad_label} ({broad_avg:.0f}%). Mention in Step 2/3 if it "
            "materially affects the Bull/Bear case."
        )
    else:
        if analog_ok:
            lines.append(
                f"All three sources converge near {(narrow_gr + broad_avg) / 2:.0f}% green. "
                "No regime-conditionality concern — fwd-5d signal is robust across "
                "narrow-per-stock and broad conditional types."
            )
        else:
            lines.append(
                f"Narrow per-stock and return-bucket sources converge near "
                f"{(narrow_gr + broad_avg) / 2:.0f}% green. Analog matching SKIPPED, so "
                "third independent confirmation is unavailable — diagnosis based on two "
                "sources only."
            )

    return lines


def main():
    parser = argparse.ArgumentParser(description="Cross-Source Convergence Check (Step 1.8c)")
    parser.add_argument("symbol", type=str)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    h = fetch(symbol)
    if h is None:
        sys.exit(1)

    today_ret = float(h["ret"].iloc[-1])

    h_ind_full = prepare_indicator_history(h)
    # MUST mirror indicator_context.py's sample base exactly so the
    # convergence comparison shows the same green-rate as Rating-1-input.
    h_ind_hist = h_ind_full.dropna(subset=["RSI", "BB_POS", "dist_high", "fwd_5d", "fwd_10d"])
    if len(h_ind_hist) < 30:
        print(
            f"ERROR: insufficient prepared history for {symbol} (n={len(h_ind_hist)})",
            file=sys.stderr,
        )
        sys.exit(1)

    today_ind = h_ind_full.iloc[-1]
    today_rsi = float(today_ind["RSI"])
    today_bb = float(today_ind["BB_POS"])
    today_disthigh = float(today_ind["dist_high"])

    strongest = strongest_indicator_axis(
        h_ind_hist,
        current_rsi=today_rsi,
        current_bb=today_bb,
        current_dist_high=today_disthigh,
        fwd_horizon=FWD_HORIZON,
    )
    pt_result = similar_return_day_green_rate(h, today_ret, fwd_horizon=FWD_HORIZON)

    h_pat = prepare_pattern_history(h)
    analog_result = analog_match_green_rate(
        h_pat,
        lookback_window=ANALOG_LOOKBACK,
        fwd_horizon=FWD_HORIZON,
        min_analogs=ANALOG_MIN,
        corr_threshold=ANALOG_CORR,
        rsi_window=ANALOG_RSI_WINDOW,
        atr_ratio_low=ANALOG_ATR_LOW,
        atr_ratio_high=ANALOG_ATR_HIGH,
    )

    print(f"=== Cross-Source Convergence: {symbol} ===")
    print(
        f"Today: ret={today_ret:+.2f}% | RSI={today_rsi:.1f} | "
        f"BB-Pos={today_bb:.1f}% | DistHigh={today_disthigh:+.2f}% | "
        f"fwd-horizon={FWD_HORIZON}d"
    )
    print()

    strongest_label = (
        f"Indicator Context strongest=[{strongest['axis_name']}]"
        if strongest["n"] > 0
        else "Indicator Context (no usable axis)"
    )

    print("Source                                            Conditional-Type")
    print("───────────────────────────────────────────────────────────────────────────────────")
    print(_fmt_row(1, strongest_label, "narrow per-stock", strongest))
    print(_fmt_row(2, "Pattern Timeline Mode 1", "return-bucket   ", pt_result))
    print(_fmt_row(3, "Pattern Timeline Mode 2", "analog-window   ", analog_result))
    print()

    if strongest["n"] > 0 and strongest.get("all_axes"):
        print("All per-stock axes (for transparency):")
        for axis_name, axis_data in strongest["all_axes"].items():
            marker = "  *" if axis_name == strongest["axis_name"] else "   "
            if axis_data["n"] == 0:
                print(f"  {marker} {axis_name:8s}  {axis_data['label']:36s}  n=0")
                continue
            print(
                f"  {marker} {axis_name:8s}  {axis_data['label']:36s}  "
                f"green={axis_data['green_rate']:5.1f}%  n={axis_data['n']:<3d} "
                f"{axis_data['tag']:5s}  adjust={axis_data['adjust']:+.2f}%"
            )
        print("  (* = axis chosen as Rating-1 input via max|adjust|)")
        print()

    valid_rates = [
        r["green_rate"]
        for r in (strongest, pt_result, analog_result)
        if r.get("ok", True) and r["n"] > 0 and not np.isnan(r["green_rate"])
    ]
    if len(valid_rates) < 2:
        print("Spread: n/a — fewer than 2 sources have usable data.")
        print("Convergence diagnosis cannot be performed. Cite available sources in Step 2/3.")
        sys.exit(0)

    spread_pp = max(valid_rates) - min(valid_rates)
    verdict = _spread_verdict(spread_pp)

    n_sources = len(valid_rates)
    print(f"Spread (max - min) across {n_sources} sources: {spread_pp:.1f} pp")
    print(f"Verdict: {verdict}")
    print()

    analog_valid = analog_result.get("ok") and analog_result["n"] > 0
    print("Reading:")
    for line in _reading(
        strongest["green_rate"] if strongest["n"] > 0 else float("nan"),
        pt_result["green_rate"] if pt_result["n"] > 0 else float("nan"),
        analog_result["green_rate"] if analog_valid else float("nan"),
        analog_tag=analog_result.get("tag", "THIN") if analog_valid else "n/a",
        analog_n=analog_result["n"] if analog_valid else 0,
        analog_axis_name="Mode 2",
    ):
        print(f"  {line}")
    print()

    print(
        "Diagnostic only — no automatic cap applied. The LLM must weight the asymmetry "
        "explicitly in Bull/Bear synthesis (Step 2) and in Judge confidence (Step 3) when "
        "the spread is HIGH (>= 20 pp)."
    )

    sys.exit(0)


if __name__ == "__main__":
    main()
