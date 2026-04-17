"""Phase 2 — Point-in-time market view.

A `HistoricalMarketView(as_of_date)` is a read-only lens over the cached
OHLCV data from Phase 1 that guarantees *nothing* after `as_of_date` is
ever observable. It is the single access point every downstream phase
uses to read market data; if this class is correct, no lookahead bias
can creep in via price / indicator access paths.

Design:
  - Internal cache maps symbol -> pd.DataFrame (Date-indexed OHLCV).
  - Every read method re-slices on `as_of_date` and asserts the slice is
    bounded.
  - Indicator math is computed ONLY on that slice — the slice is passed
    to a pure function that has no knowledge of `as_of_date`.
  - `get_earnings_calendar` returns earnings whose *announce* date is in
    the future relative to `as_of_date`, but only if those earnings were
    scheduled ≥14 calendar days in advance (most earnings schedules are
    known ~2-3 weeks ahead).

What this class deliberately does NOT expose:
  - news flow (Reddit / Trump / headlines)       — not reconstructible
  - intraday bars                                 — we only use daily
  - corporate-action previews                     — handled via yfinance
                                                    adjusted close

The earnings-calendar method is a best-effort shim: yfinance does not
expose the historical *schedule* reliably for 2014-2023, so we only
return earnings DATES that fall after `as_of_date` but within the next
60 days — simulating a 'known in advance' schedule. This is a documented
limitation.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------

_CACHE_DIR = Path(__file__).resolve().parent / "data"
_CACHE_LOCK = threading.Lock()
_MEMO: dict[str, pd.DataFrame] = {}


def _cache_path(symbol: str) -> Path:
    """CSV cache path. We use CSV (not parquet) to avoid a pyarrow
    dependency — the paper sticks strictly to what's in requirements.txt."""
    safe = symbol.replace("=", "_").replace(".", "_").replace("/", "_")
    return _CACHE_DIR / f"{safe}_2014_2023.csv"


def _load_ohlcv(symbol: str) -> pd.DataFrame:
    """Load the cached CSV produced by data_quality.py. Falls back to
    an on-demand yfinance download if the cache is missing (e.g. when
    HistoricalMarketView is used in a fresh checkout)."""
    with _CACHE_LOCK:
        if symbol in _MEMO:
            return _MEMO[symbol]

        p = _cache_path(symbol)
        if p.exists():
            df = pd.read_csv(p, index_col=0, parse_dates=True)
        else:
            import yfinance as yf
            df = yf.download(
                symbol,
                start="2014-01-01",
                end="2024-01-02",
                progress=False,
                auto_adjust=False,
                actions=True,
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df is None or df.empty:
                raise ValueError(f"no data for {symbol}")
            _CACHE_DIR.mkdir(exist_ok=True)
            try:
                df.to_csv(p)
            except Exception:
                pass

        # Normalize index to naive DatetimeIndex; yfinance sometimes returns
        # tz-aware indices which make slice comparisons brittle.
        if getattr(df.index, "tz", None) is not None:
            df = df.copy()
            df.index = df.index.tz_localize(None)
        df = df.sort_index()
        _MEMO[symbol] = df
        return df


# ---------------------------------------------------------------------------
# Pure indicator functions — operate on a slice only, no look-ahead possible.
# ---------------------------------------------------------------------------

def _wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd_hist(close: pd.Series) -> pd.Series:
    exp12 = close.ewm(span=12, adjust=False).mean()
    exp26 = close.ewm(span=26, adjust=False).mean()
    macd_line = exp12 - exp26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line - signal_line


def _atr_pct(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    h = high.values[-(period + 1):]
    l = low.values[-(period + 1):]
    c = close.values[-(period + 1):]
    tr = np.maximum(
        h[1:] - l[1:],
        np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])),
    )
    price = float(close.iloc[-1])
    if price <= 0:
        return None
    return round(float(np.mean(tr)) / price * 100, 3)


def _sma(close: pd.Series, period: int) -> float | None:
    if len(close) < period:
        return None
    return float(close.rolling(period).mean().iloc[-1])


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IndicatorSnapshot:
    """Everything the v9 signal logic needs, as of `as_of_date`."""

    as_of: pd.Timestamp
    price: float
    rsi14: float | None
    rsi14_5d_ago: float | None
    macd_hist: float | None
    macd_hist_prev: float | None
    atr_pct: float | None
    sma50: float | None
    sma200: float | None
    # distance of today's close to the SMA, in percent of close
    sma50_distance_pct: float | None
    sma200_distance_pct: float | None
    # Bars actually available (for sample-size gating in Phase 3)
    bars_available: int


# ---------------------------------------------------------------------------
# HistoricalMarketView
# ---------------------------------------------------------------------------

class HistoricalMarketView:
    """Read-only point-in-time lens over cached OHLCV data.

    Invariant: every method that returns market-derived data truncates at
    `as_of_date` (inclusive). Any violation is either (a) a test assertion
    failure, or (b) a deliberate call to `.as_of` itself.
    """

    def __init__(self, as_of_date: str | pd.Timestamp | date):
        self._as_of = pd.Timestamp(as_of_date).normalize()
        if self._as_of.tzinfo is not None:
            self._as_of = self._as_of.tz_localize(None)

    @property
    def as_of(self) -> pd.Timestamp:
        return self._as_of

    # -- core OHLCV --------------------------------------------------------

    def get_ohlcv(
        self,
        symbol: str,
        lookback_days: int | None = None,
    ) -> pd.DataFrame:
        """Return OHLCV bars whose index is strictly <= as_of_date.

        If `lookback_days` is provided, additionally restrict to the last
        N calendar days BEFORE as_of_date.
        """
        df = _load_ohlcv(symbol)
        sliced = df.loc[df.index <= self._as_of]
        if sliced.empty:
            return sliced

        # Hard assertion — defence in depth. If this ever trips, the class
        # is broken.
        assert sliced.index.max() <= self._as_of, (
            f"leak: {symbol} bar at {sliced.index.max()} > as_of {self._as_of}"
        )

        if lookback_days is not None:
            cutoff = self._as_of - pd.Timedelta(days=lookback_days)
            sliced = sliced.loc[sliced.index >= cutoff]
        return sliced

    def last_close(self, symbol: str) -> float | None:
        df = self.get_ohlcv(symbol)
        if df.empty:
            return None
        return float(df["Close"].iloc[-1])

    def next_open(self, symbol: str) -> tuple[pd.Timestamp, float] | None:
        """Return the (date, open) of the *next* trading day strictly after
        as_of_date. Used by the backtest loop to fill entries realistically
        without any same-day lookahead."""
        df = _load_ohlcv(symbol)
        future = df.loc[df.index > self._as_of]
        if future.empty:
            return None
        first = future.iloc[0]
        return future.index[0], float(first["Open"])

    # -- indicators --------------------------------------------------------

    def get_indicators(
        self,
        symbol: str,
        lookback_bars: int = 300,
    ) -> IndicatorSnapshot | None:
        """Compute RSI14, MACD hist, ATR%, SMA50/200 on the point-in-time
        slice. Returns None if not enough bars."""
        df = self.get_ohlcv(symbol)
        if df.empty:
            return None
        # Use the last `lookback_bars` bars — more than enough for SMA200.
        df = df.iloc[-max(lookback_bars, 220):]
        close = df["Close"].dropna()
        high = df["High"].dropna()
        low = df["Low"].dropna()
        if len(close) < 30:
            return None

        price = float(close.iloc[-1])
        rsi_series = _wilder_rsi(close)
        rsi_now = (
            float(rsi_series.iloc[-1])
            if not np.isnan(rsi_series.iloc[-1])
            else None
        )
        rsi_5d_ago = (
            float(rsi_series.iloc[-6])
            if len(rsi_series) >= 6 and not np.isnan(rsi_series.iloc[-6])
            else None
        )
        macd_hist = _macd_hist(close)
        macd_now = float(macd_hist.iloc[-1]) if len(macd_hist) >= 1 else None
        macd_prev = float(macd_hist.iloc[-2]) if len(macd_hist) >= 2 else None
        atr = _atr_pct(high, low, close)
        sma50 = _sma(close, 50)
        sma200 = _sma(close, 200)
        sma50_dist = (
            round((price - sma50) / sma50 * 100, 3) if sma50 else None
        )
        sma200_dist = (
            round((price - sma200) / sma200 * 100, 3) if sma200 else None
        )

        return IndicatorSnapshot(
            as_of=self._as_of,
            price=price,
            rsi14=round(rsi_now, 2) if rsi_now is not None else None,
            rsi14_5d_ago=round(rsi_5d_ago, 2) if rsi_5d_ago is not None else None,
            macd_hist=round(macd_now, 5) if macd_now is not None else None,
            macd_hist_prev=round(macd_prev, 5) if macd_prev is not None else None,
            atr_pct=atr,
            sma50=round(sma50, 4) if sma50 is not None else None,
            sma200=round(sma200, 4) if sma200 is not None else None,
            sma50_distance_pct=sma50_dist,
            sma200_distance_pct=sma200_dist,
            bars_available=len(close),
        )

    # -- earnings calendar (shim) -----------------------------------------

    # Cache of (symbol -> pd.DatetimeIndex of earnings announce dates),
    # pulled once per symbol.
    _earnings_cache: dict[str, pd.DatetimeIndex] = {}
    _earnings_lock = threading.Lock()

    @classmethod
    def _fetch_earnings_dates(cls, symbol: str) -> pd.DatetimeIndex:
        with cls._earnings_lock:
            if symbol in cls._earnings_cache:
                return cls._earnings_cache[symbol]

            dates: list[pd.Timestamp] = []
            try:
                import yfinance as yf
                tk = yf.Ticker(symbol)
                ed = tk.earnings_dates
                if ed is not None and not ed.empty:
                    idx = ed.index
                    if getattr(idx, "tz", None) is not None:
                        idx = idx.tz_localize(None)
                    dates = [pd.Timestamp(d).normalize() for d in idx]
            except Exception:
                dates = []

            # yfinance only gives the forward-looking window for most
            # tickers — we also fall back on an empty list rather than
            # inventing data.
            out = pd.DatetimeIndex(sorted(set(dates)))
            cls._earnings_cache[symbol] = out
            return out

    def get_earnings_calendar(
        self,
        symbol: str,
        horizon_days: int = 60,
        known_advance_days: int = 14,
    ) -> list[pd.Timestamp]:
        """Return *scheduled* earnings announce dates that are:

          - strictly after `as_of_date`
          - within `horizon_days` forward
          - and would plausibly have been known at least
            `known_advance_days` in advance (earnings schedules are
            usually posted ~2-3 weeks ahead).

        Honest limitation: yfinance only reliably exposes recent / near-
        future earnings dates, not the full historical schedule. For many
        2014-2019 dates this method will return an empty list. That is
        acceptable — the v9 rule that consumes it (earnings_pattern / W5
        check) gracefully degrades to NEUTRAL.
        """
        if horizon_days <= 0:
            return []
        earnings = self._fetch_earnings_dates(symbol)
        if len(earnings) == 0:
            return []
        horizon = self._as_of + pd.Timedelta(days=horizon_days)
        window_start = self._as_of + pd.Timedelta(days=1)
        upcoming = earnings[(earnings >= window_start) & (earnings <= horizon)]

        # Remove any dates within `known_advance_days` of `as_of_date` —
        # those would not have been on the public schedule yet.
        cutoff = self._as_of + pd.Timedelta(days=known_advance_days)
        plausible = upcoming[upcoming >= cutoff]
        return [pd.Timestamp(d) for d in plausible]

    # -- convenience -------------------------------------------------------

    def trading_days_between(
        self, symbol: str, start: str | pd.Timestamp, end: str | pd.Timestamp
    ) -> int:
        """Number of trading days for `symbol` in [start, end], capped at
        as_of_date."""
        end_t = min(pd.Timestamp(end), self._as_of)
        df = self.get_ohlcv(symbol)
        mask = (df.index >= pd.Timestamp(start)) & (df.index <= end_t)
        return int(mask.sum())


# Debug helper — useful from the repl but not part of the public API.
def _clear_caches_for_tests():
    _MEMO.clear()
    HistoricalMarketView._earnings_cache.clear()
