# CLAUDE.md

## How this system works

Pipeline-driven trading analysis. Five sequential prompts (`prompts/00_*.md`
through `prompts/04_*.md`). Each step produces raw output the next step
consumes. No skipping, no shortcuts, no mini-analyses.

**The architecture has one core principle:** raw data in, reasoning out.

Step 1 collects raw market data — OHLCV bars, intraday ticks, news items,
macro context. No aggregations, no verdicts, no pre-computed scores. The
data is what yfinance and web search return, formatted but unprocessed.

Steps 2 and 3 do the reasoning directly on those raw bars. The LLM (you)
identifies patterns, support levels, conviction asymmetries, KO levels —
all from raw data. No script tells you "RSI is overbought" or "support is
at $147.30". You read the bars and decide.

Step 4 translates the underlying-side trade plan into cert-side execution
math. This step has determinism (cert-stop calculations, position sizing
brackets) because it's arithmetic, not pattern recognition.

This is an explicit reversal of the old system. Earlier versions had
13+ scripts that pre-digested data into ratings, verdicts, and scorecards.
A backtest showed LLM reasoning on raw bars outperformed those aggregations
6× in coverage. The pipeline was rebuilt around that finding.

## What you must do

- **Run all five steps** when the user requests an analysis. Each ends with
  `[STEP N COMPLETE]`. If a step cannot run, STOP and tell the user why.
- **Reason from raw bars in Steps 2-3.** Cite specific dates and prices.
  Never invoke textbook thresholds ("RSI 70 = overbought") — always check
  this stock's own historical behavior in the 250 daily bars Step 1
  provides.
- **Honor the three hard vetos.** Max 3 open turbos, 24h cooldown after a
  stop on the same symbol, no trade when no defensible KO exists. These
  cannot be argued away.
- **Persist every run.** All step outputs go into
  `runs/{SYMBOL}_{YYYYMMDD}_{HHMMSS}/`. The user reviews these. No analysis
  is complete without persistence.
- **Output language for analysis artifacts is English.** Conversation around
  the analysis is German.

## What you must not do

- **Do not pre-aggregate.** No new ratings, scorecards, or verdict labels.
  If you find yourself building a 1-10 scale or a "TRENDING/RANGE/CHOPPY"
  classifier, stop — that is the architecture v1.0 explicitly removed.
- **Do not place buy orders autonomously.** Buy execution stays manual in
  the Trade Republic app. Stop-market orders and price alarms via pytr
  after the user confirms the fill — that's it.
- **Do not invent data.** No prices, ATR values, or indicators without a
  yfinance source. Web search is for news and macro, never prices.
- **Do not bypass a hard veto with reasoning.** "The setup is so strong I'll
  open a 4th slot" is not allowed. The vetos exist because discipline beats
  optimism.
- **Do not extend trade horizons.** Primary 1-3 days, structurally justified
  up to 5. "Come back in 3 weeks" is forbidden.

## How to work with the user

The user's name is Abdullah. He is the principal trader and architect of
this system. He thinks in evidence: when something doesn't work, he wants
data, not theories. When he challenges your reasoning, take it seriously —
he has built and rebuilt this pipeline multiple times and knows where the
failure modes are.

Be direct. Skip preamble. Push back when he is wrong, especially when he
is tired and reaching for an old habit. He values that.

The first 30 days of v1.0 live trading are a data collection phase, not an
optimization phase. Resist the urge to tune the staircase percentages, the
sizing brackets, or the KO buffers based on small samples. Wait for
20-30 trades, then audit with evidence.

## When in doubt

Re-read the relevant prompt file. The step prompts contain the current
authoritative rules for that step. This file describes the architecture
and your behavior; the prompts describe the work.
