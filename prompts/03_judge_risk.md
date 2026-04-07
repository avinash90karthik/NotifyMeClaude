# STEP 3: JUDGE & RISK

**Asset:** {{SYMBOL}}

**Input:** Data (Step 1) + Debate (Step 2) + Chart. Consult `memory/feedback.md`.

---

## Judge Verdict

Analyze INDEPENDENTLY from Bull/Bear. Use the chart as your own source.

| Factor | Assessment | Weight |
|--------|------------|--------|
| Bull strength (/10) | [top 2 arguments] | |
| Bear strength (/10) | [top 2 arguments] | |
| Chart signal | [what YOU see] | |
| RSI divergence | [bullish/bearish/none + strength] | |
| NSI (from Step 1) | [value + classification] | |
| Regime | [from Step 1] | |
| Short interest | [squeeze potential?] | |
| Pre-open pattern | [confirms/contradicts?] | |

### Confidence Adjustments

| Condition | Adjustment |
|-----------|------------|
| TRENDING + signal WITH trend | +5% |
| TRENDING + signal AGAINST trend (no confirming signals) | -10% |
| TRENDING + AGAINST trend + 1 confirming (RSI div OR MACD cross) | -5% |
| TRENDING + AGAINST trend + 2+ confirming (div + MACD + SMA50) | -3% |
| RANGE + signal at S/R level | +3% |
| CHOPPY | -5% to -10% |
| Pre-open pattern hit >=60% same direction | +3% |
| Pre-open pattern hit <50% | -5% |
| Reflection: win rate for bracket <30% | -5% |

### Decision

| Horizon | Signal | Confidence |
|---------|--------|------------|
| Short-term (1-5d) | LONG/SHORT/HOLD | XX% |
| Medium-term (2-8w) | LONG/SHORT/HOLD | XX% |
| Long-term (3m+) | LONG/SHORT/HOLD | XX% |

**TRADE SIGNAL = short-term verdict (this drives turbo entry/exit)**
**Reasoning:** [2-3 sentences including chart + divergence]

---

## KO Level Calculation

**Always: KO = whichever is FURTHER from price (ATR-based or chart-based)**

### A: ATR-based KO

| Asset Class | Multiplier | Criteria |
|-------------|-----------|----------|
| Large Cap | 2.0x ATR | Market cap > $50B |
| Mid/Small Cap | 2.5x ATR | Market cap < $50B |
| Commodities | 3.0x ATR | Futures (=F suffix) |
| Crypto-related | 3.0x ATR | BTC/crypto exposure |

ATR(14) from Step 1: $XX.XX (X.X%)
ATR-KO (LONG): Price - (ATR x multiplier) = **$XX.XX**
ATR-KO (SHORT): Price + (ATR x multiplier) = **$XX.XX**

If ATR5/ATR14 > 1.5: increase multiplier by +0.5
If earnings < 5 days: increase multiplier by +0.5

### B: Chart-based KO

Identify strongest support (LONG) or resistance (SHORT) from Step 1.
Chart-KO: Below strongest support + 0.5-1% buffer = **$XX.XX**

### C: Final KO

| Method | Level | Distance from price |
|--------|-------|-------------------|
| ATR-based | $XX.XX | XX.X% |
| Chart-based | $XX.XX | XX.X% |
| **FINAL KO** | **$XX.XX** | **XX.X%** |

---

## Trade Plan

**Entry:** $XX.XX | **KO:** $XX.XX | **Stop (mental, above KO):** $XX.XX

**Exits (v5):**
| Cert level | Action | Portion |
|------------|--------|---------|
| +20% | SELL immediately | 50% |
| +30% | Trail stop to +15% | hold |
| +40% | Trail stop to +25% | hold |
| +50% | Trail stop to +35% | rest |

**Time stops:** 3 days <5% profit halve | 5 days sideways exit | Earnings <2 days secure 50%

**Expected duration:** [1-3d momentum / 2-4d pullback / 1-2d event] If >5d: warn about turbo suitability.

---

## Optimal Entry

**Ziel:** Limit-Order statt Market-Buy. Bei Turbos wirkt jeder Prozent am Entry mit dem vollen Hebel.

Use `intraday_range` from collect_data.py output:

| Metric | Value |
|--------|-------|
| Typical dip from open (Median) | X.XX% → Stock @ $XX.XX |
| Conservative dip (P25, 75% hit rate) | X.XX% → Stock @ $XX.XX |
| Nearest support | $XX.XX |
| **Realistic limit** | **$XX.XX** (max of median-dip and nearest support) |

**Cert-Impact:**
```
Cert @ Market:  €X.XX  (Stock @ $XX.XX)
Cert @ Limit:   €X.XX  (Stock @ $XX.XX)
Ersparnis:      X.X% pro Cert
```

**Entscheidung:**
- Ersparnis < 3% → Market Buy OK
- Ersparnis 3-5% → Limit-Order, 1 Tag gültig
- Ersparnis > 5% → Limit-Order DRINGEND empfohlen
- Fallback: "Wenn nicht bis XX:XX gefüllt → [Market/Reassess]"

---

## Risk Audit (VETO CHECK)

| # | Rule | Value | Status |
|---|------|-------|--------|
| V1 | ATR >7%? | ATR=X.X% | PASS/VETO |
| V2 | CHOPPY + Score <50? | Regime=X, Score=X | PASS/VETO |
| V3 | >=3 positions open? | X/3 | PASS/VETO |
| V4 | Sector >60%? | Sector: X% | PASS/VETO |
| V5 | Monthly drawdown >20%? | P&L: X% | PASS/VETO |
| W1 | Earnings <5 days? | Date | PASS/WARN |
| W2 | Correlation with open? | [which] | PASS/WARN |
| W3 | KO <2x ATR? | Distance=X.Xx | PASS/WARN |
| W4 | Against SMA200 trend? | SMA200=[up/down] | PASS/WARN |
| **W5** | **Overnight event <24h?** | **[Event + time]** | **PASS/WARN** |

### W5 Overnight Event Check (MANDATORY)

Search for events in the next 24 hours that could cause gaps:
- FOMC rate decisions, Fed/ECB speeches
- CPI, NFP, Jobless Claims releases
- Presidential addresses, trade policy announcements
- Geopolitical summits, escalation risks
- Earnings of the symbol being analyzed

**If event found AND position would be held overnight:**
- Apply overnight protection rules from `memory/strategy_v7_draft.md` § Overnight-Event-Regel:
  - Position ≥+10%: Stop on BE (PFLICHT)
  - Position ≥+15%: 50% partial exit or Stop on +5%
  - Position <+10%: Default = close, or document risk acceptance
  - Friday: always BE stop before weekend

**Result:** APPROVED / BLOCKED -- [reason]

---

## Position Sizing (Confidence-basiert)

| Confidence | Total (% Portfolio) | Scout (60%) | Confirmation (40%) |
|------------|---------------------|-------------|-------------------|
| 60-65% | Small **15%** | 9% | 6% |
| 65-70% | Standard **20%** | 12% | 8% |
| 70%+ | Standard **25%** | 15% | 10% |

**Calculate:**
- Portfolio value from `prediction_db.py portfolio`
- Scout = Portfolio × Scout% → divide by cert ask price → number of certs
- Confirmation = Portfolio × Confirm% → only after signal confirmation

## Risk-Per-Trade

| Metric | Value |
|--------|-------|
| Portfolio value | XXX EUR |
| Position size (XX%) | XXX EUR |
| Scout (60%) | XXX EUR / XX certs |
| Confirmation (40%) | XXX EUR / XX certs |
| Max loss per trade (10%) | XXX EUR |
| Currently at risk | XXX EUR |
| Remaining risk budget | XXX EUR |

---

## Output

```json
{
  "step": 3,
  "symbol": "{{SYMBOL}}",
  "signal": "LONG|SHORT|HOLD",
  "confidence_pct": 0,
  "confidence_by_horizon": {
    "short_term_1_5d": 0,
    "medium_term_2_8w": 0,
    "long_term_3m_plus": 0
  },
  "regime": "",
  "ko_level_usd": 0.00,
  "ko_method": "ATR|CHART",
  "entry_usd": 0.00,
  "stop_usd": 0.00,
  "target_usd": 0.00,
  "exits": [{"price": 0, "pct": 50}],
  "risk_per_trade_eur": 0,
  "overnight_event": null,
  "overnight_protection": null,
  "vetoes": [],
  "warnings": [],
  "approved": true
}
```

```
[STEP 3 COMPLETE]
```
