#!/usr/bin/env python3
"""Step 1.4 — render a simple chart for the LLM and the user.

60 daily bars (OHLC candle-line + volume subplot). No SMA overlays, no
annotations, no indicator overlays. The LLM reads the bars from
OHLCV_DAILY in step1_data.md; this PNG is the visual companion that
goes to the user via iMessage and gets attached to the LLM prompt.

Output path:
    runs/{SYMBOL}_{YYYYMMDD}_{HHMMSS}/step1_chart.png

If --run-id is omitted, a fresh ID is generated and printed so the
caller knows which folder to read from. If --no-imessage is set, the
script skips the osascript send.

Usage:
    python3 scripts/analysis/render_chart.py NVDA
    python3 scripts/analysis/render_chart.py NVDA --run-id NVDA_20260502_191500
    python3 scripts/analysis/render_chart.py NVDA --no-imessage
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use('Agg')  # headless
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = REPO / 'runs'

# Load .env (gitignored) so locally-configured values like
# IMESSAGE_RECIPIENT are picked up without needing a wrapping shell.
try:
    from dotenv import load_dotenv
    load_dotenv(REPO / '.env')
except ImportError:
    pass

# Recipient for the iMessage chart drop. Set IMESSAGE_RECIPIENT in .env
# (gitignored). If unset, the iMessage send is skipped.
IMESSAGE_RECIPIENT = os.environ.get('IMESSAGE_RECIPIENT')


def make_run_id(symbol: str) -> str:
    cet = ZoneInfo('Europe/Berlin')
    return f'{symbol}_{datetime.now(cet).strftime("%Y%m%d_%H%M%S")}'


def fetch_bars(symbol: str, n: int = 60) -> pd.DataFrame:
    t = yf.Ticker(symbol)
    hist = t.history(period='6mo', auto_adjust=False)
    if hist.empty:
        raise RuntimeError(f'No daily history for {symbol}')
    return hist.tail(n)


def render(symbol: str, df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1, figsize=(12, 7),
        gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.05},
        sharex=True,
    )

    dates = df.index
    opens = df['Open'].values.astype(float)
    highs = df['High'].values.astype(float)
    lows = df['Low'].values.astype(float)
    closes = df['Close'].values.astype(float)
    volumes = df['Volume'].fillna(0).values.astype(float)

    # OHLC bars: vertical line for high-low, small horizontal ticks for open/close
    width_open = 0.25  # business days
    for i, d in enumerate(dates):
        x = mdates.date2num(d)
        color = '#2e7d32' if closes[i] >= opens[i] else '#c62828'
        ax_price.vlines(x, lows[i], highs[i], color=color, linewidth=0.9)
        ax_price.hlines(opens[i], x - width_open, x, color=color, linewidth=0.9)
        ax_price.hlines(closes[i], x, x + width_open, color=color, linewidth=0.9)

    # Volume subplot
    bar_colors = ['#2e7d32' if c >= o else '#c62828' for o, c in zip(opens, closes)]
    ax_vol.bar(dates, volumes, color=bar_colors, width=0.7, edgecolor='none')

    ax_price.set_title(
        f'{symbol} — last {len(df)} daily bars '
        f'(through {dates[-1].strftime("%Y-%m-%d")})',
        fontsize=11,
    )
    ax_price.grid(True, axis='y', alpha=0.3, linestyle=':')
    ax_price.set_ylabel('Price')
    ax_vol.set_ylabel('Volume')
    ax_vol.grid(True, axis='y', alpha=0.3, linestyle=':')

    # x-axis formatting: monthly ticks
    ax_vol.xaxis.set_major_locator(mdates.MonthLocator())
    ax_vol.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate(rotation=0, ha='center')

    fig.tight_layout()
    fig.savefig(out_path, dpi=130, facecolor='white')
    plt.close(fig)


def send_imessage(path: Path, symbol: str) -> None:
    """Send the PNG via osascript to the configured iMessage recipient.

    Best-effort — failures are warned about but don't break the pipeline.
    """
    if not IMESSAGE_RECIPIENT:
        print('  imessage skipped — IMESSAGE_RECIPIENT not set in .env', file=sys.stderr)
        return
    if not shutil.which('osascript'):
        print('  imessage skipped — osascript not available', file=sys.stderr)
        return
    posix = str(path.resolve())
    script = f'''
    tell application "Messages"
        set targetService to id of 1st service whose service type = iMessage
        set targetBuddy to buddy "{IMESSAGE_RECIPIENT}" of service id targetService
        set theFile to POSIX file "{posix}"
        send theFile to targetBuddy
        send "Step 1 chart — {symbol}" to targetBuddy
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
        print(f'  imessage sent to {IMESSAGE_RECIPIENT}')
    except subprocess.CalledProcessError as e:
        print(f'  imessage failed: {e.stderr.decode().strip()}', file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description='Step 1.4 chart renderer')
    p.add_argument('symbol')
    p.add_argument('--run-id', default=None,
                   help='Existing run folder ID; if omitted, a new one is created')
    p.add_argument('--bars', type=int, default=60, help='Number of daily bars (default 60)')
    p.add_argument('--no-imessage', action='store_true', help='Skip the iMessage send')
    args = p.parse_args()

    symbol = args.symbol.upper()
    run_id = args.run_id or make_run_id(symbol)
    out_path = RUNS_DIR / run_id / 'step1_chart.png'

    df = fetch_bars(symbol, n=args.bars)
    render(symbol, df, out_path)
    first = df.index[0].strftime('%Y-%m-%d')
    last = df.index[-1].strftime('%Y-%m-%d')
    print(f'CHART_PNG:   {out_path}')
    print(f'RUN_ID:      {run_id}')
    print(f'DATE_RANGE:  {first} to {last}')
    print(f'BAR_COUNT:   {len(df)}')

    if not args.no_imessage:
        send_imessage(out_path, symbol)

    return 0


if __name__ == '__main__':
    sys.exit(main())
