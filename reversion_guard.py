#!/usr/bin/env python3
"""
Reversion Guard — Per-Stock Edge Check for Entry Calibration
=============================================================
Replaces hard-coded textbook thresholds (RSI>70, Gap>10% etc.) with
per-stock historical distributions.

For each potential reversion trigger (RSI high, green-day streak, big
daily move, gap), computes:
  - The stock's own P80/P90 percentile for the trigger metric
  - The forward-5d mean and green-rate in that regime

A trigger only fires if BOTH are true:
  1. Today's metric exceeds the stock's own percentile
  2. The stock's own forward distribution shows mean-reversion
     (green-rate < 45% for LONG-Reversion / > 55% for SHORT-Reversion)

Usage:
    python3 reversion_guard.py SYMBOL [--direction LONG|SHORT]

Exit codes:
    0 = success (whether a trigger fired or not)
    1 = symbol or data fetch error
"""
import sys
import argparse
import numpy as np
import pandas as pd
import yfinance as yf


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=alpha, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period).mean()


LOOKBACK_DAYS = 252  # ~12 months
FWD_DAYS = 5
MIN_SAMPLE_SOLID = 20
MIN_SAMPLE_WEAK = 8

GREEN_RATE_BEARISH = 0.45  # forward green-rate below this = mean-reversion edge for LONG-exit (=LONG-Reversion)
GREEN_RATE_BULLISH = 0.55  # forward green-rate above this = continuation (SHORT would fail)


def label_sample(n: int) -> str:
    if n >= MIN_SAMPLE_SOLID:
        return "SOLID"
    if n >= MIN_SAMPLE_WEAK:
        return "WEAK"
    return "THIN"


def fetch_history(symbol: str) -> pd.DataFrame | None:
    t = yf.Ticker(symbol)
    try:
        h = t.history(period="2y", auto_adjust=True)
    except Exception as e:
        print(f"ERROR: yfinance history failed for {symbol}: {e}", file=sys.stderr)
        return None
    if h is None or len(h) < 60:
        print(f"ERROR: insufficient history for {symbol} ({0 if h is None else len(h)} bars)", file=sys.stderr)
        return None
    return h


def fwd_stats(hist: pd.DataFrame, mask: pd.Series) -> tuple[int, float, float]:
    """Given a boolean mask over hist, return (n, fwd5d_mean_pct, fwd5d_green_rate)."""
    close = hist["Close"].values
    n = 0
    returns = []
    greens = 0
    idx = np.where(mask.values)[0]
    for i in idx:
        if i + FWD_DAYS >= len(close):
            continue
        r = (close[i + FWD_DAYS] - close[i]) / close[i]
        returns.append(r)
        if r > 0:
            greens += 1
        n += 1
    if n == 0:
        return 0, 0.0, 0.0
    return n, float(np.mean(returns)) * 100, greens / n


def analyze_rsi(hist: pd.DataFrame, direction: str) -> dict:
    """RSI-based reversion trigger — uses stock's own P80 as threshold."""
    rsi_series = pd.Series(calc_rsi(hist["Close"], 14), index=hist.index)
    # Use last 12 months for the percentile
    recent = rsi_series.dropna().tail(LOOKBACK_DAYS)
    if len(recent) < 60:
        return {"ok": False, "reason": "insufficient RSI history"}

    today_rsi = float(rsi_series.dropna().iloc[-1])
    p80 = float(recent.quantile(0.80))
    p20 = float(recent.quantile(0.20))

    if direction == "LONG":
        # LONG-Reversion: is current RSI in top 20% AND does top-20% historically mean-revert?
        mask = rsi_series >= p80
        over = today_rsi >= p80
        label = f"RSI={today_rsi:.1f} | P80={p80:.1f}"
    else:  # SHORT-Blowoff fade
        # SHORT only works if today's RSI is extreme AND history shows reversal (low fwd green-rate)
        mask = rsi_series >= p80
        over = today_rsi >= p80
        label = f"RSI={today_rsi:.1f} | P80={p80:.1f} (SHORT-fade needs top-20% RSI)"

    # Cap mask to lookback window
    mask = mask & (rsi_series.index >= recent.index[0])
    n, fwd_mean, green = fwd_stats(hist, mask)
    return {
        "ok": True,
        "label": label,
        "over_threshold": bool(over),
        "n": n,
        "sample": label_sample(n),
        "fwd5_mean_pct": fwd_mean,
        "green_rate": green,
        "p80": p80,
        "p20": p20,
        "today": today_rsi,
    }


def analyze_green_streak(hist: pd.DataFrame) -> dict:
    """Count green days in last 10 — compare to stock's own distribution."""
    close = hist["Close"]
    daily_ret = close.pct_change()
    rolling_greens = (daily_ret > 0).rolling(10).sum()
    recent = rolling_greens.dropna().tail(LOOKBACK_DAYS)
    if len(recent) < 60:
        return {"ok": False, "reason": "insufficient history"}

    today_streak = int(rolling_greens.dropna().iloc[-1])
    p80 = float(recent.quantile(0.80))

    mask = rolling_greens >= p80
    mask = mask & (rolling_greens.index >= recent.index[0])
    n, fwd_mean, green = fwd_stats(hist, mask)
    return {
        "ok": True,
        "label": f"Greens in 10d = {today_streak} | P80 = {p80:.1f}",
        "over_threshold": today_streak >= p80,
        "n": n,
        "sample": label_sample(n),
        "fwd5_mean_pct": fwd_mean,
        "green_rate": green,
        "today": today_streak,
        "p80": p80,
    }


def analyze_daily_move(hist: pd.DataFrame) -> dict:
    """Last daily move — compare to stock's own P90."""
    daily_ret = hist["Close"].pct_change() * 100
    recent = daily_ret.dropna().tail(LOOKBACK_DAYS)
    if len(recent) < 60:
        return {"ok": False, "reason": "insufficient history"}

    today_move = float(daily_ret.dropna().iloc[-1])
    p90 = float(recent.quantile(0.90))

    mask = daily_ret >= p90
    mask = mask & (daily_ret.index >= recent.index[0])
    n, fwd_mean, green = fwd_stats(hist, mask)
    return {
        "ok": True,
        "label": f"Today daily = {today_move:+.2f}% | P90 = {p90:+.2f}%",
        "over_threshold": today_move >= p90,
        "n": n,
        "sample": label_sample(n),
        "fwd5_mean_pct": fwd_mean,
        "green_rate": green,
        "today": today_move,
        "p90": p90,
    }


def analyze_gap(hist: pd.DataFrame) -> dict:
    """Today's open gap vs previous close — compare to stock's own P90."""
    gap = (hist["Open"] / hist["Close"].shift(1) - 1) * 100
    recent = gap.dropna().tail(LOOKBACK_DAYS)
    if len(recent) < 60:
        return {"ok": False, "reason": "insufficient history"}

    today_gap = float(gap.dropna().iloc[-1])
    p90 = float(recent.quantile(0.90))

    mask = gap >= p90
    mask = mask & (gap.index >= recent.index[0])
    n, fwd_mean, green = fwd_stats(hist, mask)
    return {
        "ok": True,
        "label": f"Today gap = {today_gap:+.2f}% | P90 = {p90:+.2f}%",
        "over_threshold": today_gap >= p90,
        "n": n,
        "sample": label_sample(n),
        "fwd5_mean_pct": fwd_mean,
        "green_rate": green,
        "today": today_gap,
        "p90": p90,
    }


def format_trigger(name: str, r: dict, direction: str) -> tuple[bool, str]:
    """Returns (fires, line) — a trigger fires only if over_threshold AND historical edge exists."""
    if not r.get("ok"):
        return False, f"  {name}: SKIP ({r.get('reason', 'n/a')})"

    n = r["n"]
    sample = r["sample"]
    fwd = r["fwd5_mean_pct"]
    green = r["green_rate"]
    over = r["over_threshold"]

    if direction == "LONG":
        # LONG-Reversion fires if today is over threshold AND historical regime mean-reverts
        has_edge = green < GREEN_RATE_BEARISH
        edge_str = f"Fwd5={fwd:+.2f}% green={green*100:.0f}% [{sample} n={n}]"
        if over and has_edge and sample != "THIN":
            fires = True
            verdict = "FIRES → Pullback-Entry Pflicht"
        elif over and not has_edge:
            fires = False
            verdict = "no edge (Fortsetzung dominiert) → Entry am Close OK"
        elif over and sample == "THIN":
            fires = False
            verdict = f"THIN sample (n={n}) → insufficient evidence, treat as no-fire"
        else:
            fires = False
            verdict = "below stock's own threshold"
    else:  # SHORT
        # SHORT-Blowoff fires if today is over threshold AND history shows mean-reversion (low green rate)
        has_edge = green < GREEN_RATE_BEARISH
        edge_str = f"Fwd5={fwd:+.2f}% green={green*100:.0f}% [{sample} n={n}]"
        if over and has_edge and sample != "THIN":
            fires = True
            verdict = "FIRES → SHORT-Setup valid, Entry at Extension-Break"
        elif over and not has_edge:
            fires = False
            verdict = "continuation bias → SHORT = NO-TRADE"
        elif over and sample == "THIN":
            fires = False
            verdict = f"THIN sample (n={n}) → insufficient evidence, SHORT = NO-TRADE"
        else:
            fires = False
            verdict = "below stock's own threshold → no blowoff"

    return fires, f"  {name}: {r['label']} | {edge_str} → {verdict}"


def main():
    parser = argparse.ArgumentParser(description="Per-stock reversion guard (Rule 18)")
    parser.add_argument("symbol", type=str)
    parser.add_argument("--direction", choices=["LONG", "SHORT"], default="LONG")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    direction = args.direction
    hist = fetch_history(symbol)
    if hist is None:
        sys.exit(1)

    # ATR for entry-distance calc
    atr_val = float(calc_atr(hist["High"], hist["Low"], hist["Close"], period=14).iloc[-1])
    last_close = float(hist["Close"].iloc[-1])
    atr_pct = atr_val / last_close * 100

    print(f"=== Reversion Guard: {symbol} | Direction: {direction} ===")
    print(f"Close={last_close:.2f} | ATR(14)={atr_val:.2f} ({atr_pct:.2f}%)")
    print()

    if direction == "LONG":
        print("LONG-Reversion Trigger (per-stock percentiles + own fwd distribution):")
    else:
        print("SHORT-Blowoff Trigger (per-stock percentiles + own fwd distribution):")

    checks = [
        ("RSI", analyze_rsi(hist, direction)),
        ("Green-Streak(10)", analyze_green_streak(hist)),
        ("Daily-Move", analyze_daily_move(hist)),
    ]
    if direction == "SHORT":
        checks.append(("Gap-Open", analyze_gap(hist)))

    any_fires = False
    for name, r in checks:
        fires, line = format_trigger(name, r, direction)
        print(line)
        if fires:
            any_fires = True

    print()
    if direction == "LONG":
        if any_fires:
            limit = last_close - atr_val
            print(f"VERDICT: Pullback-Entry Pflicht.")
            print(f"  Limit-Entry MUSS ≤ {limit:.2f} (= Close − 1×ATR).")
            print(f"  DB entry_price = Limit-Level, NICHT Close.")
        else:
            print(f"VERDICT: Kein Reversion-Edge für diesen Stock.")
            print(f"  Entry am Close ({last_close:.2f}) OK — aber Schritt 1-2 (Intraday-Dip) trotzdem nutzen.")
    else:  # SHORT
        if any_fires:
            limit = last_close + atr_val
            print(f"VERDICT: SHORT-Setup ist valid (Blowoff mean-reverts in this stock's history).")
            print(f"  Entry ≥ {limit:.2f} (= Close + 1×ATR) ODER am Extension-Bruch-Level.")
            print(f"  DB entry_price = Trigger-Level, NICHT Close.")
        else:
            print(f"VERDICT: SHORT = NO-TRADE.")
            print(f"  Keine Blowoff-Reversion in dieser Aktie — Fortsetzung dominiert.")
            print(f"  Beispiel-Fehlschluss: NBIS / HOOD Gaps historisch bullish continuation, nicht mean-reverting.")

    sys.exit(0)


if __name__ == "__main__":
    main()
