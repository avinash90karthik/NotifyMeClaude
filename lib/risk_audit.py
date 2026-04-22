#!/usr/bin/env python3
"""Silver Hawk Trading - Risk Audit / Veto Layer.
Independent risk check with veto power. Runs after scoring, before output.
Any single VETO blocks the trade candidate from appearing as recommended."""


def parse_portfolio_summary():
    """Load portfolio state from predictions.db (single source of truth)."""
    try:
        from scripts.prediction_db import get_db
        conn = get_db()

        # Open positions
        rows = conn.execute(
            "SELECT symbol, direction FROM predictions WHERE status='open'"
        ).fetchall()
        positions = [{'symbol': r['symbol'], 'direction': r['direction']} for r in rows]

        # Cash
        cash_row = conn.execute(
            "SELECT value FROM portfolio_state WHERE key='cash'"
        ).fetchone()
        cash = cash_row['value'] if cash_row else 0

        # Calculate portfolio value (cash + invested)
        invested_row = conn.execute(
            "SELECT COALESCE(SUM(invested_eur), 0) as total "
            "FROM predictions WHERE status='open'"
        ).fetchone()
        invested = invested_row['total'] if invested_row else 0
        portfolio_value = cash + invested

        # Monthly P&L from close_events
        monthly_pnl = conn.execute(
            "SELECT COALESCE(SUM(pnl_eur), 0) as total FROM close_events "
            "WHERE closed_at >= date('now', 'start of month')"
        ).fetchone()
        monthly_pnl_eur = monthly_pnl['total'] if monthly_pnl else 0
        monthly_pnl_pct = (monthly_pnl_eur / portfolio_value * 100) if portfolio_value > 0 else 0

        conn.close()
        return {
            'positions': positions,
            'portfolio_value': portfolio_value,
            'cash': cash,
            'monthly_pnl_pct': monthly_pnl_pct,
        }
    except Exception as e:
        print(f'  risk_audit: DB error ({e}) — fallback to empty state')
        return {'positions': [], 'portfolio_value': 0, 'cash': 0, 'monthly_pnl_pct': 0}


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
        same_sector = sum(1 for p in positions if p.get('sector', '').lower() == sector.lower())
        if active_count > 0 and (same_sector + 1) / (active_count + 1) > 0.60:
            vetoes.append(f'V4: Sektor {sector} wäre >60%')

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
