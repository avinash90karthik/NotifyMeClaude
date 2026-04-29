#!/usr/bin/env python3
"""Silver Hawk Trading - Risk Audit Layer.

Aligned with RULES.md as of 2026-04-29. The function classifies rule
violations into three buckets matching the RULES.md severity legend:

  - vetoes        — RULES.md V-rules (V1-V5). Hard block, no override.
  - soft_vetoes   — RULES.md SV-rules (SV1-SV3). Default block, but the
                    Judge can override with a documented `<ID>-override`
                    line. This module does NOT auto-block on soft vetoes;
                    it surfaces them in the output and lets the Judge
                    decide. (Per user decision 2026-04-29: severity
                    enforcement lives in the prompt, not the script.)
  - warnings      — RULES.md W-rules. No block; Judge applies the
                    mandated trade-plan / sizing / confidence adjustment.

Subset implemented in this module (rules whose mechanics are screener-
addressable from the technicals dict + portfolio state):

  V4   — ATR > 7%
  V5   — Maximum 3 open turbo positions (hedges excluded)
  SV1  — CHOPPY regime + scorecard total < 50  (here: best _score_*<50)
  SV2  — 60-day daily-return correlation ≥ 0,7 with any open position
  SV3  — Sector concentration > 40% (AI-semis grouped)
  W10  — Earnings within 5 days

The remaining V/SV/W rules are enforced inside the prompt pipeline and
are out of scope for this module.

Returns a dict (not a tuple) so future severity buckets can be added
without breaking callers.
"""

# --- RULES.md V5: Maximum 3 open turbo positions ------------------------------
# Single source of truth for the slot cap. Bumping this value requires
# updating RULES.md V5 in the same PR.
MAX_OPEN_TURBOS = 3

# --- RULES.md SV3: AI-semi basket --------------------------------------------
# Treated as ONE effective sector regardless of yfinance label. Adding
# or removing a ticker here is the only knob to tune the SV3 sector
# grouping; sector data flows through get_effective_sector() everywhere.
AI_SEMI_GROUP = {'NVDA', 'AMD', 'AVGO', 'MRVL', 'TSM', 'ASML'}


def get_effective_sector(symbol: str) -> str:
    """Resolve a symbol's effective sector for SV3 concentration check.

    AI-semis are grouped because they trade as a single beta in practice
    (60d-corr typically 0,7-0,9 within the basket). yfinance labels them
    as 'Technology' but that bucket also contains MSFT, GOOGL, etc — not
    relevant for the AI-capex co-movement we care about.

    For non-AI-semi symbols, fall back to yfinance Ticker.info['sector'].
    On any yfinance failure, return 'Unknown' (SV3 will not match anything).
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

    Each position dict carries `sector` (resolved via get_effective_sector)
    and `cert_type` for V5 / SV3 logic. yfinance is queried per-position;
    sector lookups are not cached here — risk_audit runs once per analysis,
    so the ~200ms latency is acceptable.
    """
    try:
        from scripts.ops.prediction_db import get_db
        conn = get_db()

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

        cash_row = conn.execute(
            "SELECT value FROM portfolio_state WHERE key='cash'"
        ).fetchone()
        cash = cash_row['value'] if cash_row else 0

        invested_row = conn.execute(
            "SELECT COALESCE(SUM(invested_eur), 0) as total "
            "FROM predictions WHERE status='open'"
        ).fetchone()
        invested = invested_row['total'] if invested_row else 0
        portfolio_value = cash + invested

        conn.close()
        return {
            'positions': positions,
            'portfolio_value': portfolio_value,
            'cash': cash,
        }
    except Exception as e:
        print(f'  risk_audit: DB error ({e}) — fallback to empty state')
        return {'positions': [], 'portfolio_value': 0, 'cash': 0}


def risk_audit(symbol, data_dict, portfolio_state=None, sector=None):
    """Independent risk check, severity-aware per RULES.md.

    Args:
        symbol: Ticker symbol of the candidate trade.
        data_dict: Technical data from calc_technicals() + enrichment.
            Recognised keys: atr_pct, regime, _score_long, _score_short,
            earnings_date, earnings_days_to (int, days until next earnings).
        portfolio_state: From parse_portfolio_summary() (auto-parsed if None).
        sector: Sector of the candidate. If None, resolved via
            get_effective_sector(symbol). Pass explicit value for testing.

    Returns:
        dict with keys:
          'approved'     : bool  — True iff no hard Veto fired
          'vetoes'       : list[str] — hard Vetos (V1-V5)
          'soft_vetoes'  : list[str] — soft Vetos (SV1-SV3); do NOT block
                                       approved. The Judge in the prompt
                                       decides about override.
          'warnings'     : list[str] — W-warnings (W10 here)
    """
    if portfolio_state is None:
        portfolio_state = parse_portfolio_summary()

    if sector is None:
        sector = get_effective_sector(symbol)

    vetoes: list[str] = []
    soft_vetoes: list[str] = []
    warnings: list[str] = []

    positions = portfolio_state.get('positions', [])
    atr_pct = data_dict.get('atr_pct')
    regime = data_dict.get('regime')
    score_l = data_dict.get('_score_long', 0)
    score_s = data_dict.get('_score_short', 0)
    best_score = max(score_l, score_s)

    # --- Hard Vetos (RULES.md V1-V5) ----------------------------------------

    # V4 — ATR > 7%
    if atr_pct is not None and atr_pct > 7.0:
        vetoes.append(f'V4: ATR {atr_pct:.1f}% > 7% — cert is wrong instrument')

    # V5 — Maximum N open turbo positions (hedges excluded)
    turbo_positions = [p for p in positions if p.get('cert_type') != 'hedge']
    turbo_count = len(turbo_positions)
    if turbo_count >= MAX_OPEN_TURBOS:
        vetoes.append(
            f'V5: {turbo_count}/{MAX_OPEN_TURBOS} Turbo-Slots belegt'
        )

    # --- Soft Vetos (RULES.md SV1-SV3) --------------------------------------
    # These are surfaced but do NOT set approved=False. The Judge in the
    # prompt evaluates each and may override with `"<ID>-override: <reason>"`.

    # SV1 — CHOPPY regime + scorecard total < 50
    if regime == 'CHOPPY' and best_score < 50:
        soft_vetoes.append(
            f'SV1: CHOPPY regime + best score {best_score} < 50 '
            "(Override: 'SV1-override: <reason>')"
        )

    # SV2 — 60-day daily-return correlation ≥ 0,7 with ANY open position.
    # On indeterminate (n<60 history), emit a warning instead of a soft veto.
    for p in turbo_positions:
        corr = compute_correlation(symbol, p['symbol'])
        if corr is None:
            warnings.append(
                f'SV2 inconclusive: corr {symbol}/{p["symbol"]} n<60'
            )
            continue
        if abs(corr) >= 0.7:
            soft_vetoes.append(
                f'SV2: {symbol}/{p["symbol"]} 60d-corr={corr:+.2f} ≥ 0,7 '
                "(Override: 'SV2-override: <reason>')"
            )

    # SV3 — Sector concentration > 40% (AI-semis grouped via get_effective_sector)
    if sector and sector != 'Unknown' and turbo_positions:
        same_sector = sum(
            1 for p in turbo_positions
            if (p.get('sector') or '').lower() == sector.lower()
        )
        new_total = turbo_count + 1
        new_same = same_sector + 1
        if new_same / new_total > 0.40:
            soft_vetoes.append(
                f'SV3: Sektor {sector} wäre {new_same}/{new_total} '
                f'({new_same/new_total*100:.0f}%) > 40% '
                "(Override: 'SV3-override: <reason>')"
            )

    # --- Warnings (RULES.md W-rules) ----------------------------------------

    # W10 — Earnings within 5 trading days → KO multiplier +0,5 in Step 3.
    # Use earnings_days_to if provided; otherwise just flag the fact that
    # earnings exist and let the Judge resolve the distance check.
    earnings_days = data_dict.get('earnings_days_to')
    earnings_date = data_dict.get('earnings_date')
    if earnings_days is not None and earnings_days <= 5:
        warnings.append(
            f'W10: Earnings in {earnings_days}d ≤ 5d — apply KO multiplier +0.5'
        )
    elif earnings_date and earnings_days is None:
        warnings.append(
            f'W10 check needed: Earnings {earnings_date} '
            '(distance unknown — Judge must resolve)'
        )

    approved = len(vetoes) == 0
    return {
        'approved': approved,
        'vetoes': vetoes,
        'soft_vetoes': soft_vetoes,
        'warnings': warnings,
    }
