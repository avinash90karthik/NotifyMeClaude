# Silver Hawk Trading — Strategy v5

> **Status:** Active
> **Basis:** v3 core rules + Scout/Confirmation entry system
> **Goal:** Drastically reduce losses, fully capture gains

---

## CORE PRINCIPLE

```
v3: Full position in → stop → full loss
v5: 60% immediately, 40% on confirmation → failed trade = 40% less loss
```

---

## ENTRY IN 2 TRANCHES

### Phase 1: SCOUT (60% of planned position)

- **When:** On the 4-step analysis signal (≥60% confidence)
- **Immediately on entry:** Limit sell for 50% of scout position at +20% cert
- **Stop:** Analysis stop (ATR + chart, same as v3)

### Phase 2: CONFIRMATION (remaining 40%)

- **Trigger (one is enough):**
  - Next trading day closes GREEN (underlying, not cert)
  - Position is +5% up on cert level
  - New technical signal (breakout, volume spike, SMA reclaim)
- **If no confirmation after 2 days:**
  - Scout runs alone with original stop
  - No follow-up → wait for next analysis
- **On confirmation:**
  - Buy 40% follow-up (possibly different cert price!)
  - Limit sell for 50% of total position at +20% cert
  - Raise scout stop to break-even

### No follow-up when:

- Scout is >10% up (entry missed, too expensive)
- Scout is >10% down (trade not working as planned)
- ATR(5) > ATR(14) × 1.5 (volatility spike since entry)
- New VETO from risk audit (slots full, sector >60%)
- Earnings <3 days away

### Exception: Event Trades

- Post-earnings dip buys, FOMC reactions = time-critical
- → 100% immediately like v3 (no confirmation entry)
- → Reason: Move happens in 30 minutes, 60/40 doesn't work

---

## EXIT RULES (v5)

### Profit Exits (tiered from +30%)

| Cert Up | Action |
|---|---|
| **+10%** | Stop → break-even (scout in 2-tranche setup) |
| **+20%** | **50% SELL IMMEDIATELY** (v3 core rule!) |
| **+30%** | Trail stop to +15% |
| **+40%** | Trail stop to +25% |
| **+50%** | Trail stop to +35% |
| **+60%+** | Trail always 15% below current high |

### Trail Distance by Asset Type

| Asset Type | Min Trail Distance |
|---|---|
| Large Cap Stocks | 1.5x ATR |
| Mid/Small Cap | 2x ATR |
| Commodities | 2.5x ATR |
| Index | 1.5x ATR |

> Trail NEVER tighter than 1.5x ATR — otherwise intraday noise triggers it.

### Loss Stop (NOT tiered!)

```
╔═══════════════════════════════════════════════════════════════╗
║  ONE STOP FOR EVERYTHING — NO NEGOTIATING!                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Stop comes from the 4-step analysis:                        ║
║  → ATR-based + chart support combined                        ║
║  → Mental stop ABOVE the KO level                            ║
║  → On stop trigger: SELL EVERYTHING, no partial              ║
║                                                               ║
║  Why NO tiered stop:                                         ║
║  1. Turbo noise triggers early tiers too often               ║
║  2. Each tier is a point to "negotiate"                      ║
║  3. Positions can dip -24% before rallying +20%              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## POSITION SIZES (v5)

### Confidence → Total Size → Tranches

| Confidence | Total | Scout (60%) | Confirmation (40%) |
|---|---|---|---|
| 60-65% | Small 15% | 9% | 6% |
| 65-70% | Standard 20% | 12% | 8% |
| 70%+ | Standard 25% | 15% | 10% |

### Example at 5,000 Portfolio

| Confidence | Total | Scout | Confirmation | Max Loss* |
|---|---|---|---|---|
| 60-65% | 750 | 450 | 300 | ~90 (scout only) / ~150 (full) |
| 65-70% | 1,000 | 600 | 400 | ~120 / ~200 |
| 70%+ | 1,250 | 750 | 500 | ~150 / ~250 |

*Max loss at -20% stop on cert.

---

## WORST-CASE SCENARIOS

### A: Scout fails immediately (no follow-up)

```
Planned: 1,000 | Invested: 600 (60% scout)
Stop: -20% on cert | Loss: -120 (instead of -200 with v3)
Savings: 80 = 40% less loss
```

### B: Scout + confirmation, then stop

```
Planned: 1,000 | Invested: 1,000
Scout on BE after confirmation
Stop: Scout 0 + Confirmation -20% × 400 = -80
Total: -80 (instead of -200 with v3)
```

### C: Full trade runs (best case)

```
Planned: 1,000 | Invested: 1,000
+20%: 50% sold = +100 secured
+40%: Trail at +25% = at least +125
Total: +225+ (identical to v3)
```

---

## V5 vs V3 — COMPARISON

| Metric | v3 | v5 |
|---|---|---|
| Entry | 100% at once | 60% immediately, 40% on confirmation |
| Max loss on failed trade | 100% of position | 60% of position |
| Loss when confirmed + fails | 100% × stop | Scout BE + 40% × stop |
| Take profits | 50% at +20% | 50% at +20% (identical) |
| Trailing stops | BE only | Tiered (+15/+25/+35%) |
| Stop negotiation | 1 decision | 1 decision (identical) |
| Psychological effect on loss | Large loss = tilt | 40% smaller loss |
| Profit on full trade | Identical | ~5% less (higher avg entry) |

---

## RULES CARRIED OVER FROM V3

- ≥60% confidence gate — NO exceptions
- Max 3 open positions simultaneously
- Max 10% loss per trade
- Max 40% simultaneously at risk
- Max 60% sector concentration
- KO distance: ≥2x ATR (commodities ≥3x)
- ATR >7%: ONLY no leverage (stock directly OK)
- 50% at +20% IMMEDIATELY out
- Hedge system: 3rd slot as index SHORT with 2 LONGs + macro risk
- After-hours/weekend gap risk
- FOMC/Earnings: secure at least 50% beforehand
- Time stops: 3 days without +5% → halve, 5 days → exit

---

## RISK SCORE CLARIFICATION

```
╔═══════════════════════════════════════════════════════════════╗
║  yfinance Risk Score (1-10) is NOT a VETO reason!            ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  WHY: Risk Score only measures historical volatility +       ║
║  balance sheet metrics. It does NOT capture:                  ║
║  - Qualitative de-risking (backstop deals)                   ║
║  - Strategic investments                                     ║
║  - Revenue growth                                            ║
║  - Analyst upgrades                                          ║
║                                                               ║
║  WHAT COUNTS INSTEAD (real VETO rules):                      ║
║  V1: ATR >7% → no turbo (stock directly OK)                 ║
║  V2: CHOPPY + Score <50 → VETO (THAT is the real filter)    ║
║  V3: ≥3 open positions → no new trade                       ║
║  V4: Sector >60% → correlation risk                         ║
║  V5: Drawdown >20% → 24h pause                              ║
║                                                               ║
║  Risk Score is DOCUMENTED but not used as VETO.              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## POST-FOMC LEARNING

```
╔═══════════════════════════════════════════════════════════════╗
║  AFTER HAWKISH FOMC: WAIT 3-5 DAYS!                         ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  LONG after hawkish FOMC:                                    ║
║  → Macro works AGAINST you                                   ║
║  → Wait 3-5 days, discount technical signals (-5%)           ║
║  → "Relative strength for 1 day" = NOT a sustainable signal  ║
║                                                               ║
║  SHORT after hawkish FOMC:                                   ║
║  → Macro works WITH you                                      ║
║  → BUT: RSI oversold bounce risk                             ║
║  → WAIT for bounce, then short                               ║
║                                                               ║
║  Confidence adjustment:                                      ║
║  Day 1-2 after FOMC: -5% (LONG) / -3% (SHORT)              ║
║  Day 3-4: -3% / -1%                                         ║
║  From day 5: 0% / 0%                                        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## LIVE-TEST TRACKING

| # | Date | Symbol | Scout | Confirmed? | Follow-up | Result | v3 Comparison | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |

> Goal: Track 10 trades to evaluate v5 performance vs v3.
