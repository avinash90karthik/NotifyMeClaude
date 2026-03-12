#!/usr/bin/env python3
"""Silver Hawk Trading - Risk Audit / Veto Layer.
Independent risk check with veto power. Runs after scoring, before output.
Any single VETO blocks the trade candidate from appearing as recommended."""

import re
import os

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'portfolio.md')

# Sector correlation pairs (high correlation = warning)
CORRELATED_SECTORS = {
    ('Technology', 'Semiconductors'), ('Technology', 'AI Cloud'),
    ('Semiconductors', 'AI Cloud'), ('Energy', 'Nuclear'),
}


def parse_portfolio_summary():
    """Parse portfolio.md for current state: positions, value, monthly P&L."""
    if not os.path.exists(PORTFOLIO_FILE):
        return {'positions': [], 'portfolio_value': 0, 'cash': 0, 'monthly_pnl_pct': 0}

    with open(PORTFOLIO_FILE) as f:
        content = f.read()

    positions = []
    portfolio_value = 0
    cash = 0
    monthly_pnl_pct = 0

    # Extract portfolio value from "Aktueller Stand" table
    for line in content.splitlines():
        if 'Portfolio-Wert' in line and '~' in line:
            m = re.search(r'~([\d.,]+)\s*EUR', line)
            if m:
                portfolio_value = float(m.group(1).replace('.', '').replace(',', '.'))
        if 'Cash frei' in line and '~' in line:
            m = re.search(r'~([\d.,]+)\s*EUR', line)
            if m:
                cash = float(m.group(1).replace('.', '').replace(',', '.'))
        if 'März P&L' in line or 'P&L' in line:
            m = re.search(r'([+-]?\d+(?:[.,]\d+)?)\s*%', line)
            if m:
                monthly_pnl_pct = float(m.group(1).replace(',', '.'))

    # Parse active positions (not strikethrough)
    in_section = False
    for line in content.splitlines():
        if 'Offene Positionen' in line:
            in_section = True
            continue
        if in_section and line.startswith('## '):
            break
        if not in_section or not line.startswith('|'):
            continue
        if '~~' in line[:20]:
            continue  # strikethrough = closed
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if not cols or cols[0] in ('#', 'Symbol', '---'):
            continue
        if '---' in cols[0]:
            continue

        # Skip header
        offset = 0
        first = re.sub(r'\*+', '', cols[0]).strip()
        if re.match(r'^\d+$', first):
            offset = 1

        sym_col = cols[0 + offset] if len(cols) > 0 + offset else ''
        dir_col = cols[1 + offset] if len(cols) > 1 + offset else ''

        base_sym = re.match(r'([A-Za-z0-9=.\-^]+)', sym_col)
        if not base_sym:
            continue
        sym_clean = base_sym.group(1)
        if sym_clean in ('Symbol', '#'):
            continue

        direction = 'LONG' if 'LONG' in dir_col.upper() or 'LONG' in sym_col.upper() else (
            'SHORT' if 'SHORT' in dir_col.upper() or 'SHORT' in sym_col.upper() else '?')

        positions.append({
            'symbol': sym_clean,
            'direction': direction,
            'raw': sym_col,
        })

    return {
        'positions': positions,
        'portfolio_value': portfolio_value,
        'cash': cash,
        'monthly_pnl_pct': monthly_pnl_pct,
    }


def risk_audit(symbol, data_dict, portfolio_state=None, sector=None):
    """Independent risk check with veto power.

    Args:
        symbol: Ticker symbol
        data_dict: Technical data from calc_technicals() + enrichment
        portfolio_state: From parse_portfolio_summary() (auto-parsed if None)
        sector: Sector of the candidate

    Returns: (approved: bool, vetoes: list[str], warnings: list[str])
    """
    if portfolio_state is None:
        portfolio_state = parse_portfolio_summary()

    vetoes = []
    warnings = []
    positions = portfolio_state.get('positions', [])
    pnl_pct = portfolio_state.get('monthly_pnl_pct', 0)
    atr_pct = data_dict.get('atr_pct')
    regime = data_dict.get('regime')
    score_l = data_dict.get('_score_long', 0)
    score_s = data_dict.get('_score_short', 0)
    best_score = max(score_l, score_s)

    # --- VETO RULES ---

    # V1: ATR too high for leveraged product
    if atr_pct is not None and atr_pct > 7.0:
        vetoes.append(f'V1: ATR {atr_pct:.1f}% > 7% — nur ohne Hebel!')

    # V2: Choppy regime + low score
    if regime == 'CHOPPY' and best_score < 50:
        vetoes.append(f'V2: CHOPPY Regime + Score {best_score} < 50')

    # V3: Slot limit (max 3 active positions)
    active_count = len(positions)
    if active_count >= 3:
        vetoes.append(f'V3: {active_count}/3 Slots belegt')

    # V4: Sector concentration > 60%
    if sector and positions:
        same_sector = sum(1 for p in positions if sector.lower() in p.get('raw', '').lower())
        if active_count > 0 and (same_sector + 1) / (active_count + 1) > 0.60:
            vetoes.append(f'V4: Sektor {sector} wäre >{60}%')

    # V5: Monthly drawdown > 20%
    if pnl_pct <= -20:
        vetoes.append(f'V5: Monats-Drawdown {pnl_pct:.1f}% — 24h Pause!')

    # --- WARNING RULES ---

    # W1: Earnings within 5 trading days
    earnings = data_dict.get('earnings_date')
    if earnings:
        warnings.append(f'W1: Earnings {earnings}')

    # W2: Correlation with existing position
    for p in positions:
        if p['symbol'] in symbol or symbol in p['symbol']:
            warnings.append(f'W2: Korrelation mit {p["symbol"]} ({p["direction"]})')

    # W3: KO distance check (conceptual — no KO data in screener)
    # Skipped in screener context, applied in analysis prompts

    # W4: Against the trend (SMA200)
    dist200 = data_dict.get('sma200_distance_pct')
    if dist200 is not None:
        if score_l > score_s and dist200 < -5:
            warnings.append('W4: LONG gegen SMA200-Trend')
        elif score_s > score_l and dist200 > 5:
            warnings.append('W4: SHORT gegen SMA200-Trend')

    approved = len(vetoes) == 0
    return approved, vetoes, warnings
