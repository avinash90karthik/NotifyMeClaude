"""Market-status classification + live-price selection.

Pure logic functions extracted so they can be tested without hitting yfinance.

The two public entry points:

    classify_market_status(market_state, now_cet) -> (status, source)
        Maps yfinance ``info.marketState`` to one of PRE | OPEN | POST | CLOSED.
        Falls back to a CET-time-window heuristic when ``market_state`` is
        missing/unknown. ``source`` reports which path was taken so callers can
        log it.

    select_live_price(info, prev_close, market_status, now_utc) -> dict
        Walks the per-status price-source hierarchy (premarket / live /
        postmarket / last_close), enforces staleness checks, and returns
        the chosen price plus metadata (``price``, ``price_source``,
        ``price_timestamp``, ``warnings``).
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Optional
from zoneinfo import ZoneInfo


# yfinance marketState string -> our 4-state vocabulary
_MARKET_STATE_MAP = {
    'PRE': 'PRE',
    'PREPRE': 'PRE',
    'REGULAR': 'OPEN',
    'POST': 'POST',
    'POSTPOST': 'POST',
    'CLOSED': 'CLOSED',
}

# Fallback CET windows for US markets (when marketState is missing/unknown).
# US Pre-Market 04:00-09:30 ET => 10:00-15:30 CET (DST-naive approximation;
# acceptable as fallback only).
_FALLBACK_PRE_START = time(11, 0)
_FALLBACK_OPEN_START = time(15, 30)
_FALLBACK_POST_START = time(22, 0)
_FALLBACK_POST_END = time(2, 0)  # wraps midnight


def classify_market_status(market_state, now_cet=None):
    """Return (status, source) where status is PRE|OPEN|POST|CLOSED and
    source is 'marketState' or 'fallback_clock'.

    Parameters
    ----------
    market_state : str | None
        ``yfinance.Ticker.info.get('marketState')``. May be None or unknown.
    now_cet : datetime | None
        Current local CET datetime. Only consulted when fallback is needed.
        If None, uses ``datetime.now(ZoneInfo('Europe/Berlin'))``.
    """
    if market_state and market_state in _MARKET_STATE_MAP:
        return _MARKET_STATE_MAP[market_state], 'marketState'

    if now_cet is None:
        now_cet = datetime.now(ZoneInfo('Europe/Berlin'))
    t = now_cet.time()

    # Weekend → CLOSED regardless of clock (Mon=0..Sun=6)
    if now_cet.weekday() >= 5:
        return 'CLOSED', 'fallback_clock'

    if _FALLBACK_PRE_START <= t < _FALLBACK_OPEN_START:
        return 'PRE', 'fallback_clock'
    if _FALLBACK_OPEN_START <= t < _FALLBACK_POST_START:
        return 'OPEN', 'fallback_clock'
    # POST wraps midnight: 22:00..23:59 OR 00:00..02:00
    if t >= _FALLBACK_POST_START or t < _FALLBACK_POST_END:
        return 'POST', 'fallback_clock'
    return 'CLOSED', 'fallback_clock'


def _is_today_in_ny(epoch_ts):
    """Is the given Unix timestamp on the current US trading date?"""
    if not epoch_ts:
        return False
    try:
        ts = float(epoch_ts)
    except (TypeError, ValueError):
        return False
    if ts <= 0:
        return False
    ny = ZoneInfo('America/New_York')
    return datetime.fromtimestamp(ts, tz=ny).date() == datetime.now(ny).date()


def _is_stale(extended_price, extended_time, prev_close):
    """Decide if an extended-hours price is stale.

    Preferred check: extended_time is on the current NY trading date.
    Fallback (no timestamp): the price differs from prev_close by >0.01%
    (otherwise it is most likely the previous day's leftover).
    """
    if extended_time is not None:
        return not _is_today_in_ny(extended_time)
    if extended_price is None or prev_close is None or prev_close <= 0:
        return True
    return abs(float(extended_price) / float(prev_close) - 1.0) <= 0.0001


def _epoch_to_iso(epoch_ts):
    if not epoch_ts:
        return None
    try:
        return datetime.fromtimestamp(float(epoch_ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def select_live_price(info, prev_close, market_status, last_close=None, now_utc=None):
    """Pick the best live price + report provenance.

    Parameters
    ----------
    info : dict
        ``yfinance.Ticker.info`` (or any dict-like with the relevant keys).
    prev_close : float | None
        ``info.previousClose`` (passed explicitly so callers can override).
    market_status : str
        One of PRE | OPEN | POST | CLOSED.
    last_close : float | None
        Fallback price if everything else is missing — typically
        ``hist['Close'].iloc[-1]``.
    now_utc : datetime | None
        Override for testing; defaults to ``datetime.now(timezone.utc)``.

    Returns
    -------
    dict with keys:
        price : float | None
        price_source : 'premarket' | 'live' | 'postmarket' | 'last_close' | None
        price_timestamp : ISO string | None
        change_from_close_pct : float | None
        extended_change_pct : float | None
        warnings : list[str]
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    warnings = []

    pre_price = info.get('preMarketPrice')
    pre_time = info.get('preMarketTime')
    pre_change = info.get('preMarketChangePercent')

    post_price = info.get('postMarketPrice')
    post_time = info.get('postMarketTime')
    post_change = info.get('postMarketChangePercent')

    live_price = info.get('currentPrice') or info.get('regularMarketPrice')
    live_time = info.get('regularMarketTime')

    chosen_price = None
    chosen_source = None
    chosen_ts = None
    extended_change = None

    def _accept(price, source, ts_epoch, ext_change=None):
        nonlocal chosen_price, chosen_source, chosen_ts, extended_change
        chosen_price = float(price)
        chosen_source = source
        chosen_ts = _epoch_to_iso(ts_epoch) or now_utc.isoformat()
        extended_change = ext_change

    if market_status == 'PRE':
        if pre_price and pre_price > 0:
            if _is_stale(pre_price, pre_time, prev_close):
                warnings.append('premarket price stale, falling back to live tick')
            else:
                _accept(pre_price, 'premarket', pre_time, pre_change)
        if chosen_price is None and live_price and live_price > 0:
            warnings.append('premarket price unavailable, using last regular tick')
            _accept(live_price, 'live', live_time)
        if chosen_price is None and last_close:
            warnings.append('no live price, using last close')
            _accept(last_close, 'last_close', None)

    elif market_status == 'OPEN':
        if live_price and live_price > 0:
            _accept(live_price, 'live', live_time)
        elif last_close:
            warnings.append('no live price during OPEN, using last close')
            _accept(last_close, 'last_close', None)

    elif market_status == 'POST':
        if post_price and post_price > 0:
            if _is_stale(post_price, post_time, prev_close):
                warnings.append('postmarket price stale, falling back to live tick')
            else:
                _accept(post_price, 'postmarket', post_time, post_change)
        if chosen_price is None and live_price and live_price > 0:
            warnings.append('postmarket price unavailable, using last regular tick')
            _accept(live_price, 'live', live_time)
        if chosen_price is None and last_close:
            warnings.append('no live price, using last close')
            _accept(last_close, 'last_close', None)

    else:  # CLOSED
        if last_close:
            _accept(last_close, 'last_close', None)
        elif live_price and live_price > 0:
            _accept(live_price, 'live', live_time)

    change_from_close = None
    if chosen_price is not None and prev_close and prev_close > 0:
        change_from_close = round((chosen_price / float(prev_close) - 1.0) * 100, 3)

    return {
        'price': chosen_price,
        'price_source': chosen_source,
        'price_timestamp': chosen_ts,
        'change_from_close_pct': change_from_close,
        'extended_change_pct': float(extended_change) if extended_change is not None else None,
        'warnings': warnings,
    }
