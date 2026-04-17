"""Tests for Phase 1 data quality reporting.

The reporting function (`render_markdown_summary`) is tested with
hand-built `DataQualityReport` instances to avoid any network calls.
A single online smoke test is marked with `online` so it can be skipped.
"""

import pytest

from paper.data_quality import (
    DataQualityReport,
    render_markdown_summary,
    validate_data_quality,
)


def _mk(symbol="AAPL", **kw) -> DataQualityReport:
    defaults = dict(
        symbol=symbol,
        bucket="us_large",
        ipo_date="1980-12-12",
        fetch_ok=True,
        first_date="2014-01-02",
        last_date="2023-12-29",
        trading_days=2515,
        expected_trading_days=2516,
        ipo_after_window_start=False,
        delisted_before_window_end=False,
        window_coverage_pct=99.96,
        max_gap_calendar_days=3,
        gaps_over_3_days_count=5,
        gaps_over_7_days_count=0,
        splits_count=1,
        dividends_count=40,
        warnings=[],
    )
    defaults.update(kw)
    return DataQualityReport(**defaults)


def test_markdown_renders_all_symbols_in_table():
    reports = [_mk("AAPL"), _mk("MSFT")]
    md = render_markdown_summary(reports)
    assert "| AAPL |" in md
    assert "| MSFT |" in md
    assert "Fully usable" in md


def test_markdown_flags_partial_ipo():
    gpro = _mk(
        "GPRO",
        bucket="stress",
        ipo_date="2014-06-26",
        first_date="2014-06-26",
        trading_days=2400,
        ipo_after_window_start=True,
        window_coverage_pct=95.0,
        warnings=["IPO 2014-06-26 is after window start"],
    )
    md = render_markdown_summary([gpro])
    assert "PARTIAL-IPO" in md
    # Partial-IPO symbols should NOT appear in the "fully usable" count
    assert "Fully usable (2014-01-01 … 2023-12-31):** 0/1" in md


def test_markdown_flags_no_data():
    broken = _mk(
        "XXXX",
        fetch_ok=False,
        first_date=None,
        last_date=None,
        trading_days=0,
        warnings=["yfinance returned no data"],
    )
    md = render_markdown_summary([broken])
    assert "NO-DATA" in md


def test_markdown_flags_gaps():
    gappy = _mk(gaps_over_7_days_count=2, max_gap_calendar_days=14)
    md = render_markdown_summary([gappy])
    assert "GAP7x2" in md


@pytest.mark.online
def test_validate_returns_reasonable_aapl_report():
    """Single live check against yfinance. Skip with `-m 'not online'`."""
    r = validate_data_quality("AAPL")
    assert r.fetch_ok
    assert r.trading_days > 2400
    assert r.first_date is not None and r.first_date.startswith("2014")
    assert r.last_date is not None and r.last_date.startswith("2023")
    assert r.window_coverage_pct > 95.0
