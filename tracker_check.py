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
}

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
}

TRADING_ZONES = {
    'SI=F': {
        'bias': 'LONG',
        'context': 'Crash von $117 auf $78 am 30.01. Recovery auf $87. Signal LONG 58%. Entscheidungszone $87-92. Updated 05.02.2026.',
        'zones': [
            {'type': 'SELL', 'price': 92, 'dir': 'above',
             'note': 'Kurzfristiger Widerstand! Hoch vom 04.02 ($92.02). Teilgewinne mitnehmen.'},
            {'type': 'SELL', 'price': 100, 'dir': 'above',
             'note': 'Pre-Crash Konsolidierung + 62% Fib-Retracement. Psychologische Marke. Gewinne sichern.'},
            {'type': 'WATCH', 'price': 85, 'dir': 'below',
             'note': 'Unter $85 = bearish. Pivot $83 MUSS halten fuer Recovery-Case.'},
            {'type': 'BUY', 'price': 82, 'dir': 'below',
             'note': 'Kaufzone! Tagestief 04.02. Gestaffelter Einstieg. Strukturelles Angebotsdefizit stuetzt.'},
            {'type': 'BUY', 'price': 80, 'dir': 'below',
             'note': 'Starke Kaufzone. Crash-Tief $78 nah. Solarindustrie-Nachfrage als Boden.'},
            {'type': 'DANGER', 'price': 79, 'dir': 'below',
             'note': 'GEFAHR! Unter Crash-Tief $78. Zweite Abwaertswelle. Alle Positionen schliessen.'},
        ],
    },
    'AAPL': {
        'bias': 'LONG',
        'context': 'TEILVERKAUF: 100x verkauft, 165x verbleibend. KO $233.87. RSI 74 ueberkauft, kurzfristiger Pullback moeglich. Stop $265. Signal HOLD 62%. Updated 09.02.2026.',
        'zones': [
            {'type': 'SELL', 'price': 290, 'dir': 'above',
             'note': '52W-Hoch Zone ($288.62)! Weitere 50x verkaufen. Rest mit Stop $275 laufen lassen.'},
            {'type': 'SELL', 'price': 300, 'dir': 'above',
             'note': 'Psychologische Marke + Analyst Mean $293. Starker Widerstand. Komplett raus oder enger Stop.'},
            {'type': 'WATCH', 'price': 270, 'dir': 'below',
             'note': 'Breakout-Level + SMA50 ($269). Wenn bricht = kurzfristiger Uptrend gebrochen.'},
            {'type': 'STOP', 'price': 265, 'dir': 'below',
             'note': 'STOP-LOSS! Unter SMA50 mit Puffer. Alle verbleibenden 165x verkaufen!'},
            {'type': 'DANGER', 'price': 250, 'dir': 'below',
             'note': 'GEFAHR! Nur noch 7% ueber KO ($233.87). Sofort raus wenn noch nicht geschehen.'},
        ],
    },
    'APLD': {
        'bias': 'LONG',
        'context': 'POSITION OFFEN: 95x Turbo KO ~$31. Entry 0.701 EUR. Golden Cross, V-Shape Recovery $27→$37. Short Interest 33.7%! $16B Contracts. Exits: $42(30%), $48(40%), $55(Rest). Updated 11.02.2026.',
        'zones': [
            {'type': 'SELL', 'price': 42, 'dir': 'above',
             'note': 'Exit 1! Gap-Fill Zone. 30% Position verkaufen. Stop auf Entry nachziehen.'},
            {'type': 'SELL', 'price': 48, 'dir': 'above',
             'note': 'Exit 2! Short Squeeze Zone. 40% verkaufen. Cert ~3x vom Entry!'},
            {'type': 'SELL', 'price': 55, 'dir': 'above',
             'note': 'JACKPOT! ATH Retest. Rest verkaufen und feiern!'},
            {'type': 'WATCH', 'price': 35, 'dir': 'below',
             'note': 'Support-Test! V-Recovery Trendlinie. Wenn bricht = These wackelt.'},
            {'type': 'STOP', 'price': 31, 'dir': 'below',
             'note': 'KO-ZONE! Turbo wird wertlos unter ~$31. SOFORT raus wenn noch nicht passiert!'},
            {'type': 'DANGER', 'price': 28, 'dir': 'below',
             'note': 'GEFAHR! Unter Crash-Tief $27.62. Alles verloren.'},
        ],
    },
    'WDC': {
        'bias': 'HOLD_BUY_ON_DIP',
        'context': 'Post-Earnings -7.2% trotz Q2 Beat. AI-Storage Story intakt, +900% in 12Mo = Mean-Reversion-Risiko. Gestaffelter Entry bei Korrektur.',
        'zones': [
            {'type': 'BUY', 'price': 255, 'dir': 'below',
             'note': 'Erste Kaufzone! Tief-Retest vom 04.02. ($254). Position 25% aufbauen. KO moderat $215.'},
            {'type': 'BUY', 'price': 240, 'dir': 'below',
             'note': 'Starke Kaufzone! Januar-Support $240-243. Position 50% aufbauen. Stop $215.'},
            {'type': 'BUY', 'price': 230, 'dir': 'below',
             'note': 'Aggressive Kaufzone! Letzter starker Support. Position 25%. Wenn das bricht, raus.'},
            {'type': 'WATCH', 'price': 270, 'dir': 'below',
             'note': 'Unter Schlusskurs 04.02. Korrektur setzt sich fort. Abwarten auf tiefere Levels.'},
            {'type': 'SELL', 'price': 290, 'dir': 'above',
             'note': 'Previous Close Widerstand. Wenn Long: Teilgewinne sichern.'},
            {'type': 'SELL', 'price': 296, 'dir': 'above',
             'note': '52W-Hoch/ATH! Starker Widerstand. Komplett raus wenn Long.'},
            {'type': 'DANGER', 'price': 215, 'dir': 'below',
             'note': 'GEFAHR! Unter $215 = These invalidiert. Alle Positionen schliessen.'},
        ],
    },
    'GOOGL': {
        'bias': 'LONG_ON_DIP',
        'context': 'Q4 Earnings Beat (EPS +7.2%, Rev +2.2%). CapEx $180B schockt Markt. Cloud +48%. AH -7%->-2%. Entry bei Ruecksetzer auf $315-325. Signal LONG 62%. Updated 05.02.2026.',
        'zones': [
            {'type': 'BUY', 'price': 320, 'dir': 'below',
             'note': 'SMA 50 Support! Optimale Kaufzone. Turbo LONG mit KO $305. Cloud +48% + EPS Beat stuetzen.'},
            {'type': 'BUY', 'price': 310, 'dir': 'below',
             'note': 'Starke Kaufzone! Unter SMA50. Aggressiv kaufen mit KO $285 (konservativ).'},
            {'type': 'WATCH', 'price': 328, 'dir': 'below',
             'note': 'Unter Earnings-Day-Tief. Korrektur beschleunigt sich. Naechster Halt SMA50 $320.'},
            {'type': 'SELL', 'price': 339, 'dir': 'above',
             'note': 'Previous Close zurueckerobert! Wenn Long: Teilgewinne. Widerstand beachten.'},
            {'type': 'SELL', 'price': 349, 'dir': 'above',
             'note': 'ATH/52W-Hoch! Starker Widerstand. Double-Top-Gefahr. Gewinne sichern.'},
            {'type': 'DANGER', 'price': 300, 'dir': 'below',
             'note': 'GEFAHR! Psychologische Marke + Dezember-Gap. Unter $300 = Antitrust-Panik moeglich.'},
        ],
    },
    'RKLB': {
        'bias': 'HOLD',
        'context': 'Neutron-Rakete + Space Systems wachsen stark. Post-Earnings Korrektur (-7.9%) nach ATH $99.58. Signal HOLD 58%. SHORT-Bias bei Bruch unter $65. Updated 05.02.2026.',
        'zones': [
            {'type': 'BUY', 'price': 65, 'dir': 'below',
             'note': 'Erste Kaufzone! SMA 50 nahe $69.61. Gestaffelter Einstieg. Space-Story langfristig intakt.'},
            {'type': 'BUY', 'price': 55, 'dir': 'below',
             'note': 'Starke Kaufzone! Januar-Support. Position aufbauen. KO $48 fuer Turbo.'},
            {'type': 'BUY', 'price': 48, 'dir': 'below',
             'note': 'Aggressive Kaufzone! Dezember-Tief. Letzter starker Support vor Gap.'},
            {'type': 'WATCH', 'price': 73, 'dir': 'below',
             'note': 'Unter Previous Close $73.11. Korrektur setzt sich fort. Abwarten.'},
            {'type': 'SELL', 'price': 75, 'dir': 'above',
             'note': 'Kurzfristiger Widerstand! Wenn Long: Teilgewinne sichern.'},
            {'type': 'SELL', 'price': 88, 'dir': 'above',
             'note': 'Starker Widerstand! Januar-Hoch. 50% Position schliessen.'},
            {'type': 'SELL', 'price': 99.58, 'dir': 'above',
             'note': 'ATH/52W-Hoch! Maximaler Widerstand. Komplett raus oder enger Stop.'},
            {'type': 'DANGER', 'price': 48, 'dir': 'below',
             'note': 'GEFAHR! Unter Dezember-Support. Grosse Korrektur moeglich. Positionen schliessen.'},
        ],
    },
    'VST': {
        'bias': 'LONG',
        'context': 'NEUE POSITION geplant: Turbo LONG 200-300 EUR, KO ~$115. RSI 33.7, FwdPE 16x. Meta 20J-Nuklear-PPA. Q4 Earnings 26.02. Stop $138. Analyst Target $230. Signal LONG 58%. Updated 09.02.2026.',
        'zones': [
            {'type': 'BUY', 'price': 138, 'dir': 'below',
             'note': 'Heutiges Tief! Erste Position 25%. RSI extrem ueberverkauft bei 17.6.'},
            {'type': 'BUY', 'price': 125, 'dir': 'below',
             'note': 'Starke Kaufzone! Position 50% aufbauen. KO moderat $110.'},
            {'type': 'BUY', 'price': 110, 'dir': 'below',
             'note': 'Aggressive Kaufzone! Oktober-2024 Konsolidierung. Letzter Support.'},
            {'type': 'WATCH', 'price': 150, 'dir': 'above',
             'note': 'Erster Widerstand. Bodenbildung bestaetigt wenn darueber schliesst.'},
            {'type': 'SELL', 'price': 165, 'dir': 'above',
             'note': 'SMA 50! Teilgewinne sichern. Starker Widerstand.'},
            {'type': 'SELL', 'price': 179, 'dir': 'above',
             'note': 'SMA 200! Hauptwiderstand. 50% Position schliessen.'},
            {'type': 'SELL', 'price': 195, 'dir': 'above',
             'note': '50% Fib-Retracement vom ATH. Zielzone Bull-Case.'},
            {'type': 'DANGER', 'price': 95, 'dir': 'below',
             'note': 'GEFAHR! Nahe 52W-Tief $90.51. These invalidiert. Alles raus.'},
        ],
    },
    'GC=F': {
        'bias': 'LONG',
        'context': 'Sakularer Bull-Markt. Crash 30.01 durch Warsh-Nominierung (-12.3%). Golden Cross intakt. RSI bereinigt auf 56. JPM Target $6,300. Signal LONG 72%. Updated 05.02.2026.',
        'zones': [
            {'type': 'BUY', 'price': 4505, 'dir': 'below',
             'note': 'SMA 50 Test! Optimale Kaufzone. Trend intakt solange SMA50 haelt.'},
            {'type': 'BUY', 'price': 4400, 'dir': 'below',
             'note': 'Crash-Tief Retest (02.02). Aggressiv kaufen. KO $3,800.'},
            {'type': 'BUY', 'price': 4100, 'dir': 'below',
             'note': 'Dezember-Support. Letzter starker Support vor 200-SMA.'},
            {'type': 'WATCH', 'price': 5000, 'dir': 'above',
             'note': 'Psychologische Marke. Erster Widerstand nach Recovery.'},
            {'type': 'SELL', 'price': 5376, 'dir': 'above',
             'note': 'Pre-Crash-High zurueck! Teilgewinne sichern.'},
            {'type': 'SELL', 'price': 5586, 'dir': 'above',
             'note': 'ATH! Starker Widerstand. Gewinne sichern.'},
            {'type': 'SELL', 'price': 6000, 'dir': 'above',
             'note': 'JPM/DB Targetzone. Feiern und Gewinne mitnehmen!'},
            {'type': 'DANGER', 'price': 3800, 'dir': 'below',
             'note': 'GEFAHR! Unter 200-SMA. Bull-Markt gebrochen. Alles raus.'},
        ],
    },
    'IREN': {
        'bias': 'HOLD',
        'context': 'Microsoft $9.7B Deal. GPU-Skalierung 23k->140k. Aber -$957M FCF, 16.2% Short Float. Heute -12.3% am Earnings-Tag. Signal HOLD 52%. Nur spekulativ. Updated 05.02.2026.',
        'zones': [
            {'type': 'BUY', 'price': 35, 'dir': 'below',
             'note': 'Erste Kaufzone! Nahe SMA 200 ($32). Kleine spekulative Position max 50 EUR.'},
            {'type': 'BUY', 'price': 32, 'dir': 'below',
             'note': 'SMA 200 Test! Wenn haelt = starkes Signal. Position aufbauen.'},
            {'type': 'BUY', 'price': 25, 'dir': 'below',
             'note': 'September-Konsolidierung. Aggressive Kaufzone. KO $18.'},
            {'type': 'WATCH', 'price': 47, 'dir': 'above',
             'note': 'SMA 50 zurueckerobert! Trendwende-Signal. Erst dann groessere Position.'},
            {'type': 'SELL', 'price': 55, 'dir': 'above',
             'note': 'November-Widerstand. Teilgewinne sichern bei +40% vom Tief.'},
            {'type': 'SELL', 'price': 65, 'dir': 'above',
             'note': 'Dezember-Hoch. 50% Position schliessen.'},
            {'type': 'SELL', 'price': 76.87, 'dir': 'above',
             'note': 'ATH! Komplett raus oder enger Stop. Short Squeeze moeglich.'},
            {'type': 'DANGER', 'price': 18, 'dir': 'below',
             'note': 'GEFAHR! Unter August-Support. These komplett invalidiert.'},
        ],
    },
    'ARM': {
        'bias': 'LONG',
        'context': 'POSITION OFFEN: 64x Turbo KO $94.43. +53% P&L. MACD bullish +2.00, Short 12.6% = Squeeze! REVIDIERTER Sell-Plan: Momentum laufen lassen, KEIN Sell bei $125. Stop HOCH auf $115. Signal LONG 60%. Updated 09.02.2026.',
        'zones': [
            {'type': 'WATCH', 'price': 130, 'dir': 'above',
             'note': 'Verdoppler-Zone! Cert 3.14 = +100%. 10% verkaufen. Short Squeeze koennte hier zuenden!'},
            {'type': 'SELL', 'price': 138, 'dir': 'above',
             'note': 'SMA 200! Hauptwiderstand. 25% Position schliessen. Cert 3.85 = +147%.'},
            {'type': 'SELL', 'price': 150, 'dir': 'above',
             'note': 'Analyst Mean Target $149. 50% Position schliessen. Cert 4.82 = +210%!'},
            {'type': 'SELL', 'price': 161, 'dir': 'above',
             'note': 'Juli-2025-Hoch. Rest raus und feiern!'},
            {'type': 'STOP', 'price': 115, 'dir': 'below',
             'note': 'NEUER STOP! Breakeven gesichert. Unter SMA50 = Momentum gebrochen. RAUS!'},
            {'type': 'DANGER', 'price': 108, 'dir': 'below',
             'note': 'GEFAHR! Weit unter Earnings-Gap. Turbo schliessen wenn noch nicht bei $115 raus!'},
            {'type': 'DANGER', 'price': 94.43, 'dir': 'below',
             'note': 'KO-LEVEL! Turbo wertlos bei $94.43. MUSS vorher raus sein!'},
        ],
    },
    'NVDA': {
        'bias': 'LONG',
        'context': 'NEUE POSITION GEPLANT: 300 EUR Turbo KO $160 (~6x). Golden Cross, ueber SMAs. Earnings 25.02! $660 Mrd AI-Capex. Analyst Target $254 Mean. Stop $178. Signal LONG 68%. Updated 09.02.2026.',
        'zones': [
            {'type': 'WATCH', 'price': 195, 'dir': 'above',
             'note': 'Erste Resistance! Range-Oberseite $180-195. Durchbruch = Weg frei zu $200.'},
            {'type': 'SELL', 'price': 200, 'dir': 'above',
             'note': 'Psychologische Marke! Teilgewinne 25% sichern. Stop auf $190 nachziehen.'},
            {'type': 'SELL', 'price': 212, 'dir': 'above',
             'note': '52W-Hoch! Starker Widerstand. 25% verkaufen. Stop auf $200.'},
            {'type': 'SELL', 'price': 230, 'dir': 'above',
             'note': 'Zwischen-Target! 25% verkaufen. Rest laufen lassen bis $254.'},
            {'type': 'SELL', 'price': 254, 'dir': 'above',
             'note': 'Analyst Mean Target! JACKPOT! Alles raus oder enger Stop $240.'},
            {'type': 'WATCH', 'price': 183, 'dir': 'below',
             'note': 'SMA 50 Test! Wenn haelt = Kaufgelegenheit nachkaufen. Wenn bricht = Vorsicht.'},
            {'type': 'STOP', 'price': 178, 'dir': 'below',
             'note': 'STOP-LOSS! Unter SMA50 mit Puffer. Turbo verkaufen! Max -30% Verlust.'},
            {'type': 'WATCH', 'price': 169, 'dir': 'below',
             'note': 'SMA 200 Test! Letzter Support vor KO-Gefahr.'},
            {'type': 'DANGER', 'price': 160, 'dir': 'below',
             'note': 'KO-LEVEL! Turbo wertlos bei $160. MUSS bei $178 schon raus sein!'},
        ],
    },
    'ENR.DE': {
        'bias': 'SHORT',
        'context': 'P/E 91x bei 3.6% Margin = Blase. 42.5% ueber SMA200. Analyst Mean EUR 143 UNTER Kurs. Double Top EUR 156. Gamesa Milliardenverluste. Signal SHORT 60%. Updated 05.02.2026.',
        'zones': [
            {'type': 'SELL', 'price': 150, 'dir': 'above',
             'note': 'SHORT Entry! Widerstand. Position eroeffnen mit KO EUR 175.'},
            {'type': 'SELL', 'price': 156.70, 'dir': 'above',
             'note': 'ATH Retest! Maximaler SHORT Entry. Wenn durchbricht = Stop.'},
            {'type': 'DANGER', 'price': 165, 'dir': 'above',
             'note': 'GEFAHR! Neues ATH. SHORT-These geschwächt. Position reduzieren.'},
            {'type': 'DANGER', 'price': 175, 'dir': 'above',
             'note': 'KRITISCH! Weit ueber ATH. SHORT sofort schliessen.'},
            {'type': 'BUY', 'price': 138, 'dir': 'below',
             'note': 'SHORT Teilgewinne! -5% vom ATH. 25% Position schliessen.'},
            {'type': 'BUY', 'price': 126, 'dir': 'below',
             'note': 'SHORT Ziel 1: SMA 50. 50% Position schliessen.'},
            {'type': 'BUY', 'price': 115, 'dir': 'below',
             'note': 'SHORT Ziel 2: November-Support. 75% schliessen.'},
            {'type': 'BUY', 'price': 102, 'dir': 'below',
             'note': 'SHORT Jackpot! SMA 200. Komplett raus und feiern.'},
        ],
    },
}


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
