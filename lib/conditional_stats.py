"""Conditional Forward-Return Statistics for Silver Hawk Trading.

Canonicalises the green-rate computations that previously lived inline
in indicator_context.py, pattern_timeline.py and day_pattern.py. All
public functions return the same shape on a normalised forward
horizon (default 5 trading days):

    rsi_band_green_rate           -> narrow per-stock RSI-band conditional
    bb_band_green_rate            -> per-stock Bollinger-position conditional
    dist_high_band_green_rate     -> per-stock distance-to-3M-high conditional
    similar_return_day_green_rate -> disjoint return-bucket conditional
    daily_return_bucket_green_rate -> alias of above (kept for clarity at call site)
    fwd_distribution_per_day      -> day-by-day fwd distribution per return bucket

    prepare_indicator_history(h)  -> shared history-filter for the three
                                     per-stock band functions. Both
                                     indicator_context.py and
                                     convergence_check.py MUST use it so
                                     they share the same sample base.

    strongest_indicator_axis(...) -> picks max|adjust| among RSI/BB/DistHigh,
                                     returns the same dict shape so the
                                     consumer sees green_rate / n / tag
                                     plus the chosen axis label. This is
                                     the function convergence_check uses
                                     to ensure Rating-1-input parity.

The disjoint return-bucket logic from pattern_timeline.py is canonical.
day_pattern.py previously used overlapping bands (>= +3 was a subset of
>= +1), which is mathematically the wrong abstraction for "what comes
after a similar day". After this refactor day_pattern reports disjoint
buckets — the numbers shift slightly at bucket edges versus the legacy
overlapping behaviour.

Sample tagging mirrors indicator_context: SOLID >= 30, WEAK 15-29,
THIN < 15. Earnings-specific thresholds (SOLID >= 8) live in
earnings_pattern.py — not consolidated here because earnings sample
sizes are structurally smaller and the threshold differs.
"""

import numpy as np
import pandas as pd

from lib.indicators import sigmoid_adjust


SOLID_N = 30
WEAK_N = 15

RETURN_BUCKETS = [
    (">= +3%", lambda r: r >= 3),
    (">= +1%", lambda r: (r >= 1) & (r < 3)),
    ("flat (-1% to +1%)", lambda r: (r > -1) & (r < 1)),
    ("<= -1%", lambda r: (r <= -1) & (r > -3)),
    ("<= -3%", lambda r: r <= -3),
]


def sample_tag(n: int) -> str:
    if n >= SOLID_N:
        return "SOLID"
    if n >= WEAK_N:
        return "WEAK"
    return "THIN"


def _classify_return(today_return: float) -> tuple[str, callable]:
    for label, predicate in RETURN_BUCKETS:
        if predicate(today_return):
            return label, predicate
    return "flat (-1% to +1%)", RETURN_BUCKETS[2][1]


def _ensure_returns(history_df: pd.DataFrame) -> pd.DataFrame:
    if "ret" in history_df.columns:
        return history_df
    h = history_df.copy()
    h["ret"] = h["Close"].pct_change() * 100
    return h


def _fwd_return(history_df: pd.DataFrame, horizon: int) -> pd.Series:
    return history_df["Close"].pct_change(horizon).shift(-horizon) * 100


def prepare_indicator_history(history_df: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI / BB-position / 3M-high distance / fwd-5d / fwd-10d
    on a copy of history_df. Returned frame keeps ALL rows (including
    today, which has unknown fwd-returns). Caller must dropna on the
    fwd-columns when building the historical sample base for green-rate
    statistics, but reads today's RSI / BB / DistHigh from the last row
    of the unfiltered frame.

    This split mirrors indicator_context.py:
        now = h.iloc[-1]         # today's indicator values
        h_hist = h.dropna(...)   # sample base for fwd-statistics

    Calling code in convergence_check.py and indicator_context.py BOTH
    use this helper so the column definitions are identical and the
    Rating-1-input is reproducible.
    """
    if "Close" not in history_df.columns:
        raise ValueError("history_df missing 'Close' column")

    h = history_df.copy()

    if "RSI" not in h.columns:
        delta = h["Close"].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1 / 14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, min_periods=14).mean()
        h["RSI"] = 100 - (100 / (1 + gain / loss))

    if "BB_POS" not in h.columns:
        sma20 = h["Close"].rolling(20).mean()
        std20 = h["Close"].rolling(20).std()
        h["BB_POS"] = (h["Close"] - (sma20 - 2 * std20)) / (4 * std20) * 100

    if "high_3m" not in h.columns:
        h["high_3m"] = h["Close"].rolling(60).max()
    if "dist_high" not in h.columns:
        h["dist_high"] = (h["Close"] / h["high_3m"] - 1) * 100

    for d in (5, 10):
        col = f"fwd_{d}d"
        if col not in h.columns:
            h[col] = h["Close"].pct_change(d).shift(-d) * 100

    return h


def _band_result(
    label: str,
    subset: pd.Series,
    fwd_horizon: int,
    conditional_type: str,
) -> dict:
    """Internal: take a fwd-return subset and emit the canonical dict shape."""
    n = len(subset)
    if n == 0:
        return {
            "label": label,
            "n": 0,
            "tag": "THIN",
            "green_rate": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "adjust": 0.0,
            "fwd_horizon": fwd_horizon,
            "conditional_type": conditional_type,
        }
    green_rate = float((subset > 0).mean() * 100)
    return {
        "label": label,
        "n": n,
        "tag": sample_tag(n),
        "green_rate": green_rate,
        "mean": float(subset.mean()),
        "median": float(subset.median()),
        "adjust": float(sigmoid_adjust(green_rate / 100.0, n)),
        "fwd_horizon": fwd_horizon,
        "conditional_type": conditional_type,
    }


def rsi_band_green_rate(
    history_df: pd.DataFrame,
    current_rsi: float,
    rsi_column: str = "RSI",
    fwd_horizon: int = 5,
    band_halfwidth: float = 5.0,
) -> dict:
    """Per-stock RSI-band conditional fwd-return distribution.

    Caller is expected to pass the OUTPUT of prepare_indicator_history()
    so the sample base matches indicator_context.py exactly. Inclusive
    band [current_rsi - halfwidth, current_rsi + halfwidth].
    """
    if rsi_column not in history_df.columns:
        raise ValueError(f"history_df missing column '{rsi_column}'")

    fwd_col = f"fwd_{fwd_horizon}d"
    if fwd_col not in history_df.columns:
        raise ValueError(
            f"history_df missing column '{fwd_col}' — call prepare_indicator_history first"
        )

    rsi = history_df[rsi_column]
    band_mask = (rsi >= current_rsi - band_halfwidth) & (rsi <= current_rsi + band_halfwidth)
    subset = history_df.loc[band_mask, fwd_col].dropna()

    label = f"RSI {current_rsi-band_halfwidth:.0f}-{current_rsi+band_halfwidth:.0f}"
    return _band_result(label, subset, fwd_horizon, "narrow per-stock RSI-band")


def bb_band_green_rate(
    history_df: pd.DataFrame,
    current_bb: float,
    bb_column: str = "BB_POS",
    fwd_horizon: int = 5,
) -> dict:
    """Per-stock Bollinger-position conditional fwd-return distribution.

    Bands mirror indicator_context.py:
        BB > 100        : "BB >100% (above upper band)"
        70 < BB <= 100  : "BB 70-100% (upper third)"
        30 <= BB <= 70  : "BB 30-70% (middle)"
        0 <= BB < 30    : "BB 0-30% (lower third)"
        BB < 0          : "BB <0% (below lower band)"
    """
    fwd_col = f"fwd_{fwd_horizon}d"
    if fwd_col not in history_df.columns or bb_column not in history_df.columns:
        raise ValueError(
            f"history_df missing '{bb_column}' or '{fwd_col}' — call prepare_indicator_history first"
        )

    bb = history_df[bb_column]
    if current_bb > 100:
        mask = bb > 100
        label = "BB >100% (above upper band)"
    elif current_bb > 70:
        mask = (bb > 70) & (bb <= 100)
        label = "BB 70-100% (upper third)"
    elif current_bb < 0:
        mask = bb < 0
        label = "BB <0% (below lower band)"
    elif current_bb < 30:
        mask = (bb >= 0) & (bb < 30)
        label = "BB 0-30% (lower third)"
    else:
        mask = (bb >= 30) & (bb <= 70)
        label = "BB 30-70% (middle)"

    subset = history_df.loc[mask, fwd_col].dropna()
    return _band_result(label, subset, fwd_horizon, "per-stock BB-position band")


def dist_high_band_green_rate(
    history_df: pd.DataFrame,
    current_dist_high: float,
    dist_column: str = "dist_high",
    fwd_horizon: int = 5,
) -> dict:
    """Per-stock distance-to-3M-high conditional fwd-return distribution.

    Bands mirror indicator_context.py:
        dist_high > -3                 : "Within 3% of 3M-high"
        dist_high < -15                : "More than -15% from 3M-high (deep drawdown)"
        -15 <= dist_high <= -3         : "Between -15% and -3% from 3M-high"
    """
    fwd_col = f"fwd_{fwd_horizon}d"
    if fwd_col not in history_df.columns or dist_column not in history_df.columns:
        raise ValueError(
            f"history_df missing '{dist_column}' or '{fwd_col}' — call prepare_indicator_history first"
        )

    d = history_df[dist_column]
    if current_dist_high > -3:
        mask = d > -3
        label = "Within 3% of 3M-high"
    elif current_dist_high < -15:
        mask = d < -15
        label = "More than -15% from 3M-high (deep drawdown)"
    else:
        mask = (d >= -15) & (d <= -3)
        label = "Between -15% and -3% from 3M-high"

    subset = history_df.loc[mask, fwd_col].dropna()
    return _band_result(label, subset, fwd_horizon, "per-stock distance-to-high band")


def strongest_indicator_axis(
    history_df: pd.DataFrame,
    current_rsi: float,
    current_bb: float,
    current_dist_high: float,
    fwd_horizon: int = 5,
) -> dict:
    """Compute RSI / BB / DistHigh band stats and return the strongest by
    |adjust|. Mirrors indicator_context.py's print_aggregation logic so
    the value used for Rating 1 is identical to what convergence_check.py
    cites as the per-stock conditional source.

    Caller MUST pass the output of prepare_indicator_history(). Returns a
    dict with the standard band shape plus an extra 'axis_name' key.
    """
    rsi_axis = rsi_band_green_rate(history_df, current_rsi, fwd_horizon=fwd_horizon)
    bb_axis = bb_band_green_rate(history_df, current_bb, fwd_horizon=fwd_horizon)
    dist_axis = dist_high_band_green_rate(history_df, current_dist_high, fwd_horizon=fwd_horizon)

    candidates = [
        ("RSI", rsi_axis),
        ("BB", bb_axis),
        ("DistHigh", dist_axis),
    ]
    valid = [(name, a) for name, a in candidates if a["n"] > 0]
    if not valid:
        return {
            "axis_name": "none",
            "label": "no usable axis",
            "n": 0,
            "tag": "THIN",
            "green_rate": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "adjust": 0.0,
            "fwd_horizon": fwd_horizon,
            "conditional_type": "narrow per-stock (no axis available)",
            "all_axes": {name: a for name, a in candidates},
        }

    name, strongest = max(valid, key=lambda pair: abs(pair[1]["adjust"]))
    out = dict(strongest)
    out["axis_name"] = name
    out["all_axes"] = {n: a for n, a in candidates}
    return out


def similar_return_day_green_rate(
    history_df: pd.DataFrame,
    today_return: float,
    fwd_horizon: int = 5,
) -> dict:
    """Disjoint return-bucket conditional fwd-return distribution.

    Classifies today_return into one of five disjoint bands
    (>=+3, +1..+3, flat, -1..-3, <=-3) and computes the fwd-horizon
    green-rate from history days in the same band.

    Returns the same dict shape as rsi_band_green_rate.
    """
    h = _ensure_returns(history_df)
    label, predicate = _classify_return(today_return)
    fwd = _fwd_return(h, fwd_horizon)
    bucket_mask = predicate(h["ret"])
    subset = fwd.loc[bucket_mask].dropna()
    n = len(subset)

    if n == 0:
        return {
            "label": label,
            "n": 0,
            "tag": "THIN",
            "green_rate": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "fwd_horizon": fwd_horizon,
            "conditional_type": "disjoint return-bucket",
        }

    return {
        "label": label,
        "n": n,
        "tag": sample_tag(n),
        "green_rate": float((subset > 0).mean() * 100),
        "mean": float(subset.mean()),
        "median": float(subset.median()),
        "fwd_horizon": fwd_horizon,
        "conditional_type": "disjoint return-bucket",
    }


def daily_return_bucket_green_rate(
    history_df: pd.DataFrame,
    today_return: float,
    fwd_horizon: int = 5,
) -> dict:
    """Alias of similar_return_day_green_rate.

    Kept as a separate name so day_pattern.py and pattern_timeline.py
    both have a clear, intent-revealing call site. Internally the same
    canonical disjoint-bucket logic.
    """
    return similar_return_day_green_rate(history_df, today_return, fwd_horizon)


def prepare_pattern_history(history_df: pd.DataFrame, atr_period: int = 14) -> pd.DataFrame:
    """Compute RSI / ATR / ATR% on a copy of history_df and return the
    full frame (no rows dropped). Used as the input to analog_match_green_rate
    by both pattern_timeline.py and convergence_check.py.

    Caller reads today's RSI/ATR from h.iloc[-1]. The analog search
    inside analog_match_green_rate handles NaN warm-up days itself.
    """
    if "Close" not in history_df.columns or "High" not in history_df.columns or "Low" not in history_df.columns:
        raise ValueError("history_df missing OHLC columns")

    h = history_df.copy()
    if "ret" not in h.columns:
        h["ret"] = h["Close"].pct_change() * 100

    if "RSI" not in h.columns:
        delta = h["Close"].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1 / 14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, min_periods=14).mean()
        rs = gain / loss.replace(0, np.nan)
        h["RSI"] = 100 - (100 / (1 + rs))

    if "ATR" not in h.columns:
        prev_close = h["Close"].shift(1)
        tr = pd.concat(
            [h["High"] - h["Low"], (h["High"] - prev_close).abs(), (h["Low"] - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        h["ATR"] = tr.ewm(alpha=1.0 / atr_period, min_periods=atr_period).mean()

    if "ATR_pct" not in h.columns:
        h["ATR_pct"] = h["ATR"] / h["Close"] * 100

    return h


def analog_match_green_rate(
    history_df: pd.DataFrame,
    lookback_window: int = 7,
    fwd_horizon: int = 5,
    min_analogs: int = 10,
    corr_threshold: float = 0.70,
    rsi_window: float = 7.0,
    atr_ratio_low: float = 0.70,
    atr_ratio_high: float = 1.40,
) -> dict:
    """Find historical lookback_window-day windows that match today's
    state on three conditions:
        - return-shape correlation >= corr_threshold
        - RSI within +/- rsi_window of today's RSI
        - ATR% ratio (historical / today) in [atr_ratio_low, atr_ratio_high]

    For each match, compute fwd-1d..+fwd-horizon returns relative to the
    match's last close. Aggregate per day.

    Caller MUST pass the output of prepare_pattern_history(). The result
    dict has the same canonical band-result shape (n, tag, green_rate,
    mean, median, fwd_horizon, conditional_type) on the fwd_horizon-day
    return when n >= min_analogs, plus extra keys 'ok', 'by_day' (per-day
    breakdown for pattern_timeline's display), 'top_matches', and on SKIP
    the keys 'reason' and 'best_corr'.

    On SKIP (n < min_analogs): n=len(matches), green_rate=NaN, ok=False.
    Convergence_check should treat ok=False as "Mode 2 unavailable".
    """
    if "ret" not in history_df.columns or "RSI" not in history_df.columns or "ATR_pct" not in history_df.columns:
        raise ValueError("history_df missing 'ret'/'RSI'/'ATR_pct' — call prepare_pattern_history first")

    label = f"Analog match (window={lookback_window}d, corr>={corr_threshold:.2f})"

    if len(history_df) < lookback_window + fwd_horizon + 30:
        return {
            "label": label,
            "n": 0,
            "tag": "THIN",
            "green_rate": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "fwd_horizon": fwd_horizon,
            "conditional_type": "analog window match",
            "ok": False,
            "reason": "insufficient history for analog search",
            "by_day": {},
            "top_matches": [],
            "best_corr": 0.0,
        }

    today_window = history_df["ret"].iloc[-lookback_window:].values
    today_rsi = float(history_df["RSI"].iloc[-1])
    today_atr = float(history_df["ATR_pct"].iloc[-1])

    if np.isnan(today_rsi) or np.isnan(today_atr):
        return {
            "label": label,
            "n": 0,
            "tag": "THIN",
            "green_rate": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "fwd_horizon": fwd_horizon,
            "conditional_type": "analog window match",
            "ok": False,
            "reason": "today's RSI/ATR not computable",
            "by_day": {},
            "top_matches": [],
            "best_corr": 0.0,
        }

    matches = []
    for i in range(lookback_window, len(history_df) - fwd_horizon - 1):
        hist_window = history_df["ret"].iloc[i - lookback_window:i].values
        if len(hist_window) != lookback_window or np.isnan(hist_window).any():
            continue
        hist_rsi = history_df["RSI"].iloc[i - 1]
        hist_atr = history_df["ATR_pct"].iloc[i - 1]
        if np.isnan(hist_rsi) or np.isnan(hist_atr):
            continue
        if abs(hist_rsi - today_rsi) > rsi_window:
            continue
        atr_ratio = hist_atr / today_atr if today_atr > 0 else 0
        if atr_ratio < atr_ratio_low or atr_ratio > atr_ratio_high:
            continue
        if np.std(hist_window) < 0.01 or np.std(today_window) < 0.01:
            continue
        corr = float(np.corrcoef(hist_window, today_window)[0, 1])
        if np.isnan(corr) or corr < corr_threshold:
            continue

        base_close = float(history_df["Close"].iloc[i - 1])
        fwd_returns = {}
        for d in range(1, fwd_horizon + 1):
            if i - 1 + d >= len(history_df):
                break
            fwd_close = float(history_df["Close"].iloc[i - 1 + d])
            fwd_returns[d] = (fwd_close / base_close - 1) * 100
        if len(fwd_returns) < fwd_horizon:
            continue

        matches.append({
            "date": history_df.index[i - 1].date(),
            "corr": corr,
            "rsi_diff": float(hist_rsi - today_rsi),
            "atr_ratio": float(atr_ratio),
            "fwd": fwd_returns,
        })

    by_day = {}
    for d in range(1, fwd_horizon + 1):
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

    if len(matches) < min_analogs:
        best_corr = max((m["corr"] for m in matches), default=0.0)
        return {
            "label": label,
            "n": len(matches),
            "tag": sample_tag(len(matches)),
            "green_rate": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "fwd_horizon": fwd_horizon,
            "conditional_type": "analog window match",
            "ok": False,
            "reason": f"only {len(matches)} qualified analogs (need >= {min_analogs})",
            "by_day": by_day,
            "top_matches": sorted(matches, key=lambda m: -m["corr"])[:5],
            "best_corr": best_corr,
        }

    fwd_h_entry = by_day.get(fwd_horizon, {})
    fwd_h_vals = np.array([m["fwd"][fwd_horizon] for m in matches if fwd_horizon in m["fwd"]])
    return {
        "label": label,
        "n": len(matches),
        "tag": sample_tag(len(matches)),
        "green_rate": float((fwd_h_vals > 0).mean() * 100) if len(fwd_h_vals) else float("nan"),
        "mean": float(fwd_h_vals.mean()) if len(fwd_h_vals) else float("nan"),
        "median": float(np.median(fwd_h_vals)) if len(fwd_h_vals) else float("nan"),
        "fwd_horizon": fwd_horizon,
        "conditional_type": "analog window match",
        "ok": True,
        "by_day": by_day,
        "top_matches": sorted(matches, key=lambda m: -m["corr"])[:5],
    }


def fwd_distribution_per_day(
    history_df: pd.DataFrame,
    today_return: float,
    max_horizon: int = 5,
) -> dict:
    """Day-by-day fwd distribution (Day+1..+max_horizon) for the
    return-bucket containing today_return.

    Used by pattern_timeline.py Mode 1, which needs the per-day
    breakdown rather than just one horizon. Returns:
        {"band": label, "by_day": {1: {...}, 2: {...}, ...}}
    where each by_day entry has n, mean, std, median, green.
    """
    h = _ensure_returns(history_df)
    label, predicate = _classify_return(today_return)
    bucket_mask = predicate(h["ret"])

    by_day = {}
    for d in range(1, max_horizon + 1):
        fwd = h["Close"].pct_change(d).shift(-d) * 100
        subset = fwd.loc[bucket_mask].dropna()
        if len(subset) == 0:
            continue
        by_day[d] = {
            "n": len(subset),
            "mean": float(subset.mean()),
            "std": float(subset.std()),
            "median": float(subset.median()),
            "green": float((subset > 0).mean() * 100),
        }

    return {"band": label, "by_day": by_day}
