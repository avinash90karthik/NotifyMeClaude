# STEP 4: SUMMARY & DELIVERY

**Asset:** {{SYMBOL}}

---

**Input:** ALL outputs from the previous steps (Data, Debate, Judge, Risk)
Reference the JSON blocks from Steps 1, 2, and 3 for structured data points.

---

## TRADING CARD

```
╔══════════════════════════════════════════════════════╗
║  {{SYMBOL}} ANALYSIS                                 ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  Price:      $XX.XX (EUR XX.XX)                      ║
║  Signal:     [LONG / SHORT / HOLD]                   ║
║  Confidence: XX%                                     ║
║  ATR:        X.X% ($XX.XX/day)                       ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  KO LEVEL (ATR + Chart combined)                     ║
╠══════════════════════════════════════════════════════╣
║  ATR-based:   $XX.XX (Xx ATR, asset class: XXX)      ║
║  Chart-based: $XX.XX (below support $XX.XX)          ║
║  → FINAL KO:  $XX.XX (XX.X% distance)               ║
║  → Leverage:  ~Xx                                    ║
║  Stop-Loss:   $XX.XX (mental, above KO)              ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  POSITION RECOMMENDATION (% of portfolio)            ║
╠══════════════════════════════════════════════════════╣
║  Lotto (5%):        XXX EUR - [Product + KO]         ║
║  Small (15%):       XXX EUR - [Product + KO]         ║
║  Standard (30%):    XXX EUR - [Product + KO]         ║
║  No Leverage (20%): XXX EUR - [ETF/ETC/Stock]        ║
║                                                      ║
║  Max. loss at stop: XXX EUR (XX% portfolio)          ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  EXITS (staged)                                      ║
╠══════════════════════════════════════════════════════╣
║  Sell 1: $XX.XX (XX%) - [Rationale]                  ║
║  Sell 2: $XX.XX (XX%) - [Rationale]                  ║
║  Sell 3: $XX.XX (Rest) - [Stretch target]            ║
║  Time-Stop: X days without movement → cut in half    ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  ENTRY TIMING (data-driven!)                         ║
╠══════════════════════════════════════════════════════╣
║  Best Entry: [PRE-MARKET/FIRST-HOUR DIP/AT OPEN]    ║
║  Pre-Market Win:    XX% | First-Hour: XX% | Open: XX%║
║  Current Gap:       +X.X%                            ║
║  → [Concrete recommendation with time]              ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  SUPPORT              │  RESISTANCE                  ║
╠══════════════════════════════════════════════════════╣
║  S1: $XX.XX           │  R1: $XX.XX                  ║
║  S2: $XX.XX           │  R2: $XX.XX                  ║
║  S3: $XX.XX           │  R3: $XX.XX                  ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  RISK CHECK                                          ║
╠══════════════════════════════════════════════════════╣
║  Sector concentration: XX% [Sector]  [✅/⚠️]       ║
║  Open positions same direction: X  [✅/⚠️]         ║
║  Next event: [Event] on [Date]  [✅/⚠️]            ║
║  Risk budget used: XX%  [✅/⚠️]                     ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  TIME HORIZONS                                       ║
╠══════════════════════════════════════════════════════╣
║  Short-term:  [LONG/SHORT/HOLD]                      ║
║  Medium-term: [LONG/SHORT/HOLD]                      ║
║  Long-term:   [LONG/SHORT/HOLD]                      ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## DETAILED ANALYSIS ({{LANGUAGE}}, 500-800 words)

**MANDATORY! Minimum 500 words!**

Write a complete analysis with the following structure:

**1. INTRODUCTION (50-100 words)**
- Current context: What is happening with the asset right now?
- Why is now an important time for an analysis?

**2. TECHNICAL SITUATION (100-150 words)**
- Describe the current chart state
- Key levels and what they mean
- Trend strength and direction
- **Mention RSI delta and divergence findings!**
- **Reference your chart observations!**

**3. FUNDAMENTAL FACTORS (100-150 words)**
- What drives the asset fundamentally?
- Supply/demand situation
- Relevant macro factors

**4. NEWS & CATALYSTS (100-150 words)**
- The most important current news
- Upcoming events that could move the price
- Sentiment assessment

**5. RISKS (50-100 words)**
- What could go wrong?
- What would invalidate the thesis?
- **Correlation risk to existing positions!**

**6. CONCLUSION & ACTION RECOMMENDATION (100-150 words)**
- Clear recommendation: What should the trader do?
- Entry strategy
- Risk management (max. loss in EUR and % of portfolio)
- Time horizon
- **Take profits!** Follow staged exits!

---

---

---

## VALIDATION BEFORE DELIVERY (MANDATORY!)

Check EVERY point before sending. If any ❌ → STOP and correct!

| # | Check | Criterion |
|---|-------|-----------|
| 1 | Portfolio read? | portfolio.md read |
| 2 | yfinance data? | Price, ATR, RSI from yfinance (not web search) |
| 3 | RSI divergence checked? | Delta, slope and divergence check performed |
| 4 | Stop-loss present? | Every trade has a stop (mental or TR) |
| 5 | KO calculated? | KO = MAX(ATR-based, Chart-based), not estimated |
| 6 | SHORT evaluated? | Scorecard filled out, SHORT setup if score >= LONG |
| 7 | Exchange rate live? | EUR/USD from yfinance, not hardcoded |
| 8 | Positions in %? | Recommendations in % of portfolio, not fixed EUR |
| 9 | Correlation OK? | Sector concentration < 60% after this trade |
| 10 | Risk budget OK? | Max. 10% loss per trade, 40% total |

Show the checklist in the output:
✅ or ❌ per item, with concrete value.

---

## TELEGRAM DELIVERY (MANDATORY!)

**Send the Trading Card as a Telegram message:**

```bash
source .env
python send_telegram.py "$(cat <<'EOF'
🎯 {{SYMBOL}} ANALYSIS

Signal: [LONG/SHORT/HOLD] | Confidence: XX%
Price: $XX.XX | KO: $XX.XX (XX.X%)
Stop: $XX.XX | Leverage: ~Xx

Exits: $XX.XX (XX%) → $XX.XX (XX%) → $XX.XX (Rest)
Time-Stop: X days

⚠️ Risk: Max. XXX EUR (XX% portfolio)
📊 Sector conc.: XX% [Sector]
📈 RSI divergence: [Bullish/Bearish/None]
EOF
)"
```

**Send chart as photo (if available):**
```bash
source .env 2>/dev/null
CHART_FILE="${CHART_OUTPUT_DIR:-charts}/{{SYMBOL}}_chart.png"
if [ -f "$CHART_FILE" ]; then
  python -c "
from send_telegram import send_photo
send_photo('$CHART_FILE', '📊 {{SYMBOL}} Chart')
"
else
  echo "No chart available — skipped"
fi
```

---

## UPDATE PORTFOLIO.MD (MANDATORY!)

After EVERY analysis: update `memory/portfolio.md`.
This is the Single Source of Truth for the portfolio state.

- New position? → Add to "Open Positions"
- Position closed? → Move to "Closed Trades" + P&L
- Recalculate sector distribution
- Update upcoming events
- Update last modification date

---

## ENFORCEMENT

- ✅ Trading Card with all key facts incl. KO method and risk check
- ✅ Position recommendation in % of portfolio (not fixed EUR amounts)
- ✅ Minimum 500 words in the analysis
- ✅ **RSI divergence mentioned in analysis and Telegram**
- ✅ Send chart via Telegram (if available)
- ✅ Send Telegram message with Trading Card (MANDATORY!)
- ✅ Send chart as Telegram photo (if available)
- ✅ Update portfolio.md (MANDATORY!)

```
✅ [STEP 4: SUMMARY & DELIVERY COMPLETED]
🏁 [ANALYSIS COMPLETE]
```
