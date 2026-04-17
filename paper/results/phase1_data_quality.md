# Phase 1 — Data Quality Summary

Generated: 2026-04-17 06:33 UTC

Window: 2014-01-01 → 2023-12-31
Universe: 25 symbols (see `paper/universe.py`)

## Coverage Table

| Symbol | Bucket | IPO | First Bar | Last Bar | Days | Expected | Cov % | Gaps >3d | Gaps >7d | Max Gap | Splits | Divs | Flags |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| AAPL | us_large | 1980-12-12 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 2 | 40 | ok |
| MSFT | us_large | 1986-03-13 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 40 | ok |
| NVDA | us_large | 1999-01-22 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 1 | 40 | ok |
| META | us_large | 2012-05-18 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 0 | ok |
| AMZN | us_large | 1997-05-15 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 1 | 0 | ok |
| GOOGL | us_large | 2004-08-19 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 2 | 0 | ok |
| JPM | us_large | 1980-03-17 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 40 | ok |
| V | us_large | 2008-03-19 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 1 | 40 | ok |
| XOM | us_large | 1970-01-01 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 40 | ok |
| JNJ | us_large | 1970-01-01 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 40 | ok |
| F | us_midsmall | 1956-01-17 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 34 | ok |
| GAP | us_midsmall | 1976-05-06 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 36 | ok |
| MOS | us_midsmall | 2004-10-22 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 41 | ok |
| RRC | us_midsmall | 1980-01-01 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 30 | ok |
| CLF | us_midsmall | 1985-01-01 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 10 | ok |
| SAP.DE | eu_large | 1988-11-04 | 2014-01-02 | 2023-12-29 | 2540 | 2550 | 99.6 | 35 | 0 | 6 | 0 | 10 | ok |
| ASML.AS | eu_large | 1995-03-14 | 2014-01-02 | 2023-12-29 | 2559 | 2550 | 100.3 | 24 | 0 | 5 | 0 | 18 | ok |
| MC.PA | eu_large | 1987-07-01 | 2014-01-02 | 2023-12-29 | 2561 | 2550 | 100.4 | 24 | 0 | 5 | 0 | 20 | ok |
| NESN.SW | eu_large | 1970-01-01 | 2014-01-03 | 2023-12-29 | 2514 | 2550 | 98.6 | 46 | 0 | 6 | 0 | 10 | ok |
| SHEL.L | eu_large | 1970-01-01 | 2014-01-02 | 2023-12-29 | 2525 | 2550 | 99.0 | 56 | 0 | 5 | 0 | 40 | ok |
| GC=F | commodity | 2000-08-30 | 2014-01-02 | 2023-12-29 | 2513 | 2500 | 100.5 | 73 | 0 | 4 | 0 | 0 | ok |
| CL=F | commodity | 2000-08-23 | 2014-01-02 | 2023-12-29 | 2514 | 2500 | 100.6 | 72 | 0 | 4 | 0 | 0 | ok |
| SI=F | commodity | 2000-08-30 | 2014-01-02 | 2023-12-29 | 2513 | 2500 | 100.5 | 73 | 0 | 4 | 0 | 0 | ok |
| BA | stress | 1962-01-02 | 2014-01-02 | 2023-12-29 | 2516 | 2516 | 100.0 | 70 | 0 | 4 | 0 | 25 | ok |
| GPRO | stress | 2014-06-26 | 2014-06-26 | 2023-12-29 | 2395 | 2516 | 95.2 | 66 | 0 | 4 | 0 | 0 | PARTIAL-IPO |

## Per-Symbol Warnings

### AAPL (us_large)
- 2 stock splits in window — ensure auto_adjust handling is consistent in later phases

### GOOGL (us_large)
- 2 stock splits in window — ensure auto_adjust handling is consistent in later phases

### GPRO (stress)
- IPO 2014-06-26 is after window start 2014-01-01 — symbol has partial history, flag in paper

## Aggregate

- **Fully usable (2014-01-01 … 2023-12-31):** 24/25
- **Partial history (post-2014 IPO):** 1
- **Possibly delisted / ticker changed:** 0
- **Fetch failures:** 0

## Notes

- Expected trading-days count is a per-bucket heuristic, not an exact calendar — use it only to flag gross issues.
- `splits` and `dividends` counts come from `yfinance.Ticker.actions` and only include events inside the window.
- Gaps are measured in *calendar* days between consecutive trading bars; weekends already account for a 3-day gap.
- Symbols flagged `PARTIAL-IPO` (e.g. GPRO) are kept in the universe but later phases must only trade them from the first available bar onwards. That is a correctness requirement on the HistoricalMarketView in Phase 2.
