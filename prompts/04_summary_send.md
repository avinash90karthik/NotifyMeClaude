# STEP 4: SUMMARY & DELIVERY

**Asset:** {{SYMBOL}}

**Input:** ALL previous steps + JSON blocks.

---

## 1. Record Prediction (BEFORE sending!)

```bash
python prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT] \
  --confidence [XX] \
  --entry [XX.XX] \
  --stop [XX.XX] \
  --target [XX.XX] \
  --ko [XX.XX] \
  --regime [TRENDING|RANGE|CHOPPY|TRANSITIONAL] \
  --atr-pct [X.X]
```

## 2. Trading Card (Telegram format)

```
{{SYMBOL}} ANALYSIS

Signal: [LONG/SHORT/HOLD] | Confidence: XX%
Price: $XX.XX (EUR XX.XX) | Regime: [REGIME]

KO: $XX.XX (XX.X% distance, [ATR/CHART])
Stop: $XX.XX | Leverage: ~Xx

Entry Timing: [PRE-MARKET/FIRST-HOUR DIP/AT OPEN]
  Pre-Mkt: XX% | Open: XX% | FH-Dip: XX%

Exits: +20% -> 50% out | +30% -> trail +15% | +40% -> trail +25%
Time-Stop: 3d <5% -> halve | 5d -> exit

S: $XX / $XX / $XX | R: $XX / $XX / $XX

Risk: Max XXX EUR (XX% portfolio)
Sector: XX% [Sector] [OK/WARN]
Correlation: [OK/WARNING]
```

## 3. Detailed Analysis (500-800 words, {{LANGUAGE}})

Structure: Introduction, Technical Situation (include RSI divergence), Fundamentals, News/Catalysts, Risks, Conclusion with action recommendation.

## 4. Validation Checklist

| # | Check | Value | Status |
|---|-------|-------|--------|
| 1 | portfolio.md read? | | |
| 2 | yfinance data (not web search)? | | |
| 3 | RSI divergence checked? | | |
| 4 | Stop-loss present? | | |
| 5 | KO = MAX(ATR, Chart)? | | |
| 6 | SHORT evaluated (scorecard)? | | |
| 7 | EUR/USD live? | | |
| 8 | Positions in %? | | |
| 9 | Sector <60%? | | |
| 10 | Prediction recorded in DB? | | |

## 5. Send via Telegram

```bash
source .env
python send_telegram.py "$(cat <<'EOF'
[Trading Card from above]
EOF
)"

# Chart photo (if available)
CHART="${CHART_OUTPUT_DIR:-charts}/{{SYMBOL}}_chart.png"
[ -f "$CHART" ] && python -c "from send_telegram import send_photo; send_photo('$CHART', '{{SYMBOL}}')"
```

## 6. Update portfolio.md

- Add new position to "Open Positions" (if trade taken)
- Update sector distribution
- Update "Last Updated" date

```
[STEP 4 COMPLETE -- ANALYSIS FINISHED]
```
