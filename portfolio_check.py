#!/usr/bin/env python3
"""Silver Hawk Trading - Portfolio Health Check (GitHub Actions).
Fetches live data for open positions + full watchlist, sends Telegram alert with RSI flags."""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from supabase_client import supabase_request


def get_open_positions():
    """Fetch open positions from portfolio table."""
    result = supabase_request('GET', 'portfolio?select=*&status=eq.open')
    return result or []


def get_watchlist_symbols():
    """Fetch all active symbols from stocks table."""
    result = supabase_request('GET', 'stocks?select=symbol,name&is_active=eq.true')
    return result or []


def fetch_yfinance_data(symbols):
    """Fetch live yfinance data for a list of symbols."""
    import yfinance as yf
    import numpy as np

    data = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            info = t.info
            hist = t.history(period='3mo')

            rsi = None
            macd_hist = None

            if len(hist) >= 14:
                delta = hist['Close'].diff()
                gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
                rs = gain / loss
                rsi_val = float((100 - (100 / (1 + rs))).iloc[-1])
                if not np.isnan(rsi_val):
                    rsi = round(rsi_val, 1)

            if len(hist) >= 26:
                exp12 = hist['Close'].ewm(span=12, adjust=False).mean()
                exp26 = hist['Close'].ewm(span=26, adjust=False).mean()
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
    """Build the Telegram alert message."""
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
        entry = pos.get('entry_price')
        stop = pos.get('stop_loss')
        target = pos.get('target_price')
        ko = pos.get('ko_level')
        qty = pos.get('quantity', 0)

        pnl_pct = ((price - entry) / entry * 100) if entry and entry > 0 else 0

        rsi_flag = ''
        if rsi and rsi > 70:
            rsi_flag = '!'
            alerts.append(f'RSI {sym} = {rsi:.0f} VERKAUF ERWAEGEN!')
        elif rsi and rsi < 30:
            rsi_flag = '*'
            alerts.append(f'RSI {sym} = {rsi:.0f} NACHKAUFEN?')

        if stop and price:
            stop_dist = abs(price - stop) / price * 100
            if stop_dist < 5:
                alerts.append(f'{sym} {stop_dist:.1f}% vom Stop ${stop:.0f}!')

        if ko and price:
            ko_dist = abs(price - ko) / price * 100
            if ko_dist < 15:
                alerts.append(f'{sym} {ko_dist:.1f}% vom KO ${ko:.2f}!')

        if target and price:
            target_dist = abs(target - price) / price * 100
            if target_dist < 5:
                alerts.append(f'{sym} fast am Ziel ${target:.0f}!')

        rsi_str = f'{rsi:.0f}{rsi_flag}' if rsi else '-'
        pnl_sign = '+' if pnl_pct >= 0 else ''
        chg = f'{d["change_pct"]:+.1f}%'

        line = f'  {sym} ${price:.2f} ({chg}) RSI:{rsi_str}'
        line += f'\n    {pnl_sign}{pnl_pct:.1f}% | {qty:.0f}x'

        level_parts = []
        if stop:
            level_parts.append(f'S${stop:.0f}')
        if ko:
            level_parts.append(f'KO${ko:.0f}')
        if target:
            level_parts.append(f'T${target:.0f}')
        if level_parts:
            line += f' | {"/".join(level_parts)}'

        pos_lines.append(line)

    for stock in watchlist:
        sym = stock['symbol']
        if sym in owned_symbols:
            continue
        d = data.get(sym)
        if not d:
            continue

        price = d['price']
        rsi = d['rsi']
        name = stock.get('name', sym)

        rsi_flag = ''
        if rsi and rsi > 70:
            rsi_flag = '!'
            alerts.append(f'{sym} RSI {rsi:.0f} - OVERBOUGHT')
        elif rsi and rsi < 30:
            rsi_flag = '*'
            alerts.append(f'{sym} RSI {rsi:.0f} - OVERSOLD (Chance?)')

        rsi_str = f'{rsi:.0f}{rsi_flag}' if rsi else '-'
        chg = f'{d["change_pct"]:+.1f}%'
        watch_lines.append(f'  {sym} ${price:.2f} ({chg}) RSI:{rsi_str}')

    any_state = next((d.get('market_state', '') for d in data.values() if d), '')
    state_map = {'REGULAR': 'OPEN', 'PRE': 'PRE', 'POST': 'POST'}
    market_str = state_map.get(any_state, 'CLOSED')

    msg = f'<b>PORTFOLIO CHECK</b>\n'
    msg += f'{check_time} | Markt: {market_str}\n'

    if alerts:
        msg += f'\n<b>ALERTS</b>\n'
        for a in alerts:
            msg += f'  {a}\n'

    if pos_lines:
        msg += f'\n<b>POSITIONEN</b>\n'
        msg += '\n'.join(pos_lines)

    if watch_lines:
        msg += f'\n\n<b>WATCHLIST</b>\n'
        msg += '\n'.join(watch_lines)

    return msg


def send_telegram(text):
    """Send message via Telegram."""
    token = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']

    body = urllib.parse.urlencode({
        'chat_id': chat_id,
        'parse_mode': 'HTML',
        'text': text
    }).encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=body)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def main():
    now = datetime.now(timezone.utc)
    check_time = now.strftime('%d.%m.%Y %H:%M UTC')
    print(f'[{now.strftime("%H:%M:%S")} UTC] Portfolio Health Check')

    positions = get_open_positions()
    watchlist = get_watchlist_symbols()

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
