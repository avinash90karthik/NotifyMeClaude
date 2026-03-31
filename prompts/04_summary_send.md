# STEP 4: SUMMARY & DELIVERY

**Asset:** {{SYMBOL}}

**Input:** ALL previous steps + JSON blocks.

---

## 1. Record Analysis (ALWAYS — even HOLD signals!)

```bash
python prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT] \
  --confidence [XX] \
  --entry [XX.XX] \
  --stop [XX.XX] \
  --target [XX.XX] \
  --ko [XX.XX] \
  --regime [TRENDING|RANGE|CHOPPY|TRANSITIONAL] \
  --atr-pct [X.X] \
  --reason "Brief thesis summary"
```

**After user confirms trade:**
```bash
python prediction_db.py open ID --shares XX --cert-price XX.XX [--cert-type turbo|warrant|stock]
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

## 4. Entry Timing Recommendation

Check the current time (Berlin timezone) and recommend when to execute the trade:

```python
python3 -c "
from datetime import datetime
import pytz
berlin = pytz.timezone('Europe/Berlin')
now = datetime.now(berlin)
hour = now.hour
print(f'Berlin Time: {now.strftime(\"%H:%M\")}')
print(f'US Market: {\"OPEN\" if 15 <= hour < 22 else \"CLOSED (opens 15:30)\"}')
print(f'EU Market: {\"OPEN\" if 8 <= hour < 17 else \"CLOSED\"}')
"
```

**Decision matrix (for confidence >= 60%):**

| Current Time (Berlin) | US Stock | EU Stock | Recommendation |
|----------------------|----------|----------|----------------|
| 08:00 - 15:29 | Wait for US Open (15:30) — wider spreads pre-market | Trade now (EU market open) | US: set limit order for 15:30+ / EU: execute now |
| 15:30 - 16:30 | First-Hour Dip opportunity — use pre-open data | EU still open, but watch US spillover | Wait for first-hour dip if pre-open says so |
| 16:30 - 22:00 | Full liquidity, tight spreads | EU closed, TR still trades | Best execution window for US stocks |
| After 22:00 | Market closed, wide spreads | Closed | DO NOT trade — set limit order for tomorrow |

**Output:** "Execute [NOW / AT US OPEN / FIRST-HOUR DIP / TOMORROW]" with reasoning.

## 5. Validation Checklist

| # | Check | Value | Status |
|---|-------|-------|--------|
| 1 | portfolio (DB) checked? | | |
| 2 | yfinance data (not web search)? | | |
| 3 | RSI divergence checked? | | |
| 4 | Stop-loss present? | | |
| 5 | KO = MAX(ATR, Chart)? | | |
| 6 | SHORT evaluated (scorecard)? | | |
| 7 | EUR/USD live? | | |
| 8 | Positions in %? | | |
| 9 | Sector <60%? | | |
| 10 | Analysis recorded in DB? (always!) | | |

## 6. Send via Telegram

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

## 7. Wait for User Confirmation

- Analysis is recorded as `analysis` status
- When user confirms trade → run `open` command
- When user confirms v5 confirmation → run `confirm` command
- Portfolio state auto-updates in DB — no manual file editing

```
[STEP 4 COMPLETE -- ANALYSIS FINISHED]
```
