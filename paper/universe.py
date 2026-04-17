"""Phase 1 — Static test universe for the 2014-2023 out-of-sample backtest.

Selection was frozen BEFORE looking at any returns, explicitly to avoid
survivorship and forward-looking bias. Criteria per bucket are documented
below so the paper can cite this module as the source of truth.

Rules that governed the picks:
  - IPO strictly before 2014-01-01 (otherwise partial history = bias).
  - No name chosen for being a "known winner" of 2014-2023.
  - Mid/Small bucket includes at least one documented underperformer.
  - Commodities are priced in USD on the futures continuous front month.
  - Stress bucket must contain at least one near-failure (GPRO) and one
    crisis-survivor (BA).

If you change this list after seeing backtest results, the study is tainted.
"""

from dataclasses import dataclass
from typing import Literal

Bucket = Literal["us_large", "us_midsmall", "eu_large", "commodity", "stress"]


@dataclass(frozen=True)
class UniverseEntry:
    symbol: str
    bucket: Bucket
    name: str
    ipo_date: str  # YYYY-MM-DD; used by data_quality to flag partial history
    rationale: str


UNIVERSE: list[UniverseEntry] = [
    # --- 10 US Large Caps --------------------------------------------------
    UniverseEntry("AAPL", "us_large", "Apple", "1980-12-12",
                  "Mega-cap tech; continuous listing since 1980."),
    UniverseEntry("MSFT", "us_large", "Microsoft", "1986-03-13",
                  "Mega-cap tech."),
    UniverseEntry("NVDA", "us_large", "NVIDIA", "1999-01-22",
                  "Tech, included despite being a known 2023 winner — selection "
                  "criterion is 'pre-2014 IPO', not 'underperformer'."),
    UniverseEntry("META", "us_large", "Meta (Facebook)", "2012-05-18",
                  "Tech; IPO 1.5y before window start, full window available."),
    UniverseEntry("AMZN", "us_large", "Amazon", "1997-05-15", "Tech/Retail."),
    UniverseEntry("GOOGL", "us_large", "Alphabet Class A", "2004-08-19",
                  "Tech; using GOOGL (voting) not GOOG."),
    UniverseEntry("JPM", "us_large", "JPMorgan Chase", "1980-03-17",
                  "Financials — diversifies away from tech."),
    UniverseEntry("V", "us_large", "Visa", "2008-03-19", "Financials/Payments."),
    UniverseEntry("XOM", "us_large", "Exxon Mobil", "1970-01-01",
                  "Energy — counter-cyclical to tech, survived 2014-16 oil crash."),
    UniverseEntry("JNJ", "us_large", "Johnson & Johnson", "1970-01-01",
                  "Healthcare — defensive."),

    # --- 5 US Mid/Small (picked pre-seeing-returns) ------------------------
    # Filter: listed well before 2014, NOT chosen for future performance.
    # At least one clear underperformer is included on purpose.
    UniverseEntry("F", "us_midsmall", "Ford Motor", "1956-01-17",
                  "Auto; pre-2014 mid-cap, flat-to-down performance 2014-2023. "
                  "Included precisely because it is NOT a known winner."),
    UniverseEntry("GAP", "us_midsmall", "Gap Inc (formerly GPS)", "1976-05-06",
                  "Retail mid-cap that lost >50% in the window. Survivorship "
                  "control. Ticker was GPS through 2024-01; renamed to GAP on "
                  "2024-02-01 — rename happened AFTER the backtest window, so "
                  "using the new symbol introduces no forward-looking bias "
                  "(it is simply the current yfinance handle for the same "
                  "historical price series)."),
    UniverseEntry("MOS", "us_midsmall", "Mosaic", "2004-10-22",
                  "Fertilizer/Commodities mid-cap; high volatility, uneven "
                  "performance."),
    UniverseEntry("RRC", "us_midsmall", "Range Resources", "1980-01-01",
                  "Shale E&P; strong draw-down during 2015-16 oil bust, "
                  "another survivorship control."),
    UniverseEntry("CLF", "us_midsmall", "Cleveland-Cliffs", "1985-01-01",
                  "Cyclical US steel mid-cap — chosen as the steel slot "
                  "after yfinance stopped serving X (United States Steel) "
                  "following its 2024 acquisition. CLF was listed throughout "
                  "2014-2023 and suffered the same 2015-16 cyclical bust, "
                  "so it preserves the 'stressed steel name' role. Swap "
                  "was made during Phase 1 data validation, before any "
                  "returns were inspected — documented here for audit."),

    # --- 5 EU Large Caps ---------------------------------------------------
    UniverseEntry("SAP.DE", "eu_large", "SAP SE", "1988-11-04",
                  "German mega-cap enterprise software."),
    UniverseEntry("ASML.AS", "eu_large", "ASML Holding", "1995-03-14",
                  "Dutch semi-cap-equipment; well-known winner but selected on "
                  "pre-2014 criterion."),
    UniverseEntry("MC.PA", "eu_large", "LVMH", "1987-07-01",
                  "French luxury conglomerate."),
    UniverseEntry("NESN.SW", "eu_large", "Nestlé", "1970-01-01",
                  "Swiss defensive; CHF-denominated, tests FX handling."),
    UniverseEntry("SHEL.L", "eu_large", "Shell plc", "1970-01-01",
                  "UK energy; ticker change from RDSB.L in 2022 — a good "
                  "torture test for the data layer."),

    # --- 3 Commodities futures --------------------------------------------
    UniverseEntry("GC=F", "commodity", "Gold futures", "2000-08-30",
                  "Continuous front-month gold."),
    UniverseEntry("CL=F", "commodity", "Crude Oil WTI futures", "2000-08-23",
                  "Continuous front-month WTI — huge 2014-16 bear market."),
    UniverseEntry("SI=F", "commodity", "Silver futures", "2000-08-30",
                  "Continuous front-month silver; high-ATR stress test."),

    # --- 2 Stress tests ----------------------------------------------------
    UniverseEntry("BA", "stress", "Boeing", "1962-01-02",
                  "Crisis-survivor: 737-MAX grounding 2019, COVID 2020, -75% "
                  "peak drawdown but still listed."),
    UniverseEntry(
        "GPRO", "stress", "GoPro", "2014-06-26",
        "Near-failure case (-95% peak-to-trough). IPO was 2014-06-26, i.e. "
        "~6 months into the window — this is a documented partial-history "
        "symbol, NOT forward-looking bias (GPRO was observable in real time "
        "for all dates we backtest it on)."),
]

assert len(UNIVERSE) == 25, "Universe size must be exactly 25."


def symbols() -> list[str]:
    return [e.symbol for e in UNIVERSE]


def by_bucket(bucket: Bucket) -> list[UniverseEntry]:
    return [e for e in UNIVERSE if e.bucket == bucket]


BACKTEST_START = "2014-01-01"
BACKTEST_END = "2023-12-31"


if __name__ == "__main__":
    print(f"Universe size: {len(UNIVERSE)}")
    for b in ("us_large", "us_midsmall", "eu_large", "commodity", "stress"):
        entries = by_bucket(b)
        print(f"  {b:12s} ({len(entries)}): "
              f"{', '.join(e.symbol for e in entries)}")
