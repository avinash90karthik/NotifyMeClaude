"""Phase 4b — Signal-quality analysis, independent of trade mechanics.

The backtest loop in paper/backtest.py applies real trade mechanics
(stops, targets, time-stops, costs) that can mask whether the *signal
itself* carries directional information. To validate the multi-agent
gate architecture on its own terms, this module answers a simpler
question:

    For every APPROVED v9 signal at time T, what was the Fwd-5d and
    Fwd-10d return in the signal's direction?

If the mean forward return in the signal's direction is reliably
positive (or the hit rate > 50%), the gate is adding information —
regardless of whether the current trade mechanics convert that into
a cert-P&L win.

This complements, rather than replaces, the full backtest.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from paper.historical_view import HistoricalMarketView, _load_ohlcv
from paper.frozen_v9 import frozen_v9_signal
from paper.universe import symbols as universe_symbols, BACKTEST_START, BACKTEST_END


@dataclass
class SignalRecord:
    symbol: str
    as_of: str
    direction: str
    confidence: float
    close: float
    fwd_5d_pct: float | None
    fwd_10d_pct: float | None
    direction_5d_hit: bool | None   # True if fwd move agrees with direction
    direction_10d_hit: bool | None


def _fwd_return(df: pd.DataFrame, idx: pd.Timestamp, n: int) -> float | None:
    """Return the (close[idx+n] / close[idx] - 1) * 100 or None."""
    if idx not in df.index:
        return None
    pos = df.index.get_loc(idx)
    if pos + n >= len(df):
        return None
    p0 = float(df["Close"].iloc[pos])
    pn = float(df["Close"].iloc[pos + n])
    if p0 <= 0:
        return None
    return (pn / p0 - 1) * 100


def collect_approved_signals(
    start: str = BACKTEST_START,
    end: str = BACKTEST_END,
    cadence_days: int = 5,
) -> pd.DataFrame:
    """Iterate a grid of dates (every `cadence_days` business days) and
    record every APPROVED signal + its forward-5d/10d outcome."""
    universe = universe_symbols()
    records: list[SignalRecord] = []

    dates = pd.bdate_range(start=start, end=end, freq=f"{cadence_days}B")
    print(f"Sampling {len(dates)} dates × {len(universe)} symbols = {len(dates)*len(universe)} evaluations",
          flush=True)

    for i, d in enumerate(dates):
        view = HistoricalMarketView(d)
        for sym in universe:
            try:
                sig = frozen_v9_signal(view, sym)
            except Exception:
                continue
            if sig is None or not sig.approved:
                continue
            try:
                df = _load_ohlcv(sym)
            except Exception:
                continue
            fwd5 = _fwd_return(df, d, 5)
            fwd10 = _fwd_return(df, d, 10)
            dir_sign = 1 if sig.direction == "LONG" else -1
            hit5 = None if fwd5 is None else (dir_sign * fwd5 > 0)
            hit10 = None if fwd10 is None else (dir_sign * fwd10 > 0)
            records.append(SignalRecord(
                symbol=sym,
                as_of=str(d.date()),
                direction=sig.direction,
                confidence=sig.confidence_pct,
                close=sig.close,
                fwd_5d_pct=round(fwd5, 3) if fwd5 is not None else None,
                fwd_10d_pct=round(fwd10, 3) if fwd10 is not None else None,
                direction_5d_hit=hit5,
                direction_10d_hit=hit10,
            ))
        if i % 50 == 0 and i > 0:
            print(f"  {d.date()}: {len(records)} signals so far", flush=True)

    df = pd.DataFrame([r.__dict__ for r in records])
    return df


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n_signals": 0}
    # Direction-adjusted forward returns (LONG as-is, SHORT flipped)
    def _adj(row, col):
        v = row[col]
        if pd.isna(v):
            return np.nan
        return v if row["direction"] == "LONG" else -v

    df = df.copy()
    df["adj_fwd5"] = df.apply(lambda r: _adj(r, "fwd_5d_pct"), axis=1)
    df["adj_fwd10"] = df.apply(lambda r: _adj(r, "fwd_10d_pct"), axis=1)

    out = {
        "n_signals": int(len(df)),
        "n_long": int((df["direction"] == "LONG").sum()),
        "n_short": int((df["direction"] == "SHORT").sum()),
        "mean_adj_fwd5_pct": round(float(df["adj_fwd5"].mean()), 3),
        "median_adj_fwd5_pct": round(float(df["adj_fwd5"].median()), 3),
        "mean_adj_fwd10_pct": round(float(df["adj_fwd10"].mean()), 3),
        "hit_rate_5d_pct": round(float((df["adj_fwd5"] > 0).mean() * 100), 2),
        "hit_rate_10d_pct": round(float((df["adj_fwd10"] > 0).mean() * 100), 2),
    }
    # By confidence bucket
    buckets = []
    for lo, hi in [(60, 65), (65, 70), (70, 80), (80, 100)]:
        sub = df[(df["confidence"] >= lo) & (df["confidence"] < hi)]
        if len(sub) == 0:
            continue
        buckets.append({
            "bracket": f"{lo}-{hi}%",
            "n": len(sub),
            "mean_fwd5_pct": round(float(sub["adj_fwd5"].mean()), 3),
            "hit_rate_5d_pct": round(float((sub["adj_fwd5"] > 0).mean() * 100), 2),
        })
    out["by_confidence_bracket"] = buckets
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=BACKTEST_START)
    p.add_argument("--end", default=BACKTEST_END)
    p.add_argument("--cadence-days", type=int, default=5)
    p.add_argument("--out", default="paper/results/phase4_signal_quality")
    args = p.parse_args()

    df = collect_approved_signals(args.start, args.end, args.cadence_days)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "approved_signals.csv", index=False)
    summary = summarize(df)

    print("\n--- Signal-Quality Summary ---")
    for k, v in summary.items():
        if k == "by_confidence_bracket":
            print(f"  by_confidence_bracket:")
            for b in v:
                print(f"    {b['bracket']:8s} n={b['n']:3d}  fwd5_mean={b['mean_fwd5_pct']:+6.2f}%  hit={b['hit_rate_5d_pct']:.0f}%")
        else:
            print(f"  {k:24s} {v}")
    import json
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
