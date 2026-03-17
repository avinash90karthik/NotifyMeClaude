#!/usr/bin/env python3
"""Silver Hawk Trading - Single Check (for GitHub Actions).
Runs once, checks prices, sends alerts if needed, then exits.
State is persisted in memory/tracker_state.json (committed back by GitHub Actions)."""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
API = f'https://api.telegram.org/bot{TOKEN}'

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'tracker_state.json')

SYMBOLS = {
    'SI=F': {'name': 'Silber', 'emoji': '🥈'},
    'AAPL': {'name': 'Apple', 'emoji': '🍎'},
    'APLD': {'name': 'Applied Digital', 'emoji': '⚡'},
    'WDC':  {'name': 'Western Digital', 'emoji': '💾'},
    'GOOGL': {'name': 'Alphabet', 'emoji': '🔍'},
    'RKLB': {'name': 'Rocket Lab', 'emoji': '🚀'},
    'VST':  {'name': 'Vistra Energy', 'emoji': '🔋'},
    'GC=F': {'name': 'Gold', 'emoji': '🥇'},
    'IREN': {'name': 'IREN', 'emoji': '🔥'},
    'ARM':  {'name': 'ARM Holdings', 'emoji': '🧠'},
    'NVDA': {'name': 'NVIDIA', 'emoji': '🤖'},
    'ENR.DE': {'name': 'Siemens Energy', 'emoji': '🏭'},
    'WIX':  {'name': 'Wix.com', 'emoji': '🌐'},
}

# Last updated: 2026-02 — levels may be stale, review before re-enabling tracker
ALERT_RULES = {
    'flash_move_pct': 1.5,
    'big_daily_move_pct': 5.0,
    'SI=F': {
        'above': [92, 95, 100],
        'below': [85, 82, 80, 79],
    },
    'APLD': {
        'above': [42, 48, 55],
        'below': [35, 31, 28],
    },
    'AAPL': {
        'above': [290, 300],
        'below': [270, 265, 250],
    },
    'WDC': {
        'above': [290, 296, 310],
        'below': [270, 255, 240, 230, 215],
    },
    'GOOGL': {
        'above': [339, 345, 349, 360],
        'below': [328, 320, 310, 300],
    },
    'RKLB': {
        'above': [75, 88, 99.58, 105],
        'below': [65, 55, 48],
    },
    'VST': {
        'above': [150, 165, 179, 195],
        'below': [138, 125, 110, 95],
    },
    'GC=F': {
        'above': [5000, 5376, 5586, 6000],
        'below': [4505, 4400, 4100, 3800],
    },
    'IREN': {
        'above': [47, 55, 65, 76.87],
        'below': [35, 32, 25, 18],
    },
    'ARM': {
        'above': [130, 138, 150, 161],
        'below': [115, 108, 94.43],
    },
    'NVDA': {
        'above': [195, 200, 212, 230, 254],
        'below': [183, 178, 169, 160],
    },
    'ENR.DE': {
        'above': [150, 156.70, 165, 175],
        'below': [138, 126, 115, 102],
    },
    'WIX': {
        'above': [100, 110, 127],
        'below': [87, 85, 83, 75],
    },
}

# TODO: Update when tracker re-enabled
TRADING_ZONES = {}


def load_state():
    """Load tracker state from local JSON file."""
    if not os.path.exists(STATE_FILE):
        print('  [state: no file found, starting fresh]')
        return {}, set(), -1
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        prev_prices = state.get('prev_prices', {})
        alerted_raw = state.get('alerted_levels', [])
        now = datetime.now(timezone.utc)
        if now.hour == 14 and now.minute < 15:
            alerted_raw = [k for k in alerted_raw if '_daily_' not in k]
            print('  [state: daily alerts reset for new trading day]')
        alerted_levels = set(alerted_raw)
        last_summary_hour = state.get('last_summary_hour', -1)
        print(f'  [state loaded: {len(prev_prices)} prices, {len(alerted_levels)} alerts]')
        return prev_prices, alerted_levels, last_summary_hour
    except Exception as e:
        print(f'  State load error: {e}, starting fresh')
        return {}, set(), -1


def save_state(prev_prices, alerted_levels, last_summary_hour):
    """Save tracker state to local JSON file."""
    state = {
        'prev_prices': prev_prices,
        'alerted_levels': list(alerted_levels),
        'last_summary_hour': last_summary_hour,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
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


ZONE_TYPE_EMOJI = {'BUY': '🟢', 'SELL': '🔴', 'WATCH': '👀', 'STOP': '⚠️', 'DANGER': '🔥'}


def get_zone_context(sym, price_level, direction):
    """Get AI trading context for a price level."""
    if sym not in TRADING_ZONES:
        return None
    for zone in TRADING_ZONES[sym]['zones']:
        if zone['price'] == price_level and zone['dir'] == direction:
            emoji = ZONE_TYPE_EMOJI.get(zone['type'], '')
            return f'{emoji} {zone["note"]}'
    return None



def check_alerts(prices, prev_prices, alerted_levels):
    """Check all alert conditions. Returns list of alert messages.
    Groups multiple level crossings per symbol into one message.
    Skips stale prices (unchanged from last check = market closed)."""
    alerts = []

    for sym, meta in SYMBOLS.items():
        data = prices.get(sym, {})
        if 'error' in data or not data.get('price'):
            continue

        price = data['price']
        change = data['change_pct']

        # Skip stale prices - if price identical to last check, market is closed
        prev = prev_prices.get(sym, 0)
        price_is_stale = (prev > 0 and abs(price - prev) < 0.001)

        # Flash move (vs previous check) - only on fresh prices
        if not price_is_stale and prev > 0:
            move = ((price / prev) - 1) * 100
            if abs(move) >= ALERT_RULES['flash_move_pct']:
                direction = '📈 SPIKE' if move > 0 else '📉 DROP'
                alerts.append({
                    'text': (f'⚡ <b>{direction}: {meta["emoji"]} {meta["name"]}</b>\n'
                             f'${price:.2f} ({move:+.1f}% in ~10 Min!)\n'
                             f'Tageschange: {change:+.1f}%'),
                    'silent': False,
                })

        # Price level crossings - grouped per symbol
        level_lines = []
        if sym in ALERT_RULES and not price_is_stale:
            levels = ALERT_RULES[sym]
            for lvl in levels.get('above', []):
                key = f'{sym}_above_{lvl}'
                if price >= lvl and key not in alerted_levels:
                    alerted_levels.add(key)
                    alerted_levels.discard(f'{sym}_below_{lvl}')
                    zone_note = get_zone_context(sym, lvl, 'above')
                    line = f'  ÜBER ${lvl}'
                    if zone_note:
                        line += f' - {zone_note}'
                    level_lines.append(line)
            for lvl in levels.get('below', []):
                key = f'{sym}_below_{lvl}'
                if price <= lvl and key not in alerted_levels:
                    alerted_levels.add(key)
                    alerted_levels.discard(f'{sym}_above_{lvl}')
                    zone_note = get_zone_context(sym, lvl, 'below')
                    line = f'  UNTER ${lvl}'
                    if zone_note:
                        line += f' - {zone_note}'
                    level_lines.append(line)

        # Send ONE combined message per symbol for level crossings
        if level_lines:
            n = len(level_lines)
            label = 'Level gekreuzt' if n == 1 else f'{n} Levels gekreuzt'
            text = f'🚨 <b>{meta["emoji"]} {meta["name"]} - {label}!</b>\n'
            text += f'Aktuell: ${price:.2f} ({change:+.1f}%)\n\n'
            text += '\n'.join(level_lines)
            alerts.append({'text': text, 'silent': False})

        # Big daily move - only alert once per threshold per day
        if not price_is_stale:
            threshold = ALERT_RULES['big_daily_move_pct']
            for t in [threshold, threshold * 2, threshold * 3]:
                key = f'{sym}_daily_{int(t)}'
                if abs(change) >= t and key not in alerted_levels:
                    alerted_levels.add(key)
                    emoji = '🟢' if change > 0 else '🔴'
                    alerts.append({
                        'text': (f'{emoji} <b>{meta["emoji"]} {meta["name"]}: {change:+.1f}% heute!</b>\n'
                                 f'Aktuell: ${price:.2f}\n'
                                 f'Range: ${data["day_low"]:.2f} - ${data["day_high"]:.2f}'),
                        'silent': False,
                    })

    return alerts



def main():
    now = datetime.now(timezone.utc)
    print(f'[{now.strftime("%H:%M:%S")} UTC] Silver Hawk Check')

    prev_prices, alerted_levels, last_summary_hour = load_state()
    prices = get_prices()

    alerts = check_alerts(prices, prev_prices, alerted_levels)
    for alert in alerts:
        send_telegram(alert['text'], silent=alert['silent'])
        print(f'  ALERT SENT: {alert["text"][:60]}...')

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
