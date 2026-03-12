#!/usr/bin/env python3
"""Silver Hawk Trading - Morning Screener v3.
Scans NASDAQ-100 + custom watchlist + futures before market open.
Scores LONG and SHORT independently with RSI delta, divergence, ADX,
directional volume, Bollinger squeeze, and wrong-side penalties.
Two-phase: fast batch yf.download(), then individual enrichment for top picks.
Runs daily at 08:00 CET via GitHub Actions."""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import re

from indicators import calc_technicals, detect_rsi_divergence

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'watchlist.json')
PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'portfolio.md')

FUTURES = {'SI=F', 'GC=F'}
MIN_VOLUME = 100_000
MIN_SCORE = 25
TOP_N = 5
ENRICH_N = 10
SECTOR_LIMIT = 0.60


def fetch_nasdaq100_symbols():
    """Fetch NASDAQ-100 constituents + ICB sectors + company names from Wikipedia."""
    try:
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        req = urllib.request.Request(url, headers={'User-Agent': 'SilverHawk/1.0'})
        resp = urllib.request.urlopen(req, timeout=20)
        html = resp.read().decode()
        parts = html.split('id="constituents"')
        if len(parts) < 2:
            print('  Wikipedia: NASDAQ-100 constituents table not found')
            return [], {}, {}
        table_html = parts[1].split('</table>')[0]
        rows = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)
        tickers = []
        sectors = {}
        names = {}
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 3:
                # Columns: [0]=Ticker, [1]=Company, [2]=ICB Industry, [3]=ICB Subsector
                ticker = re.sub(r'<[^>]+>', '', cells[0]).strip().replace('.', '-')
                if ticker and re.match(r'^[A-Z][A-Z0-9-]{0,5}$', ticker):
                    tickers.append(ticker)
                    name_text = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    if name_text:
                        names[ticker] = name_text
                    sector_text = re.sub(r'<[^>]+>', '', cells[2]).strip()
                    if sector_text:
                        sectors[ticker] = sector_text
        return tickers, sectors, names
    except Exception as e:
        print(f'  Wikipedia fetch failed: {e}')
        return [], {}, {}


def get_watchlist():
    """Load watchlist from memory/watchlist.json."""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE) as f:
        return json.load(f)


def get_open_positions():
    """Parse open positions from memory/portfolio.md."""
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    with open(PORTFOLIO_FILE) as f:
        content = f.read()
    positions = []
    in_table = False
    for line in content.splitlines():
        if 'Offene Positionen' in line:
            in_table = True
            continue
        if in_table and line.startswith('---'):
            break
        if not in_table or not line.startswith('|'):
            continue
        if 'Symbol' in line or '---' in line:
            continue
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if not cols:
            continue
        symbol = re.sub(r'\*+', '', cols[0]).strip()
        if not symbol or symbol.lower() in ('cash', 'nvda aktie'):
            continue
        ko = None
        if len(cols) > 5:
            ko_raw = re.sub(r'[\$€\*~]', '', cols[5]).strip().split()[0] if cols[5] else None
            try:
                ko = float(ko_raw) if ko_raw else None
            except (ValueError, TypeError):
                ko = None
        positions.append({'symbol': symbol, 'ko_level': ko, 'sector': None})
    return positions


def get_position_directions(positions, price_data=None):
    """Infer LONG/SHORT direction from KO vs current stock price.
    entry_price is the Turbo certificate price, NOT the stock price,
    so we compare KO against the live stock price instead."""
    dirs = {}
    for p in positions:
        sym = p['symbol']
        ko = p.get('ko_level')
        current_price = price_data.get(sym, {}).get('price') if price_data else None
        if ko and current_price:
            dirs[sym] = 'LONG' if ko < current_price else 'SHORT'
        else:
            dirs[sym] = '?'
    return dirs


def batch_download(symbols):
    """Batch download 1 year of OHLCV data for all symbols."""
    import yfinance as yf
    return yf.download(symbols, period='1y', group_by='ticker', threads=True, progress=False)


def enrich_candidates(symbols, data):
    """Fetch individual yfinance info for top candidates."""
    import yfinance as yf
    today = datetime.now(timezone.utc).date()

    for sym in symbols:
        if sym not in data:
            continue
        try:
            t = yf.Ticker(sym)
            info = t.info
            data[sym]['analyst_rating'] = info.get('recommendationKey')
            data[sym]['short_pct'] = info.get('shortPercentOfFloat', 0)
            data[sym]['market_cap'] = info.get('marketCap', 0)
            data[sym]['sector'] = info.get('sector', '')
            try:
                cal = t.calendar
                if cal and isinstance(cal, dict) and 'Earnings Date' in cal:
                    dates = cal['Earnings Date']
                    if dates:
                        ed = dates[0].date() if hasattr(dates[0], 'date') else dates[0]
                        if ed >= today:
                            data[sym]['earnings_date'] = str(ed)
            except Exception:
                pass
        except Exception as e:
            print(f'  Enrich {sym}: {e}')


def passes_hard_gates(sym, d):
    if not d or not d.get('price') or d.get('rsi') is None:
        return False
    if sym in FUTURES:
        return True
    if (d.get('volume') or 0) < MIN_VOLUME:
        return False
    # RSI Range Quality: must oscillate (range >= 15) AND hit an extreme in 20 days
    rsi_range = d.get('rsi_range')
    rsi_had_extreme = d.get('rsi_had_extreme', False)
    if rsi_range is not None and (rsi_range < 15 or not rsi_had_extreme):
        return False
    return True


def score_long(d):
    """Score LONG potential (0-100). v4 Trend/Momentum scoring.
    Rewards: uptrend + pullback + momentum resuming.
    Penalizes: falling knives, no trend, overextended."""
    score = 0
    signals = []
    rsi = d['rsi']
    price = d['price']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')

    # Trend alignment: SMA200 (0-15)
    if dist200 is not None:
        if dist200 < 0:
            # Below SMA200: heavy penalty, kills the setup
            score -= 15
            signals.append('UNTER SMA200')
        elif 0 <= dist200 <= 5:
            score += 15; signals.append('Uptrend nah SMA200')
        elif 5 < dist200 <= 15:
            score += 12; signals.append('Uptrend')
        elif 15 < dist200 <= 30:
            score += 8
        else:
            score += 4  # Very extended above SMA200

    # SMA50 pullback timing (0-12)
    if dist50 is not None and dist200 is not None and dist200 >= 0:
        if -3 <= dist50 <= 1:
            score += 12; signals.append('SMA50 Pullback')
        elif -5 <= dist50 <= 3:
            score += 8; signals.append('Nahe SMA50')
        elif dist50 > 3:
            score += 4  # Above SMA50, trending

    # RSI sweet spot (0-12)
    if 35 <= rsi <= 45:
        score += 12; signals.append(f'RSI {rsi:.0f} Pullback-Zone')
    elif 45 < rsi <= 55:
        score += 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 30 <= rsi < 35:
        score += 6; signals.append(f'RSI {rsi:.0f} niedrig')
    elif 55 < rsi <= 65:
        score += 5  # Still ok, momentum
    elif rsi > 70:
        score -= 5  # Overbought = bad entry for LONG
    elif rsi < 30:
        score -= 8  # Falling knife territory

    # RSI delta: momentum resuming (0-8)
    if rd is not None:
        if rd > 5 and 30 <= rsi <= 55:
            score += 8; signals.append(f'RSI dreht +{rd:.0f}')
        elif rd > 3 and rsi <= 55:
            score += 5
        elif rd > 0:
            score += 2
        elif rd < -5:
            score -= 3  # Momentum fading

    # RSI divergence (0-5)
    div = d.get('rsi_divergence')
    if div == 'bullish' and dist200 is not None and dist200 >= 0:
        score += 5; signals.append('DIV bullish')

    # MACD confirmation (0-13)
    mc = d.get('macd_hist')
    mp = d.get('macd_hist_prev')
    m_dir = d.get('macd_hist_direction')
    if mc is not None and mp is not None:
        if mp < 0 and mc > 0:
            score += 10; signals.append('MACD Cross UP')
        elif mc > 0 and m_dir == 'increasing':
            score += 8; signals.append('MACD steigend')
        elif mc > 0:
            score += 5
        elif mp < 0 and mc < 0 and m_dir == 'increasing':
            score += 3  # Converging from below = potential cross

    # ATR% volatility (0-18)
    atr = d.get('atr_pct')
    if atr is not None:
        if atr >= 5.0:
            score += 18; signals.append(f'ATR {atr:.1f}%')
        elif atr >= 3.5:
            score += 14
        elif atr >= 2.5:
            score += 9
        elif atr >= 1.5:
            score += 4

    # ADX trend strength (0-10)
    if adx is not None:
        if adx >= 35:
            score += 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            score += 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            score += 3
        else:
            score -= 2  # No trend = bad for momentum

    # Volume confirmation (0-8)
    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg > 0:
        score += 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg > 0:
        score += 5
    elif vr >= 1.5 and chg < -1:
        score -= 3  # High vol on red = distribution

    # Bollinger squeeze (0-5)
    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            score += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            score += 2

    # Extras (0-7)
    si = d.get('short_pct') or 0
    if si >= 0.20:
        score += 4; signals.append(f'SI {si*100:.0f}%')
    elif si >= 0.10:
        score += 2

    rating = d.get('analyst_rating') or ''
    if rating in ('strong_buy', 'strongBuy'):
        score += 3
    elif rating in ('buy',):
        score += 2

    c5d = d.get('change_5d')
    if c5d is not None and -8 <= c5d <= -2 and dist200 is not None and dist200 >= 0:
        score += 5; signals.append('5d Pullback im Uptrend')

    return max(0, min(100, score)), signals


def score_short(d):
    """Score SHORT potential (0-100). v4 Trend/Momentum scoring.
    Rewards: downtrend + bounce to resistance + momentum fading.
    Penalizes: strong uptrends, oversold bounces."""
    score = 0
    signals = []
    rsi = d['rsi']
    price = d['price']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')

    # Trend alignment: SMA200 (0-15)
    if dist200 is not None:
        if dist200 > 0:
            # Above SMA200: heavy penalty, kills the setup
            score -= 15
            signals.append('UEBER SMA200')
        elif -5 <= dist200 < 0:
            score += 15; signals.append('Downtrend nah SMA200')
        elif -15 <= dist200 < -5:
            score += 12; signals.append('Downtrend')
        elif -30 <= dist200 < -15:
            score += 8
        else:
            score += 4  # Very extended below SMA200

    # SMA50 rejection timing (0-12)
    if dist50 is not None and dist200 is not None and dist200 < 0:
        if -1 <= dist50 <= 3:
            score += 12; signals.append('SMA50 Abprall')
        elif -3 <= dist50 <= 5:
            score += 8; signals.append('Nahe SMA50')
        elif dist50 < -3:
            score += 4  # Below SMA50, trending down

    # RSI sweet spot (0-12)
    if 55 <= rsi <= 65:
        score += 12; signals.append(f'RSI {rsi:.0f} Bounce-Zone')
    elif 50 <= rsi < 55:
        score += 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 65 < rsi <= 70:
        score += 6; signals.append(f'RSI {rsi:.0f} hoch')
    elif 40 <= rsi < 50:
        score += 5  # Still ok
    elif rsi < 30:
        score -= 5  # Oversold = bad entry for SHORT
    elif rsi > 75:
        score -= 8  # Extreme = could be strong momentum, risky short

    # RSI delta: momentum fading (0-8)
    if rd is not None:
        if rd < -5 and 45 <= rsi <= 70:
            score += 8; signals.append(f'RSI faellt {rd:.0f}')
        elif rd < -3 and rsi >= 45:
            score += 5
        elif rd < 0:
            score += 2
        elif rd > 5:
            score -= 3  # Momentum picking up = bad for short

    # RSI divergence (0-5)
    div = d.get('rsi_divergence')
    if div == 'bearish' and dist200 is not None and dist200 < 0:
        score += 5; signals.append('DIV bearish')

    # MACD confirmation (0-13)
    mc = d.get('macd_hist')
    mp = d.get('macd_hist_prev')
    m_dir = d.get('macd_hist_direction')
    if mc is not None and mp is not None:
        if mp > 0 and mc < 0:
            score += 10; signals.append('MACD Cross DOWN')
        elif mc < 0 and m_dir == 'decreasing':
            score += 8; signals.append('MACD fallend')
        elif mc < 0:
            score += 5
        elif mp > 0 and mc > 0 and m_dir == 'decreasing':
            score += 3  # Converging from above = potential cross down

    # ATR% volatility (0-18)
    atr = d.get('atr_pct')
    if atr is not None:
        if atr >= 5.0:
            score += 18; signals.append(f'ATR {atr:.1f}%')
        elif atr >= 3.5:
            score += 14
        elif atr >= 2.5:
            score += 9
        elif atr >= 1.5:
            score += 4

    # ADX trend strength (0-10)
    if adx is not None:
        if adx >= 35:
            score += 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            score += 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            score += 3
        else:
            score -= 2  # No trend = bad for momentum

    # Volume confirmation (0-8)
    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg < 0:
        score += 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg < 0:
        score += 5
    elif vr >= 1.5 and chg > 1:
        score -= 3  # High vol on green = accumulation

    # Bollinger squeeze (0-5)
    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            score += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            score += 2

    # Extras (0-7)
    si = d.get('short_pct') or 0
    if si >= 0.25:
        score -= 5  # Too crowded, squeeze risk
    elif si >= 0.15:
        score -= 2
    elif si < 0.05:
        score += 2  # Low SI = room to short

    rating = d.get('analyst_rating') or ''
    if rating in ('sell', 'strong_sell', 'strongSell'):
        score += 3
    elif rating in ('underperform',):
        score += 2

    c5d = d.get('change_5d')
    if c5d is not None and 2 <= c5d <= 8 and dist200 is not None and dist200 < 0:
        score += 5; signals.append('5d Bounce im Downtrend')

    return max(0, min(100, score)), signals


def calc_sector_concentration(positions, sector_map):
    sector_values = {}
    total = 0
    for pos in positions:
        sym = pos['symbol']
        sector = sector_map.get(sym, 'Unbekannt')
        value = (pos.get('entry_price', 0) or 0) * (pos.get('quantity', 0) or 0)
        sector_values[sector] = sector_values.get(sector, 0) + value
        total += value
    if total == 0:
        return {}
    return {s: round(v / total * 100, 1) for s, v in sector_values.items()}


def fmt_candidate(i, score, sym, sector, d, signals, direction, pos_dirs, name=''):
    """Format a single candidate line for Telegram."""
    emoji = '🟢' if direction == 'LONG' else '🔴'
    name_str = f' {name}' if name else ''
    line = f'{emoji} {i}. <b>{sym}</b>{name_str} ({sector}) {score}/100'

    if sym in pos_dirs:
        pd = pos_dirs[sym]
        if (direction == 'LONG' and pd == 'LONG') or (direction == 'SHORT' and pd == 'SHORT'):
            line += f' [{pd}] ✅'
        elif pd in ('LONG', 'SHORT'):
            line += f' [{pd}] ⚠️ GEGEN!'
        else:
            line += ' [BESITZ]'
    line += '\n'

    # Core indicators
    rsi_str = f'RSI {d["rsi"]:.0f}'
    if d.get('rsi_delta') is not None:
        rsi_str += f' (Δ{d["rsi_delta"]:+.0f})'
    line += f'   {rsi_str}'
    if d.get('adx') is not None:
        warn = '⚠️' if d['adx'] < 20 else ''
        line += f' | ADX {d["adx"]:.0f}{warn}'
    if d.get('atr_pct'):
        line += f' | ATR {d["atr_pct"]:.1f}%'
    line += '\n'

    # Signals
    if signals:
        line += f'   {", ".join(signals[:4])}\n'

    # Extras: volume, SI, BB, divergence
    extras = []
    if d.get('vol_ratio') and d['vol_ratio'] >= 1.5:
        arrow = '↑' if d.get('change_pct', 0) > 0 else '↓'
        extras.append(f'Vol {d["vol_ratio"]:.1f}x{arrow}')
    if d.get('short_pct') and d['short_pct'] >= 0.05:
        extras.append(f'SI {d["short_pct"]*100:.0f}%')
    if d.get('bb_width_percentile') is not None and d['bb_width_percentile'] < 20:
        extras.append('BB🔥')
    if d.get('rsi_divergence') == 'bullish':
        extras.append('DIV↑')
    elif d.get('rsi_divergence') == 'bearish':
        extras.append('DIV↓')
    if extras:
        line += f'   {" | ".join(extras)}\n'

    if d.get('earnings_date'):
        line += f'   Earnings: {d["earnings_date"]}\n'

    return line


def build_message(all_data, positions, sector_map, scan_time, total_scanned, pos_dirs, name_map=None):
    """Build the Telegram screener message."""
    name_map = name_map or {}
    passed = {sym: d for sym, d in all_data.items() if passes_hard_gates(sym, d)}

    long_scores = []
    short_scores = []
    for sym, d in passed.items():
        ls, lsig = score_long(d)
        ss, ssig = score_short(d)
        sector = sector_map.get(sym, d.get('sector') or '?')
        long_scores.append((ls, sym, sector, d, lsig))
        short_scores.append((ss, sym, sector, d, ssig))

    long_scores.sort(key=lambda x: x[0], reverse=True)
    short_scores.sort(key=lambda x: x[0], reverse=True)
    top_long = long_scores[:TOP_N]
    top_short = short_scores[:TOP_N]

    sector_conc = calc_sector_concentration(positions, sector_map)

    msg = f'<b>MORNING SCREENER v3</b> | {scan_time}\n'
    msg += f'Gescannt: {total_scanned} | Bestanden: {len(passed)}\n'

    if positions:
        msg += f'\n<b>PORTFOLIO</b>\n'
        for sec, pct in sorted(sector_conc.items(), key=lambda x: x[1], reverse=True):
            warn = ' WARNUNG!' if pct > SECTOR_LIMIT * 100 else ''
            msg += f'  {sec}: {pct:.0f}%{warn}\n'

    msg += f'\n<b>TOP LONG</b>\n'
    if top_long and top_long[0][0] >= MIN_SCORE:
        for i, (sc, sym, sec, d, sig) in enumerate(top_long, 1):
            if sc < MIN_SCORE:
                break
            msg += fmt_candidate(i, sc, sym, sec, d, sig, 'LONG', pos_dirs, name_map.get(sym, ''))
    else:
        msg += '  Keine starken Setups\n'

    msg += f'\n<b>TOP SHORT</b>\n'
    if top_short and top_short[0][0] >= MIN_SCORE:
        for i, (sc, sym, sec, d, sig) in enumerate(top_short, 1):
            if sc < MIN_SCORE:
                break
            msg += fmt_candidate(i, sc, sym, sec, d, sig, 'SHORT', pos_dirs, name_map.get(sym, ''))
    else:
        msg += '  Keine starken Setups\n'

    events = [(d.get('earnings_date'), sym) for sym, d in passed.items() if d.get('earnings_date')]
    events.sort()
    if events:
        msg += f'\n<b>EVENTS</b>\n'
        for date, sym in events[:5]:
            msg += f'  {sym}: Earnings {date}\n'

    msg += f'\n<i>Score Min: {MIN_SCORE} | Analyse via Claude Code</i>'
    return msg


def send_telegram(text):
    """Send message via Telegram. Splits if over 4096 chars."""
    token = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']
    api = f'https://api.telegram.org/bot{token}/sendMessage'

    chunks = []
    if len(text) <= 4096:
        chunks = [text]
    else:
        current = ''
        for line in text.split('\n'):
            if len(current) + len(line) + 1 > 4000:
                chunks.append(current)
                current = line
            else:
                current = current + '\n' + line if current else line
        if current:
            chunks.append(current)

    result = None
    for chunk in chunks:
        body = urllib.parse.urlencode({
            'chat_id': chat_id, 'parse_mode': 'HTML', 'text': chunk,
        }).encode()
        req = urllib.request.Request(api, data=body)
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
    return result


def main():
    now = datetime.now(timezone.utc)
    scan_time = now.strftime('%d.%m.%Y %H:%M UTC')
    print(f'[{now.strftime("%H:%M:%S")} UTC] Morning Screener v3')

    print('  Fetching NASDAQ-100 list...')
    ndx100, ndx100_sectors, ndx100_names = fetch_nasdaq100_symbols()
    print(f'  NASDAQ-100: {len(ndx100)} symbols')

    watchlist = get_watchlist()
    positions = get_open_positions()
    print(f'  Watchlist: {len(watchlist)} | Positions: {len(positions)} open')

    watchlist_syms = {s['symbol'] for s in watchlist}
    position_syms = {p['symbol'] for p in positions}
    all_symbols = sorted(set(ndx100) | watchlist_syms | position_syms | FUTURES)
    total_scanned = len(all_symbols)
    print(f'  Total universe: {total_scanned} symbols')

    if not all_symbols:
        print('  No symbols to scan.')
        return

    sector_map = dict(ndx100_sectors)
    for s in watchlist:
        sector_map.setdefault(s['symbol'], s.get('sector', 'Unbekannt'))

    name_map = dict(ndx100_names)
    for s in watchlist:
        name_map.setdefault(s['symbol'], s.get('name', s['symbol']))
    sector_map.setdefault('SI=F', 'Commodities')
    sector_map.setdefault('GC=F', 'Commodities')

    print(f'  Phase 1: Batch downloading {total_scanned} symbols...')
    single = len(all_symbols) == 1
    batch_data = batch_download(all_symbols)
    print('  Download complete.')

    print('  Calculating technicals...')
    data = calc_technicals(batch_data, all_symbols, single=single)
    print(f'  Technicals for {len(data)} symbols')

    pos_dirs = get_position_directions(positions, data)
    for sym, d in pos_dirs.items():
        print(f'    {sym}: {d}')

    passed = {sym: d for sym, d in data.items() if passes_hard_gates(sym, d)}
    print(f'  Hard gates: {len(passed)} passed')

    long_pre = sorted([(score_long(d)[0], sym) for sym, d in passed.items()], reverse=True)
    short_pre = sorted([(score_short(d)[0], sym) for sym, d in passed.items()], reverse=True)

    enrich_syms = {sym for _, sym in long_pre[:ENRICH_N]} | {sym for _, sym in short_pre[:ENRICH_N]}
    enrich_syms |= (FUTURES | position_syms) & set(data.keys())

    print(f'  Phase 2: Enriching {len(enrich_syms)} candidates...')
    enrich_candidates(list(enrich_syms), data)

    for sym in enrich_syms:
        if sym in data and data[sym].get('sector'):
            sector_map.setdefault(sym, data[sym]['sector'])

    msg = build_message(data, positions, sector_map, scan_time, total_scanned, pos_dirs, name_map)
    print(f'\n{msg}\n')

    result = send_telegram(msg)
    print(f'  Telegram sent: {result.get("ok", False)}')


if __name__ == '__main__':
    main()
