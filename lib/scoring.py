"""LONG / SHORT scoring functions extracted from the legacy morning_screener.

These two functions consume the technical-indicator dict produced by
calc_technicals() and return a 0-100 score plus a list of triggered
signals. They are used by:

  - scripts/preopen_check.py
  - scripts/preopen_backtest.py
  - scripts/backtest.py (rolling-window validation + feature-importance
    decomposition; the only falsification loop for the weights below)

Both functions are pure: they only inspect the input dict and an optional
regime-weight multiplier. No external state, no I/O, no other imports
beyond stdlib.
"""

def score_long(d, regime=None, decompose=False):
    """Score LONG potential (0-100). v5 Trend/Momentum scoring.
    Rewards: uptrend + pullback + momentum resuming.
    Penalizes: falling knives, no trend, overextended.
    regime: optional dict with 'trend', 'oscillator', 'overall' weight multipliers.
    If decompose=True, returns (score, signals, components) with per-indicator breakdown.
    # Weight calibration: see memory/backtest_results.md"""
    trend_pts = 0   # SMA200, SMA50, MACD, ADX
    osc_pts = 0     # RSI, RSI delta, RSI divergence, BB
    other_pts = 0   # ATR, volume, extras
    signals = []
    rsi = d['rsi']
    price = d['price']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')
    rw = regime or {'trend': 1.0, 'oscillator': 1.0, 'overall': 1.0}

    # Component tracking for decompose mode
    sma200_pts = 0
    sma50_pts = 0
    rsi_pts = 0
    macd_pts = 0
    adx_pts = 0
    atr_pts = 0
    vol_pts = 0

    # Trend alignment: SMA200 (0-15)
    if dist200 is not None:
        if dist200 < 0:
            trend_pts -= 15; sma200_pts = -15; signals.append('UNTER SMA200')
        elif 0 <= dist200 <= 5:
            trend_pts += 15; sma200_pts = 15; signals.append('Uptrend nah SMA200')
        elif 5 < dist200 <= 15:
            trend_pts += 12; sma200_pts = 12; signals.append('Uptrend')
        elif 15 < dist200 <= 30:
            trend_pts += 8; sma200_pts = 8
        else:
            trend_pts += 4; sma200_pts = 4

    # SMA50 pullback timing (0-12)
    if dist50 is not None and dist200 is not None and dist200 >= 0:
        if -3 <= dist50 <= 1:
            trend_pts += 12; sma50_pts = 12; signals.append('SMA50 Pullback')
        elif -5 <= dist50 <= 3:
            trend_pts += 8; sma50_pts = 8; signals.append('Nahe SMA50')
        elif dist50 > 3:
            trend_pts += 4; sma50_pts = 4

    # RSI sweet spot (0-12)
    if 35 <= rsi <= 45:
        osc_pts += 12; rsi_pts = 12; signals.append(f'RSI {rsi:.0f} Pullback-Zone')
    elif 45 < rsi <= 55:
        osc_pts += 10; rsi_pts = 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 30 <= rsi < 35:
        osc_pts += 6; rsi_pts = 6; signals.append(f'RSI {rsi:.0f} niedrig')
    elif 55 < rsi <= 65:
        osc_pts += 5; rsi_pts = 5
    elif rsi > 70:
        osc_pts -= 5; rsi_pts = -5
    elif rsi < 30:
        osc_pts -= 8; rsi_pts = -8

    # RSI delta: momentum resuming (0-8)
    if rd is not None:
        if rd > 5 and 30 <= rsi <= 55:
            osc_pts += 8; signals.append(f'RSI dreht +{rd:.0f}')
        elif rd > 3 and rsi <= 55:
            osc_pts += 5
        elif rd > 0:
            osc_pts += 2
        elif rd < -5:
            osc_pts -= 3

    # RSI divergence (0-5)
    div = d.get('rsi_divergence')
    if div == 'bullish' and dist200 is not None and dist200 >= 0:
        osc_pts += 5; signals.append('DIV bullish')

    # MACD confirmation (0-13)
    mc = d.get('macd_hist')
    mp = d.get('macd_hist_prev')
    m_dir = d.get('macd_hist_direction')
    if mc is not None and mp is not None:
        if mp < 0 and mc > 0:
            trend_pts += 10; macd_pts = 10; signals.append('MACD Cross UP')
        elif mc > 0 and m_dir == 'increasing':
            trend_pts += 8; macd_pts = 8; signals.append('MACD steigend')
        elif mc > 0:
            trend_pts += 5; macd_pts = 5
        elif mp < 0 and mc < 0 and m_dir == 'increasing':
            trend_pts += 3; macd_pts = 3

    # ATR% volatility (0-18)
    atr = d.get('atr_pct')
    if atr is not None:
        if atr >= 5.0:
            other_pts += 18; atr_pts = 18; signals.append(f'ATR {atr:.1f}%')
        elif atr >= 3.5:
            other_pts += 14; atr_pts = 14
        elif atr >= 2.5:
            other_pts += 9; atr_pts = 9
        elif atr >= 1.5:
            other_pts += 4; atr_pts = 4

    # ADX trend strength (0-10)
    if adx is not None:
        if adx >= 35:
            trend_pts += 10; adx_pts = 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            trend_pts += 7; adx_pts = 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            trend_pts += 3; adx_pts = 3
        else:
            trend_pts -= 2; adx_pts = -2

    # Volume confirmation (0-8)
    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg > 0:
        other_pts += 8; vol_pts = 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg > 0:
        other_pts += 5; vol_pts = 5
    elif vr >= 1.5 and chg < -1:
        other_pts -= 3; vol_pts = -3

    # Bollinger squeeze (0-5)
    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            osc_pts += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            osc_pts += 2

    # Extras (0-7)
    si = d.get('short_pct') or 0
    if si >= 0.20:
        other_pts += 4; signals.append(f'SI {si*100:.0f}%')
    elif si >= 0.10:
        other_pts += 2

    rating = d.get('analyst_rating') or ''
    if rating in ('strong_buy', 'strongBuy'):
        other_pts += 3
    elif rating in ('buy',):
        other_pts += 2

    c5d = d.get('change_5d')
    if c5d is not None and -8 <= c5d <= -2 and dist200 is not None and dist200 >= 0:
        other_pts += 5; signals.append('5d Pullback im Uptrend')

    # Apply regime weight multipliers
    score = int(trend_pts * rw['trend'] + osc_pts * rw['oscillator'] + other_pts)
    score = int(score * rw['overall'])
    score = max(0, min(100, score))
    if decompose:
        components = {
            'sma200': sma200_pts, 'sma50': sma50_pts, 'rsi': rsi_pts,
            'macd': macd_pts, 'adx': adx_pts, 'atr': atr_pts, 'volume': vol_pts,
        }
        return score, signals, components
    return score, signals


def score_short(d, regime=None, decompose=False):
    """Score SHORT potential (0-100). v5 Trend/Momentum scoring.
    Rewards: downtrend + bounce to resistance + momentum fading.
    Penalizes: strong uptrends, oversold bounces.
    If decompose=True, returns (score, signals, components) with per-indicator breakdown.
    # Weight calibration: see memory/backtest_results.md"""
    trend_pts = 0
    osc_pts = 0
    other_pts = 0
    signals = []
    rsi = d['rsi']
    price = d['price']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')
    rw = regime or {'trend': 1.0, 'oscillator': 1.0, 'overall': 1.0}

    # Component tracking for decompose mode
    sma200_pts = 0
    sma50_pts = 0
    rsi_pts = 0
    macd_pts = 0
    adx_pts = 0
    atr_pts = 0
    vol_pts = 0

    # Trend alignment: SMA200 (0-15)
    if dist200 is not None:
        if dist200 > 0:
            trend_pts -= 15; sma200_pts = -15; signals.append('UEBER SMA200')
        elif -5 <= dist200 < 0:
            trend_pts += 15; sma200_pts = 15; signals.append('Downtrend nah SMA200')
        elif -15 <= dist200 < -5:
            trend_pts += 12; sma200_pts = 12; signals.append('Downtrend')
        elif -30 <= dist200 < -15:
            trend_pts += 8; sma200_pts = 8
        else:
            trend_pts += 4; sma200_pts = 4

    # SMA50 rejection timing (0-12)
    if dist50 is not None and dist200 is not None and dist200 < 0:
        if -1 <= dist50 <= 3:
            trend_pts += 12; sma50_pts = 12; signals.append('SMA50 Abprall')
        elif -3 <= dist50 <= 5:
            trend_pts += 8; sma50_pts = 8; signals.append('Nahe SMA50')
        elif dist50 < -3:
            trend_pts += 4; sma50_pts = 4

    # RSI sweet spot (0-12)
    if 55 <= rsi <= 65:
        osc_pts += 12; rsi_pts = 12; signals.append(f'RSI {rsi:.0f} Bounce-Zone')
    elif 50 <= rsi < 55:
        osc_pts += 10; rsi_pts = 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 65 < rsi <= 70:
        osc_pts += 6; rsi_pts = 6; signals.append(f'RSI {rsi:.0f} hoch')
    elif 40 <= rsi < 50:
        osc_pts += 5; rsi_pts = 5
    elif rsi < 30:
        osc_pts -= 5; rsi_pts = -5
    elif rsi > 75:
        osc_pts -= 8; rsi_pts = -8

    # RSI delta: momentum fading (0-8)
    if rd is not None:
        if rd < -5 and 45 <= rsi <= 70:
            osc_pts += 8; signals.append(f'RSI faellt {rd:.0f}')
        elif rd < -3 and rsi >= 45:
            osc_pts += 5
        elif rd < 0:
            osc_pts += 2
        elif rd > 5:
            osc_pts -= 3

    # RSI divergence (0-5)
    div = d.get('rsi_divergence')
    if div == 'bearish' and dist200 is not None and dist200 < 0:
        osc_pts += 5; signals.append('DIV bearish')

    # MACD confirmation (0-13)
    mc = d.get('macd_hist')
    mp = d.get('macd_hist_prev')
    m_dir = d.get('macd_hist_direction')
    if mc is not None and mp is not None:
        if mp > 0 and mc < 0:
            trend_pts += 10; macd_pts = 10; signals.append('MACD Cross DOWN')
        elif mc < 0 and m_dir == 'decreasing':
            trend_pts += 8; macd_pts = 8; signals.append('MACD fallend')
        elif mc < 0:
            trend_pts += 5; macd_pts = 5
        elif mp > 0 and mc > 0 and m_dir == 'decreasing':
            trend_pts += 3; macd_pts = 3

    # ATR% volatility (0-18)
    atr = d.get('atr_pct')
    if atr is not None:
        if atr >= 5.0:
            other_pts += 18; atr_pts = 18; signals.append(f'ATR {atr:.1f}%')
        elif atr >= 3.5:
            other_pts += 14; atr_pts = 14
        elif atr >= 2.5:
            other_pts += 9; atr_pts = 9
        elif atr >= 1.5:
            other_pts += 4; atr_pts = 4

    # ADX trend strength (0-10)
    if adx is not None:
        if adx >= 35:
            trend_pts += 10; adx_pts = 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            trend_pts += 7; adx_pts = 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            trend_pts += 3; adx_pts = 3
        else:
            trend_pts -= 2; adx_pts = -2

    # Volume confirmation (0-8)
    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg < 0:
        other_pts += 8; vol_pts = 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg < 0:
        other_pts += 5; vol_pts = 5
    elif vr >= 1.5 and chg > 1:
        other_pts -= 3; vol_pts = -3

    # Bollinger squeeze (0-5)
    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            osc_pts += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            osc_pts += 2

    # Extras (0-7)
    si = d.get('short_pct') or 0
    if si >= 0.25:
        other_pts -= 5
    elif si >= 0.15:
        other_pts -= 2
    elif si < 0.05:
        other_pts += 2

    rating = d.get('analyst_rating') or ''
    if rating in ('sell', 'strong_sell', 'strongSell'):
        other_pts += 3
    elif rating in ('underperform',):
        other_pts += 2

    c5d = d.get('change_5d')
    if c5d is not None and 2 <= c5d <= 8 and dist200 is not None and dist200 < 0:
        other_pts += 5; signals.append('5d Bounce im Downtrend')

    # Apply regime weight multipliers
    score = int(trend_pts * rw['trend'] + osc_pts * rw['oscillator'] + other_pts)
    score = int(score * rw['overall'])
    score = max(0, min(100, score))
    if decompose:
        components = {
            'sma200': sma200_pts, 'sma50': sma50_pts, 'rsi': rsi_pts,
            'macd': macd_pts, 'adx': adx_pts, 'atr': atr_pts, 'volume': vol_pts,
        }
        return score, signals, components
    return score, signals


