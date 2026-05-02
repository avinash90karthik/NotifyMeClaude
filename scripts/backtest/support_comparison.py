#!/usr/bin/env python3
"""Support-detection backtest: A (algorithm) vs. B (LLM raw) vs. A+B (hybrid).

Workflow:

    # Phase 1: generate setups + prompts
    python3 scripts/backtest/support_comparison.py prepare

    # Phase 2: a human (Claude Code, in-conversation) writes answers into
    # results/backtest/answers/<setup_id>_<arch>_<rep>.json — see prompts.

    # Phase 3: score outcomes once all answers exist
    python3 scripts/backtest/support_comparison.py score

Outputs:

    results/backtest/setups.json                         # the 9 setups
    results/backtest/prompts/<setup>_<arch>_<rep>.md     # 36 prompt files
    results/backtest/answers/<setup>_<arch>_<rep>.json   # 36 answer files (filled by Claude Code)
    results/backtest/architecture_A.json                 # algorithm output (deterministic)
    results/backtest/<timestamp>_detail.csv              # per-setup outcomes
    results/backtest/<timestamp>_summary.md              # aggregate metrics
    results/backtest/<timestamp>_findings.md             # narrative + limitations
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from lib.support_levels import parse_support_resistance  # noqa: E402

OUT = REPO / 'results' / 'backtest'
PROMPTS = OUT / 'prompts'
ANSWERS = OUT / 'answers'

SYMBOLS = ['NVDA', 'GOOGL', 'ENR.DE']
SETUPS_PER_SYMBOL = 3   # trend + reversal + range
REPETITIONS = 2
ALGO_RANGE_PCT = 0.005  # ±0.5% range around algorithmic point levels
SEED = 42


# ---------------------------------------------------------------------------
# Setup generation
# ---------------------------------------------------------------------------

def _classify_regime(hist: pd.DataFrame, idx: int) -> str:
    """Crude regime label for the bar at index `idx` based on prior 20 bars.

    - 'trend':    |20d return| > 5% AND realized vol < median
    - 'reversal': last 5 days realized vol > 90th percentile of last 60d
    - 'range':    everything else
    """
    if idx < 60:
        return 'unknown'
    window20 = hist.iloc[idx - 20:idx]
    window5 = hist.iloc[idx - 5:idx]
    window60 = hist.iloc[idx - 60:idx]

    ret20 = float(window20['Close'].iloc[-1] / window20['Close'].iloc[0] - 1)
    vol5 = float(window5['Close'].pct_change().std())
    vol60 = window60['Close'].pct_change().std()
    p90 = float(window60['Close'].pct_change().rolling(5).std().quantile(0.9))

    if vol5 > p90:
        return 'reversal'
    if abs(ret20) > 0.05 and vol5 < float(vol60):
        return 'trend'
    return 'range'


def _pick_setups_for_symbol(symbol: str, rng: random.Random) -> list[dict]:
    """Pick 3 setup days (one per regime) from yfinance daily history.

    Setup day must have >=63 prior daily bars (for indicators) and >=3 future
    bars (for T+1/T+2/T+3 outcome measurement).
    """
    hist = yf.Ticker(symbol).history(period='2y', auto_adjust=True)
    if hist.empty or len(hist) < 100:
        raise RuntimeError(f'{symbol}: insufficient history')

    if hist.index.tz is not None:
        hist.index = hist.index.tz_convert('UTC').tz_localize(None)

    # Eligible window: bars 63..len-4 (need 3 future bars + the setup day itself)
    eligible_idx = list(range(63, len(hist) - 4))
    rng.shuffle(eligible_idx)

    by_regime: dict[str, dict] = {}
    for idx in eligible_idx:
        regime = _classify_regime(hist, idx)
        if regime in ('trend', 'reversal', 'range') and regime not in by_regime:
            setup_day = hist.index[idx]
            prior_close = float(hist['Close'].iloc[idx - 1])  # cutoff = day-before close
            by_regime[regime] = {
                'symbol': symbol,
                'regime': regime,
                'setup_date': setup_day.strftime('%Y-%m-%d'),
                'cutoff_idx': idx - 1,
                'cutoff_close': round(prior_close, 2),
            }
        if len(by_regime) == 3:
            break

    if len(by_regime) < 3:
        raise RuntimeError(f'{symbol}: could not find one setup per regime')

    return list(by_regime.values())


def _format_prior_bars(hist: pd.DataFrame, cutoff_idx: int, n: int = 60) -> str:
    """Format the n daily bars prior to (and including) cutoff_idx as a table."""
    start = max(0, cutoff_idx - n + 1)
    sl = hist.iloc[start:cutoff_idx + 1].copy()
    sl['Volume'] = (sl['Volume'] / 1e6).round(1)
    for col in ('Open', 'High', 'Low', 'Close'):
        sl[col] = sl[col].round(2)
    sl.index = [d.strftime('%Y-%m-%d') for d in sl.index]
    return sl[['Open', 'High', 'Low', 'Close', 'Volume']].to_string()


def _stats_block(hist: pd.DataFrame, cutoff_idx: int) -> str:
    sl = hist.iloc[:cutoff_idx + 1]
    y = sl.tail(252)
    three_m = sl.tail(63)
    sma50 = float(sl['Close'].tail(50).mean())
    sma200 = float(sl['Close'].tail(200).mean()) if len(sl) >= 200 else float('nan')
    return (
        f'52w high: ${y["High"].max():.2f}  on {y["High"].idxmax().strftime("%Y-%m-%d")}\n'
        f'52w low:  ${y["Low"].min():.2f}  on {y["Low"].idxmin().strftime("%Y-%m-%d")}\n'
        f'3m high:  ${three_m["High"].max():.2f}  on {three_m["High"].idxmax().strftime("%Y-%m-%d")}\n'
        f'3m low:   ${three_m["Low"].min():.2f}  on {three_m["Low"].idxmin().strftime("%Y-%m-%d")}\n'
        f'SMA50:    ${sma50:.2f}\n'
        f'SMA200:   ${sma200:.2f}'
    )


def _algorithm_supports(hist: pd.DataFrame, cutoff_idx: int) -> list[dict]:
    """Run lib.support_levels (current branch state) on data up to cutoff."""
    sl = hist.iloc[:cutoff_idx + 1]
    price = float(sl['Close'].iloc[-1])
    supports, _ = parse_support_resistance(sl, price)
    out = []
    for s in supports:
        low = round(s * (1 - ALGO_RANGE_PCT), 2)
        high = round(s * (1 + ALGO_RANGE_PCT), 2)
        out.append({'low': low, 'high': high, 'point': s,
                    'dist_pct': round((s / price - 1) * 100, 2)})
    return out


def _build_prompt_B(setup: dict, bars_table: str, stats: str) -> str:
    return f"""# Support-Level Identification — Architecture B (LLM, raw data)

You are looking at recent price action for one stock. Identify 1-3 support
levels that you'd trust to hold over the next 1-3 trading days.

Stock: {setup['symbol']}
Setup date (cutoff): {setup['setup_date']} (you only see data up to and including the prior close)
Last close (this is "current price"): ${setup['cutoff_close']}

## Last 60 daily bars
date | Open High Low Close Volume[M]

```
{bars_table}
```

## Stats
{stats}

## Your task

Look at the bars carefully. Think about:
- Multiple touches at similar levels (cluster strength)
- Volume confirmation (high-volume reversal days = institutional accumulation)
- Prior resistance that may flip to support
- Round numbers
- SMA50 / SMA200 confluence

Return your answer as JSON only. No prose around it. Schema:

```json
{{
  "supports": [
    {{"low": 199.0, "high": 200.5, "reasoning": "4 touches in late April + 24.04 reversal day with 214M volume"}},
    {{"low": 195.0, "high": 196.5, "reasoning": "..."}}
  ]
}}
```

Each support must be a *range*, not a point. Order from highest-conviction
(closest to price / strongest evidence) to lowest. 1 to 3 supports total.
If you genuinely cannot identify a support level above the 3-month low,
return an empty list.
"""


def _build_prompt_AB(setup: dict, bars_table: str, stats: str, algo: list[dict]) -> str:
    if algo:
        algo_lines = '\n'.join(
            f"  - ${c['point']} (range ${c['low']}-${c['high']}, {c['dist_pct']:+.1f}% from price)"
            for c in algo
        )
    else:
        algo_lines = '  (algorithm returned no supports below current price)'

    return f"""# Support-Level Identification — Architecture A+B (LLM with algorithm candidates)

You are looking at recent price action for one stock. Identify 1-3 support
levels that you'd trust to hold over the next 1-3 trading days.

Stock: {setup['symbol']}
Setup date (cutoff): {setup['setup_date']}
Last close: ${setup['cutoff_close']}

## Algorithm candidates (lib/support_levels.py, simple-swing detection)
{algo_lines}

## Last 60 daily bars
```
{bars_table}
```

## Stats
{stats}

## Your task

You have the algorithm's candidates AS A STARTING POINT. You may:
- Pick from the candidates as-is (if you agree)
- Adjust the range around a candidate (if you think the cluster is wider/narrower)
- Ignore candidates and propose your own levels
- Mix: some from the algorithm, some new

Return your answer as JSON only. No prose. Schema:

```json
{{
  "supports": [
    {{"low": 199.0, "high": 200.5, "reasoning": "...", "source": "algo|llm|merged"}}
  ]
}}
```

Each support is a range. Order highest-conviction first. 1 to 3 supports.
Set "source" to indicate where the level came from.
"""


def cmd_prepare() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PROMPTS.mkdir(parents=True, exist_ok=True)
    ANSWERS.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)

    setups: list[dict] = []
    architecture_a: dict[str, list[dict]] = {}

    for sym in SYMBOLS:
        print(f'Picking setups for {sym}...')
        sym_setups = _pick_setups_for_symbol(sym, rng)
        hist = yf.Ticker(sym).history(period='2y', auto_adjust=True)
        if hist.index.tz is not None:
            hist.index = hist.index.tz_convert('UTC').tz_localize(None)

        for s in sym_setups:
            setup_id = f"{s['symbol']}_{s['setup_date']}_{s['regime']}".replace('.', '-')
            s['setup_id'] = setup_id

            # Architecture A — deterministic
            algo_out = _algorithm_supports(hist, s['cutoff_idx'])
            architecture_a[setup_id] = algo_out

            # Cache the bars + stats so prompts and scoring share one source
            bars_table = _format_prior_bars(hist, s['cutoff_idx'])
            stats = _stats_block(hist, s['cutoff_idx'])

            # Future bars for outcome measurement
            future = hist.iloc[s['cutoff_idx'] + 1:s['cutoff_idx'] + 4][['Open', 'High', 'Low', 'Close']]
            s['future_bars'] = [
                {
                    'date': idx.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                }
                for idx, row in future.iterrows()
            ]
            # ATR-14 at cutoff
            sl = hist.iloc[:s['cutoff_idx'] + 1]
            tr = pd.concat([
                sl['High'] - sl['Low'],
                (sl['High'] - sl['Close'].shift()).abs(),
                (sl['Low'] - sl['Close'].shift()).abs(),
            ], axis=1).max(axis=1)
            s['atr_14'] = round(float(tr.rolling(14).mean().iloc[-1]), 2)

            # Write prompts (one per architecture per repetition)
            for arch, prompt_builder in (('B', _build_prompt_B), ('AB', _build_prompt_AB)):
                for rep in range(1, REPETITIONS + 1):
                    if arch == 'B':
                        text = prompt_builder(s, bars_table, stats)
                    else:
                        text = prompt_builder(s, bars_table, stats, algo_out)
                    fp = PROMPTS / f'{setup_id}_{arch}_rep{rep}.md'
                    fp.write_text(text)

            setups.append(s)

    (OUT / 'setups.json').write_text(json.dumps(setups, indent=2))
    (OUT / 'architecture_A.json').write_text(json.dumps(architecture_a, indent=2))

    n_setups = len(setups)
    n_prompts = n_setups * 2 * REPETITIONS
    print(f'\nWrote {n_setups} setups, {n_prompts} prompts in {PROMPTS}')
    print(f'Answers expected in {ANSWERS}/<setup_id>_<arch>_rep<N>.json')
    print('Each answer file: {{"supports": [{{"low": float, "high": float, "reasoning": str, "source"?: str}}]}}')


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_one_level(level: dict, future_bars: list[dict], atr: float, cutoff: float) -> dict:
    """Return {touched, held, false_fill, r_multiple} for one support level vs the next 3 bars."""
    low = float(level['low'])
    high = float(level['high'])
    mid = (low + high) / 2
    stop = low - atr  # LONG-only test: stop = below range minus 1xATR

    touched = False
    false_fill = False
    held = False
    r_mult = None

    if not future_bars:
        return {'touched': False, 'held': False, 'false_fill': False, 'r_multiple': None}

    # touched: any of T+1..T+3 trades into the range
    for bar in future_bars:
        if bar['low'] <= high and bar['high'] >= low:
            touched = True
        # false_fill: low pierces below (low - 0.5*ATR) at any point AND close is below low
        if bar['low'] < (low - 0.5 * atr):
            # require close also below low to count as a real false-fill
            if bar['close'] < low:
                false_fill = True

    # held: T+1 close is on the right side of the range (>= low for LONG/support)
    t1 = future_bars[0]
    if touched and t1['close'] >= low:
        held = True

    # r_multiple: from entry (mid) to T+3 close, in (mid - stop) units
    if held:
        t3_close = future_bars[-1]['close']
        risk = mid - stop
        if risk > 0:
            r_mult = round((t3_close - mid) / risk, 2)

    return {
        'touched': touched,
        'held': held,
        'false_fill': false_fill,
        'r_multiple': r_mult,
    }


def _consistency_metric(answers_per_arch_setup: dict) -> dict:
    """Compute consistency across repetitions for B and A+B.

    For each setup × architecture, take the mid of the top-1 support across
    all repetitions; report the spread (max-min) as a fraction of the cutoff
    price.
    """
    out = {}
    for (arch, setup_id), reps in answers_per_arch_setup.items():
        if len(reps) < 2:
            continue
        mids = []
        for rep in reps:
            sups = rep.get('supports') or []
            if sups:
                m = (float(sups[0]['low']) + float(sups[0]['high'])) / 2
                mids.append(m)
        if len(mids) >= 2:
            spread = max(mids) - min(mids)
            cutoff = rep['_cutoff']
            out[f'{arch}|{setup_id}'] = round(spread / cutoff * 100, 3)
    return out


def cmd_score() -> None:
    setups = json.loads((OUT / 'setups.json').read_text())
    arch_a = json.loads((OUT / 'architecture_A.json').read_text())

    rows: list[dict] = []
    answers_index: dict[tuple, list[dict]] = {}

    for s in setups:
        sid = s['setup_id']
        future = s['future_bars']
        atr = s['atr_14']
        cutoff = s['cutoff_close']

        # Architecture A — single deterministic answer, no repetitions
        for rank, lvl in enumerate(arch_a.get(sid, []), start=1):
            sc = _score_one_level(lvl, future, atr, cutoff)
            rows.append({
                'setup_id': sid, 'symbol': s['symbol'], 'regime': s['regime'],
                'cutoff_close': cutoff, 'atr_14': atr,
                'arch': 'A', 'rep': 0, 'rank': rank,
                'low': lvl['low'], 'high': lvl['high'],
                'touched': sc['touched'], 'held': sc['held'],
                'false_fill': sc['false_fill'], 'r_multiple': sc['r_multiple'],
                'reasoning': '', 'source': 'algo',
            })

        # Architectures B and AB — read answer files
        for arch in ('B', 'AB'):
            for rep in range(1, REPETITIONS + 1):
                fp = ANSWERS / f'{sid}_{arch}_rep{rep}.json'
                if not fp.exists():
                    print(f'MISSING answer: {fp.name}')
                    continue
                ans = json.loads(fp.read_text())
                ans['_cutoff'] = cutoff
                answers_index.setdefault((arch, sid), []).append(ans)
                for rank, lvl in enumerate(ans.get('supports', []), start=1):
                    sc = _score_one_level(lvl, future, atr, cutoff)
                    rows.append({
                        'setup_id': sid, 'symbol': s['symbol'], 'regime': s['regime'],
                        'cutoff_close': cutoff, 'atr_14': atr,
                        'arch': arch, 'rep': rep, 'rank': rank,
                        'low': lvl['low'], 'high': lvl['high'],
                        'touched': sc['touched'], 'held': sc['held'],
                        'false_fill': sc['false_fill'], 'r_multiple': sc['r_multiple'],
                        'reasoning': lvl.get('reasoning', ''),
                        'source': lvl.get('source', 'llm'),
                    })

    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    detail_path = OUT / f'{ts}_detail.csv'
    fields = ['setup_id', 'symbol', 'regime', 'cutoff_close', 'atr_14', 'arch',
              'rep', 'rank', 'low', 'high', 'touched', 'held', 'false_fill',
              'r_multiple', 'source', 'reasoning']
    with detail_path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Aggregate metrics
    summary_lines = ['# Support-Detection Backtest — Summary',
                     f'\nGenerated: {datetime.now(timezone.utc).isoformat()}',
                     f'\nDetail file: `{detail_path.name}`\n',
                     f'\n## Sample\n',
                     f'- Setups: {len(setups)} ({", ".join(SYMBOLS)} × {SETUPS_PER_SYMBOL} regimes)',
                     f'- Architectures: A (algorithm), B (LLM raw), A+B (LLM + algo candidates)',
                     f'- LLM repetitions per setup: {REPETITIONS}',
                     '\n## Metrics by architecture\n',
                     '| Arch | Levels proposed | Touched | Held | False-fill | Coverage (setups) | Mean R-mult (held) |',
                     '|------|-----------------|---------|------|------------|-------------------|--------------------|']

    for arch in ('A', 'B', 'AB'):
        sub = [r for r in rows if r['arch'] == arch]
        if not sub:
            continue
        n = len(sub)
        touched = sum(1 for r in sub if r['touched'])
        held = sum(1 for r in sub if r['held'])
        ff = sum(1 for r in sub if r['false_fill'])
        # coverage: setups with at least one held level
        held_setups = {r['setup_id'] for r in sub if r['held']}
        total_setups = {r['setup_id'] for r in sub}
        coverage = f'{len(held_setups)}/{len(total_setups)}'
        rmults = [r['r_multiple'] for r in sub if r['r_multiple'] is not None]
        mean_r = f'{np.mean(rmults):+.2f}' if rmults else 'n/a'
        summary_lines.append(
            f'| {arch} | {n} | {touched}/{n} ({touched/n*100:.0f}%) | '
            f'{held}/{n} ({held/n*100:.0f}%) | {ff}/{n} ({ff/n*100:.0f}%) | '
            f'{coverage} | {mean_r} |'
        )

    # Consistency
    cons = _consistency_metric(answers_index)
    if cons:
        summary_lines.append('\n## Consistency (top-1 support mid-spread, % of price)\n')
        summary_lines.append('| Setup × Arch | Spread |')
        summary_lines.append('|--------------|--------|')
        for k, v in sorted(cons.items()):
            summary_lines.append(f'| {k} | {v:.2f}% |')

    summary_path = OUT / f'{ts}_summary.md'
    summary_path.write_text('\n'.join(summary_lines))

    print(f'Wrote {detail_path}')
    print(f'Wrote {summary_path}')
    print(f'\nNext: write the findings markdown by hand based on these numbers.')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prepare', 'score'])
    args = ap.parse_args()
    if args.cmd == 'prepare':
        cmd_prepare()
    else:
        cmd_score()


if __name__ == '__main__':
    main()
