#!/usr/bin/env python3
"""Silver Hawk Trading - Portfolio Health Check (GitHub Actions).
Reads open positions from memory/portfolio.md, watchlist from memory/watchlist.json.
Fetches live yfinance data and sends RSI/stop/KO alerts via Telegram."""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'portfolio.md')
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'watchlist.json')


def get_open_positions():
    """Parse open position symbols from memory/portfolio.md."""
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
        # Skip header rows
        if 'Symbol' in line or '---' in line:
            continue
        # Parse: | **VST** | ... | KO | Shares | Buy-In | Stop |
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if not cols:
            continue
        # Extract symbol (remove ** bold markers and extra whitespace)
        symbol = re.sub(r'\*+', '', cols[0]).strip()
        if not symbol or symbol.lower() in ('cash', 'nvda aktie'):
            continue
        # Try to extract KO from col[5] (index 5 = KO Underlying)
        ko = None
        if len(cols) > 5:
            ko_raw = re.sub(r'[\$€\*~]', '', cols[5]).strip().split()[0] if cols[5] else None
            try:
                ko = float(ko_raw) if ko_raw else None
            except (ValueError, TypeError):
                ko = None
        positions.append({'symbol': symbol, 'ko_level': ko})

    return positions


def get_watchlist_symbols():
    """Load watchlist symbols from memory/watchlist.json."""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE) as f:
        stocks = json.load(f)
    return [{'symbol': s['symbol'], 'name': s.get('name', s['symbol'])} for s in stocks]


def fetch_yfinance_data(symbols):
    import yfinance as yf
    import numpy as np
    from wavelet_utils import wavelet_denoise

    data = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            info = t.info
            hist = t.history(period='3mo')

            close_d = wavelet_denoise(hist['Close']) if len(hist) >= 14 else hist['Close']

            rsi = None
            if len(hist) >= 14:
                delta = close_d.diff()
                gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
                rsi_val = float((100 - (100 / (1 + gain / loss))).iloc[-1])
                if not np.isnan(rsi_val):
                    rsi = round(rsi_val, 1)

            macd_hist = None
            if len(hist) >= 26:
                exp12 = close_d.ewm(span=12, adjust=False).mean()
                exp26 = close_d.ewm(span=26, adjust=False).mean()
                macd = exp12 - exp26
                signal = macd.ewm(span=9, adjust=False).mean()
                macd_hist = round(float((macd - signal).iloc[-1]), 2)

            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            prev_close = info.get('previousClose', 0)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

            data[sym] = {
                'price': price,
                'change_pct': round(change_pct, 2),
                'rsi': rsi,
                'macd_hist': macd_hist,
                'sma50': info.get('fiftyDayAverage', 0),
                'sma200': info.get('twoHundredDayAverage', 0),
                'market_state': info.get('marketState', 'UNKNOWN'),
            }
        except Exception as e:
            print(f'  {sym}: ERROR - {e}')
            data[sym] = None

    return data


def build_message(positions, watchlist, data, check_time):
    alerts = []
    pos_lines = []
    watch_lines = []

    owned_symbols = {p['symbol'] for p in positions}

    for pos in positions:
        sym = pos['symbol']
        d = data.get(sym)
        if not d:
            continue

        price = d['price']
        rsi = d['rsi']
        ko = pos.get('ko_level')

        rsi_flag = ''
        if rsi and rsi > 70:
            rsi_flag = '!'
            alerts.append(f'RSI {sym} = {rsi:.0f} VERKAUF ERWAEGEN!')
        elif rsi and rsi < 30:
            rsi_flag = '*'
            alerts.append(f'RSI {sym} = {rsi:.0f} UEBERVERKAUFT!')

        if ko and price:
            ko_dist = abs(price - ko) / price * 100
            if ko_dist < 15:
                alerts.append(f'{sym} {ko_dist:.1f}% vom KO {ko:.2f}!')

        rsi_str = f'{rsi:.0f}{rsi_flag}' if rsi else '-'
        chg = f'{d["change_pct"]:+.1f}%'
        line = f'  {sym} ${price:.2f} ({chg}) RSI:{rsi_str}'
        if ko:
            line += f' | KO:{ko:.2f}'
        pos_lines.append(line)

    for stock in watchlist:
        sym = stock['symbol']
        if sym in owned_symbols:
            continue
        d = data.get(sym)
        if not d:
            continue

        rsi = d['rsi']
        rsi_flag = ''
        if rsi and rsi > 70:
            rsi_flag = '!'
            alerts.append(f'{sym} RSI {rsi:.0f} - OVERBOUGHT')
        elif rsi and rsi < 30:
            rsi_flag = '*'
            alerts.append(f'{sym} RSI {rsi:.0f} - OVERSOLD')

        rsi_str = f'{rsi:.0f}{rsi_flag}' if rsi else '-'
        chg = f'{d["change_pct"]:+.1f}%'
        watch_lines.append(f'  {sym} ${d["price"]:.2f} ({chg}) RSI:{rsi_str}')

    any_state = next((d.get('market_state', '') for d in data.values() if d), '')
    market_str = {'REGULAR': 'OPEN', 'PRE': 'PRE', 'POST': 'POST'}.get(any_state, 'CLOSED')

    msg = f'<b>PORTFOLIO CHECK</b>\n{check_time} | Markt: {market_str}\n'

    if alerts:
        msg += f'\n<b>ALERTS</b>\n' + ''.join(f'  {a}\n' for a in alerts)

    if pos_lines:
        msg += f'\n<b>POSITIONEN</b>\n' + '\n'.join(pos_lines)

    if watch_lines:
        msg += f'\n\n<b>WATCHLIST</b>\n' + '\n'.join(watch_lines)

    return msg


def send_telegram(text):
    token = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']
    body = urllib.parse.urlencode({'chat_id': chat_id, 'parse_mode': 'HTML', 'text': text}).encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=body)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def main():
    now = datetime.now(timezone.utc)
    check_time = now.strftime('%d.%m.%Y %H:%M UTC')
    print(f'[{now.strftime("%H:%M:%S")} UTC] Portfolio Health Check')

    positions = get_open_positions()
    watchlist = get_watchlist_symbols()

    print(f'  Positions: {[p["symbol"] for p in positions]}')

    all_symbols = list({p['symbol'] for p in positions} | {s['symbol'] for s in watchlist})
    if not all_symbols:
        print('  No symbols to check.')
        return

    print(f'  Fetching {len(all_symbols)} symbols...')
    data = fetch_yfinance_data(all_symbols)

    owned_syms = {p['symbol'] for p in positions}
    for sym in sorted(data.keys()):
        d = data[sym]
        if d:
            owned = ' [OWNED]' if sym in owned_syms else ''
            print(f'  {sym}: ${d["price"]:.2f} RSI={d["rsi"]}{owned}')

    msg = build_message(positions, watchlist, data, check_time)
    result = send_telegram(msg)
    print(f'  Telegram sent: {result.get("ok", False)}')


if __name__ == '__main__':
    main()
