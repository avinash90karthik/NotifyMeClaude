#!/usr/bin/env python3
"""Silver Hawk Trading - Reflection/Learning Loop.
Parses closed trades and analyses from portfolio.md, calculates win rates,
pattern analysis, risk/reward, and generates memory/reflections.md.

Usage:
    python reflect.py                # Generate reflections.md
    python reflect.py --telegram     # Also send summary via Telegram
"""

import argparse
import os
import re
from datetime import datetime, timezone

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'portfolio.md')
REFLECTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'reflections.md')


def parse_closed_trades(content):
    """Parse closed trades tables from portfolio.md.

    Handles both März format (4 cols: Symbol, Kauf, Verkauf, P&L, Notiz)
    and Februar format (3 cols: Symbol, P&L, Notiz)."""
    trades = []

    # März trades (5 columns: Symbol | Kauf | Verkauf | P&L EUR | Notiz)
    maerz_match = re.search(
        r'## Geschlossene Trades \(März\)\s*\n\s*\|.*\|\s*\n\s*\|[-| ]+\|\s*\n((?:\|.*\|\s*\n)*)',
        content
    )
    if maerz_match:
        for line in maerz_match.group(1).strip().splitlines():
            cols = [c.strip() for c in line.split('|') if c.strip()]
            if len(cols) < 4:
                continue
            symbol_raw = cols[0]
            notiz = cols[-1] if len(cols) >= 5 else ''
            pnl_raw = cols[3] if len(cols) >= 5 else cols[2]

            trade = _parse_trade_line(symbol_raw, pnl_raw, notiz, 'März')
            if trade:
                trades.append(trade)

    # Februar trades (3 columns: Symbol | P&L EUR | Notiz)
    feb_match = re.search(
        r'Geschlossene Trades \(Februar\).*?\|.*?\|\s*\n\s*\|[-| ]+\|\s*\n((?:\|.*\|\s*\n)*)',
        content, re.DOTALL
    )
    if feb_match:
        for line in feb_match.group(1).strip().splitlines():
            cols = [c.strip() for c in line.split('|') if c.strip()]
            if len(cols) < 2:
                continue
            symbol_raw = cols[0]
            pnl_raw = cols[1]
            notiz = cols[2] if len(cols) >= 3 else ''

            trade = _parse_trade_line(symbol_raw, pnl_raw, notiz, 'Februar')
            if trade:
                trades.append(trade)

    return trades


def _parse_trade_line(symbol_raw, pnl_raw, notiz, month):
    """Parse a single trade line into a structured dict."""
    # Clean symbol
    symbol = re.sub(r'\*+', '', symbol_raw).strip()
    if not symbol or symbol.startswith('GESAMT') or symbol.startswith('Zinsen'):
        return None

    # Extract base symbol (e.g. "ENR.DE" from "ENR.DE LONG KO 138,40 (50%)")
    base_match = re.match(r'([A-Za-z0-9=.\-^]+)', symbol)
    base_symbol = base_match.group(1) if base_match else symbol

    # Determine direction
    direction = 'UNKNOWN'
    sym_upper = symbol.upper()
    if 'SHORT' in sym_upper:
        direction = 'SHORT'
    elif 'LONG' in sym_upper or 'Aktie' in symbol:
        direction = 'LONG'

    # Parse P&L
    pnl_eur = _parse_pnl(pnl_raw)

    # Detect patterns from notiz
    patterns = _detect_patterns(notiz, pnl_eur)

    return {
        'symbol': base_symbol,
        'full_name': symbol,
        'direction': direction,
        'pnl_eur': pnl_eur,
        'notiz': notiz,
        'patterns': patterns,
        'month': month,
    }


def _parse_pnl(pnl_raw):
    """Extract numeric P&L from string like '+16,62' or '~-184,58'."""
    cleaned = re.sub(r'[*~€EUR ]', '', pnl_raw).replace(',', '.').strip()
    # Handle cases like "+16.62" or "-184.58"
    match = re.search(r'([+-]?\d+\.?\d*)', cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return 0.0


def _detect_patterns(notiz, pnl_eur):
    """Detect trading patterns from trade notes."""
    patterns = []
    notiz_lower = notiz.lower()

    if 'stop' in notiz_lower and ('ausgelöst' in notiz_lower or 'triggered' in notiz_lower):
        patterns.append('STOP_TRIGGERED')
    if 'break-even' in notiz_lower or 'be-stop' in notiz_lower or 'be ' in notiz_lower:
        patterns.append('BREAK_EVEN')
    if '50%' in notiz and ('+20%' in notiz or '+29%' in notiz or 'v3' in notiz_lower):
        patterns.append('V3_PARTIAL_EXIT')
    if 'runner' in notiz_lower:
        patterns.append('RUNNER')
    if 'ohne analyse' in notiz_lower or 'eigenmächtig' in notiz_lower or 'ohne neue analyse' in notiz_lower:
        patterns.append('DISCIPLINE_VIOLATION')
    if 'unter 60%' in notiz_lower or '<60%' in notiz_lower or '55%' in notiz_lower:
        patterns.append('BELOW_GATE')
    if 'gier' in notiz_lower:
        patterns.append('DISCIPLINE_VIOLATION')
    if 'falsch' in notiz_lower:
        patterns.append('EXECUTION_ERROR')

    return patterns


def calc_duration_stats(trades, analyses=None):
    """Calculate trade duration statistics from date info in trade notes.
    Uses robust patterns matching real portfolio.md notation.
    Falls back to analysis dates for entry when not found in notes.
    Returns dict with avg/median durations or None if insufficient data."""

    # Build analysis date lookup: symbol → earliest analysis date (DD.MM)
    analysis_dates = {}
    if analyses:
        for a in analyses:
            sym = a.get('symbol', '')
            datum = a.get('datum', '')
            date_match = re.search(r'(\d{1,2})\.(\d{1,2})', datum)
            if date_match and sym and sym not in analysis_dates:
                analysis_dates[sym] = (int(date_match.group(1)), int(date_match.group(2)))

    # Robust exit patterns matching real portfolio.md notation
    EXIT_PATTERNS = [
        r'[Vv]erkauft?\s+(\d{1,2})\.(\d{1,2})',            # "Verkauft 06.03", "verkauft 05.03"
        r'[Gg]eschlossen\s+(\d{1,2})\.(\d{1,2})',           # "Geschlossen 12.03"
        r'ausgelöst\s+(\d{1,2})\.(\d{1,2})',                 # "ausgelöst 10.03", "ausgelöst 11.03"
        r'ausgeloest\s+(\d{1,2})\.(\d{1,2})',                # ASCII variant
        r'Stop-Sell\s+(\d{1,2})\.(\d{1,2})',                 # "Stop-Sell 02.03"
        r'(\d{1,2})\.(\d{1,2})\s+(?:bei|Fr|abends|Break)',  # "06.03 Fr Abend", "05.03 abends"
    ]

    ENTRY_PATTERNS = [
        r'[Kk]auf\s+(\d{1,2})\.(\d{1,2})',                  # "Kauf 02.03"
        r'[Ee]instieg\s+(\d{1,2})\.(\d{1,2})',              # "Einstieg 05.03"
        r'[Gg]ekauft\s+(\d{1,2})\.(\d{1,2})',               # "Gekauft 18.02"
        r'[Ee]ntry\s+(\d{1,2})\.(\d{1,2})',                 # "Entry 02.03"
    ]

    durations_win = []
    durations_loss = []

    for t in trades:
        notiz = t.get('notiz', '')
        full = t.get('full_name', '') + ' ' + notiz

        # Find exit date (first matching pattern wins)
        exit_day, exit_month = None, None
        for pat in EXIT_PATTERNS:
            m = re.search(pat, full)
            if m:
                exit_day, exit_month = int(m.group(1)), int(m.group(2))
                break

        if exit_day is None:
            continue

        # Find entry date: try notiz patterns first, then analysis table
        entry_day, entry_month = None, None
        for pat in ENTRY_PATTERNS:
            m = re.search(pat, full)
            if m:
                entry_day, entry_month = int(m.group(1)), int(m.group(2))
                break

        # Fallback: use analysis date for this symbol
        if entry_day is None and t['symbol'] in analysis_dates:
            entry_day, entry_month = analysis_dates[t['symbol']]

        if entry_day is None:
            continue

        try:
            year = 2026
            entry_date = datetime(year, entry_month, entry_day)
            exit_year = year
            if exit_month < entry_month:
                exit_year = year + 1
            exit_date = datetime(exit_year, exit_month, exit_day)

            days = (exit_date - entry_date).days
            if days < 0 or days > 365:
                continue

            if t['pnl_eur'] > 0:
                durations_win.append(days)
            elif t['pnl_eur'] < 0:
                durations_loss.append(days)
        except (ValueError, OverflowError):
            continue

    all_durations = durations_win + durations_loss
    if not all_durations:
        return None

    all_durations.sort()
    median = all_durations[len(all_durations) // 2]

    return {
        'avg_days': round(sum(all_durations) / len(all_durations), 1),
        'median_days': median,
        'avg_days_winners': round(sum(durations_win) / len(durations_win), 1) if durations_win else None,
        'avg_days_losers': round(sum(durations_loss) / len(durations_loss), 1) if durations_loss else None,
        'n_parsed': len(all_durations),
    }


def parse_analyses(content):
    """Parse completed analyses for confidence data."""
    analyses = []

    # Match analysis tables (März + Februar)
    for table_match in re.finditer(
        r'Abgeschlossene Analysen.*?\|.*?\|\s*\n\s*\|[-| ]+\|\s*\n((?:\|.*\|\s*\n)*)',
        content, re.DOTALL
    ):
        for line in table_match.group(1).strip().splitlines():
            cols = [c.strip() for c in line.split('|') if c.strip()]
            if len(cols) < 4:
                continue
            datum = cols[0]
            symbol = cols[1]
            signal = cols[2]
            konfidenz_raw = cols[3]

            # Parse confidence
            conf_match = re.search(r'(\d+)%', konfidenz_raw)
            confidence = int(conf_match.group(1)) if conf_match else None

            # Determine direction from signal
            direction = 'UNKNOWN'
            sig_upper = signal.upper()
            if 'SHORT' in sig_upper:
                direction = 'SHORT'
            elif 'LONG' in sig_upper:
                direction = 'LONG'
            elif 'WARTEN' in sig_upper or 'HOLD' in sig_upper:
                direction = 'HOLD'

            analyses.append({
                'datum': datum,
                'symbol': symbol,
                'signal': signal,
                'direction': direction,
                'confidence': confidence,
            })

    return analyses


def analyze_trades(trades, analyses):
    """Compute trading statistics from closed trades and analyses."""
    if not trades:
        return {}

    # Basic stats
    wins = [t for t in trades if t['pnl_eur'] > 0]
    losses = [t for t in trades if t['pnl_eur'] < 0]
    breakevens = [t for t in trades if t['pnl_eur'] == 0]

    total = len(trades)
    win_rate = round(len(wins) / total * 100, 1) if total > 0 else 0

    # Win rate by direction
    dir_stats = {}
    for direction in ('LONG', 'SHORT'):
        dir_trades = [t for t in trades if t['direction'] == direction]
        if dir_trades:
            dir_wins = [t for t in dir_trades if t['pnl_eur'] > 0]
            dir_stats[direction] = {
                'total': len(dir_trades),
                'wins': len(dir_wins),
                'win_rate': round(len(dir_wins) / len(dir_trades) * 100, 1),
                'total_pnl': round(sum(t['pnl_eur'] for t in dir_trades), 2),
                'avg_pnl': round(sum(t['pnl_eur'] for t in dir_trades) / len(dir_trades), 2),
            }

    # Win rate by confidence bracket
    conf_stats = {}
    if analyses:
        # Map analyses to trades by symbol
        analysis_conf = {}
        for a in analyses:
            if a['confidence'] is not None:
                analysis_conf[a['symbol']] = a['confidence']

        for bracket_name, low, high in [('50-59', 50, 59), ('60-69', 60, 69), ('70-79', 70, 79), ('80+', 80, 100)]:
            bracket_trades = []
            for t in trades:
                conf = analysis_conf.get(t['symbol'])
                if conf is not None and low <= conf <= high:
                    bracket_trades.append(t)
            if bracket_trades:
                bracket_wins = [t for t in bracket_trades if t['pnl_eur'] > 0]
                conf_stats[bracket_name] = {
                    'total': len(bracket_trades),
                    'wins': len(bracket_wins),
                    'win_rate': round(len(bracket_wins) / len(bracket_trades) * 100, 1),
                    'avg_pnl': round(sum(t['pnl_eur'] for t in bracket_trades) / len(bracket_trades), 2),
                }

    # Pattern analysis
    pattern_stats = {}
    for t in trades:
        for p in t['patterns']:
            if p not in pattern_stats:
                pattern_stats[p] = {'count': 0, 'total_pnl': 0}
            pattern_stats[p]['count'] += 1
            pattern_stats[p]['total_pnl'] = round(pattern_stats[p]['total_pnl'] + t['pnl_eur'], 2)

    # Risk/Reward
    avg_win = round(sum(t['pnl_eur'] for t in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(t['pnl_eur'] for t in losses) / len(losses), 2) if losses else 0
    rr_ratio = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else float('inf')

    # v3 Compliance
    v3_exits = len([t for t in trades if 'V3_PARTIAL_EXIT' in t['patterns']])
    discipline_violations = len([t for t in trades if 'DISCIPLINE_VIOLATION' in t['patterns']])
    below_gate = len([t for t in trades if 'BELOW_GATE' in t['patterns']])

    duration = calc_duration_stats(trades, analyses)

    return {
        'total_trades': total,
        'wins': len(wins),
        'losses': len(losses),
        'breakevens': len(breakevens),
        'win_rate': win_rate,
        'total_pnl': round(sum(t['pnl_eur'] for t in trades), 2),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'rr_ratio': rr_ratio,
        'direction_stats': dir_stats,
        'confidence_stats': conf_stats,
        'pattern_stats': pattern_stats,
        'v3_partial_exits': v3_exits,
        'discipline_violations': discipline_violations,
        'below_gate_trades': below_gate,
        'duration': duration,
    }


def generate_reflections_md(stats, trades):
    """Generate memory/reflections.md with trading statistics."""
    now = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')

    lines = [
        '# Silver Hawk Trading - Reflections',
        '',
        f'**Generiert:** {now}',
        f'**Quelle:** memory/portfolio.md',
        '',
        '---',
        '',
        '## Performance-Übersicht',
        '',
        f'| Metrik | Wert |',
        f'|--------|------|',
        f'| Trades gesamt | {stats["total_trades"]} |',
        f'| Gewinner | {stats["wins"]} |',
        f'| Verlierer | {stats["losses"]} |',
        f'| Break-Even | {stats["breakevens"]} |',
        f'| **Win-Rate** | **{stats["win_rate"]}%** |',
        f'| Gesamt P&L | {stats["total_pnl"]:+.2f} EUR |',
        f'| Avg Win | {stats["avg_win"]:+.2f} EUR |',
        f'| Avg Loss | {stats["avg_loss"]:+.2f} EUR |',
        f'| **Risk/Reward** | **{stats["rr_ratio"]:.2f}** |',
        '',
        '---',
        '',
        '## Win-Rate nach Richtung',
        '',
        '| Richtung | Trades | Wins | Win-Rate | Gesamt P&L | Avg P&L |',
        '|----------|--------|------|----------|------------|---------|',
    ]

    for direction in ('LONG', 'SHORT'):
        ds = stats['direction_stats'].get(direction)
        if ds:
            lines.append(
                f'| {direction} | {ds["total"]} | {ds["wins"]} | {ds["win_rate"]}% | '
                f'{ds["total_pnl"]:+.2f} EUR | {ds["avg_pnl"]:+.2f} EUR |'
            )

    lines.extend([
        '',
        '---',
        '',
        '## Win-Rate nach Konfidenz-Bracket',
        '',
        '| Konfidenz | Trades | Wins | Win-Rate | Avg P&L |',
        '|-----------|--------|------|----------|---------|',
    ])

    for bracket in ('50-59', '60-69', '70-79', '80+'):
        cs = stats['confidence_stats'].get(bracket)
        if cs:
            lines.append(
                f'| {bracket}% | {cs["total"]} | {cs["wins"]} | {cs["win_rate"]}% | '
                f'{cs["avg_pnl"]:+.2f} EUR |'
            )

    lines.extend([
        '',
        '> **Interpretation:** Trades mit höherer Konfidenz sollten besser performen.',
        '> Wenn 60-69% besser als 70-79% → Overconfidence-Problem.',
        '',
        '---',
        '',
        '## Pattern-Analyse',
        '',
        '| Pattern | Anzahl | Gesamt P&L | Bedeutung |',
        '|---------|--------|------------|-----------|',
    ])

    pattern_meanings = {
        'STOP_TRIGGERED': 'Stop-Loss ausgelöst',
        'BREAK_EVEN': 'Break-Even Exit',
        'V3_PARTIAL_EXIT': '50% bei +20% verkauft (v3 Regel)',
        'RUNNER': 'Runner-Position (Rest nach Teilverkauf)',
        'DISCIPLINE_VIOLATION': 'Disziplin-Verstoß (ohne Analyse/Gier)',
        'BELOW_GATE': 'Trade unter 60% Konfidenz-Gate',
        'EXECUTION_ERROR': 'Ausführungsfehler',
    }

    for pattern, ps in sorted(stats['pattern_stats'].items(), key=lambda x: x[1]['total_pnl']):
        meaning = pattern_meanings.get(pattern, pattern)
        emoji = '🟢' if ps['total_pnl'] > 0 else '🔴' if ps['total_pnl'] < 0 else '🟡'
        lines.append(f'| {emoji} {pattern} | {ps["count"]} | {ps["total_pnl"]:+.2f} EUR | {meaning} |')

    # Trade-Duration section
    dur = stats.get('duration')
    if dur:
        lines.extend([
            '',
            '---',
            '',
            '## Trade-Duration',
            '',
            f'| Metrik | Wert |',
            f'|--------|------|',
            f'| Trades mit Datums-Info | {dur["n_parsed"]} |',
            f'| Durchschnitt | {dur["avg_days"]} Tage |',
            f'| Median | {dur["median_days"]} Tage |',
        ])
        if dur['avg_days_winners'] is not None:
            lines.append(f'| Avg Gewinner | {dur["avg_days_winners"]} Tage |')
        if dur['avg_days_losers'] is not None:
            lines.append(f'| Avg Verlierer | {dur["avg_days_losers"]} Tage |')
        lines.extend([
            '',
            f'> **Empfehlung:** Gewinner laufen ~{dur.get("avg_days_winners", "?")} Tage → Time-Stop bei 3/5 Tagen sinnvoll.',
        ])

    lines.extend([
        '',
        '---',
        '',
        '## v3 Compliance',
        '',
        f'| Metrik | Wert | Status |',
        f'|--------|------|--------|',
        f'| Teilverkäufe bei +20% | {stats["v3_partial_exits"]} | {"✅" if stats["v3_partial_exits"] > 0 else "⚠️"} |',
        f'| Disziplin-Verstöße | {stats["discipline_violations"]} | {"✅" if stats["discipline_violations"] == 0 else "🔴"} |',
        f'| Trades unter Gate | {stats["below_gate_trades"]} | {"✅" if stats["below_gate_trades"] == 0 else "🔴"} |',
        '',
        '---',
        '',
        '## Schlüssel-Erkenntnisse',
        '',
    ]
    )

    # Auto-generate key insights
    if stats['rr_ratio'] < 1.0:
        lines.append('- 🔴 **Risk/Reward < 1.0** — Verluste sind größer als Gewinne. Exits zu spät, Stops zu weit.')
    if stats['rr_ratio'] >= 1.5:
        lines.append('- 🟢 **Risk/Reward >= 1.5** — Gutes Gewinn/Verlust-Verhältnis.')

    long_stats = stats['direction_stats'].get('LONG')
    short_stats = stats['direction_stats'].get('SHORT')
    if long_stats and short_stats:
        if long_stats['win_rate'] > short_stats['win_rate'] + 15:
            lines.append(f'- ⚠️ **LONG deutlich besser als SHORT** ({long_stats["win_rate"]}% vs {short_stats["win_rate"]}%) — SHORT-Setups überprüfen.')
        elif short_stats['win_rate'] > long_stats['win_rate'] + 15:
            lines.append(f'- ⚠️ **SHORT deutlich besser als LONG** ({short_stats["win_rate"]}% vs {long_stats["win_rate"]}%) — LONG-Setups überprüfen.')

    if stats['discipline_violations'] > 0:
        viol_pnl = stats['pattern_stats'].get('DISCIPLINE_VIOLATION', {}).get('total_pnl', 0)
        lines.append(f'- 🔴 **{stats["discipline_violations"]} Disziplin-Verstöße** kosteten {viol_pnl:+.2f} EUR — KEINE Trades ohne Analyse!')

    if stats['below_gate_trades'] > 0:
        gate_pnl = stats['pattern_stats'].get('BELOW_GATE', {}).get('total_pnl', 0)
        lines.append(f'- 🔴 **{stats["below_gate_trades"]} Trades unter 60% Gate** kosteten {gate_pnl:+.2f} EUR — Gate ist ABSOLUT!')

    if stats['v3_partial_exits'] > 0:
        v3_pnl = stats['pattern_stats'].get('V3_PARTIAL_EXIT', {}).get('total_pnl', 0)
        lines.append(f'- 🟢 **{stats["v3_partial_exits"]} v3 Teilverkäufe** brachten {v3_pnl:+.2f} EUR — Kern-Strategie funktioniert!')

    lines.append('')
    return '\n'.join(lines)


def format_telegram(stats):
    """Format a compact Telegram summary."""
    msg = '<b>REFLECTION REPORT</b>\n'
    msg += f'{datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")}\n\n'

    msg += f'Trades: {stats["total_trades"]} | Win-Rate: {stats["win_rate"]}%\n'
    msg += f'P&L: {stats["total_pnl"]:+.2f} EUR\n'
    msg += f'R/R: {stats["rr_ratio"]:.2f} | Avg Win: {stats["avg_win"]:+.0f} | Avg Loss: {stats["avg_loss"]:+.0f}\n\n'

    for direction in ('LONG', 'SHORT'):
        ds = stats['direction_stats'].get(direction)
        if ds:
            emoji = '🟢' if direction == 'LONG' else '🔴'
            msg += f'{emoji} {direction}: {ds["win_rate"]}% ({ds["wins"]}/{ds["total"]}) {ds["total_pnl"]:+.0f}€\n'

    dur = stats.get('duration')
    if dur:
        msg += f'\n⏱ Avg Duration: {dur["avg_days"]} Tage'
        if dur['avg_days_winners'] is not None:
            msg += f' (Gewinner: {dur["avg_days_winners"]}, Verlierer: {dur.get("avg_days_losers", "?")})'
        msg += '\n'

    msg += f'\nv3: {stats["v3_partial_exits"]} Teilverkäufe'
    if stats['discipline_violations'] > 0:
        msg += f' | ⚠️ {stats["discipline_violations"]} Verstöße'
    if stats['below_gate_trades'] > 0:
        msg += f' | ⚠️ {stats["below_gate_trades"]} unter Gate'

    msg += '\n\n<i>Reflection Engine v1</i>'
    return msg


def main():
    parser = argparse.ArgumentParser(description='Silver Hawk Reflection Loop')
    parser.add_argument('--telegram', action='store_true', help='Send summary via Telegram')
    args = parser.parse_args()

    if not os.path.exists(PORTFOLIO_FILE):
        print(f'Portfolio file not found: {PORTFOLIO_FILE}')
        return

    with open(PORTFOLIO_FILE) as f:
        content = f.read()

    print('Parsing closed trades...')
    trades = parse_closed_trades(content)
    print(f'  Found {len(trades)} closed trades')

    print('Parsing analyses...')
    analyses = parse_analyses(content)
    print(f'  Found {len(analyses)} analyses')

    print('Analyzing trades...')
    stats = analyze_trades(trades, analyses)

    if not stats:
        print('No trades to analyze.')
        return

    print(f'\nResults:')
    print(f'  Win-Rate: {stats["win_rate"]}% ({stats["wins"]}/{stats["total_trades"]})')
    print(f'  Total P&L: {stats["total_pnl"]:+.2f} EUR')
    print(f'  Risk/Reward: {stats["rr_ratio"]:.2f}')
    print(f'  v3 Partial Exits: {stats["v3_partial_exits"]}')
    print(f'  Discipline Violations: {stats["discipline_violations"]}')

    # Generate reflections.md
    reflections_md = generate_reflections_md(stats, trades)
    with open(REFLECTIONS_FILE, 'w') as f:
        f.write(reflections_md)
    print(f'\nWritten: {REFLECTIONS_FILE}')

    if args.telegram:
        from send_telegram import send_message
        msg = format_telegram(stats)
        send_message(msg)
        print('Telegram sent.')


if __name__ == '__main__':
    main()
