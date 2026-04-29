#!/usr/bin/env python3
"""Silver Hawk Trading - Risk Audit / Veto Layer.
Independent risk check with veto power. Runs after scoring, before output.
Any single VETO blocks the trade candidate from appearing as recommended.

v10 (2026-04-28):
  V3 tightened 3 → 2 open turbo positions (hedges excluded).
  V4 tightened 60% → 40% with AI-semi grouping rule.
  V6 replaces W2: hard veto at 60d daily-return correlation ≥ 0,7.
"""

# AI-semi basket — treated as ONE effective sector regardless of yfinance label.
# Adding/removing a ticker here is the only knob to tune the v10 sector
# grouping; sector data flows through get_effective_sector() everywhere.
AI_SEMI_GROUP = {'NVDA', 'AMD', 'AVGO', 'MRVL', 'TSM', 'ASML'}


def get_effective_sector(symbol: str) -> str:
    """Resolve a symbol's effective sector for V4 concentration check.

    AI-semis are grouped because they trade as a single beta in practice
    (60d-corr typically 0,7-0,9 within the basket). yfinance labels them
    as 'Technology' but that bucket also contains MSFT, GOOGL, etc — not
    relevant for the AI-capex co-movement we care about.

    For non-AI-semi symbols, fall back to yfinance Ticker.info['sector'].
    On any yfinance failure, return 'Unknown' (V4 will not match anything).
    """
    if symbol.upper() in AI_SEMI_GROUP:
        return "AI-Semi-Group"
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info
        return info.get('sector', 'Unknown') or 'Unknown'
    except Exception:
        return 'Unknown'


def compute_correlation(sym_a: str, sym_b: str, days: int = 60) -> float | None:
    """60-day daily-return correlation between two symbols.

    Returns None when:
      - yfinance fetch fails for either symbol
      - either symbol has < `days` of history
      - merged calendar has < 80% overlap (different holidays / listings)

    The 80% overlap rule guards against mismatched trading-day calendars
    (ENR.DE/NVDA differ by ~3 weeks/year of US-only or DE-only holidays).
    A correlation computed on << 60 aligned days is statistically too thin
    to be a hard veto basis.
    """
    try:
        import yfinance as yf
        import pandas as pd
        a_hist = yf.Ticker(sym_a).history(period=f"{days + 10}d")['Close']
        b_hist = yf.Ticker(sym_b).history(period=f"{days + 10}d")['Close']
        if len(a_hist) < days or len(b_hist) < days:
            return None
        a_ret = a_hist.pct_change().dropna().tail(days)
        b_ret = b_hist.pct_change().dropna().tail(days)
        merged = pd.concat([a_ret, b_ret], axis=1, join='inner')
        if len(merged) < days * 0.8:
            return None
        return float(merged.iloc[:, 0].corr(merged.iloc[:, 1]))
    except Exception:
        return None


def parse_portfolio_summary():
    """Load portfolio state from predictions.db (single source of truth).

    v10 enrichment: each position dict now carries `sector` (resolved via
    get_effective_sector) and `cert_type` for V3/V4 logic. yfinance is
    queried per-position; sector lookups are not cached here — risk_audit
    runs once per analysis, so the ~200ms latency is acceptable.
    """
    try:
        from scripts.ops.prediction_db import get_db
        conn = get_db()

        # Open positions — include cert_type so V3 can exclude hedges.
        rows = conn.execute(
            "SELECT symbol, direction, cert_type FROM predictions WHERE status='open'"
        ).fetchall()
        positions = [
            {
                'symbol': r['symbol'],
                'direction': r['direction'],
                'cert_type': r['cert_type'] or 'turbo',
                'sector': get_effective_sector(r['symbol']),
            }
            for r in rows
        ]

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
        sector: Sector of the candidate. If None, resolved via
            get_effective_sector(symbol). Pass explicit value for testing.

    Returns: (approved: bool, vetoes: list[str], warnings: list[str])
    """
    if portfolio_state is None:
        portfolio_state = parse_portfolio_summary()

    # Resolve candidate sector if not provided. Tests pass an explicit
    # value to avoid yfinance round-trips.
    if sector is None:
        sector = get_effective_sector(symbol)

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

    # V3 (v10): Slot limit — max 2 active TURBO positions. Hedges excluded.
    turbo_positions = [p for p in positions if p.get('cert_type') != 'hedge']
    turbo_count = len(turbo_positions)
    if turbo_count >= 2:
        vetoes.append(f'V3: {turbo_count}/2 Turbo-Slots belegt')

    # V4 (v10): Sector concentration > 40% (AI-semis grouped via get_effective_sector).
    if sector and sector != 'Unknown' and turbo_positions:
        same_sector = sum(
            1 for p in turbo_positions
            if (p.get('sector') or '').lower() == sector.lower()
        )
        # New-trade exposure: (same-sector positions + this candidate) / (total + 1)
        new_total = turbo_count + 1
        new_same = same_sector + 1
        if new_same / new_total > 0.40:
            vetoes.append(
                f'V4: Sektor {sector} wäre {new_same}/{new_total} '
                f'({new_same/new_total*100:.0f}%) > 40%'
            )

    # V5: Monthly drawdown > 20%
    if pnl_pct <= -20:
        vetoes.append(f'V5: Monats-Drawdown {pnl_pct:.1f}% — 24h Pause!')

    # V6 (v10): 60-day daily-return correlation ≥ 0,7 with ANY open position.
    # On indeterminate (n<60 history), emit soft warning instead of veto.
    for p in turbo_positions:
        corr = compute_correlation(symbol, p['symbol'])
        if corr is None:
            warnings.append(
                f'V6 inconclusive: corr {symbol}/{p["symbol"]} n<60 '
                '(soft warning, no veto)'
            )
            continue
        if abs(corr) >= 0.7:
            vetoes.append(
                f'V6: {symbol}/{p["symbol"]} 60d-corr={corr:+.2f} '
                "(Override: 'V6-override: <reason>')"
            )

    # --- WARNING RULES ---

    # W1: Earnings within 5 trading days
    earnings = data_dict.get('earnings_date')
    if earnings:
        warnings.append(f'W1: Earnings {earnings}')

    # W2 was upgraded to V6 in v10 — see veto block above.

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
