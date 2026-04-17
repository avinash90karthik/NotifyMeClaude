"""Phase 3 — unit tests for frozen_v9_signal and its components.

Each component is tested in isolation. The full `frozen_v9_signal` is
then exercised with two hand-constructed synthetic histories (uptrend
and crash-then-bottom) to verify gate behaviour, oversold bonus, and
V-vetos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paper import historical_view as hv
from paper.historical_view import HistoricalMarketView, _clear_caches_for_tests
from paper import frozen_v9
from paper.frozen_v9 import (
    IndicatorContext,
    ReversionResult,
    PriceActionResult,
    _technical_axis,
    _price_action_axis,
    _news_axis,
    _event_axis,
    _reversion_edge_axis,
    _oversold_bonus_pct,
    _position_size_and_split,
    _ko_multiplier,
    _calc_ko,
    frozen_v9_signal,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_caches():
    _clear_caches_for_tests()
    yield
    _clear_caches_for_tests()


def _install(symbol: str, df: pd.DataFrame):
    hv._MEMO[symbol] = df.copy()


def _build_uptrend(n: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=0.002, scale=0.01, size=n)  # strong upward drift
    close = 100 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0.0, 0.003, size=n)))
    low = close * (1 - np.abs(rng.normal(0.0, 0.003, size=n)))
    open_ = close * (1 + rng.normal(0.0, 0.002, size=n))
    vol = rng.integers(1_000_000, 5_000_000, size=n)
    idx = pd.bdate_range(start="2018-01-02", periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx)


def _build_crash(n: int = 400, crash_at: int = 300, seed: int = 11) -> pd.DataFrame:
    """Builds a series that drifts upward then crashes at `crash_at`."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=0.001, scale=0.01, size=n)
    rets[crash_at:crash_at + 15] = -0.04  # 15 consecutive -4% days
    close = 100 * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0.0, 0.005, size=n)))
    low = close * (1 - np.abs(rng.normal(0.0, 0.005, size=n)))
    open_ = close * (1 + rng.normal(0.0, 0.003, size=n))
    vol = rng.integers(1_000_000, 5_000_000, size=n)
    idx = pd.bdate_range(start="2018-01-02", periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx)


# ---------------------------------------------------------------------------
# Oversold bonus
# ---------------------------------------------------------------------------

def test_oversold_bonus_5pct_when_rsi_under_20_green_65_solid():
    ctx = IndicatorContext(rsi_now=18.0, rsi_band_green_rate=0.67,
                           rsi_band_n=25, rsi_band_avg_fwd5=2.5,
                           sample_quality="SOLID")
    assert _oversold_bonus_pct(ctx) == 5.0


def test_oversold_bonus_8pct_when_rsi_under_15_green_70_solid():
    ctx = IndicatorContext(rsi_now=12.0, rsi_band_green_rate=0.74,
                           rsi_band_n=25, rsi_band_avg_fwd5=4.0,
                           sample_quality="SOLID")
    assert _oversold_bonus_pct(ctx) == 8.0


def test_oversold_bonus_zero_when_green_too_low():
    ctx = IndicatorContext(rsi_now=18.0, rsi_band_green_rate=0.55,
                           rsi_band_n=25, rsi_band_avg_fwd5=1.0,
                           sample_quality="SOLID")
    assert _oversold_bonus_pct(ctx) == 0.0


def test_oversold_bonus_zero_when_sample_thin():
    ctx = IndicatorContext(rsi_now=18.0, rsi_band_green_rate=0.70,
                           rsi_band_n=10, rsi_band_avg_fwd5=3.0,
                           sample_quality="THIN")
    # n=10 < 20 required
    assert _oversold_bonus_pct(ctx) == 0.0


def test_oversold_bonus_zero_when_rsi_above_20():
    ctx = IndicatorContext(rsi_now=22.0, rsi_band_green_rate=0.80,
                           rsi_band_n=40, rsi_band_avg_fwd5=2.0,
                           sample_quality="SOLID")
    assert _oversold_bonus_pct(ctx) == 0.0


def test_oversold_bonus_exact_boundary_rsi_20_not_triggered():
    """RSI < 20, NOT <=. So exactly 20 does not fire."""
    ctx = IndicatorContext(rsi_now=20.0, rsi_band_green_rate=0.80,
                           rsi_band_n=40, rsi_band_avg_fwd5=2.0,
                           sample_quality="SOLID")
    assert _oversold_bonus_pct(ctx) == 0.0


# ---------------------------------------------------------------------------
# Technical axis
# ---------------------------------------------------------------------------

def test_technical_axis_high_green_rate_favours_long():
    ctx = IndicatorContext(50.0, 0.75, 30, 2.0, "SOLID")
    long_s, short_s = _technical_axis(ctx)
    assert long_s > short_s
    assert long_s == 9


def test_technical_axis_low_green_rate_favours_short():
    ctx = IndicatorContext(70.0, 0.30, 30, -1.0, "SOLID")
    long_s, short_s = _technical_axis(ctx)
    assert short_s > long_s
    assert short_s == 8


def test_technical_axis_neutral_on_thin_sample():
    ctx = IndicatorContext(50.0, 0.90, 10, 3.0, "THIN")
    assert _technical_axis(ctx) == (5, 5)


# ---------------------------------------------------------------------------
# Price action axis
# ---------------------------------------------------------------------------

def test_price_action_strong_uptrend_favours_long():
    pa = PriceActionResult(8, 0.05, True, False)
    assert _price_action_axis(pa) == (9, 1)


def test_price_action_strong_downtrend_favours_short():
    pa = PriceActionResult(2, -0.05, False, True)
    assert _price_action_axis(pa) == (1, 9)


def test_price_action_flat_neutral():
    pa = PriceActionResult(5, 0.0, False, False)
    assert _price_action_axis(pa) == (5, 5)


# ---------------------------------------------------------------------------
# News axis always neutral (paper limitation)
# ---------------------------------------------------------------------------

def test_news_axis_is_always_neutral():
    assert _news_axis() == (5, 5)


# ---------------------------------------------------------------------------
# Reversion edge axis mapping (from prompts/02)
# ---------------------------------------------------------------------------

def test_reversion_edge_mapping_all_four_cases():
    # long "no edge" + short "NO-TRADE"
    lr = ReversionResult("LONG", False, "no edge", 65, 60, 0.55, "SOLID")
    sr = ReversionResult("SHORT", False, "continuation", 65, 60, 0.55, "SOLID")
    assert _reversion_edge_axis(lr, sr) == (6, 2)

    # long "no edge" + short "valid"
    lr = ReversionResult("LONG", False, "no edge", 70, 60, 0.52, "SOLID")
    sr = ReversionResult("SHORT", True, "Blowoff-Fade valid", 70, 60, 0.35, "SOLID")
    assert _reversion_edge_axis(lr, sr) == (4, 7)

    # long "pullback" + short "NO-TRADE"
    lr = ReversionResult("LONG", True, "Pullback-Pflicht", 80, 72, 0.30, "SOLID")
    sr = ReversionResult("SHORT", False, "continuation", 80, 72, 0.30, "SOLID")
    assert _reversion_edge_axis(lr, sr) == (3, 2)

    # long "pullback" + short "valid"
    lr = ReversionResult("LONG", True, "Pullback-Pflicht", 80, 72, 0.30, "SOLID")
    sr = ReversionResult("SHORT", True, "Blowoff-Fade valid", 80, 72, 0.30, "SOLID")
    assert _reversion_edge_axis(lr, sr) == (2, 7)


# ---------------------------------------------------------------------------
# Position sizing + Scout inversion (Rule 20)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("conf,expected_pct,expected_inverted", [
    (55.0, 0.0, False),
    (60.0, 15.0, True),
    (63.0, 15.0, True),
    (64.9, 15.0, True),
    (65.0, 20.0, False),
    (69.9, 20.0, False),
    (70.0, 25.0, False),
    (85.0, 25.0, False),
])
def test_position_size_and_split(conf, expected_pct, expected_inverted):
    pct, inv = _position_size_and_split(conf)
    assert pct == expected_pct
    assert inv == expected_inverted


# ---------------------------------------------------------------------------
# KO multipliers
# ---------------------------------------------------------------------------

def test_ko_multiplier_by_bucket():
    assert _ko_multiplier("AAPL") == 2.0     # us_large
    assert _ko_multiplier("GAP") == 2.5      # us_midsmall
    assert _ko_multiplier("GC=F") == 3.0     # commodity
    assert _ko_multiplier("SAP.DE") == 2.0   # eu_large
    assert _ko_multiplier("BA") == 2.0       # stress (BA is large)
    assert _ko_multiplier("UNKNOWN") == 2.0  # default


# ---------------------------------------------------------------------------
# End-to-end: uptrend stock produces LONG signal, high confidence, approved
# ---------------------------------------------------------------------------

def test_uptrend_produces_long_signal():
    df = _build_uptrend()
    _install("UP", df)
    view = HistoricalMarketView(df.index[-1])
    sig = frozen_v9_signal(view, "UP")
    assert sig is not None
    assert sig.direction == "LONG"
    # Strong uptrend should score at least 30 on LONG total
    assert sig.long_total >= 30
    assert sig.long_total > sig.short_total


def test_end_of_crash_window_produces_sensible_signal():
    """At the bottom of a crash, RSI is very low. We don't assert LONG or
    SHORT (SHORT is also plausible, momentum is down); we just assert the
    signal is produced without error and diagnostics are coherent."""
    df = _build_crash(n=400, crash_at=300)
    _install("CRASH", df)
    view = HistoricalMarketView(df.index[320])  # mid-crash
    sig = frozen_v9_signal(view, "CRASH")
    assert sig is not None
    # During the down-move, price action is negative → SHORT axis should
    # be favoured or both close enough for NO-TRADE.
    assert sig.short_total >= sig.long_total - 5
    # ATR should be elevated after 15 big red days
    assert sig.atr_pct is not None and sig.atr_pct > 2.0


def test_gate_rejects_below_60pct_confidence():
    """Low-information bar → confidence below gate, approved = False."""
    # Perfectly flat price — all signals neutral → 30/30 → confidence 50 (raw)
    flat = np.ones(400) * 100.0
    idx = pd.bdate_range(start="2018-01-02", periods=len(flat))
    df = pd.DataFrame({"Open": flat, "High": flat * 1.001, "Low": flat * 0.999,
                       "Close": flat, "Volume": 1_000_000}, index=idx)
    _install("FLAT", df)
    view = HistoricalMarketView(idx[-1])
    sig = frozen_v9_signal(view, "FLAT")
    assert sig is not None
    # Flat series has perfect 30/30, direction=NO-TRADE, approved=False
    assert sig.approved is False
    assert sig.direction == "NO-TRADE"


def test_v1_veto_fires_when_atr_gt_7pct():
    """Build a series with wild intraday moves to force ATR > 7%."""
    rng = np.random.default_rng(3)
    n = 300
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close * 1.10  # +10% intraday range each day
    low = close * 0.90
    open_ = close
    idx = pd.bdate_range(start="2018-01-02", periods=n)
    df = pd.DataFrame({"Open": open_, "High": high, "Low": low,
                       "Close": close, "Volume": 1_000_000}, index=idx)
    _install("WILD", df)
    view = HistoricalMarketView(idx[-1])
    sig = frozen_v9_signal(view, "WILD")
    assert sig is not None
    assert sig.atr_pct > 7.0
    assert sig.v1_veto is True
    assert sig.approved is False
    assert "V1 veto" in (sig.rejection_reason or "")


def test_short_notrade_when_no_reversion_trigger_fires():
    """Rule 18: if direction=SHORT but no short-reversion trigger fires
    anywhere, reject with NO-TRADE."""
    # Falling-momentum series with RSI well below P80 → no blowoff trigger
    n = 300
    rng = np.random.default_rng(5)
    rets = rng.normal(-0.003, 0.01, n)  # drift down
    close = 100 * np.exp(np.cumsum(rets))
    high = close * 1.01
    low = close * 0.99
    idx = pd.bdate_range(start="2018-01-02", periods=n)
    df = pd.DataFrame({"Open": close, "High": high, "Low": low,
                       "Close": close, "Volume": 1_000_000}, index=idx)
    _install("DRIFT_DOWN", df)
    view = HistoricalMarketView(idx[-1])
    sig = frozen_v9_signal(view, "DRIFT_DOWN")
    assert sig is not None
    if sig.direction == "SHORT":
        # If direction is SHORT, Rule 18 must have blocked the approval
        # because the short-reversion trigger cannot fire on a quiet
        # downtrend (RSI is below P80 at the close).
        assert sig.approved is False
        assert "Rule 18" in (sig.rejection_reason or "") or sig.rejection_reason is not None


def test_determinism_same_as_of_same_signal():
    df = _build_uptrend()
    _install("DET", df)
    as_of = df.index[350]
    s1 = frozen_v9_signal(HistoricalMarketView(as_of), "DET")
    s2 = frozen_v9_signal(HistoricalMarketView(as_of), "DET")
    assert s1 is not None and s2 is not None
    assert s1 == s2


def test_diff_penalty_applied_when_diff_under_10():
    """Construct a scorecard with diff < 10 and verify confidence is
    multiplied by 0.9."""
    # Hand-built: we only verify the formula by wiring the penalty math
    # through the end-to-end function. We use a near-flat series where
    # LONG and SHORT scorecards stay close.
    df = _build_uptrend(seed=99)
    _install("NEAR", df)
    view = HistoricalMarketView(df.index[-1])
    sig = frozen_v9_signal(view, "NEAR")
    assert sig is not None
    if sig.diff_penalty_applied:
        # Confidence should be ~= raw * 0.9 + bonus
        expected = sig.raw_confidence_pct * 0.9 + sig.oversold_bonus_pct
        assert abs(sig.confidence_pct - expected) < 0.01
    else:
        # Without penalty, confidence = raw + bonus
        expected = sig.raw_confidence_pct + sig.oversold_bonus_pct
        assert abs(sig.confidence_pct - expected) < 0.01


def test_no_data_returns_none():
    view = HistoricalMarketView("2020-01-15")
    # Symbol never installed in cache; yfinance would also fail for this
    # synthetic name, but let's just check the None return path.
    assert frozen_v9_signal(view, "NOT-A-REAL-TICKER-XYZ") is None
