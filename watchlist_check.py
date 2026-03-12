#!/usr/bin/env python3
"""Silver Hawk Trading - Watchlist Check.
Scans personal watchlist (memory/watchlist.md) 2x daily.
Scores LONG and SHORT independently with v4 Trend/Momentum scoring.
Stateless — no state file needed, no git commit.
Runs at 07:30 + 21:15 CET via GitHub Actions."""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from indicators import calc_technicals, detect_rsi_divergence

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'watchlist.md')
PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'portfolio.md')

FUTURES = {'SI=F', 'GC=F'}
INDEX_FUTURES = ['ES=F', 'NQ=F', 'YM=F']  # S&P, Nasdaq, Dow — for pre-market sentiment
MIN_VOLUME = 50_000
MIN_SCORE = 20
TOP_N = 5
ENRICH_N = 10


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_watchlist_md():
    """Parse memory/watchlist.md → list of {symbol, name, sector}."""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE) as f:
        content = f.read()
    items = []
    current_sector = 'Unbekannt'
    for line in content.splitlines():
        if line.startswith('## ') and not line.startswith('## Legende'):
            current_sector = line[3:].strip()
            continue
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if not cols or cols[0] in ('Symbol', '---', '-----'):
            continue
        if '---' in cols[0]:
            continue
        symbol = cols[0].strip()
        if not symbol or not re.match(r'^[A-Za-z0-9=.\-^]+$', symbol):
            continue
        name = cols[1].strip() if len(cols) > 1 else symbol
        items.append({'symbol': symbol, 'name': name, 'sector': current_sector})
    return items


def get_open_positions():
    """Parse open positions from memory/portfolio.md."""
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    with open(PORTFOLIO_FILE) as f:
        content = f.read()
    positions = []
    in_section = False
    in_table = False
    for line in content.splitlines():
        if line.startswith('## Offene Positionen'):
            in_section = True
            continue
        if in_section and line.startswith('## '):
            break
        if in_section and line.startswith('---'):
            if in_table:
                break
            continue
        if not in_section or not line.startswith('|'):
            continue
        if 'Symbol' in line or '---' in line or 'Richtung' in line:
            in_table = True
            continue
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if not cols:
            continue
        # Skip header row with '#'
        first = re.sub(r'\*+', '', cols[0]).strip()
        if not first or first == '#' or first == 'Symbol':
            continue
        # Detect column layout: portfolio.md has | # | Symbol | Richtung | ... |
        # If first col is a number, shift by 1
        offset = 0
        if re.match(r'^\d+$', first):
            offset = 1
        sym_col = cols[0 + offset] if len(cols) > 0 + offset else ''
        dir_col = cols[1 + offset] if len(cols) > 1 + offset else ''
        pnl_col = cols[5 + offset] if len(cols) > 5 + offset else ''
        ko_col = cols[6 + offset] if len(cols) > 6 + offset else ''

        # Extract base symbol (e.g. "DAX SHORT Turbo KO 25.009" → "DAX")
        base_sym = re.match(r'([A-Za-z0-9=.\-^]+)', sym_col)
        if not base_sym:
            continue
        sym_clean = base_sym.group(1)

        direction = 'LONG' if 'LONG' in dir_col.upper() else ('SHORT' if 'SHORT' in dir_col.upper() else '?')
        if direction == '?' and 'LONG' in sym_col.upper():
            direction = 'LONG'
        elif direction == '?' and 'SHORT' in sym_col.upper():
            direction = 'SHORT'

        # Extract P&L percentage
        pnl_pct = None
        pnl_match = re.search(r'([+-]?\d+(?:[.,]\d+)?)\s*%', pnl_col) or re.search(r'([+-]?\d+(?:[.,]\d+)?)\s*%', str(cols))
        if pnl_match:
            pnl_pct = pnl_match.group(1).replace(',', '.')

        positions.append({
            'symbol': sym_clean,
            'direction': direction,
            'pnl_pct': pnl_pct,
            'raw': sym_col,
        })
    return positions


def batch_download(symbols):
    import yfinance as yf
    return yf.download(symbols, period='1y', group_by='ticker', threads=True, progress=False)


def enrich_candidates(symbols, data):
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


# ---------------------------------------------------------------------------
# Scoring (copied from morning_screener.py — v4, self-contained)
# ---------------------------------------------------------------------------

def passes_hard_gates(sym, d):
    if not d or not d.get('price') or d.get('rsi') is None:
        return False
    if sym in FUTURES:
        return True
    if (d.get('volume') or 0) < MIN_VOLUME:
        return False
    rsi_range = d.get('rsi_range')
    rsi_had_extreme = d.get('rsi_had_extreme', False)
    if rsi_range is not None and (rsi_range < 15 or not rsi_had_extreme):
        return False
    return True


def score_long(d):
    score = 0
    signals = []
    rsi = d['rsi']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')

    if dist200 is not None:
        if dist200 < 0:
            score -= 15; signals.append('UNTER SMA200')
        elif 0 <= dist200 <= 5:
            score += 15; signals.append('Uptrend nah SMA200')
        elif 5 < dist200 <= 15:
            score += 12; signals.append('Uptrend')
        elif 15 < dist200 <= 30:
            score += 8
        else:
            score += 4

    if dist50 is not None and dist200 is not None and dist200 >= 0:
        if -3 <= dist50 <= 1:
            score += 12; signals.append('SMA50 Pullback')
        elif -5 <= dist50 <= 3:
            score += 8; signals.append('Nahe SMA50')
        elif dist50 > 3:
            score += 4

    if 35 <= rsi <= 45:
        score += 12; signals.append(f'RSI {rsi:.0f} Pullback-Zone')
    elif 45 < rsi <= 55:
        score += 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 30 <= rsi < 35:
        score += 6; signals.append(f'RSI {rsi:.0f} niedrig')
    elif 55 < rsi <= 65:
        score += 5
    elif rsi > 70:
        score -= 5
    elif rsi < 30:
        score -= 8

    if rd is not None:
        if rd > 5 and 30 <= rsi <= 55:
            score += 8; signals.append(f'RSI dreht +{rd:.0f}')
        elif rd > 3 and rsi <= 55:
            score += 5
        elif rd > 0:
            score += 2
        elif rd < -5:
            score -= 3

    div = d.get('rsi_divergence')
    if div == 'bullish' and dist200 is not None and dist200 >= 0:
        score += 5; signals.append('DIV bullish')

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
            score += 3

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

    if adx is not None:
        if adx >= 35:
            score += 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            score += 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            score += 3
        else:
            score -= 2

    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg > 0:
        score += 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg > 0:
        score += 5
    elif vr >= 1.5 and chg < -1:
        score -= 3

    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            score += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            score += 2

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
    score = 0
    signals = []
    rsi = d['rsi']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')

    if dist200 is not None:
        if dist200 > 0:
            score -= 15; signals.append('UEBER SMA200')
        elif -5 <= dist200 < 0:
            score += 15; signals.append('Downtrend nah SMA200')
        elif -15 <= dist200 < -5:
            score += 12; signals.append('Downtrend')
        elif -30 <= dist200 < -15:
            score += 8
        else:
            score += 4

    if dist50 is not None and dist200 is not None and dist200 < 0:
        if -1 <= dist50 <= 3:
            score += 12; signals.append('SMA50 Abprall')
        elif -3 <= dist50 <= 5:
            score += 8; signals.append('Nahe SMA50')
        elif dist50 < -3:
            score += 4

    if 55 <= rsi <= 65:
        score += 12; signals.append(f'RSI {rsi:.0f} Bounce-Zone')
    elif 50 <= rsi < 55:
        score += 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 65 < rsi <= 70:
        score += 6; signals.append(f'RSI {rsi:.0f} hoch')
    elif 40 <= rsi < 50:
        score += 5
    elif rsi < 30:
        score -= 5
    elif rsi > 75:
        score -= 8

    if rd is not None:
        if rd < -5 and 45 <= rsi <= 70:
            score += 8; signals.append(f'RSI fällt {rd:.0f}')
        elif rd < -3 and rsi >= 45:
            score += 5
        elif rd < 0:
            score += 2
        elif rd > 5:
            score -= 3

    div = d.get('rsi_divergence')
    if div == 'bearish' and dist200 is not None and dist200 < 0:
        score += 5; signals.append('DIV bearish')

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
            score += 3

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

    if adx is not None:
        if adx >= 35:
            score += 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            score += 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            score += 3
        else:
            score -= 2

    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg < 0:
        score += 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg < 0:
        score += 5
    elif vr >= 1.5 and chg > 1:
        score -= 3

    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            score += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            score += 2

    si = d.get('short_pct') or 0
    if si >= 0.25:
        score -= 5
    elif si >= 0.15:
        score -= 2
    elif si < 0.05:
        score += 2

    rating = d.get('analyst_rating') or ''
    if rating in ('sell', 'strong_sell', 'strongSell'):
        score += 3
    elif rating in ('underperform',):
        score += 2

    c5d = d.get('change_5d')
    if c5d is not None and 2 <= c5d <= 8 and dist200 is not None and dist200 < 0:
        score += 5; signals.append('5d Bounce im Downtrend')

    return max(0, min(100, score)), signals


# ---------------------------------------------------------------------------
# Formatting + Telegram
# ---------------------------------------------------------------------------

def fmt_candidate(i, score, sym, sector, d, signals, direction, positions, name=''):
    emoji = '🟢' if direction == 'LONG' else '🔴'
    name_str = f' {name}' if name else ''
    line = f'{emoji} {i}. <b>{sym}</b>{name_str} ({sector}) {score}/100'

    # Check if already in portfolio
    for p in positions:
        if p['symbol'] in sym or sym in p['symbol']:
            pd = p['direction']
            if (direction == 'LONG' and pd == 'LONG') or (direction == 'SHORT' and pd == 'SHORT'):
                line += f' [{pd}] ✅'
            elif pd in ('LONG', 'SHORT'):
                line += f' [{pd}] ⚠️ GEGEN!'
            else:
                line += ' [BESITZ]'
            break
    line += '\n'

    # Price + core indicators
    price_str = f'${d["price"]:.2f}' if d['price'] >= 1 else f'${d["price"]:.4f}'
    rsi_str = f'RSI {d["rsi"]:.0f}'
    if d.get('rsi_delta') is not None:
        rsi_str += f' (Δ{d["rsi_delta"]:+.0f})'
    line += f'   {price_str} | {rsi_str}'
    if d.get('adx') is not None:
        warn = '⚠️' if d['adx'] < 20 else ''
        line += f' | ADX {d["adx"]:.0f}{warn}'
    if d.get('atr_pct'):
        line += f' | ATR {d["atr_pct"]:.1f}%'
    line += '\n'

    # Signals
    if signals:
        line += f'   {", ".join(signals[:4])}\n'

    # Extras
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


def get_futures_sentiment():
    """Fetch US index futures for pre-market sentiment."""
    import yfinance as yf
    names = {'ES=F': 'S&P 500', 'NQ=F': 'Nasdaq', 'YM=F': 'Dow Jones'}
    results = []
    for sym in INDEX_FUTURES:
        try:
            t = yf.Ticker(sym)
            fi = t.fast_info
            price = fi.get('lastPrice', fi.get('last_price', None))
            prev = fi.get('previousClose', fi.get('previous_close', None))
            if price and prev and prev > 0:
                chg = round((price - prev) / prev * 100, 2)
                results.append({'symbol': sym, 'name': names.get(sym, sym), 'price': price, 'change_pct': chg})
        except Exception:
            continue
    return results


def fmt_futures_block(futures_data):
    """Format futures sentiment as a compact block for the Telegram message."""
    if not futures_data:
        return ''
    lines = ['<b>🇺🇸 US FUTURES</b>']
    avg_chg = sum(f['change_pct'] for f in futures_data) / len(futures_data)
    for f in futures_data:
        arrow = '🟢' if f['change_pct'] > 0.1 else '🔴' if f['change_pct'] < -0.1 else '⚪'
        lines.append(f'  {arrow} {f["name"]}: {f["change_pct"]:+.2f}%')
    if avg_chg > 0.5:
        lines.append('  → Tendenz: <b>Risk-On</b> 📈')
    elif avg_chg < -0.5:
        lines.append('  → Tendenz: <b>Risk-Off</b> 📉')
    else:
        lines.append('  → Tendenz: <b>Neutral</b> ↔️')
    return '\n'.join(lines) + '\n'


def build_message(all_data, positions, sector_map, name_map, scan_time, total_symbols, total_ok, futures_data=None):
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

    # Determine session label
    hour_utc = datetime.now(timezone.utc).hour
    if hour_utc < 12:
        session = 'Pre-Market'
    else:
        session = 'Post-Close'

    msg = f'<b>📋 WATCHLIST CHECK</b> | {scan_time}\n'
    msg += f'{session} | {total_ok}/{total_symbols} Symbole\n'

    # US Futures sentiment
    if futures_data:
        msg += '\n' + fmt_futures_block(futures_data)

    # Portfolio summary
    if positions:
        msg += f'\n<b>📊 PORTFOLIO ({len(positions)} Positionen)</b>\n'
        for p in positions:
            pnl_str = ''
            if p.get('pnl_pct'):
                pnl_val = float(p['pnl_pct'])
                pnl_emoji = '🟢' if pnl_val >= 0 else '🔴'
                pnl_str = f' {pnl_emoji} {p["pnl_pct"]}%'
            msg += f'  {p["raw"][:30]}{pnl_str}\n'

        # Sector concentration
        sectors = {}
        for p in positions:
            s = sector_map.get(p['symbol'], '?')
            sectors[s] = sectors.get(s, 0) + 1
        sector_str = ', '.join(f'{s} {n}' for s, n in sorted(sectors.items(), key=lambda x: x[1], reverse=True))
        msg += f'  Sektoren: {sector_str}\n'

    # TOP LONG
    msg += f'\n<b>🟢 TOP {TOP_N} LONG</b>\n'
    long_shown = 0
    for i, (sc, sym, sec, d, sig) in enumerate(top_long, 1):
        if sc < MIN_SCORE:
            break
        msg += fmt_candidate(i, sc, sym, sec, d, sig, 'LONG', positions, name_map.get(sym, ''))
        long_shown += 1
    if long_shown == 0:
        msg += '  Keine starken Setups\n'

    # TOP SHORT
    msg += f'\n<b>🔴 TOP {TOP_N} SHORT</b>\n'
    short_shown = 0
    for i, (sc, sym, sec, d, sig) in enumerate(top_short, 1):
        if sc < MIN_SCORE:
            break
        msg += fmt_candidate(i, sc, sym, sec, d, sig, 'SHORT', positions, name_map.get(sym, ''))
        short_shown += 1
    if short_shown == 0:
        msg += '  Keine starken Setups\n'

    # Events
    events = [(d.get('earnings_date'), sym) for sym, d in all_data.items() if d.get('earnings_date')]
    events.sort()
    if events:
        msg += f'\n<b>📅 EVENTS</b>\n'
        for date, sym in events[:5]:
            msg += f'  {sym}: Earnings {date}\n'

    rest = total_ok - long_shown - short_shown
    if rest > 0:
        msg += f'\n💤 {rest} weitere im Normalbereich\n'

    msg += f'\n<i>Min Score {MIN_SCORE} | Watchlist Check v1</i>'
    return msg


def send_telegram(text):
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(timezone.utc)
    scan_time = now.strftime('%d.%m.%Y %H:%M UTC')
    print(f'[{now.strftime("%H:%M:%S")} UTC] Watchlist Check v1')

    # 1. Parse watchlist
    watchlist = parse_watchlist_md()
    print(f'  Watchlist: {len(watchlist)} Symbole aus watchlist.md')
    if not watchlist:
        print('  FEHLER: Keine Symbole in watchlist.md gefunden!')
        return

    # 2. Parse portfolio
    positions = get_open_positions()
    print(f'  Portfolio: {len(positions)} offene Positionen')

    # Build maps
    symbols = [w['symbol'] for w in watchlist]
    sector_map = {w['symbol']: w['sector'] for w in watchlist}
    name_map = {w['symbol']: w['name'] for w in watchlist}

    # 3. Batch download
    total_symbols = len(symbols)
    print(f'  Downloading {total_symbols} Symbole...')
    single = len(symbols) == 1
    batch_data = batch_download(symbols)
    print('  Download complete.')

    # 4. Technicals
    print('  Calculating technicals...')
    data = calc_technicals(batch_data, symbols, single=single)
    total_ok = len(data)
    print(f'  Technicals für {total_ok}/{total_symbols} Symbole')

    # 5. Pre-score to find enrich candidates
    passed = {sym: d for sym, d in data.items() if passes_hard_gates(sym, d)}
    print(f'  Hard gates: {len(passed)} bestanden')

    long_pre = sorted([(score_long(d)[0], sym) for sym, d in passed.items()], reverse=True)
    short_pre = sorted([(score_short(d)[0], sym) for sym, d in passed.items()], reverse=True)

    enrich_syms = {sym for _, sym in long_pre[:ENRICH_N]} | {sym for _, sym in short_pre[:ENRICH_N]}
    enrich_syms |= FUTURES & set(data.keys())

    # 6. Enrich top candidates
    print(f'  Enriching {len(enrich_syms)} Kandidaten...')
    enrich_candidates(list(enrich_syms), data)

    for sym in enrich_syms:
        if sym in data and data[sym].get('sector'):
            sector_map.setdefault(sym, data[sym]['sector'])

    # 7. Fetch US futures sentiment
    print('  Fetching US futures...')
    futures_data = get_futures_sentiment()
    if futures_data:
        avg = sum(f['change_pct'] for f in futures_data) / len(futures_data)
        parts = ['{} {:+.2f}%'.format(f['name'], f['change_pct']) for f in futures_data]
        print(f'  Futures: {", ".join(parts)} → avg {avg:+.2f}%')
    else:
        print('  Futures: keine Daten')

    # 8. Build + send message
    msg = build_message(data, positions, sector_map, name_map, scan_time, total_symbols, total_ok, futures_data)
    print(f'\n{msg}\n')

    result = send_telegram(msg)
    print(f'  Telegram sent: {result.get("ok", False)}')


if __name__ == '__main__':
    main()
