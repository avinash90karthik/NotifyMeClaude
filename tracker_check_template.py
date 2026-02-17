#!/usr/bin/env python3
"""Silver Hawk Trading - Price Tracker Template (for GitHub Actions).
Runs once, checks prices, sends alerts if needed, then exits.
State is persisted in Supabase.

SETUP:
  1. Copy this file: cp tracker_check_template.py tracker_check.py
  2. Edit SYMBOLS, ALERT_RULES, and TRADING_ZONES with YOUR stocks
  3. tracker_check.py is in .gitignore (your personal config stays private)
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_ANON_KEY']
API = f'https://api.telegram.org/bot{TOKEN}'

# ══════════════════════════════════════════════════════════════
# CUSTOMIZE BELOW: Add your tracked symbols
# ══════════════════════════════════════════════════════════════

SYMBOLS = {
    # 'AAPL': {'name': 'Apple', 'emoji': '🍎'},
    # 'NVDA': {'name': 'NVIDIA', 'emoji': '🟢'},
    # 'TSLA': {'name': 'Tesla', 'emoji': '⚡'},
    # 'GC=F': {'name': 'Gold', 'emoji': '🥇'},
}

ALERT_RULES = {
    'flash_move_pct': 1.5,      # Alert on >1.5% move in 5 minutes
    'big_daily_move_pct': 5.0,  # Alert on >5% intraday change
    # Add price levels per symbol:
    # 'AAPL': {
    #     'above': [250, 260],   # Alert when price goes ABOVE these levels
    #     'below': [220, 210],   # Alert when price goes BELOW these levels
    # },
}

# AI Trading Context - add notes for your price zones
TRADING_ZONES = {
    # 'AAPL': {
    #     'bias': 'LONG',
    #     'context': 'Your analysis notes here.',
    #     'zones': [
    #         {'type': 'BUY',  'price': 220, 'dir': 'below', 'note': 'Strong support zone.'},
    #         {'type': 'SELL', 'price': 260, 'dir': 'above', 'note': 'Take profits here.'},
    #         {'type': 'STOP', 'price': 210, 'dir': 'below', 'note': 'Stop-loss! Exit position.'},
    #     ],
    # },
}

# ══════════════════════════════════════════════════════════════
# DO NOT EDIT BELOW - Core tracker logic
# ══════════════════════════════════════════════════════════════


def supabase_request(method, path, data=None):
    """Make a request to Supabase REST API."""
    url = f'{SUPABASE_URL}/rest/v1/{path}'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=representation')
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except Exception as e:
        print(f'  Supabase error: {e}')
        return None


def load_state():
    """Load tracker state from Supabase."""
    result = supabase_request('GET', 'tracker_state?select=key,value')
    if not result:
        return {}, set(), -1
    state = {row['key']: row['value'] for row in result}
    prev_prices = state.get('prev_prices', {})
    alerted_levels = set(state.get('alerted_levels', []))
    last_summary_hour = state.get('last_summary_hour', -1)
    return prev_prices, alerted_levels, last_summary_hour


def save_state(prev_prices, alerted_levels, last_summary_hour):
    """Save tracker state to Supabase via upsert."""
    now = datetime.now(timezone.utc).isoformat()
    items = [
        {'key': 'prev_prices', 'value': prev_prices, 'updated_at': now},
        {'key': 'alerted_levels', 'value': list(alerted_levels), 'updated_at': now},
        {'key': 'last_summary_hour', 'value': last_summary_hour, 'updated_at': now},
    ]
    for item in items:
        url = f'{SUPABASE_URL}/rest/v1/tracker_state?on_conflict=key'
        req = urllib.request.Request(url, data=json.dumps(item).encode(), method='POST')
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Prefer', 'resolution=merge-duplicates')
        try:
            urllib.request.urlopen(req)
        except Exception as e:
            print(f'  State save error: {e}')


def get_prices():
    """Fetch current prices via yfinance."""
    import yfinance as yf
    result = {}
    for sym in SYMBOLS:
        try:
            t = yf.Ticker(sym)
            info = t.info
            result[sym] = {
                'price': info.get('regularMarketPrice', 0),
                'change_pct': info.get('regularMarketChangePercent', 0),
                'day_high': info.get('dayHigh', 0),
                'day_low': info.get('dayLow', 0),
                'prev_close': info.get('previousClose', 0),
                'market_state': info.get('marketState', 'UNKNOWN'),
            }
        except Exception as e:
            result[sym] = {'error': str(e)}
    return result


def send_telegram(text, silent=True):
    """Send message via Telegram."""
    data = urllib.parse.urlencode({
        'chat_id': CHAT_ID,
        'parse_mode': 'HTML',
        'text': text,
        'disable_notification': 'true' if silent else 'false',
    }).encode()
    req = urllib.request.Request(f'{API}/sendMessage', data=data)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except Exception as e:
        print(f'  Telegram error: {e}')
        return None


def get_zone_context(sym, price_level, direction):
    """Get AI trading context for a price level."""
    if sym not in TRADING_ZONES:
        return None
    for zone in TRADING_ZONES[sym]['zones']:
        if zone['price'] == price_level and zone['dir'] == direction:
            type_emoji = {'BUY': '\U0001f7e2', 'SELL': '\U0001f534', 'WATCH': '\U0001f440', 'STOP': '\u26a0\ufe0f', 'DANGER': '\U0001f525'}.get(zone['type'], '')
            return f'{type_emoji} {zone["note"]}'
    return None


def get_zone_status(sym, price):
    """Get current zone status for a symbol in hourly summary."""
    if sym not in TRADING_ZONES:
        return ''
    zones = TRADING_ZONES[sym]
    nearest = None
    nearest_dist = float('inf')
    for zone in zones['zones']:
        dist = abs(price - zone['price'])
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = zone
    if not nearest:
        return ''
    pct_away = ((nearest['price'] - price) / price) * 100
    if abs(pct_away) < 1:
        return f' <-- {nearest["type"]} Zone!'
    elif abs(pct_away) < 5:
        return f' ({abs(pct_away):.1f}% to {nearest["type"]} ${nearest["price"]})'
    return ''


def check_alerts(prices, prev_prices, alerted_levels):
    """Check all alert conditions. Returns list of alert messages."""
    alerts = []

    for sym, meta in SYMBOLS.items():
        data = prices.get(sym, {})
        if 'error' in data or not data.get('price'):
            continue

        price = data['price']
        change = data['change_pct']

        # Flash move vs previous check
        if sym in prev_prices and prev_prices[sym] > 0:
            move = ((price / prev_prices[sym]) - 1) * 100
            if abs(move) >= ALERT_RULES['flash_move_pct']:
                direction = 'SPIKE' if move > 0 else 'DROP'
                alerts.append({
                    'text': (f'<b>{direction}: {meta["emoji"]} {meta["name"]}</b>\n'
                             f'${price:.2f} ({move:+.1f}% in 5 min!)\n'
                             f'Daily change: {change:+.1f}%'),
                    'silent': False,
                })

        # Price level crossings
        if sym in ALERT_RULES:
            levels = ALERT_RULES[sym]
            for lvl in levels.get('above', []):
                key = f'{sym}_above_{lvl}'
                if price >= lvl and key not in alerted_levels:
                    alerted_levels.add(key)
                    alerted_levels.discard(f'{sym}_below_{lvl}')
                    zone_note = get_zone_context(sym, lvl, 'above')
                    text = f'<b>{meta["emoji"]} {meta["name"]} ABOVE ${lvl}!</b>\n'
                    text += f'Current: ${price:.2f} ({change:+.1f}%)'
                    if zone_note:
                        text += f'\n\n<i>{zone_note}</i>'
                    alerts.append({'text': text, 'silent': False})
            for lvl in levels.get('below', []):
                key = f'{sym}_below_{lvl}'
                if price <= lvl and key not in alerted_levels:
                    alerted_levels.add(key)
                    alerted_levels.discard(f'{sym}_above_{lvl}')
                    zone_note = get_zone_context(sym, lvl, 'below')
                    text = f'<b>{meta["emoji"]} {meta["name"]} BELOW ${lvl}!</b>\n'
                    text += f'Current: ${price:.2f} ({change:+.1f}%)'
                    if zone_note:
                        text += f'\n\n<i>{zone_note}</i>'
                    alerts.append({'text': text, 'silent': False})

        # Big daily move alert
        threshold = ALERT_RULES['big_daily_move_pct']
        for t in [threshold, threshold * 2, threshold * 3]:
            key = f'{sym}_daily_{int(t)}'
            if abs(change) >= t and key not in alerted_levels:
                alerted_levels.add(key)
                emoji = '\U0001f7e2' if change > 0 else '\U0001f534'
                alerts.append({
                    'text': (f'{emoji} <b>{meta["emoji"]} {meta["name"]}: {change:+.1f}% today!</b>\n'
                             f'Current: ${price:.2f}\n'
                             f'Range: ${data["day_low"]:.2f} - ${data["day_high"]:.2f}'),
                    'silent': False,
                })

    return alerts


def format_summary(prices, prev_prices):
    """Format a quiet hourly summary."""
    now = datetime.now(timezone.utc).strftime('%H:%M')
    lines = [f'<b>Hourly Update</b> | {now} UTC', '']

    for sym, meta in SYMBOLS.items():
        data = prices.get(sym, {})
        if 'error' in data:
            continue
        price = data['price']
        change = data['change_pct']
        arrow = '\U0001f7e2' if change > 0.5 else '\U0001f534' if change < -0.5 else '\u26aa'

        move_txt = ''
        if sym in prev_prices and prev_prices[sym] > 0:
            move = ((price / prev_prices[sym]) - 1) * 100
            if abs(move) > 0.1:
                move_txt = f' ({"+" if move > 0 else ""}{move:.1f}%/5m)'

        zone_txt = get_zone_status(sym, price)
        lines.append(f'{arrow} {meta["emoji"]} <b>{meta["name"]}</b>: ${price:.2f} ({change:+.1f}%){move_txt}{zone_txt}')

    return '\n'.join(lines)


def main():
    if not SYMBOLS:
        print('No symbols configured! Edit SYMBOLS in tracker_check.py')
        return

    now = datetime.now(timezone.utc)
    hour = now.hour
    print(f'[{now.strftime("%H:%M:%S")} UTC] Silver Hawk Check')

    prev_prices, alerted_levels, last_summary_hour = load_state()
    prices = get_prices()

    alerts = check_alerts(prices, prev_prices, alerted_levels)
    for alert in alerts:
        send_telegram(alert['text'], silent=alert['silent'])
        print(f'  ALERT SENT: {alert["text"][:60]}...')

    if hour != last_summary_hour and now.minute < 35:
        msg = format_summary(prices, prev_prices)
        send_telegram(msg, silent=True)
        last_summary_hour = hour
        print(f'  [summary sent]')

    for sym, data in prices.items():
        if 'price' in data:
            p = data['price']
            c = data['change_pct']
            print(f'  {sym}=${p:.2f}({c:+.1f}%)')
            prev_prices[sym] = p

    save_state(prev_prices, alerted_levels, last_summary_hour)
    print('  [state saved]')


if __name__ == '__main__':
    main()
