# Silver Hawk Trading

Personal trading-analysis pipeline for turbo-certs and warrants on Trade
Republic. Five sequential prompts produce a complete trade plan from
market data — entry range, KO, stop staircase, position size, exit
orders — for a 1-3 day horizon.

## Who this is for

Traders who want to build their own LLM-driven analysis system and want a
working reference. The code is opinionated about one thing: the LLM should
reason on raw market data, not on pre-digested aggregates.

This is not a library, not a hosted service, not financial advice. It runs
locally on a personal machine, talks to yfinance and Trade Republic via
pytr, and persists state in a local SQLite file.

## The core idea

Earlier versions of this project had thirteen scripts that pre-processed
market data into ratings, verdicts, and scorecards. The LLM then made
decisions on those aggregates. It worked, but a backtest showed something
uncomfortable: when the LLM read raw OHLCV bars directly, it identified
useful support and resistance levels in 6 of 9 setups. The aggregation
pipeline managed 1 of 9.

The pipeline was rebuilt around that finding. Step 1 collects raw data.
Steps 2 and 3 reason on those bars directly — identifying patterns,
support levels, KO points, conviction asymmetries. Step 4 translates the
underlying-side trade plan into cert-side execution math, which is the
only place determinism is preserved (because cert leverage and position
sizing are arithmetic, not pattern recognition).

The result is shorter, easier to reason about, and measurably better at
the thing the LLM was already good at.

## How it works

When you tell Claude Code "Analysiere SYMBOL", it runs five steps:

```
Step 0  Pre-flight       Date, market hours, symbol validity, hard vetos
Step 1  Data collection  Raw OHLCV (daily + intraday), news, macro
Step 2  Investment debate Bull vs Bear with per-stock conditioning
Step 3  Judge & risk      Direction, trade window, KO, targets, sizing
Step 4  Summary & delivery Cert request → user picks → trading card → exit orders
```

Each step persists its output to `runs/{SYMBOL}_{TIMESTAMP}/`. A single
analysis takes a few minutes and produces a reviewable folder of artifacts.

After the user manually buys the cert in the Trade Republic app and
confirms the fill, `place_exits.py` deploys the stop staircase
(-10% / -17% / -25% from fill price) and target alarms via pytr. Buy
execution stays manual. Stops and alarms go automatic.

## Quick start

Requires Claude Code, Python 3.10+, and a Trade Republic account.

```bash
git clone https://github.com/AbdullahKaratas/NotifyMeClaude.git
cd NotifyMeClaude
pip3 install yfinance numpy pandas pytr python-dotenv
python3 scripts/analysis/preflight_check.py AAPL
claude
> Analysiere AAPL
```

The first run creates `memory/predictions.db` and the `runs/` directory.
Configure pytr separately following the
[pytr documentation](https://github.com/marzzzello/pytr).

## Where to look next

Read in this order:

```
CLAUDE.md                Architecture and behavior rules
prompts/00_master.md     Pipeline index
prompts/00_preflight.md  Step 0
prompts/01_data_collection.md   Step 1 — what raw data the LLM gets
prompts/02_investment_debate.md Step 2 — the reasoning structure
prompts/03_judge_risk.md         Step 3 — trade plan
prompts/04_summary_send.md       Step 4 — execution
```

The prompts are the system. Reading them top to bottom shows the full
shape of an analysis.

## A note on the approach

The hardest part of building this was deleting things. Every script that
came out improved the pipeline. Every "rule" that was code-enforced and
got moved to LLM context made the analyses sharper. The instinct when
something doesn't work is to add validation, scoring, normalization. The
backtest data here suggests the opposite is often true: less plumbing,
more raw data, lets the LLM actually do the work it's good at.

Whether that generalizes beyond support detection is an open question.
The first month of v1.0 live trading is a data collection phase to find
out.

## License

Personal use. Fork and customize.
