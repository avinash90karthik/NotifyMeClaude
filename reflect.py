#!/usr/bin/env python3
"""Silver Hawk Trading - Reflection/Learning Loop.
Reads closed trades and analyses from predictions.db, calculates win rates,
pattern analysis, risk/reward, and generates memory/reflections.md.

Usage:
    python reflect.py                # Generate reflections.md
    python reflect.py
"""

import argparse
import os
import sqlite3
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, 'memory', 'predictions.db')
REFLECTIONS_FILE = os.path.join(SCRIPT_DIR, 'memory', 'reflections.md')


def get_closed_trades():
    """Read closed trades from predictions.db."""
    if not os.path.exists(DB_FILE):
        return []

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT p.id, p.symbol, p.direction, p.confidence, p.status,
               p.created_at, p.closed_at, p.realized_pnl_eur,
               p.shares, p.cert_buyin, p.invested_eur, p.trade_notes,
               p.entry_price, p.stop_price, p.target_price, p.ko_level
        FROM predictions p
        WHERE p.status = 'closed'
        ORDER BY p.closed_at
    """).fetchall()

    trades = []
    for r in rows:
        pnl = r['realized_pnl_eur'] or 0.0
        notes = r['trade_notes'] or ''

        # Detect patterns from trade notes
        patterns = _detect_patterns(notes, pnl)

        trades.append({
            'id': r['id'],
            'symbol': r['symbol'],
            'direction': r['direction'],
            'confidence': r['confidence'],
            'pnl_eur': pnl,
            'notiz': notes,
            'patterns': patterns,
            'created_at': r['created_at'],
            'closed_at': r['closed_at'],
        })

    conn.close()
    return trades


def get_analyses():
    """Read all analyses from predictions.db for confidence stats."""
    if not os.path.exists(DB_FILE):
        return []

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT id, symbol, direction, confidence, created_at, status
        FROM predictions
        ORDER BY created_at
    """).fetchall()

    analyses = []
    for r in rows:
        analyses.append({
            'id': r['id'],
            'symbol': r['symbol'],
            'direction': r['direction'],
            'confidence': r['confidence'],
            'created_at': r['created_at'],
            'status': r['status'],
        })

    conn.close()
    return analyses


def _detect_patterns(notiz, pnl_eur):
    """Detect trading patterns from trade notes."""
    patterns = []
    notiz_lower = notiz.lower()

    if 'stop' in notiz_lower and ('ausgelöst' in notiz_lower or 'triggered' in notiz_lower):
        patterns.append('STOP_TRIGGERED')
    if 'break-even' in notiz_lower or 'be-stop' in notiz_lower or 'be ' in notiz_lower:
        patterns.append('BREAK_EVEN')
    if '50%' in notiz and ('+20%' in notiz or '+29%' in notiz or 'v3' in notiz_lower or 'v5' in notiz_lower):
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


def calc_duration_stats(trades):
    """Calculate trade duration statistics from DB timestamps.
    Returns dict with avg/median durations or None if insufficient data."""

    durations_win = []
    durations_loss = []

    for t in trades:
        if not t.get('created_at') or not t.get('closed_at'):
            continue
        try:
            d1 = datetime.fromisoformat(t['created_at'])
            d2 = datetime.fromisoformat(t['closed_at'])
            days = (d2 - d1).days
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
    for bracket_name, low, high in [('50-59', 50, 59), ('60-69', 60, 69), ('70-79', 70, 79), ('80+', 80, 100)]:
        bracket_trades = [t for t in trades if t.get('confidence') and low <= t['confidence'] <= high]
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

    # Strategy Compliance (50% at +20% rule)
    v3_exits = len([t for t in trades if 'V3_PARTIAL_EXIT' in t['patterns']])
    discipline_violations = len([t for t in trades if 'DISCIPLINE_VIOLATION' in t['patterns']])
    below_gate = len([t for t in trades if 'BELOW_GATE' in t['patterns']])

    duration = calc_duration_stats(trades)

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
        f'**Quelle:** memory/predictions.db',
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
        'V3_PARTIAL_EXIT': '50% bei +20% verkauft (Kern-Regel)',
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
        '## Strategy Compliance',
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
        lines.append(f'- 🟢 **{stats["v3_partial_exits"]} Teilverkäufe bei +20%** brachten {v3_pnl:+.2f} EUR — Kern-Strategie funktioniert!')

    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Silver Hawk Reflection Loop')
    args = parser.parse_args()

    if not os.path.exists(DB_FILE):
        print(f'Database not found: {DB_FILE}')
        return

    print('Reading closed trades from predictions.db...')
    trades = get_closed_trades()
    print(f'  Found {len(trades)} closed trades')

    print('Reading analyses from predictions.db...')
    analyses = get_analyses()
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
    print(f'  Partial Exits (+20%): {stats["v3_partial_exits"]}')
    print(f'  Discipline Violations: {stats["discipline_violations"]}')

    # Generate reflections.md
    reflections_md = generate_reflections_md(stats, trades)
    with open(REFLECTIONS_FILE, 'w') as f:
        f.write(reflections_md)
    print(f'\nWritten: {REFLECTIONS_FILE}')


if __name__ == '__main__':
    main()
