# MULTI-AGENT TRADING ANALYSIS - ORCHESTRATOR

**Asset:** {{SYMBOL}}
**Language:** {{LANGUAGE}} *(Default: English)*

---

## PROCEDURE

You will conduct a complete Multi-Agent Trading Analysis for **{{SYMBOL}}**.

Read and execute the following 4 prompts **sequentially**. Each step builds on the previous ones.

### Step 1: Data Collection
```
Read: prompts/01_data_collection.md
```
- Execute ALL actions (yfinance, chart, news, macro)
- **Output:** Structured data block with price, technicals, chart analysis, news, fundamentals

### Step 2: Investment Debate
```
Read: prompts/02_investment_debate.md
```
- **Input:** Data block + chart from Step 1
- Conduct 2 full debate rounds (Bull vs Bear)
- **Output:** Complete debate transcript

### Step 3: Judge, Risk & Positioning
```
Read: prompts/03_judge_risk.md
```
- **Input:** Data block from Step 1 + debate from Step 2 + chart
- Judge evaluates independently, provides signal + confidence
- 3 Risk Analysts define KO levels (ATR-based!)
- Position matrix: 4 scenarios (Mini/Small/Standard/No Leverage)
- Stop-loss strategy with mental stop above KO
- **Output:** Signal, confidence, 3 KO strategies, position recommendations

### Step 4: Summary & Delivery
```
Read: prompts/04_summary_send.md
```
- **Input:** ALL outputs from previous steps
- Trading card, detailed analysis, JSON output
- Send chart + analysis via Telegram
- **Output:** Telegram message with complete analysis

---

## QUALITY REQUIREMENTS

- **NO step may be skipped**
- **yfinance ALWAYS first** - no web search for price data
- **Chart is analyzed by EVERY agent**
- **Every argument: 4-6 sentences with concrete numbers**
- **Language:** {{LANGUAGE}} (Default: English). All analyses, tables, and text in this language. JSON keys remain in English.
- **If you notice you are cutting corners -> STOP -> Do it properly!**
