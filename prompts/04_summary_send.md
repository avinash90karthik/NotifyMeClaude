# STEP 4: SUMMARY & DELIVERY

**Asset:** {{SYMBOL}}
**Input:** Cards from Step 1, Step 2, Step 3.

This step produces the final user-facing artifact. Order: **Trading Card -> Cert Request -> DB Record**. Step 3 already settled the underlying-side trade plan; Step 4 picks the certificate, validates the leverage math, and records the prediction.

---

## 1. Trading Card (final user output)

```
╔══════════════════════════════════════════════════════════════╗
║ {{SYMBOL}} - FINAL                                           ║
╠══════════════════════════════════════════════════════════════╣
║ Signal:          LONG | SHORT | NO-TRADE                     ║
║ Confidence:      XX%   (Scorecard: LONG XX / SHORT XX)       ║
║ Price:           $XX.XX  (EUR XX.XX)                         ║
║ Regime:          TRENDING | RANGE | CHOPPY | TRANSITIONAL    ║
║                                                              ║
║ Judge override:  YES | NO                                    ║
║   Rating:        <Technical|Price-Action|News|Event>         ║
║   Reason:        <1 sentence - only when YES>                ║
║   Impact:        scorecard <X> -> Judge <Y>                  ║
║                                                              ║
║ ─ ENTRY PLAN (limit range, underlying) ──────────────        ║
║ Center:          Stock $XX.XX                                ║
║ Half-width:      $X.XX  (max(0.25×ATR, 0.5%, 0.10€))         ║
║ 1. PRIMARY:      Stock $XX.XX  (range low) until XX:XX CET   ║
║ 2. FALLBACK:     Stock $XX.XX  (range high) from XX:XX CET   ║
║                  (+60-90 min after primary)                  ║
║ 3. NO-CHASE:     Stock > $XX.XX (Center + 2×half-width)      ║
║                  -> trade expires, do NOT buy                ║
║                                                              ║
║ ─ STOCK TRADE PLAN ──────────────────────────────────        ║
║ Stop (mental):   $XX.XX (underlying)                         ║
║ KO (underlying): $XX.XX                                      ║
║ Target +20%cert: ≈ $XX.XX (underlying equivalent)            ║
║                                                              ║
║ ─ POSITION SIZING ───────────────────────────────────        ║
║ Position:        XX% portfolio = XXX EUR                     ║
║ v9 split:        Scout XX% / Confirm XX%                     ║
║ Scout EUR:       XXX EUR                                     ║
║ Confirm EUR:     XXX EUR                                     ║
║                                                              ║
║ ─ EXITS (v9) ────────────────────────────────────────        ║
║ +20% cert:       80% out immediately                         ║
║ +30%+ cert:      rest with trail                             ║
║ Time stop:       3d <5% -> halve  |  5d sideways -> exit     ║
║ Overnight/Trump: all out                                     ║
║                                                              ║
║ ─ CONTEXT ───────────────────────────────────────────        ║
║ Reversion-Guard: <Pullback-Pflicht @ X.XX | No-Edge |        ║
║                   SHORT-NO-TRADE>                            ║
║ S:               XX / XX / XX                                ║
║ R:               XX / XX / XX                                ║
║ Next event:      <event + time + clarity/uncertainty>        ║
║                                                              ║
║ Don't-Chase:     price now X.X% above fallback -> OK|WAIT    ║
║ Time window:     XX:XX Berlin - [OK | after 22:00: limits    ║
║                  for tomorrow, no trade today]               ║
║                                                              ║
║ V-Vetos active:  none | V1/V3/...                            ║
║ W-Warnings:      none | W1/W5/...  -> trade-plan mods        ║
║ Approved:        YES | NO                                    ║
║                                                              ║
║ Reasoning:       <2-3 sentences from Step 3 - core thesis>   ║
╚══════════════════════════════════════════════════════════════╝
```

Field rationale:
- **Don't-Chase** and **Time window** are the two single-liners from the old entry-timing chain that actually add value. The rest was duplication from Step 3.
- **Judge override** is mandatory-visible (CLAUDE.md: user sees every override).
- **Reversion-Guard line** shows which entry mode was chosen.
- **Entry plan** is on the **underlying** - cert-side translation lives in the cert request below. One source of truth for the stock trigger, one source of truth for the cert.

---

## 2. Cert Request (MANDATORY - depends on signal)

The cert request always follows the trading card, even on NO-TRADE. The format depends on the signal strength.

### 2a. Leverage formula (target-based on +20% cert in 1-5 days)

The cert leverage is chosen so that a realistic stock move hits the +20% target AND a normal counter-day (1× ATR) does NOT knock the position out.

**Formula:**
```
Stock-move-for-+20%  =  0.8 × ATR%        (realistic 2-3 day move)
Leverage             =  20 / Stock-move-for-+20%
                     =  25 / ATR%         (round to 0.5 step)

Implied KO distance  =  100 / Leverage    (implicit from leverage)
KO buffer to ATR     =  KO-distance / ATR%   (must be >= 3.0)
```

**Reference table (derived from formula):**

| ATR% | Leverage (target +20% in ~3d) | KO distance ≈ | KO / ATR | Check |
|------|-------------------------------|---------------|----------|-------|
| <2%  | 12-15× | 7-8% | 3.5-4× | OK |
| 2-3% | 9-12×  | 8-11% | 3.5-4× | OK |
| 3-4% | 7-9×   | 11-14% | 3.5-4× | OK |
| 4-5% | 5-7×   | 14-20% | 3.5-4× | OK |
| 5-7% | 4-5×   | 20-25% | 3.5-4× | OK (high vol) |
| >7%  | -      | -     | -    | V1 veto: warrants/options only |

**Why this formula:**
- **0.8× ATR as 2-3d move:** ATR is daily true range. Over 2-3 days, ~0.7-1.0× ATR cumulates as net move (not 2-3× ATR - that's only extreme continuation). 0.8× is the median.
- **KO at 3.5-4× ATR distance:** survives a normal -1σ day (~0.8-1× ATR counter-move) with buffer. CLAUDE.md W3 warning ("KO < 2× ATR") is safely avoided.
- **Leverage scales inversely with ATR:** low-vol stocks need more leverage to reach +20% (otherwise too slow); high-vol stocks need less (otherwise stop-out risk).

**Mandatory sanity check (always perform):**
```
Leverage × KO-distance% ≈ 100     (mathematical coherence)
KO-distance / ATR%      ≥ 3.0     (vol buffer)
```

If the chosen cert violates either check -> pick a different cert or adjust leverage.

### 2b. Cert range (sanity check, not a separate trade trigger)

The stock-side limit range from Step 3 is the trigger. The cert-side range is a **sanity check** only:

```
Cert primary level    ≈ ask at Stock = primary level   (interpolate via cert delta)
Cert fallback level   ≈ ask at Stock = fallback level
Cert range width      = |Cert fallback - Cert primary|

Check: Cert range width must be > broker spread (typically €0.01-0.05).
       Otherwise the range is smaller than the spread and the trade is unfillable
       -> pick a different cert with smaller spread.
```

EUR/USD movement and discrete cert tick steps are the two main reasons we do this sanity check - the relationship is mostly linear, but tick steps and FX shift can collapse the range.

### 2c. Request templates

**On Signal = LONG/SHORT (Gate PASS):**
```
Cert request:
  Please find a cert with:
  - Type: Turbo-{Long|Short} on {{SYMBOL}}
  - KO range: ${KO-low} to ${KO-high}
      (from leverage formula: KO-distance = 100/leverage)
  - Leverage range: {Lev-low}× to {Lev-high}×
      (formula: 25/ATR% = {target-leverage}×, range ±20%)
  - Current ask price (for exact share count)
  - Available on Trade Republic

  Pre-buy sanity check:
  - Leverage × KO-distance% ≈ 100?  [YES/NO]
  - KO-distance ≥ 3× ATR%?           [YES/NO]
  - Cert range width > broker spread? [YES/NO]
```

**On Signal = NO-TRADE but borderline (confidence 55-59%):**
```
Cert request (stand-by, in case conditions flip):
  Gate missed by X%. If tomorrow {concrete trigger} happens, the trade activates.
  Pre-source a cert with:
  - Type: Turbo-{Long|Short} on {{SYMBOL}}
  - KO range: ${KO-low} to ${KO-high}
  - Leverage range: {Lev-low}× to {Lev-high}×  (25/ATR% formula)
  - Current ask price
  - Available on Trade Republic

  We do NOT buy the cert now - only have it ready if tomorrow's re-run gives PASS.
```

**On Signal = NO-TRADE clearly below gate (<55%):**
No cert request. Reason: "no setup in reach." instead.

The leverage formula + sanity checks are **mandatory** - no free-form leverage proposals.

---

## 3. DB Record (MANDATORY - even on NO-TRADE)

```bash
python3 scripts/prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT] \
  --confidence [XX] \
  --entry [XX.XX] \
  --stop [XX.XX] \
  --target [XX.XX] \
  --ko [XX.XX] \
  --regime [TRENDING|RANGE|CHOPPY|TRANSITIONAL] \
  --atr-pct [X.X] \
  --reason "Brief thesis summary (1-2 sentences from Step 3 reasoning)"
```

**Hard (Rule 18 + Rule 22):** `--entry` = limit/trigger CENTER level from Step 3 entry plan, NEVER the close. On Judge override, the override reason must appear in `--reason`.

**After user confirms the trade:**
```bash
python3 scripts/prediction_db.py open ID --shares XX --cert-price XX.XX [--cert-type turbo|warrant|stock]
```

---

## 4. Wait for User Confirmation

- The analysis is in the DB with status `analysis`. No trade yet.
- User confirms trade -> `prediction_db.py open ID ...`
- User confirms v9 confirmation buy -> `prediction_db.py confirm ID ...`
- Portfolio state updates automatically in the DB.

```
[STEP 4 COMPLETE - ANALYSIS FINISHED]
```
