"""Phase 1 — Data quality validation for the 2014-2023 universe.

This module only *describes* the data yfinance returns for each symbol.
No trading logic, no indicator computation, no entry/exit — that is
explicitly deferred to later phases.

The output is intended to be pasted into the paper as a reproducibility
appendix: it tells the reader exactly which symbols were usable for the
full window and which had partial history or quality issues.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# We do not want this module to depend on the production collect_data.py —
# the paper backtest must be able to stand alone.
import yfinance as yf

from paper.universe import UNIVERSE, UniverseEntry, BACKTEST_START, BACKTEST_END


@dataclass
class DataQualityReport:
    symbol: str
    bucket: str
    ipo_date: str

    # Availability
    fetch_ok: bool
    first_date: str | None
    last_date: str | None
    trading_days: int
    expected_trading_days: int  # rough NYSE calendar heuristic

    # Coverage
    ipo_after_window_start: bool          # IPO > 2014-01-01
    delisted_before_window_end: bool      # last bar well before 2023-12-31
    window_coverage_pct: float            # trading_days / expected_trading_days

    # Gaps
    max_gap_calendar_days: int
    gaps_over_3_days_count: int
    gaps_over_7_days_count: int

    # Corporate actions
    splits_count: int
    dividends_count: int

    # Flags / warnings — machine-readable, human-readable rendered in the MD
    warnings: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


# Cache raw yfinance responses so repeated runs are cheap and deterministic.
_CACHE_DIR = Path(__file__).resolve().parent / "data"
_CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(symbol: str) -> Path:
    """CSV cache — avoids optional pyarrow/fastparquet dependency."""
    safe = symbol.replace("=", "_").replace(".", "_").replace("/", "_")
    return _CACHE_DIR / f"{safe}_2014_2023.csv"


def _fetch_ohlcv(symbol: str) -> pd.DataFrame | None:
    """Fetch full 2014-2023 OHLCV once, cached on disk."""
    cache = _cache_path(symbol)
    if cache.exists():
        try:
            return pd.read_csv(cache, index_col=0, parse_dates=True)
        except Exception:
            cache.unlink(missing_ok=True)  # corrupt cache, refetch

    df = yf.download(
        symbol,
        start=BACKTEST_START,
        end="2024-01-02",
        progress=False,
        auto_adjust=False,
        actions=True,
    )
    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.sort_index()
    try:
        df.to_csv(cache)
    except Exception:
        pass
    return df


def _fetch_actions(symbol: str) -> tuple[int, int]:
    """Return (splits_count, dividends_count) inside the window."""
    try:
        tk = yf.Ticker(symbol)
        actions = tk.actions
    except Exception:
        return (0, 0)

    if actions is None or actions.empty:
        return (0, 0)
    # Restrict to window
    idx = actions.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
        actions = actions.copy()
        actions.index = idx
    mask = (actions.index >= pd.Timestamp(BACKTEST_START)) & (
        actions.index <= pd.Timestamp(BACKTEST_END)
    )
    windowed = actions.loc[mask]
    splits = int((windowed.get("Stock Splits", pd.Series(dtype=float)) != 0).sum())
    divs = int((windowed.get("Dividends", pd.Series(dtype=float)) != 0).sum())
    return splits, divs


def _expected_trading_days(bucket: str) -> int:
    """Rough expected count of trading days in 2014-01-01 .. 2023-12-31.

    Numbers checked against typical NYSE / Xetra / LSE calendars. We
    intentionally report a single expected number per bucket to keep the
    metric simple — the paper discusses this as an approximation.
    """
    # ~252 trading days/year * 10 years ≈ 2516 (US), ~255*10 ≈ 2550 (EU),
    # commodities are close to US hours.
    return {
        "us_large": 2516,
        "us_midsmall": 2516,
        "eu_large": 2550,
        "commodity": 2500,
        "stress": 2516,
    }.get(bucket, 2516)


def validate_data_quality(
    symbol: str,
    start: str = BACKTEST_START,
    end: str = BACKTEST_END,
) -> DataQualityReport:
    """Return a DataQualityReport for a single symbol.

    This is the function the paper cites as the validation routine. It
    deliberately does not compute any indicators or try to 'fix' gaps.
    """
    entry = next((e for e in UNIVERSE if e.symbol == symbol), None)
    if entry is None:
        raise ValueError(f"{symbol!r} not in the defined universe")

    warnings: list[str] = []

    df = _fetch_ohlcv(symbol)
    if df is None or df.empty:
        return DataQualityReport(
            symbol=symbol,
            bucket=entry.bucket,
            ipo_date=entry.ipo_date,
            fetch_ok=False,
            first_date=None,
            last_date=None,
            trading_days=0,
            expected_trading_days=_expected_trading_days(entry.bucket),
            ipo_after_window_start=False,
            delisted_before_window_end=False,
            window_coverage_pct=0.0,
            max_gap_calendar_days=0,
            gaps_over_3_days_count=0,
            gaps_over_7_days_count=0,
            splits_count=0,
            dividends_count=0,
            warnings=["yfinance returned no data — symbol may be delisted or "
                     "ticker changed; re-check required"],
        )

    # Clip to requested window
    df = df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]
    if df.empty:
        warnings.append("no bars inside requested window")

    first_date = df.index.min().strftime("%Y-%m-%d") if not df.empty else None
    last_date = df.index.max().strftime("%Y-%m-%d") if not df.empty else None
    trading_days = len(df)
    expected = _expected_trading_days(entry.bucket)

    ipo_after_start = pd.Timestamp(entry.ipo_date) > pd.Timestamp(start)
    # "Delisted" heuristic: last bar > 30 calendar days before window end
    delisted = False
    if last_date is not None:
        gap_end = (pd.Timestamp(end) - pd.Timestamp(last_date)).days
        delisted = gap_end > 30

    # Gaps between consecutive bars
    if len(df) >= 2:
        diffs = df.index.to_series().diff().dt.days.dropna()
        max_gap = int(diffs.max())
        gaps_3 = int((diffs > 3).sum())
        gaps_7 = int((diffs > 7).sum())
    else:
        max_gap = 0
        gaps_3 = 0
        gaps_7 = 0

    splits_count, dividends_count = _fetch_actions(symbol)

    coverage = 100.0 * trading_days / expected if expected else 0.0

    # Build warnings
    if ipo_after_start:
        warnings.append(
            f"IPO {entry.ipo_date} is after window start {start} — "
            "symbol has partial history, flag in paper")
    if delisted:
        warnings.append(
            f"last bar {last_date} is >30d before window end {end} — "
            "possible delisting or ticker change")
    if coverage < 90.0 and not ipo_after_start and not delisted:
        warnings.append(
            f"coverage {coverage:.1f}% below 90% without obvious IPO/delisting "
            "reason — investigate")
    if gaps_7 > 0:
        warnings.append(
            f"{gaps_7} gaps >7 calendar days found (max {max_gap}d)")
    if splits_count >= 2:
        warnings.append(
            f"{splits_count} stock splits in window — ensure auto_adjust "
            "handling is consistent in later phases")

    return DataQualityReport(
        symbol=symbol,
        bucket=entry.bucket,
        ipo_date=entry.ipo_date,
        fetch_ok=True,
        first_date=first_date,
        last_date=last_date,
        trading_days=trading_days,
        expected_trading_days=expected,
        ipo_after_window_start=ipo_after_start,
        delisted_before_window_end=delisted,
        window_coverage_pct=round(coverage, 2),
        max_gap_calendar_days=max_gap,
        gaps_over_3_days_count=gaps_3,
        gaps_over_7_days_count=gaps_7,
        splits_count=splits_count,
        dividends_count=dividends_count,
        warnings=warnings,
    )


def render_markdown_summary(reports: list[DataQualityReport]) -> str:
    """Turn a list of reports into the markdown table the paper embeds."""
    lines: list[str] = []
    lines.append("# Phase 1 — Data Quality Summary")
    lines.append("")
    lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append(f"Window: {BACKTEST_START} → {BACKTEST_END}")
    lines.append(f"Universe: {len(reports)} symbols (see `paper/universe.py`)")
    lines.append("")

    lines.append("## Coverage Table")
    lines.append("")
    lines.append("| Symbol | Bucket | IPO | First Bar | Last Bar | Days | Expected | Cov % | Gaps >3d | Gaps >7d | Max Gap | Splits | Divs | Flags |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in reports:
        flags = []
        if not r.fetch_ok:
            flags.append("NO-DATA")
        if r.ipo_after_window_start:
            flags.append("PARTIAL-IPO")
        if r.delisted_before_window_end:
            flags.append("POSSIBLE-DELIST")
        if r.window_coverage_pct < 90 and not r.ipo_after_window_start:
            flags.append("LOW-COV")
        if r.gaps_over_7_days_count > 0:
            flags.append(f"GAP7x{r.gaps_over_7_days_count}")
        flags_str = ", ".join(flags) if flags else "ok"
        lines.append(
            f"| {r.symbol} | {r.bucket} | {r.ipo_date} | "
            f"{r.first_date or '-'} | {r.last_date or '-'} | "
            f"{r.trading_days} | {r.expected_trading_days} | "
            f"{r.window_coverage_pct:.1f} | "
            f"{r.gaps_over_3_days_count} | {r.gaps_over_7_days_count} | "
            f"{r.max_gap_calendar_days} | "
            f"{r.splits_count} | {r.dividends_count} | {flags_str} |"
        )

    lines.append("")
    lines.append("## Per-Symbol Warnings")
    lines.append("")
    any_warnings = False
    for r in reports:
        if r.warnings:
            any_warnings = True
            lines.append(f"### {r.symbol} ({r.bucket})")
            for w in r.warnings:
                lines.append(f"- {w}")
            lines.append("")
    if not any_warnings:
        lines.append("_No symbols raised warnings._")
        lines.append("")

    # Aggregate
    usable = [r for r in reports
              if r.fetch_ok
              and not r.ipo_after_window_start
              and not r.delisted_before_window_end
              and r.window_coverage_pct >= 90.0]
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- **Fully usable (2014-01-01 … 2023-12-31):** "
                 f"{len(usable)}/{len(reports)}")
    lines.append(f"- **Partial history (post-2014 IPO):** "
                 f"{sum(1 for r in reports if r.ipo_after_window_start)}")
    lines.append(f"- **Possibly delisted / ticker changed:** "
                 f"{sum(1 for r in reports if r.delisted_before_window_end)}")
    lines.append(f"- **Fetch failures:** "
                 f"{sum(1 for r in reports if not r.fetch_ok)}")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Expected trading-days count is a per-bucket heuristic, not "
                 "an exact calendar — use it only to flag gross issues.")
    lines.append("- `splits` and `dividends` counts come from "
                 "`yfinance.Ticker.actions` and only include events inside "
                 "the window.")
    lines.append("- Gaps are measured in *calendar* days between consecutive "
                 "trading bars; weekends already account for a 3-day gap.")
    lines.append("- Symbols flagged `PARTIAL-IPO` (e.g. GPRO) are kept in "
                 "the universe but later phases must only trade them from "
                 "the first available bar onwards. That is a correctness "
                 "requirement on the HistoricalMarketView in Phase 2.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="paper/results/phase1_data_quality.md",
                        help="Markdown output path")
    parser.add_argument("--symbol", default=None,
                        help="Optional: validate only one symbol (debug)")
    args = parser.parse_args()

    entries = [e for e in UNIVERSE
               if args.symbol is None or e.symbol == args.symbol]
    if not entries:
        print(f"No universe entry for {args.symbol!r}", file=sys.stderr)
        return 2

    reports: list[DataQualityReport] = []
    for i, entry in enumerate(entries, 1):
        print(f"[{i}/{len(entries)}] {entry.symbol} ({entry.bucket})...",
              flush=True)
        try:
            r = validate_data_quality(entry.symbol)
        except Exception as e:
            print(f"    FAILED: {e}", file=sys.stderr)
            r = DataQualityReport(
                symbol=entry.symbol,
                bucket=entry.bucket,
                ipo_date=entry.ipo_date,
                fetch_ok=False,
                first_date=None, last_date=None,
                trading_days=0,
                expected_trading_days=_expected_trading_days(entry.bucket),
                ipo_after_window_start=False,
                delisted_before_window_end=False,
                window_coverage_pct=0.0,
                max_gap_calendar_days=0,
                gaps_over_3_days_count=0,
                gaps_over_7_days_count=0,
                splits_count=0, dividends_count=0,
                warnings=[f"exception during validation: {e}"],
            )
        reports.append(r)
        # Gentle on yfinance; avoid hammering the endpoint.
        time.sleep(0.3)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown_summary(reports))
    print(f"\nWrote {out} ({len(reports)} symbols).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
