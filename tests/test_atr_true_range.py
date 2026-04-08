"""Test ATR uses True Range (not just High-Low).

The bug: ATR was calculated as mean(High-Low), ignoring overnight gaps.
True Range = max(H-L, |H-PrevClose|, |L-PrevClose|).
After a gap-up/down, High-Low underestimates volatility → KO levels too tight.
"""

import numpy as np
import pandas as pd
import pytest


def make_hist(opens, highs, lows, closes, volumes=None):
    """Build a DataFrame mimicking yfinance history output."""
    n = len(closes)
    idx = pd.date_range('2026-01-01', periods=n, freq='B')
    return pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes or [1_000_000] * n,
    }, index=idx)


def calc_atr_true_range(hist, period=14):
    """Reference implementation: correct True Range ATR."""
    tr = pd.concat([
        hist['High'] - hist['Low'],
        (hist['High'] - hist['Close'].shift()).abs(),
        (hist['Low'] - hist['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def calc_atr_high_low_only(hist, period=14):
    """Old buggy implementation: just High-Low."""
    return (hist['High'] - hist['Low']).rolling(period).mean().iloc[-1]


class TestATRTrueRange:
    """Verify ATR calculation accounts for overnight gaps."""

    def test_no_gap_both_methods_equal(self):
        """Without gaps, True Range ≈ High-Low."""
        n = 20
        closes = [100 + i * 0.5 for i in range(n)]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        opens = [c - 0.5 for c in closes]

        hist = make_hist(opens, highs, lows, closes)
        atr_tr = calc_atr_true_range(hist)
        atr_hl = calc_atr_high_low_only(hist)

        # Should be very close (small difference from slight trend)
        assert abs(atr_tr - atr_hl) < 1.0, \
            f"Without gaps, methods should be close: TR={atr_tr:.2f} vs HL={atr_hl:.2f}"

    def test_gap_up_true_range_higher(self):
        """After a gap-up, True Range must be HIGHER than High-Low."""
        n = 20
        closes = [100.0] * n
        highs = [102.0] * n
        lows = [98.0] * n
        opens = [100.0] * n

        # Day 15: gap up from 100 to 110 (overnight gap of +10)
        closes[14] = 100.0  # prev close
        opens[15] = 110.0   # gap up!
        lows[15] = 109.0    # intraday low still above prev close
        highs[15] = 113.0   # intraday high
        closes[15] = 112.0

        hist = make_hist(opens, highs, lows, closes)
        atr_tr = calc_atr_true_range(hist)
        atr_hl = calc_atr_high_low_only(hist)

        # True Range for day 15: max(113-109=4, |113-100|=13, |109-100|=9) = 13
        # High-Low for day 15: 113-109 = 4
        assert atr_tr > atr_hl, \
            f"Gap-up: True Range ({atr_tr:.2f}) must exceed High-Low ({atr_hl:.2f})"

    def test_gap_down_true_range_higher(self):
        """After a gap-down, True Range must be HIGHER than High-Low."""
        n = 20
        closes = [150.0] * n
        highs = [152.0] * n
        lows = [148.0] * n
        opens = [150.0] * n

        # Day 15: gap down from 150 to 135 (overnight gap of -15)
        closes[14] = 150.0
        opens[15] = 135.0
        lows[15] = 133.0
        highs[15] = 137.0
        closes[15] = 134.0

        hist = make_hist(opens, highs, lows, closes)
        atr_tr = calc_atr_true_range(hist)
        atr_hl = calc_atr_high_low_only(hist)

        assert atr_tr > atr_hl, \
            f"Gap-down: True Range ({atr_tr:.2f}) must exceed High-Low ({atr_hl:.2f})"

    def test_collect_data_uses_true_range(self):
        """Verify collect_data.py imports pandas.concat for True Range calculation."""
        import importlib.util
        import ast

        spec = importlib.util.find_spec('collect_data')
        if spec is None:
            pytest.skip("collect_data module not on path")

        with open(spec.origin) as f:
            source = f.read()

        # The code must contain pd.concat with three TR components
        assert 'pd.concat' in source, "collect_data.py must use pd.concat for True Range"
        assert "hist['Close'].shift()" in source, \
            "collect_data.py must reference previous close for True Range"
        # Must NOT have the old buggy pattern as the only ATR calc
        # (it's OK if it appears in comments)
        lines = [l for l in source.split('\n')
                 if 'atr14' in l.lower() and not l.strip().startswith('#')]
        assert not any("hist['High'] - hist['Low']).rolling" in l for l in lines), \
            "collect_data.py still has old High-Low-only ATR"
