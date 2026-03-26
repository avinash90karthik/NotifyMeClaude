#!/usr/bin/env python3
"""Silver Hawk Trading - Watchlist Check.
Scans personal watchlist (memory/predictions.db) 2x daily.
Scores LONG and SHORT independently with v5 Trend/Momentum scoring.
Stateless — no state file needed, no git commit.
Runs at 07:30 + 21:15 CET via GitHub Actions."""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from indicators import calc_technicals
from risk_audit import risk_audit, parse_portfolio_summary

# Watchlist is stored in predictions.db (loaded via prediction_db.get_watchlist_symbols)
PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'portfolio.md')

INDEX_FUTURES = ['ES=F', 'NQ=F', 'YM=F']  # S&P, Nasdaq, Dow — for pre-market sentiment
MIN_VOLUME = 50_000
MIN_SCORE = 20
TOP_N = 5
ENRICH_N = 10


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_watchlist_md():
    """Load watchlist from predictions.db (single source of truth)."""
    try:
        from prediction_db import get_watchlist_symbols
        return get_watchlist_symbols()
    except Exception:
        return []


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

        combined = dir_col.upper() + ' ' + sym_col.upper()
        if 'LONG' in combined:
            direction = 'LONG'
        elif 'SHORT' in combined:
            direction = 'SHORT'
        else:
            direction = '?'

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
# Scoring (shared with morning_screener.py)
# ---------------------------------------------------------------------------

from morning_screener import passes_hard_gates as _ms_hard_gates
from morning_screener import score_long, score_short


def passes_hard_gates(sym, d):
    return _ms_hard_gates(sym, d, min_volume=MIN_VOLUME)


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
        rw = d.get('regime_weights')
        ls, lsig = score_long(d, regime=rw)
        ss, ssig = score_short(d, regime=rw)
        regime = d.get('regime', '?')
        if regime == 'CHOPPY':
            lsig.insert(0, 'CHOPPY')
            ssig.insert(0, 'CHOPPY')
        elif regime == 'TRENDING':
            lsig.insert(0, 'TREND')
        elif regime == 'RANGE':
            lsig.insert(0, 'RANGE')
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

    # Count regimes for summary
    regime_counts = {}
    for sym, d in passed.items():
        r = d.get('regime', 'TRANSITIONAL')
        regime_counts[r] = regime_counts.get(r, 0) + 1

    msg = f'<b>📋 WATCHLIST CHECK</b> | {scan_time}\n'
    msg += f'{session} | {total_ok}/{total_symbols} Symbole\n'
    regime_str = ' '.join(f'{r[0]}:{c}' for r, c in sorted(regime_counts.items()))
    msg += f'Regimes: {regime_str}\n'

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

    # Risk audit
    pf_state = parse_portfolio_summary()

    # TOP LONG
    msg += f'\n<b>🟢 TOP {TOP_N} LONG</b>\n'
    long_shown = 0
    for i, (sc, sym, sec, d, sig) in enumerate(top_long, 1):
        if sc < MIN_SCORE:
            break
        d['_score_long'] = sc
        d['_score_short'] = 0
        approved, vetoes, warns = risk_audit(sym, d, pf_state, sector=sec)
        if vetoes:
            sig.insert(0, f'VETO: {vetoes[0].split(":")[0]}')
        for w in warns:
            sig.append(f'⚠️{w.split(":")[0]}')
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
        d['_score_long'] = 0
        d['_score_short'] = sc
        approved, vetoes, warns = risk_audit(sym, d, pf_state, sector=sec)
        if vetoes:
            sig.insert(0, f'VETO: {vetoes[0].split(":")[0]}')
        for w in warns:
            sig.append(f'⚠️{w.split(":")[0]}')
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

    msg += f'\n<i>Min Score {MIN_SCORE} | Watchlist Check v2</i>'
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
    print(f'  Watchlist: {len(watchlist)} Symbole aus DB')
    if not watchlist:
        print('  FEHLER: Keine Symbole in predictions.db gefunden!')
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

    long_pre = sorted([(score_long(d, regime=d.get('regime_weights'))[0], sym) for sym, d in passed.items()], reverse=True)
    short_pre = sorted([(score_short(d, regime=d.get('regime_weights'))[0], sym) for sym, d in passed.items()], reverse=True)

    enrich_syms = {sym for _, sym in long_pre[:ENRICH_N]} | {sym for _, sym in short_pre[:ENRICH_N]}
    from morning_screener import is_futures
    futures_syms = {sym for sym in data if is_futures(sym)}
    enrich_syms |= futures_syms & set(data.keys())

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
