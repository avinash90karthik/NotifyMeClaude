"""Tests for the frozen paper universe (Phase 1)."""

from datetime import date

import pytest

from paper.universe import UNIVERSE, symbols, by_bucket, BACKTEST_START


def test_universe_has_exactly_25_symbols():
    assert len(UNIVERSE) == 25


def test_bucket_counts():
    assert len(by_bucket("us_large")) == 10
    assert len(by_bucket("us_midsmall")) == 5
    assert len(by_bucket("eu_large")) == 5
    assert len(by_bucket("commodity")) == 3
    assert len(by_bucket("stress")) == 2


def test_symbols_are_unique():
    syms = symbols()
    assert len(syms) == len(set(syms)), "duplicate symbols in universe"


def test_ipo_dates_are_parseable():
    for e in UNIVERSE:
        y, m, d = map(int, e.ipo_date.split("-"))
        # Sanity: no IPOs after the window start except the documented one.
        ipo = date(y, m, d)
        window_start = date(*map(int, BACKTEST_START.split("-")))
        if ipo > window_start:
            assert e.symbol == "GPRO", (
                f"{e.symbol} IPO {e.ipo_date} is after window start, "
                "but it is not the documented GPRO exception")


def test_mid_small_bucket_includes_documented_underperformers():
    # The paper claim is that we included underperformers; this test pins
    # the specific names so future edits to universe.py break loudly.
    # (GAP replaced GPS after ticker rename; CLF replaced X after its
    #  acquisition removed the yfinance feed — both swaps are documented
    #  in universe.py and happened before any backtest return was seen.)
    ms = {e.symbol for e in by_bucket("us_midsmall")}
    for required in ("GAP", "CLF", "RRC"):
        assert required in ms, (
            f"{required} was included as a survivorship control and must "
            "remain unless the paper is re-scoped")


def test_stress_bucket_is_gpro_and_ba():
    stress = {e.symbol for e in by_bucket("stress")}
    assert stress == {"BA", "GPRO"}
