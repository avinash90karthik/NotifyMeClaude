"""Phase 3 — Frozen v9 signal logic, deterministic.

This module is the out-of-sample reimplementation of the Silver Hawk
v9 decision rules (CLAUDE.md rules 1-20, prompts 01/02/03) as a pure
function. It takes a HistoricalMarketView and a symbol and returns a
`TradingSignal`.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
-----------------------------------------
- **No LLM calls.** The Step 2 Bull/Bear debate is *replaced* by the
  deterministic 6-axis scorecard formula. We cannot faithfully simulate
  LLM rebuttals out-of-sample and pretending otherwise would invalidate
  the study.
- **No news / Reddit / Trump signals.** Scorecard axis 3 is fixed at
  NEUTRAL (5/10 for both LONG and SHORT). This is a documented
  limitation in paper/README.md.
- **No non-earnings macro calendar** (NFP, CPI, Fed days). Axis 4 only
  uses scheduled earnings. Macro-event awareness is also NEUTRAL.
- **No wavelet denoising.** Indicators are computed on raw closes, on
  purpose (see docstring in historical_view.py).

WHAT IS FAITHFULLY IMPLEMENTED
------------------------------
- Rule 16: per-stock Indicator Context (RSI-band Fwd-5d green-rate).
- Rule 18: per-stock Reversion Guard (P80 / P90 percentiles with own
  forward green-rate).
- Rule 19: v9 Extrem-Oversold-Bonus (+5% @ RSI-band <20 / +8% @ <15,
  both requiring green-rate ≥65%/70% and SOLID sample n≥20).
- Rule 20: v9 Scout-Confirmation inversion (60-65% → 40/60, ≥65% → 60/40).
- Step 3 Judge formula: Confidence = max(LONG,SHORT)/60 × 100, then
  Differenz-Strafe ×0.9 if |Diff|<10, then Oversold-Bonus.
- 60% hard gate.
- V-Vetos V1 (ATR>7%), V2 (CHOPPY+score<50), V3 (slot count — handled
  by the backtest loop, not here), V4 (sector concentration — ditto),
  V5 (monthly drawdown — ditto). We emit V1, V2 from this signal;
  V3/V4/V5 are portfolio-level and applied by the backtest.
- KO calculation: 3-step max(ATR-based, chart-based).

Inputs come from HistoricalMarketView only; outputs are pure data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
import pandas as pd

from paper.historical_view import HistoricalMarketView, IndicatorSnapshot
from paper.universe import UNIVERSE


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

Direction = Literal["LONG", "SHORT", "NO-TRADE"]


@dataclass(frozen=True)
class TradingSignal:
    symbol: str
    as_of: pd.Timestamp
    direction: Direction
    approved: bool                    # passed gate AND no V-veto
    confidence_pct: float             # after diff-penalty + oversold-bonus
    raw_confidence_pct: float         # before any modifier
    oversold_bonus_pct: float         # 0, 5 or 8
    diff_penalty_applied: bool        # True if diff < 10

    # Scorecard
    long_total: int
    short_total: int
    axes: dict[str, tuple[int, int]]  # axis_name -> (long, short), 0-10 each

    # Prices / levels
    close: float
    atr_pct: float | None

    # Trade plan (only meaningful if approved)
    entry_limit: float | None         # Limit price where the entry is placed
    stop_loss: float | None           # mental stop (slightly above/below KO)
    ko_level: float | None            # final KO = max(ATR, chart)
    target_20pct: float | None        # +20% on cert = ~2-3% on underlying at 7-8x leverage
    position_size_pct: float          # % of portfolio
    scout_inverted: bool              # v9 Rule 20

    # Diagnostics
    regime: str                       # TRENDING / CHOPPY / RANGE / TRANSITIONAL
    reversion_verdict: str            # human-readable string
    v1_veto: bool                     # ATR > 7%
    v2_veto: bool                     # CHOPPY + score < 50
    rejection_reason: str | None      # why approved is False (if applicable)


# ---------------------------------------------------------------------------
# Indicator Context (Rule 16) — pure function form
# ---------------------------------------------------------------------------

def _rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


@dataclass(frozen=True)
class IndicatorContext:
    rsi_now: float | None
    rsi_band_green_rate: float | None     # 0.0-1.0
    rsi_band_n: int                        # sample size in band (+-5 RSI)
    rsi_band_avg_fwd5: float | None        # mean forward 5d return, percent
    sample_quality: Literal["SOLID", "WEAK", "THIN", "NONE"]


def _sample_quality(n: int) -> Literal["SOLID", "WEAK", "THIN"]:
    if n >= 30:
        return "SOLID"
    if n >= 15:
        return "WEAK"
    return "THIN"


def indicator_context(
    view: HistoricalMarketView, symbol: str, band_width: int = 5
) -> IndicatorContext:
    """Replicates indicator_context.py § RSI-Band on point-in-time data.

    Returns Fwd-5d green-rate for the ±band_width RSI bucket around today.
    """
    df = view.get_ohlcv(symbol)
    # Use ~3 years of history to match the production script (period="3y")
    if len(df) < 60:
        return IndicatorContext(None, None, 0, None, "NONE")
    df = df.tail(252 * 3)
    close = df["Close"].dropna()
    if len(close) < 60:
        return IndicatorContext(None, None, 0, None, "NONE")

    rsi = _rsi_wilder(close)
    rsi_now = float(rsi.dropna().iloc[-1]) if rsi.dropna().size else None
    if rsi_now is None:
        return IndicatorContext(None, None, 0, None, "NONE")

    # Forward 5-day return
    fwd5 = close.pct_change(5).shift(-5) * 100
    hist = pd.DataFrame({"rsi": rsi, "fwd5": fwd5}).dropna()
    if hist.empty:
        return IndicatorContext(rsi_now, None, 0, None, "NONE")

    band = hist[(hist["rsi"] >= rsi_now - band_width) & (hist["rsi"] <= rsi_now + band_width)]
    n = len(band)
    if n == 0:
        return IndicatorContext(rsi_now, None, 0, None, "NONE")

    green_rate = float((band["fwd5"] > 0).mean())
    avg = float(band["fwd5"].mean())
    return IndicatorContext(
        rsi_now=round(rsi_now, 2),
        rsi_band_green_rate=round(green_rate, 4),
        rsi_band_n=n,
        rsi_band_avg_fwd5=round(avg, 3),
        sample_quality=_sample_quality(n),
    )


# ---------------------------------------------------------------------------
# Reversion Guard (Rule 18) — pure function form
# ---------------------------------------------------------------------------

REV_LOOKBACK_DAYS = 252
REV_FWD_DAYS = 5
REV_MIN_SOLID = 20
REV_MIN_WEAK = 8
REV_GREEN_EDGE = 0.45  # fwd green-rate below this = mean-reversion edge


@dataclass(frozen=True)
class ReversionResult:
    direction: Literal["LONG", "SHORT"]
    any_trigger_fires: bool
    verdict: str                  # human-readable
    rsi_today: float | None
    rsi_p80: float | None
    green_rate_in_band: float | None   # 0-1
    sample: str                   # SOLID / WEAK / THIN / NONE


def _reversion_rsi_stats(df: pd.DataFrame) -> tuple[float | None, float | None, float | None, int]:
    """Return (rsi_now, p80, green_rate_at_or_above_p80, n)."""
    close = df["Close"].dropna()
    if len(close) < 60:
        return None, None, None, 0
    rsi = _rsi_wilder(close).dropna().tail(REV_LOOKBACK_DAYS)
    if len(rsi) < 60:
        return None, None, None, 0
    rsi_now = float(rsi.iloc[-1])
    p80 = float(rsi.quantile(0.80))

    # Forward stats — use the full history for the band mask
    rsi_full = _rsi_wilder(close)
    fwd5 = close.pct_change(REV_FWD_DAYS).shift(-REV_FWD_DAYS)
    combined = pd.DataFrame({"rsi": rsi_full, "fwd5": fwd5}).dropna()
    # Restrict to same lookback window
    combined = combined.loc[combined.index >= rsi.index[0]]
    band = combined[combined["rsi"] >= p80]
    n = len(band)
    if n == 0:
        return rsi_now, p80, None, 0
    green = float((band["fwd5"] > 0).mean())
    return rsi_now, p80, green, n


def reversion_guard(
    view: HistoricalMarketView, symbol: str, direction: Literal["LONG", "SHORT"]
) -> ReversionResult:
    """Per-stock reversion trigger replication (simplified to RSI-based only —
    the production script also checks green-streak/daily-move/gap, but the
    RSI leg is by far the most-fired and is what the scorecard truly
    depends on. Keeping the backtest to one leg is a documented
    simplification.
    """
    df = view.get_ohlcv(symbol)
    rsi_now, p80, green, n = _reversion_rsi_stats(df)

    if rsi_now is None:
        return ReversionResult(direction, False, "insufficient history",
                               None, None, None, "NONE")

    over = (p80 is not None) and (rsi_now >= p80)
    if not over:
        if direction == "LONG":
            return ReversionResult(direction, False,
                                   "below P80 → no pullback pressure",
                                   rsi_now, p80, green,
                                   _sample_quality(n) if n else "NONE")
        else:
            return ReversionResult(direction, False,
                                   "below P80 → no blowoff → SHORT NO-TRADE",
                                   rsi_now, p80, green,
                                   _sample_quality(n) if n else "NONE")

    sample = _sample_quality(n) if n else "NONE"
    if sample == "THIN" or sample == "NONE":
        if direction == "LONG":
            verdict = "THIN sample — treat as no-fire, entry at close OK"
        else:
            verdict = "THIN sample → SHORT = NO-TRADE"
        return ReversionResult(direction, False, verdict, rsi_now, p80, green, sample)

    has_edge = (green is not None) and (green < REV_GREEN_EDGE)
    if direction == "LONG":
        if has_edge:
            return ReversionResult(direction, True,
                                   f"Pullback-Pflicht (green={green*100:.0f}% <45%)",
                                   rsi_now, p80, green, sample)
        else:
            return ReversionResult(direction, False,
                                   f"no edge (green={green*100:.0f}% ≥45%) → continuation",
                                   rsi_now, p80, green, sample)
    else:  # SHORT
        if has_edge:
            return ReversionResult(direction, True,
                                   f"Blowoff-Fade valid (green={green*100:.0f}% <45%)",
                                   rsi_now, p80, green, sample)
        else:
            return ReversionResult(direction, False,
                                   f"continuation (green={green*100:.0f}% ≥45%) → SHORT NO-TRADE",
                                   rsi_now, p80, green, sample)


# ---------------------------------------------------------------------------
# Price Action Check (Rule 14)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PriceActionResult:
    green_days_in_last_10: int
    trend_5d_pct: float | None         # close_today / close_5d_ago - 1
    momentum_up: bool                  # score >= 5 greens AND trend_5d > 0
    momentum_down: bool                # <= 3 greens AND trend_5d < 0


def price_action_check(view: HistoricalMarketView, symbol: str) -> PriceActionResult:
    df = view.get_ohlcv(symbol)
    close = df["Close"].dropna()
    if len(close) < 11:
        return PriceActionResult(0, None, False, False)
    last10 = close.tail(11)  # 10 changes
    diffs = last10.diff().dropna()
    greens = int((diffs > 0).sum())
    trend_5d = None
    if len(close) >= 6:
        trend_5d = float(close.iloc[-1] / close.iloc[-6] - 1)
    momentum_up = greens >= 5 and (trend_5d or 0) > 0
    momentum_down = greens <= 3 and (trend_5d or 0) < 0
    return PriceActionResult(greens, trend_5d, momentum_up, momentum_down)


# ---------------------------------------------------------------------------
# Regime detection (simplified — ADX replacement)
# ---------------------------------------------------------------------------

def detect_regime(view: HistoricalMarketView, symbol: str) -> str:
    """Replicates indicators.detect_regime on the point-in-time slice.

    We compute ADX inline (don't import the production file) and classify.
    """
    df = view.get_ohlcv(symbol).tail(200)
    if len(df) < 30:
        return "TRANSITIONAL"
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    both = (plus_dm > 0) & (minus_dm > 0)
    plus_dm = plus_dm.where(~(both & (plus_dm < minus_dm)), 0)
    minus_dm = minus_dm.where(~(both & (minus_dm < plus_dm)), 0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    alpha = 1.0 / 14
    atr = tr.ewm(alpha=alpha, min_periods=14).mean()
    smooth_plus = plus_dm.ewm(alpha=alpha, min_periods=14).mean()
    smooth_minus = minus_dm.ewm(alpha=alpha, min_periods=14).mean()

    plus_di = 100 * smooth_plus / atr
    minus_di = 100 * smooth_minus / atr
    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx_series = dx.ewm(alpha=alpha, min_periods=14).mean()

    if adx_series.dropna().empty:
        return "TRANSITIONAL"
    adx = float(adx_series.iloc[-1])
    pdi = float(plus_di.iloc[-1]) if not np.isnan(plus_di.iloc[-1]) else None
    mdi = float(minus_di.iloc[-1]) if not np.isnan(minus_di.iloc[-1]) else None
    di_spread = abs((pdi or 0) - (mdi or 0))

    if adx >= 25 and di_spread > 10:
        return "TRENDING"
    if adx < 20:
        # Proxy for BB-width percentile: compare recent 20-day std to its 120-day percentile
        std20 = close.rolling(20).std()
        recent = std20.dropna().tail(120)
        if len(recent) >= 20 and not np.isnan(std20.iloc[-1]):
            pctl = float((recent < std20.iloc[-1]).sum() / len(recent) * 100)
            if pctl < 30:
                return "RANGE"
            if pctl > 60:
                return "CHOPPY"
    return "TRANSITIONAL"


# ---------------------------------------------------------------------------
# Chart Structure score (axis 5)
# ---------------------------------------------------------------------------

def chart_structure_score(view: HistoricalMarketView, symbol: str) -> tuple[int, int]:
    """Quantify axis 5 via SMA50/SMA200 alignment.

    Return (long_score, short_score), each 0-10.

    Heuristic (deterministic, documented):
      - price > SMA50 > SMA200: +4 LONG
      - price > SMA200 only: +2 LONG
      - price < SMA50 < SMA200: +4 SHORT
      - price < SMA200 only: +2 SHORT
      - ADX-regime TRENDING: +1 to the dominant side
      - Last close within 1% of SMA50 (support test): +1 LONG
      - Last close within 1% of SMA200 (major support): +1 LONG
      - mirrored above for SHORT
      - bounded at [0, 10]
    """
    snap = view.get_indicators(symbol)
    if snap is None or snap.sma50 is None or snap.sma200 is None:
        return 5, 5  # neutral

    price = snap.price
    sma50 = snap.sma50
    sma200 = snap.sma200
    regime = detect_regime(view, symbol)

    long_score = 0
    short_score = 0

    if price > sma50 > sma200:
        long_score += 4
    elif price > sma200:
        long_score += 2
    if price < sma50 < sma200:
        short_score += 4
    elif price < sma200:
        short_score += 2

    if regime == "TRENDING":
        if sma50 > sma200:
            long_score += 1
        elif sma50 < sma200:
            short_score += 1

    # Support / resistance proximity
    if abs(price - sma50) / sma50 < 0.01:
        if price > sma200:
            long_score += 1
        else:
            short_score += 1
    if abs(price - sma200) / sma200 < 0.01:
        if price > sma50:
            long_score += 1
        else:
            short_score += 1

    # If neither side has any structure, treat as neutral (5/5) rather than
    # (0/0) which would bias toward NO-TRADE on every low-structure bar.
    if long_score == 0 and short_score == 0:
        return 5, 5

    return int(min(long_score, 10)), int(min(short_score, 10))


# ---------------------------------------------------------------------------
# Scorecard axis computations
# ---------------------------------------------------------------------------

def _technical_axis(ctx: IndicatorContext) -> tuple[int, int]:
    """Axis 1 — Technical Green-Rate. Derived from Fwd-5d green-rate of the
    stock's own RSI-band."""
    if ctx.rsi_band_green_rate is None or ctx.rsi_band_n < 15:
        # THIN or unavailable → neutral (5/5), documented behaviour
        return 5, 5
    g = ctx.rsi_band_green_rate
    # Map: g >= 0.70 → 9 LONG / 1 SHORT
    #      0.60 .. 0.70 → 7 LONG / 3 SHORT
    #      0.50 .. 0.60 → 6 LONG / 4 SHORT
    #      0.40 .. 0.50 → 4 LONG / 6 SHORT
    #      g < 0.40   → 2 LONG / 8 SHORT
    if g >= 0.70:
        return 9, 1
    if g >= 0.60:
        return 7, 3
    if g >= 0.50:
        return 6, 4
    if g >= 0.40:
        return 4, 6
    return 2, 8


def _price_action_axis(pa: PriceActionResult) -> tuple[int, int]:
    """Axis 2 — Price-Action Reality.

    Requires BOTH the green-day count and the 5-day trend to agree before
    tilting off-neutral. A flat 5-of-10 with zero trend is genuinely
    ambiguous → (5, 5).
    """
    g = pa.green_days_in_last_10
    t = pa.trend_5d_pct or 0.0
    if g >= 7 and t > 0.02:
        return 9, 1
    if g >= 6 and t > 0:
        return 7, 3
    if g >= 5 and t > 0:
        return 6, 4
    if g <= 3 and t < -0.02:
        return 1, 9
    if g <= 4 and t < 0:
        return 3, 7
    return 5, 5


def _news_axis() -> tuple[int, int]:
    """Axis 3 — News + Reddit Flow. DISABLED in paper backtest, documented
    limitation. Always NEUTRAL."""
    return 5, 5


def _event_axis(view: HistoricalMarketView, symbol: str) -> tuple[int, int]:
    """Axis 4 — Event/Catalyst. Only the earnings sub-component is used;
    macro-calendar events are NEUTRAL.

    Heuristic: if there are upcoming earnings within 5 days AND within the
    plausible-knowability window → both sides slightly penalised (event
    risk). Otherwise NEUTRAL.
    """
    upcoming = view.get_earnings_calendar(symbol, horizon_days=7,
                                          known_advance_days=14)
    if not upcoming:
        return 5, 5
    days = (upcoming[0] - view.as_of).days
    if days <= 5:
        # Event risk: slightly favour no-trade (both sides cooler)
        return 4, 4
    return 5, 5


def _reversion_edge_axis(
    long_rev: ReversionResult, short_rev: ReversionResult
) -> tuple[int, int]:
    """Axis 6 — mapping from Rule 18 verdicts → scorecard (prompts/02.md)."""
    long_no_edge = not long_rev.any_trigger_fires and "no edge" in long_rev.verdict
    long_pullback = long_rev.any_trigger_fires  # Pullback-Pflicht
    short_notrade = not short_rev.any_trigger_fires
    short_valid = short_rev.any_trigger_fires

    # Use the 4-case mapping from prompts/02_investment_debate.md
    if long_no_edge and short_notrade:
        return 6, 2
    if long_no_edge and short_valid:
        return 4, 7
    if long_pullback and short_notrade:
        return 3, 2
    if long_pullback and short_valid:
        return 2, 7
    # Fallbacks — below P80, or THIN samples
    # Prefer LONG slightly when neither side has a clean verdict (matches
    # the "default to no information" interpretation of continuation).
    return 5, 3


# ---------------------------------------------------------------------------
# Oversold Bonus (Rule 19)
# ---------------------------------------------------------------------------

def _oversold_bonus_pct(ctx: IndicatorContext) -> float:
    """+5% if RSI<20 band, Fwd5 green ≥65%, SOLID.
       +8% if RSI<15 band, Fwd5 green ≥70%, SOLID.
       Only applies to LONG side (this is applied by caller)."""
    if (
        ctx.rsi_now is not None
        and ctx.rsi_now < 15
        and ctx.rsi_band_green_rate is not None
        and ctx.rsi_band_green_rate >= 0.70
        and ctx.rsi_band_n >= 20
    ):
        return 8.0
    if (
        ctx.rsi_now is not None
        and ctx.rsi_now < 20
        and ctx.rsi_band_green_rate is not None
        and ctx.rsi_band_green_rate >= 0.65
        and ctx.rsi_band_n >= 20
    ):
        return 5.0
    return 0.0


# ---------------------------------------------------------------------------
# KO calculation
# ---------------------------------------------------------------------------

def _ko_multiplier(symbol: str) -> float:
    """Large Cap 2.0× ATR, Mid/Small 2.5× ATR, Commodities 3.0× ATR."""
    entry = next((e for e in UNIVERSE if e.symbol == symbol), None)
    if entry is None:
        return 2.0
    if entry.bucket == "commodity":
        return 3.0
    if entry.bucket == "us_midsmall":
        return 2.5
    return 2.0  # us_large, eu_large, stress


def _chart_support(view: HistoricalMarketView, symbol: str, lookback: int = 60) -> float | None:
    """Simple support = rolling 60-day low."""
    df = view.get_ohlcv(symbol).tail(lookback)
    if df.empty:
        return None
    return float(df["Low"].min())


def _chart_resistance(view: HistoricalMarketView, symbol: str, lookback: int = 60) -> float | None:
    df = view.get_ohlcv(symbol).tail(lookback)
    if df.empty:
        return None
    return float(df["High"].max())


def _calc_ko(
    view: HistoricalMarketView,
    symbol: str,
    direction: Literal["LONG", "SHORT"],
    close: float,
    atr_pct: float | None,
) -> float | None:
    if atr_pct is None or close <= 0:
        return None
    mult = _ko_multiplier(symbol)
    atr_abs = (atr_pct / 100.0) * close
    atr_ko = close - mult * atr_abs if direction == "LONG" else close + mult * atr_abs
    chart = (_chart_support(view, symbol) if direction == "LONG"
             else _chart_resistance(view, symbol))
    if chart is None:
        return round(atr_ko, 4)
    if direction == "LONG":
        # Further away = smaller number for LONG
        ko = min(atr_ko, chart)
    else:
        ko = max(atr_ko, chart)
    return round(ko, 4)


# ---------------------------------------------------------------------------
# Position sizing (Rule 20)
# ---------------------------------------------------------------------------

def _position_size_and_split(confidence: float) -> tuple[float, bool]:
    """Return (total_pct_of_portfolio, scout_is_inverted)."""
    if confidence < 60:
        return 0.0, False
    if confidence < 65:
        return 15.0, True   # 40/60 inverted
    if confidence < 70:
        return 20.0, False  # 60/40 classic
    return 25.0, False      # 60/40 classic


# ---------------------------------------------------------------------------
# Public signal function
# ---------------------------------------------------------------------------

def frozen_v9_signal(
    view: HistoricalMarketView, symbol: str
) -> TradingSignal | None:
    """Compute the v9 trading decision at `view.as_of` for `symbol`.

    Returns None if there is not enough data to compute any snapshot at
    all. Returns a TradingSignal with direction="NO-TRADE" and approved=
    False if the setup is valid but the gate/vetos block it.
    """
    try:
        snap = view.get_indicators(symbol)
    except (ValueError, KeyError):
        return None
    if snap is None or snap.price is None:
        return None

    # Per-stock stats
    ctx = indicator_context(view, symbol)
    long_rev = reversion_guard(view, symbol, "LONG")
    short_rev = reversion_guard(view, symbol, "SHORT")
    pa = price_action_check(view, symbol)
    regime = detect_regime(view, symbol)

    # Scorecard axes
    axis1 = _technical_axis(ctx)
    axis2 = _price_action_axis(pa)
    axis3 = _news_axis()
    axis4 = _event_axis(view, symbol)
    axis5 = chart_structure_score(view, symbol)
    axis6 = _reversion_edge_axis(long_rev, short_rev)

    axes = {
        "technical_greenrate": axis1,
        "price_action": axis2,
        "news_reddit": axis3,
        "event_catalyst": axis4,
        "chart_structure": axis5,
        "reversion_edge": axis6,
    }
    long_total = sum(a[0] for a in axes.values())
    short_total = sum(a[1] for a in axes.values())

    direction: Direction
    if long_total > short_total:
        direction = "LONG"
    elif short_total > long_total:
        direction = "SHORT"
    else:
        direction = "NO-TRADE"

    raw_conf = max(long_total, short_total) / 60.0 * 100.0

    # Differenz-Strafe
    diff = abs(long_total - short_total)
    diff_penalty = diff < 10
    conf_after_diff = raw_conf * 0.9 if diff_penalty else raw_conf

    # Oversold bonus (LONG only)
    bonus = _oversold_bonus_pct(ctx) if direction == "LONG" else 0.0
    final_conf = conf_after_diff + bonus

    # V-Vetos that are computable from the signal alone
    atr = snap.atr_pct
    v1 = (atr is not None) and (atr > 7.0)
    max_side = max(long_total, short_total)
    # Production Rule V2: "CHOPPY + Score < 50" — 50 is on the 60-point scale.
    v2 = (regime == "CHOPPY") and (max_side < 50)

    # CLAUDE.md Rule: "V-Vetos (hart — bei EINEM aktivem V: Signal = NO-TRADE)".
    # V-Vetos are checked BEFORE the confidence gate so a failed-signal setup
    # is reported with its true root cause (e.g. ATR blow-up dominates a
    # low-confidence finding).
    rejection_reason = None
    approved = True
    if direction == "NO-TRADE":
        approved = False
        rejection_reason = "scorecard LONG == SHORT"
    elif v1:
        approved = False
        rejection_reason = f"V1 veto: ATR {atr:.2f}% > 7%"
    elif v2:
        approved = False
        rejection_reason = f"V2 veto: regime CHOPPY and max side {max_side} < 50"
    elif final_conf < 60.0:
        approved = False
        rejection_reason = f"confidence {final_conf:.1f}% < 60% gate"

    # Trade plan (only meaningful if approved)
    entry_limit = None
    stop_loss = None
    ko_level = None
    target_20pct = None
    pos_pct = 0.0
    scout_inverted = False

    if approved and direction != "NO-TRADE":
        close = snap.price
        ko = _calc_ko(view, symbol, direction, close, atr)

        # Rule 18 entry logic
        if direction == "LONG":
            if long_rev.any_trigger_fires:
                # Pullback-Pflicht: Limit ≤ Close − 1×ATR
                entry_limit = round(close * (1 - (atr or 0) / 100), 4)
            else:
                # No trigger → entry at close is OK
                entry_limit = round(close, 4)
        else:  # SHORT
            if short_rev.any_trigger_fires:
                entry_limit = round(close * (1 + (atr or 0) / 100), 4)
            else:
                # Rule 18: no short-trigger fires anywhere → SHORT = NO-TRADE
                approved = False
                rejection_reason = "Rule 18: SHORT requires reversion trigger, none fired"

        if approved:
            ko_level = ko
            if ko_level is not None and entry_limit is not None:
                # Stop slightly inside KO (0.5% buffer)
                if direction == "LONG":
                    stop_loss = round(ko_level * 1.002, 4)
                else:
                    stop_loss = round(ko_level * 0.998, 4)
            # Target +20% on cert ≈ ~2.5% underlying at 8x leverage — but we
            # model the underlying target because the backtest trades the
            # underlying, not certificates. So "+20% on cert" maps to a
            # conservative +2.5% on the underlying for LONG, -2.5% for SHORT.
            if direction == "LONG":
                target_20pct = round(entry_limit * 1.025, 4) if entry_limit else None
            else:
                target_20pct = round(entry_limit * 0.975, 4) if entry_limit else None
            pos_pct, scout_inverted = _position_size_and_split(final_conf)

    # Reversion verdict string (human-readable, for diagnostics)
    if direction == "LONG":
        rev_verdict = f"LONG: {long_rev.verdict}"
    elif direction == "SHORT":
        rev_verdict = f"SHORT: {short_rev.verdict}"
    else:
        rev_verdict = "no direction"

    return TradingSignal(
        symbol=symbol,
        as_of=view.as_of,
        direction=direction,
        approved=approved,
        confidence_pct=round(final_conf, 2),
        raw_confidence_pct=round(raw_conf, 2),
        oversold_bonus_pct=bonus,
        diff_penalty_applied=diff_penalty,
        long_total=long_total,
        short_total=short_total,
        axes=axes,
        close=snap.price,
        atr_pct=atr,
        entry_limit=entry_limit,
        stop_loss=stop_loss,
        ko_level=ko_level,
        target_20pct=target_20pct,
        position_size_pct=pos_pct,
        scout_inverted=scout_inverted,
        regime=regime,
        reversion_verdict=rev_verdict,
        v1_veto=v1,
        v2_veto=v2,
        rejection_reason=rejection_reason,
    )
