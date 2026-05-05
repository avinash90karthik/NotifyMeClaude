# STEP 4: SUMMARY & DELIVERY

**Asset:** {{SYMBOL}}
**Input:** Step 3 Output Card (Underlying trade plan).

This step delivers the final trade artifact in two phases:

- **Phase A**: Cert Request for the user (before user picks cert)
- **User input**: User searches in Trade Republic, returns ISIN + current ask
- **Phase B**: Final Trading Card + DB Record + `place_exits.py` (after user input)

Step 3 settled the underlying-side trade plan. Step 4 picks the certificate translation and records the prediction.

---

## Phase A: Cert Request

### A.1 Leverage Estimate from KO and Entry Range

From Step 3 Output Card:
- KO Level (Underlying): $XX.XX
- Entry range (Underlying): $XX.XX  -  $XX.XX
- Target 1 (Underlying): $XX.XX
- Target 2 (Underlying): $XX.XX

Because the entry is a range, the resulting leverage is also a range. The LLM reasons in 2-3 sentences:

- Leverage at entry-range low: 100 / (distance from low to KO)%
- Leverage at entry-range high: 100 / (distance from high to KO)%
- Sanity-check: at this leverage, Target 1 should produce roughly +10-15% cert gain, Target 2 roughly +20-30%. If the math produces +5% cert at Target 1 (leverage too low) or +35% at Target 1 (leverage too high), reconsider — likely the KO-distance or Targets need adjustment back in Step 3.

### A.2 Geometry Sanity Check

The cert-stop staircase needs room between Stop 3 (-25% cert) and the KO. Compute the underlying move that would trigger Stop 3:

```
Stop3_Underlying_move = 25% / Leverage
```

If `Stop3_Underlying_move` is close to or beyond the KO distance, the staircase degenerates — Stop 3 sits at or beyond the KO and provides no meaningful discipline before the auto-knockout.

If the geometry doesn't work cleanly, surface the constraint to the user with two alternative paths:

- Search for a cert with higher leverage (tighter KO, more room for the staircase)
- Or a cert with a wider KO (further out, but lower leverage and possibly weaker target gains)

The LLM explains briefly which path is more sensible for this trade. Only if neither path is available on Trade Republic: NO-TRADE.

### A.3 Emit Cert Request

Output to user (German conversational tone, this is for the user not the pipeline):

```
Bitte such ein Cert auf Trade Republic:

  Symbol:        {{SYMBOL}}
  Type:          Turbo-{Long|Short}
  Leverage:      <Lev-low>× bis <Lev-high>×
  KO range:      $<KO-low> bis $<KO-high>  (Underlying)
  Issuer:        any verfügbare — am liebsten engster Spread und sinnvolle KO-Distance

Dann sag mir:
  - ISIN
  - Aktueller Ask-Preis
  - Tatsächliche Leverage und KO laut TR
```

Stop here. Wait for user input. Do not proceed to Phase B until the user provides ISIN + ask + actual leverage + actual KO.

If the user reports "kein passendes Cert verfügbar":
- If close to leverage range (off by ≤20%): proceed with what's available, note deviation in DB record reason
- If significantly off (off by >40%): discuss with user — accept the deviation with smaller position, or NO-TRADE

---

## Phase B: Final Trading Card

After user provides ISIN + ask:

### B.1 Calculate Cert-Side Levels

Cert-Stop staircase (from §5 Step 3, uniform across all trades):

```
Cert ask price:     ASK
Stop 1 (-10%):      ASK × 0.90  — sell 33% of position
Stop 2 (-17%):      ASK × 0.83  — sell 33% of position
Stop 3 (-25%):      ASK × 0.75  — sell 34% of position
```

Cert-Side Targets (from underlying-move × actual leverage):

```
Target 1 cert price: ASK × (1 + Underlying-move-1% × Leverage / 100)
Target 2 cert price: ASK × (1 + Underlying-move-2% × Leverage / 100)
```

Position math:

```
Position EUR:        from Step 3 sizing
Cert count:          Position EUR / ASK  (round down to whole number)
Actual position EUR: Cert count × ASK
Max loss (full KO):  Cert count × ASK
Realistic max loss   Cert count × ASK × 0.25  (= position lost at Stop 3)
  (staircase):
```

### B.2 Trading Card

```
╔══════════════════════════════════════════════════════════════╗
║ {{SYMBOL}} — FINAL                                           ║
╠══════════════════════════════════════════════════════════════╣
║ Signal:          LONG | SHORT                                ║
║ Confidence:      XX%                                         ║
║ Underlying:      $XX.XX  |  Cert ask: EUR XX.XX              ║
║                                                              ║
║ ─ TRADE WINDOW (Underlying, valid 3 trading days) ─────      ║
║ Entry range:     $XX.XX  -  $XX.XX                           ║
║ Current price:   $XX.XX  (inside | wait for retrace/bounce)  ║
║ No-chase level:  $XX.XX                                      ║
║                                                              ║
║ ─ CERT (translated for execution) ──────────────────         ║
║ ISIN:            DE000XXXXXX                                 ║
║ Type:            Turbo-Long | Turbo-Short                    ║
║ Issuer:          HSBC | SocGen | Vontobel | UBS              ║
║ Leverage:        X.X×                                        ║
║ Cert ask:        EUR XX.XX                                   ║
║                                                              ║
║ ─ POSITION ─────────────────────────────────────────         ║
║ Position EUR:    XXX EUR  (XX% of cash)                      ║
║ Cert count:      XX shares                                   ║
║ Max loss (KO):   XXX EUR                                     ║
║ Max loss (3rd stop): XXX EUR  (= 25% of position)            ║
║                                                              ║
║ ─ EXIT STAIRCASE (Cert-%, placed via pytr after fill) ──     ║
║ Stop 1 (-10% cert):  EUR XX.XX  → sell 33%                   ║
║ Stop 2 (-17% cert):  EUR XX.XX  → sell 33%                   ║
║ Stop 3 (-25% cert):  EUR XX.XX  → sell 34%                   ║
║ KO (Underlying):     $XX.XX  (TR auto-out, backstop)         ║
║                                                              ║
║ Target 1 (+XX% cert): EUR XX.XX  → manual sell 75%           ║
║                                  + recalibrate stops to BE   ║
║ Target 2 (+XX% cert): EUR XX.XX  → manual sell remaining 25% ║
║                                                              ║
║ ─ TIME STOPS ────────────────────────────────────────        ║
║ End of Day 1 flat/negative cert: consider 50% exit           ║
║ 3 days < 5% profit:    halve position                        ║
║ 5 days sideways:       full exit                             ║
║ Earnings < 2 days:     50% off                               ║
║                                                              ║
║ ─ REASONING ────────────────────────────────────────         ║
║ <3 sentences from Step 3 Output Card>                        ║
╚══════════════════════════════════════════════════════════════╝
```

### B.3 NO-TRADE Variant of the Card

If Step 3 returned NO-TRADE, Phase A is skipped entirely. Phase B emits a minimal card:

```
╔══════════════════════════════════════════════════════════════╗
║ {{SYMBOL}} — NO TRADE                                        ║
╠══════════════════════════════════════════════════════════════╣
║ Signal:          NO-TRADE                                    ║
║ Reason:          <one sentence from Step 3>                  ║
║ Underlying:      $XX.XX                                      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## DB Record (always, including NO-TRADE)

```bash
python3 scripts/ops/prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT|NO_TRADE] \
  --confidence [XX] \
  --entry-low [XX.XX] \
  --entry-high [XX.XX] \
  --ko [XX.XX] \
  --target1 [XX.XX] \
  --target2 [XX.XX] \
  --reason "<2-3 sentences from Step 3 reasoning>"
```

For NO-TRADE: `--entry-low`, `--entry-high`, `--ko`, `--target1`, `--target2` are NULL. The `--reason` captures why the trade was declined.

---

## After User Confirms the Trade

Workflow:

1. User manually buys the cert in the Trade Republic app
2. User confirms fill in the chat (with fill price)
3. **ASAP** after fill confirmation, run the two commands below to mark the prediction opened and place all exit orders + target alarms

```bash
# 1. Mark prediction as opened in DB
python3 scripts/ops/prediction_db.py open <prediction_id> \
  --shares <count> --cert-price <fill_price>

# 2. Place exit orders + target alarms via pytr
python3 scripts/tr/place_exits.py \
  --isin <CERT_ISIN> \
  --buy <FILL_PRICE> \
  --shares <COUNT> \
  --stops 10:33,17:33,25:34 \
  --targets <T1-cert-pct>,<T2-cert-pct>
```

`place_exits.py` behavior:

- Cancels any existing sell orders on the ISIN first (avoids "not enough shares" rejections)
- Places stop-market sell orders per `--stops` (e.g. -10%/-17%/-25% with 33/33/34% sizes)
- Sets PRICE ALARMS for the cert-% gains in `--targets` (push to TR mobile app)
- Exchange is derived from the ISIN issuer (TUB for HSBC, SGL for SocGen, LSX for stock/ETF certs); override with `--exchange` if needed
- Use `--dry-run` to preview the plan before mutating

**Why alarms not orders for Targets**: TR reserves shares for any open sell order. The three stops already reserve 100% of shares; placing limit-sells for targets would block the stops. The user must sell manually in the TR app when an alarm fires.

### Workflow when Target 1 alarm fires

1. User sells 75% manually in TR app
2. User runs `place_exits.py --recalibrate` — cancels all existing stops, places a single new stop at break-even (fill price) on the remaining 25%
3. After Target 1: no more loss possible on the remaining position

### Workflow when Target 2 alarm fires

1. User sells the remaining 25% manually in TR app
2. Trade is closed; mark as closed in DB:
   ```bash
   python3 scripts/ops/prediction_db.py close <prediction_id> \
     --exit-price <last_sell_price> --reason target
   ```

### Workflow when a stop triggers

TR auto-sells the configured share count, no user action needed. The position size in DB is updated on next portfolio sync. If Stop 3 triggers (full exit at -25% cert), mark the prediction closed with reason `stop_3`.

### Time-stop manual interventions

Time stops (Day 1 flat, 3 days < 5%, 5 days sideways, earnings within 2 days) are **manual** — the user observes and decides whether to act. There is no automated time-stop daemon.

---

## Persistence

Phase A request and Phase B trading card both written to:

```
runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/step4_delivery.md
```

Overwrite if file exists.

---

## What Step 4 does NOT do

- Does not autonomously place buy orders — user manually buys in TR app after seeing the trading card
- Does not pick the cert for the user — the user searches TR with the request specification and reports back
- Does not place target limit-orders — TR share-reservation makes this incompatible with the stop staircase; targets are alarms

---

## Audit: Mai 2026 → Bewertung Juni 2026

Die Cert-Stop-Treppe (-10/-17/-25 mit 33/33/34% Anteilen) ist für Mai 2026 bewusst einheitlich über alle Trades und Volatilitäten. Sicherheit vor Optimierung in der initialen Live-Phase.

Bewertung Anfang Juni 2026 nach den Mai-Trades:

1. Wurde Stop 1 (-10%) häufig getriggert und Position erholte sich danach? Wenn ja: -10% ist zu eng für die typische Setup-Volatilität.
2. Wurde KO trotz Stop-Treppe erreicht? Wenn ja: dritter Stop zu nah an KO oder Treppe insgesamt zu langsam.
3. Funktioniert die Treppe für NVDA (vol) und ENR.DE (ruhig) gleich gut, oder braucht es vol-abhängige Stufen?

Bis dahin: keine Anpassungen, nur Daten sammeln. Anpassungen evidenzbasiert, nicht bauchgefühlbasiert.

---

## Pipeline Complete

```
[STEP 4 COMPLETE — ANALYSIS FINISHED]
```

Subsequent monitoring is via portfolio dashboard and TR app push notifications.

### When the TR price alarm fires (alarm-fired re-run)

Do NOT trigger a full Step 1 → 2 → 3 re-run. The original plan defined the
trigger condition deliberately; the trigger firing is the entry signal, not
a request for re-debate.

Instead, run §8 Mode A (Catastrophic Event Check) from `03_judge_risk.md`.
This is a short check (~30 seconds, four explicit yes/no questions) against
the original plan's `metadata.json` timestamp:

  1. Earnings surprise on this stock since original plan?
  2. Material company-specific news (M&A, fraud, SEC, guidance pull, CEO,
     recall) since original plan?
  3. Market regime break (VIX +50%, SPX/DAX -3% intraday, sector ETF -4%)?
  4. Per-stock structure break (daily close below the original KO)?

If all four = NO: emit a Mode A confirmation card. The underlying-side plan
is preserved unchanged (entry zone, KO, targets, position EUR, staircase
percentages). No new run_id — append the confirmation card to the original
`runs/{SYMBOL}_*/` folder as `step4_alarm_confirmation.md`.

Cert-side recalculation is mandatory:
  - User reports current cert ask (may differ from original ask)
  - Cert-Stop-Staircase prices recomputed: new_ask × 0.90 / 0.83 / 0.75
  - Cert count = position EUR / new_ask
  - Target cert prices recomputed from current cert ask × leverage

If any = YES: this becomes a Mode B (User-Initiated Re-Run) with full
pipeline AND Drift Audit applied. New run_id, new folder.

### When the user asks for a fresh look (user-initiated re-run)

Full Step 1 → 2 → 3 → 4 pipeline with new run_id. Step 3 §8 Mode B applies
(Drift Audit). This is the right place for the conservative "3+ corrective
changes = NO-TRADE" gate — the user came in fresh, structural deterioration
is a real signal.
