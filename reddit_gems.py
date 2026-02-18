#!/usr/bin/env python3
"""Silver Hawk Trading - Daily Reddit Gems Scanner.
Scans ApeWisdom for trending Reddit stocks, enriches with yfinance data,
filters for actionable gems, and sends a Telegram summary.
Runs daily via GitHub Actions."""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
API_TG = f'https://api.telegram.org/bot{TOKEN}'

SKIP_TICKERS = {
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI',
    'BTC', 'ETH', 'DOGE', 'SOL',
}

MIN_MARKET_CAP = 500_000_000
MIN_MENTION_CHANGE_PCT = 50
MAX_RESULTS = 50
TOP_GEMS = 8


def fetch_reddit_trending():
    """Fetch trending stocks from ApeWisdom (all stock subreddits)."""
    url = 'https://apewisdom.io/api/v1.0/filter/all-stocks/page/1'
    req = urllib.request.Request(url, headers={'User-Agent': 'SilverHawk/1.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data.get('results', [])[:MAX_RESULTS]
    except Exception as e:
        print(f'  ApeWisdom error: {e}')
        return []


def fetch_wsb_trending():
    """Fetch WSB-specific trending for extra signal."""
    url = 'https://apewisdom.io/api/v1.0/filter/wallstreetbets/page/1'
    req = urllib.request.Request(url, headers={'User-Agent': 'SilverHawk/1.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return {r['ticker']: r for r in data.get('results', [])[:30]}
    except Exception:
        return {}


def enrich_with_yfinance(tickers):
    """Fetch yfinance data for a list of tickers. Returns dict of enriched data."""
    import yfinance as yf
    enriched = {}
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            info = t.info
            price = info.get('regularMarketPrice', 0)
            if not price:
                continue
            prev_close = info.get('previousClose', price)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

            hist = t.history(period='1mo')
            rsi = None
            if len(hist) >= 14:
                delta = hist['Close'].diff()
                gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
                if loss > 0:
                    rsi = 100 - (100 / (1 + gain / loss))

            avg_vol = info.get('averageVolume', 0)
            today_vol = info.get('volume', 0)
            vol_ratio = (today_vol / avg_vol) if avg_vol > 0 else 1.0

            enriched[sym] = {
                'price': price,
                'change_pct': change_pct,
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', ''),
                'rsi': rsi,
                'vol_ratio': vol_ratio,
                'beta': info.get('beta', 1.0),
                'short_pct': info.get('shortPercentOfFloat', 0),
                'name': info.get('shortName', sym),
                'pe': info.get('trailingPE', None),
                'fwd_pe': info.get('forwardPE', None),
                '52w_high': info.get('fiftyTwoWeekHigh', 0),
                '52w_low': info.get('fiftyTwoWeekLow', 0),
            }
        except Exception as e:
            print(f'  yfinance error {sym}: {e}')
    return enriched


def score_gem(reddit_data, yf_data, wsb_data):
    """Score a potential gem (0-100). Higher = more interesting."""
    score = 0
    sym = reddit_data['ticker']

    # Mention momentum (0-25 pts)
    mentions_now = reddit_data.get('mentions', 0)
    mentions_24h = reddit_data.get('mentions_24h_ago', 1) or 1
    mention_growth = ((mentions_now - mentions_24h) / mentions_24h) * 100
    if mention_growth >= 200:
        score += 25
    elif mention_growth >= 100:
        score += 20
    elif mention_growth >= 50:
        score += 15
    elif mention_growth >= 25:
        score += 8

    # Rank improvement (0-15 pts)
    rank_now = reddit_data.get('rank', 50)
    rank_24h = reddit_data.get('rank_24h_ago', 50) or 50
    rank_jump = rank_24h - rank_now
    if rank_jump >= 20:
        score += 15
    elif rank_jump >= 10:
        score += 10
    elif rank_jump >= 5:
        score += 5

    # WSB presence bonus (0-10 pts)
    if sym in wsb_data:
        wsb_rank = wsb_data[sym].get('rank', 50)
        if wsb_rank <= 5:
            score += 10
        elif wsb_rank <= 15:
            score += 5

    # Technical signals from yfinance (0-25 pts)
    if yf_data:
        # RSI oversold = buy opportunity
        rsi = yf_data.get('rsi')
        if rsi and rsi < 30:
            score += 15
        elif rsi and rsi < 40:
            score += 8
        elif rsi and rsi > 75:
            score += 5  # Momentum play

        # Volume spike = institutional interest
        vol_ratio = yf_data.get('vol_ratio', 1.0)
        if vol_ratio >= 3.0:
            score += 10
        elif vol_ratio >= 2.0:
            score += 7
        elif vol_ratio >= 1.5:
            score += 3

    # Short squeeze potential (0-15 pts)
    if yf_data:
        short_pct = yf_data.get('short_pct', 0) or 0
        if short_pct >= 0.25:
            score += 15
        elif short_pct >= 0.15:
            score += 10
        elif short_pct >= 0.10:
            score += 5

    # Price momentum (0-10 pts)
    if yf_data:
        change = yf_data.get('change_pct', 0)
        if abs(change) >= 10:
            score += 10
        elif abs(change) >= 5:
            score += 7
        elif abs(change) >= 3:
            score += 3

    return score, mention_growth


def format_gem_line(rank, sym, reddit, yf_data, score, mention_growth, wsb_data):
    """Format a single gem line for Telegram."""
    mentions = reddit.get('mentions', 0)
    upvotes = reddit.get('upvotes', 0)

    if mention_growth >= 100:
        arrow = '🔥🔥'
    elif mention_growth >= 50:
        arrow = '🔥'
    elif mention_growth >= 0:
        arrow = '📈'
    else:
        arrow = '📉'

    line = f'{rank}. <b>{sym}</b> {arrow} Score: {score}/100\n'

    if yf_data:
        price = yf_data['price']
        change = yf_data['change_pct']
        cap = yf_data['market_cap']
        cap_str = f'${cap/1e9:.1f}B' if cap >= 1e9 else f'${cap/1e6:.0f}M'
        emoji = '🟢' if change > 0 else '🔴' if change < 0 else '⚪'

        line += f'   {emoji} ${price:.2f} ({change:+.1f}%) | {cap_str}'

        rsi = yf_data.get('rsi')
        if rsi:
            rsi_tag = ' 🔵OVS' if rsi < 35 else ' 🔴OVB' if rsi > 70 else ''
            line += f' | RSI {rsi:.0f}{rsi_tag}'

        short_pct = yf_data.get('short_pct', 0) or 0
        if short_pct >= 0.10:
            line += f' | SI {short_pct*100:.0f}%🩳'

        vol_ratio = yf_data.get('vol_ratio', 1.0)
        if vol_ratio >= 2.0:
            line += f' | Vol {vol_ratio:.1f}x📊'

        line += '\n'

    line += f'   Reddit: {mentions} mentions (+{mention_growth:.0f}%) | {upvotes} upvotes'
    if sym in wsb_data:
        line += ' | WSB✅'

    return line


def send_telegram(text, silent=True):
    """Send message via Telegram."""
    data = urllib.parse.urlencode({
        'chat_id': CHAT_ID,
        'parse_mode': 'HTML',
        'text': text,
        'disable_notification': 'true' if silent else 'false',
    }).encode()
    req = urllib.request.Request(f'{API_TG}/sendMessage', data=data)
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f'  Telegram error: {e}')


def load_portfolio_symbols():
    """Load current portfolio symbols from memory/portfolio.md to exclude from gems."""
    portfolio_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'portfolio.md')
    if not os.path.exists(portfolio_file):
        return set()
    symbols = set()
    in_table = False
    with open(portfolio_file) as f:
        for line in f:
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
            if cols:
                sym = cols[0].replace('*', '').strip()
                if sym and sym.lower() not in ('cash', 'nvda aktie'):
                    symbols.add(sym)
    return symbols


def main():
    now = datetime.now(timezone.utc)
    print(f'[{now.strftime("%H:%M:%S")} UTC] Reddit Gems Scanner')

    portfolio_syms = load_portfolio_symbols()
    skip = SKIP_TICKERS | portfolio_syms
    print(f'  Skipping: {skip}')

    print('  Fetching ApeWisdom all-stocks...')
    trending = fetch_reddit_trending()
    print(f'  Got {len(trending)} trending stocks')

    print('  Fetching WSB specifically...')
    wsb = fetch_wsb_trending()
    print(f'  Got {len(wsb)} WSB stocks')

    if not trending:
        print('  No data from ApeWisdom, aborting.')
        return

    candidates = []
    for r in trending:
        sym = r['ticker']
        if sym in skip:
            continue
        mentions = r.get('mentions', 0)
        mentions_24h = r.get('mentions_24h_ago', 1) or 1
        growth = ((mentions - mentions_24h) / mentions_24h) * 100
        if growth >= MIN_MENTION_CHANGE_PCT or r.get('rank', 99) <= 10:
            candidates.append(r)

    print(f'  {len(candidates)} candidates after filtering')
    if not candidates:
        print('  No interesting gems found today.')
        send_telegram('🦅 <b>Daily Reddit Scan</b>\n\nKeine neuen Gems gefunden. Ruhiger Tag auf Reddit.', silent=True)
        return

    tickers_to_check = [c['ticker'] for c in candidates[:20]]
    print(f'  Enriching {len(tickers_to_check)} tickers with yfinance...')
    yf_data = enrich_with_yfinance(tickers_to_check)

    scored = []
    for r in candidates:
        sym = r['ticker']
        yf = yf_data.get(sym)
        if yf and yf['market_cap'] < MIN_MARKET_CAP:
            continue
        mentions_24h = r.get('mentions_24h_ago', 1) or 1
        mention_growth = ((r['mentions'] - mentions_24h) / mentions_24h) * 100
        score, _ = score_gem(r, yf, wsb)
        scored.append((score, mention_growth, sym, r, yf))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:TOP_GEMS]

    if not top:
        send_telegram('🦅 <b>Daily Reddit Scan</b>\n\nKeine Gems ueber dem Schwellenwert.', silent=True)
        return

    date_str = now.strftime('%d.%m.%Y')
    lines = [f'🦅 <b>Daily Reddit Gems</b> | {date_str}\n']

    for i, (score, mg, sym, reddit, yf) in enumerate(top, 1):
        line = format_gem_line(i, sym, reddit, yf, score, mg, wsb)
        lines.append(line)

    lines.append(f'\n📊 Gescannt: {len(trending)} Reddit-Stocks')
    lines.append(f'🔍 Gefiltert: {len(candidates)} Kandidaten')
    lines.append(f'⭐ Top {len(top)} Gems (Score > {top[-1][0]})')
    lines.append('\n<i>Score = Mention-Wachstum + RSI + Volume + Short Interest + Momentum</i>')

    msg = '\n'.join(lines)
    send_telegram(msg, silent=False)
    print(f'  Sent {len(top)} gems to Telegram!')

    for score, mg, sym, reddit, yf in top:
        cap = f'${yf["market_cap"]/1e9:.1f}B' if yf and yf["market_cap"] >= 1e9 else 'N/A'
        print(f'  #{reddit["rank"]} {sym}: Score={score}, Mentions +{mg:.0f}%, Cap={cap}')


if __name__ == '__main__':
    main()
