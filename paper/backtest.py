"""Phase 4 — Backtest loop.

For each trading day in [start, end]:
  1. Build HistoricalMarketView(as_of=day).
  2. For each symbol in the universe: compute frozen_v9_signal(view, sym).
  3. Apply portfolio-level gates (V3 slot cap, V4 sector concentration).
  4. For approved signals, enqueue entry at *next* open (not today's close).
  5. Manage open positions: stop-loss, v8 target, time-stops.
  6. Update daily equity.

Cost model: 0.3% spread + 10 EUR fixed order cost + 0.1% slippage on fill.

The backtest trades the UNDERLYING, not certificates. The v9 rule set
is written around turbo-certs with 8× leverage, so "+20% cert" maps to
"+2.5% underlying" (already computed as TradingSignal.target_20pct by
frozen_v9). Stops map directly to the KO level on the underlying.

Realism of fills:
  - Entry fill price = next-day Open + slippage (buy: +0.1%, sell: -0.1%).
  - Stop-loss: if the next day's Low pierces the stop, fill at stop
    (pessimistic but realistic for a mental stop).
  - Target: if the next day's High pierces the target, fill at target.
  - Same-bar ambiguity: if both stop and target are hit on the same bar,
    assume the stop triggers first (conservative — matches CFA handbook
    treatment of within-bar ambiguity).

Output: CSV file per run (one row per trade) + daily equity CSV.
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd

from paper.historical_view import HistoricalMarketView, _load_ohlcv
from paper.frozen_v9 import frozen_v9_signal, TradingSignal
from paper.universe import UNIVERSE, symbols as universe_symbols, BACKTEST_START, BACKTEST_END


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BacktestConfig:
    start: str = BACKTEST_START
    end: str = BACKTEST_END
    initial_capital: float = 10_000.0

    # Portfolio constraints
    max_open_positions: int = 3           # V3 slot cap
    sector_cap_pct: float = 60.0          # V4 sector concentration

    # Costs
    spread_pct: float = 0.003             # 0.3% round-trip spread
    fixed_order_cost: float = 10.0        # EUR per order (entry + exit = 2)
    slippage_pct: float = 0.001           # 0.1% slippage on fill

    # Time stops (production: on cert P&L; underlying equivalent in %)
    timestop_days_small_profit: int = 3   # 3d without +0.6% underlying → halve
    timestop_threshold_small: float = 0.006
    timestop_days_stagnant: int = 5       # 5d sideways → exit

    # Horizon
    max_hold_days: int = 10               # hard stop — Rule 17: 1-5d horizon,
                                          # give 2x headroom before forced exit

    # If True, restrict universe to bucket or custom list
    universe_override: tuple[str, ...] | None = None


# ---------------------------------------------------------------------------
# Position / Trade
# ---------------------------------------------------------------------------

@dataclass
class OpenPosition:
    symbol: str
    bucket: str
    direction: Literal["LONG", "SHORT"]
    entry_date: pd.Timestamp
    entry_price: float          # fill price on the underlying
    shares: float
    stop_price: float
    target_price: float
    size_eur: float             # gross EUR at entry (pre-costs)
    entry_confidence: float

    # Tracking
    halved: bool = False        # Rule 17 / v7 time-stop: size halved once


@dataclass
class ClosedTrade:
    symbol: str
    bucket: str
    direction: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: float
    pnl_eur: float
    pnl_pct: float
    exit_reason: str
    hold_days: int
    entry_confidence: float
    size_eur_at_entry: float


# ---------------------------------------------------------------------------
# Core backtest
# ---------------------------------------------------------------------------

class Backtest:
    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.cash = self.config.initial_capital
        self.positions: list[OpenPosition] = []
        self.closed: list[ClosedTrade] = []
        self.equity_curve: list[tuple[pd.Timestamp, float]] = []
        self.symbol_bucket = {e.symbol: e.bucket for e in UNIVERSE}
        # Map bucket → rough 'sector' (we keep buckets as-is; commodity &
        # eu_large count as their own sectors for concentration math).
        self.symbol_sector = {e.symbol: e.bucket for e in UNIVERSE}

    # -- equity math --------------------------------------------------------

    def _mark_to_market(self, view: HistoricalMarketView) -> float:
        equity = self.cash
        for p in self.positions:
            px = view.last_close(p.symbol)
            if px is None:
                px = p.entry_price
            if p.direction == "LONG":
                equity += p.shares * px
            else:  # SHORT: pnl = (entry - px) * shares; notional = entry * shares
                equity += p.shares * (2 * p.entry_price - px)
        return equity

    def _sector_exposure(self, equity: float) -> dict[str, float]:
        exposure: dict[str, float] = {}
        for p in self.positions:
            sect = self.symbol_sector.get(p.symbol, "unknown")
            exposure.setdefault(sect, 0.0)
            exposure[sect] += p.size_eur
        return {k: v / equity * 100 if equity > 0 else 0.0 for k, v in exposure.items()}

    def _can_enter(self, signal: TradingSignal, equity: float) -> tuple[bool, str]:
        if len(self.positions) >= self.config.max_open_positions:
            return False, "V3: slot cap"
        # One position per symbol at a time
        if any(p.symbol == signal.symbol for p in self.positions):
            return False, "already open"
        # Sector concentration (after adding this position)
        sect = self.symbol_sector.get(signal.symbol, "unknown")
        current = self._sector_exposure(equity).get(sect, 0.0)
        prospective = current + signal.position_size_pct
        if prospective > self.config.sector_cap_pct:
            return False, f"V4: sector {sect} would be {prospective:.0f}% > {self.config.sector_cap_pct:.0f}%"
        return True, ""

    # -- entries ------------------------------------------------------------

    def _open_position(
        self,
        signal: TradingSignal,
        view: HistoricalMarketView,
        equity: float,
    ) -> str | None:
        """Returns None if opened, else reason for skip."""
        ok, why = self._can_enter(signal, equity)
        if not ok:
            return why

        nxt = view.next_open(signal.symbol)
        if nxt is None:
            return "no next-open bar"
        fill_date, next_open = nxt

        # Slippage on entry (buy LONG: pay higher; sell SHORT: receive lower)
        if signal.direction == "LONG":
            fill_price = next_open * (1 + self.config.slippage_pct + self.config.spread_pct / 2)
        else:
            fill_price = next_open * (1 - self.config.slippage_pct - self.config.spread_pct / 2)

        size_eur = equity * signal.position_size_pct / 100.0
        if size_eur < 100:
            return f"position too small ({size_eur:.2f} EUR)"
        if size_eur > self.cash * 0.95:
            # Don't blow out cash; a real account would margin-trade, but
            # we're cash-only for the paper.
            size_eur = self.cash * 0.95
        shares = size_eur / fill_price
        if shares <= 0 or not math.isfinite(shares):
            return "invalid share count"

        self.cash -= size_eur + self.config.fixed_order_cost

        # Use KO level as the hard stop.
        stop = signal.stop_loss if signal.stop_loss is not None else (
            fill_price * 0.97 if signal.direction == "LONG" else fill_price * 1.03
        )
        # Recompute target relative to the actual fill, not the pre-slippage
        # entry_limit — this keeps the +2.5% target honest on the underlying.
        if signal.direction == "LONG":
            target = fill_price * 1.025
        else:
            target = fill_price * 0.975

        self.positions.append(OpenPosition(
            symbol=signal.symbol,
            bucket=self.symbol_bucket.get(signal.symbol, "unknown"),
            direction=signal.direction,  # type: ignore[arg-type]
            entry_date=fill_date,
            entry_price=fill_price,
            shares=shares,
            stop_price=stop,
            target_price=target,
            size_eur=size_eur,
            entry_confidence=signal.confidence_pct,
        ))
        return None

    # -- exits --------------------------------------------------------------

    def _try_exits_for_bar(self, view: HistoricalMarketView) -> None:
        """Apply stop / target / time-stop rules against today's OHLC for
        every open position. `view.as_of` is today."""
        still_open: list[OpenPosition] = []
        for p in self.positions:
            # The bar we evaluate exits against is today's bar at view.as_of.
            df = view.get_ohlcv(p.symbol)
            if df.empty or p.entry_date >= view.as_of:
                # Position opened this bar → no exit yet
                still_open.append(p)
                continue
            # We need today's bar specifically (view.as_of)
            if view.as_of not in df.index:
                still_open.append(p)
                continue
            bar = df.loc[view.as_of]
            high = float(bar["High"])
            low = float(bar["Low"])
            close = float(bar["Close"])

            hit_stop = False
            hit_target = False
            exit_px = None
            if p.direction == "LONG":
                if low <= p.stop_price:
                    hit_stop = True
                    exit_px = p.stop_price
                elif high >= p.target_price:
                    hit_target = True
                    exit_px = p.target_price
            else:  # SHORT
                if high >= p.stop_price:
                    hit_stop = True
                    exit_px = p.stop_price
                elif low <= p.target_price:
                    hit_target = True
                    exit_px = p.target_price

            hold_days = int((view.as_of - p.entry_date).days)

            # Time stops (only if still open after SL/TP checks)
            time_exit_reason: str | None = None
            if not hit_stop and not hit_target:
                # Compute open P&L on underlying today
                if p.direction == "LONG":
                    pnl_pct = (close - p.entry_price) / p.entry_price
                else:
                    pnl_pct = (p.entry_price - close) / p.entry_price
                if hold_days >= self.config.max_hold_days:
                    time_exit_reason = f"max_hold_{hold_days}d"
                    exit_px = close
                elif (
                    hold_days >= self.config.timestop_days_stagnant
                    and abs(pnl_pct) < self.config.timestop_threshold_small
                ):
                    time_exit_reason = f"stagnant_{hold_days}d"
                    exit_px = close
                elif (
                    hold_days >= self.config.timestop_days_small_profit
                    and pnl_pct < self.config.timestop_threshold_small
                    and not p.halved
                ):
                    # Halve the position (v7 rule). Realise P&L on half.
                    half_shares = p.shares / 2
                    fill = close * (1 - self.config.slippage_pct - self.config.spread_pct / 2) \
                        if p.direction == "LONG" else \
                        close * (1 + self.config.slippage_pct + self.config.spread_pct / 2)
                    if p.direction == "LONG":
                        realised = half_shares * fill
                    else:
                        realised = half_shares * (2 * p.entry_price - fill)
                    self.cash += realised - self.config.fixed_order_cost
                    # Pro-rata the recorded trade (leave the halved flag so we
                    # don't halve again)
                    pnl_eur = (fill - p.entry_price) * half_shares if p.direction == "LONG" \
                        else (p.entry_price - fill) * half_shares
                    self.closed.append(ClosedTrade(
                        symbol=p.symbol, bucket=p.bucket, direction=p.direction,
                        entry_date=str(p.entry_date.date()),
                        exit_date=str(view.as_of.date()),
                        entry_price=round(p.entry_price, 4),
                        exit_price=round(fill, 4),
                        shares=round(half_shares, 4),
                        pnl_eur=round(pnl_eur, 2),
                        pnl_pct=round(pnl_eur / (p.entry_price * half_shares) * 100, 3),
                        exit_reason="halve_timestop",
                        hold_days=hold_days,
                        entry_confidence=p.entry_confidence,
                        size_eur_at_entry=round(p.size_eur, 2),
                    ))
                    # Update remaining position
                    p.shares = p.shares - half_shares
                    p.size_eur = p.size_eur / 2
                    p.halved = True

            if hit_stop or hit_target or time_exit_reason:
                reason = "stop" if hit_stop else ("target" if hit_target else time_exit_reason)
                # Slippage on exit
                if p.direction == "LONG":
                    fill = exit_px * (1 - self.config.slippage_pct - self.config.spread_pct / 2)
                    gross = p.shares * fill
                    pnl_eur = gross - p.size_eur - self.config.fixed_order_cost
                else:
                    fill = exit_px * (1 + self.config.slippage_pct + self.config.spread_pct / 2)
                    gross = p.shares * (2 * p.entry_price - fill)
                    pnl_eur = gross - p.size_eur - self.config.fixed_order_cost
                self.cash += gross - self.config.fixed_order_cost
                self.closed.append(ClosedTrade(
                    symbol=p.symbol, bucket=p.bucket, direction=p.direction,
                    entry_date=str(p.entry_date.date()),
                    exit_date=str(view.as_of.date()),
                    entry_price=round(p.entry_price, 4),
                    exit_price=round(fill, 4),
                    shares=round(p.shares, 4),
                    pnl_eur=round(pnl_eur, 2),
                    pnl_pct=round(pnl_eur / p.size_eur * 100, 3),
                    exit_reason=reason,  # type: ignore[arg-type]
                    hold_days=hold_days,
                    entry_confidence=p.entry_confidence,
                    size_eur_at_entry=round(p.size_eur, 2),
                ))
            else:
                still_open.append(p)
        self.positions = still_open

    # -- main loop ---------------------------------------------------------

    def _trading_days(self) -> pd.DatetimeIndex:
        """Union of all trading days across the universe within the window."""
        syms = self.config.universe_override or tuple(universe_symbols())
        union = pd.DatetimeIndex([])
        for s in syms:
            try:
                df = _load_ohlcv(s)
            except Exception:
                continue
            mask = (df.index >= pd.Timestamp(self.config.start)) & (
                df.index <= pd.Timestamp(self.config.end))
            union = union.union(df.loc[mask].index)
        return union.sort_values()

    def run(self, verbose: bool = False) -> "BacktestResult":
        syms = self.config.universe_override or tuple(universe_symbols())
        days = self._trading_days()
        if len(days) == 0:
            raise RuntimeError("no trading days in window — check Phase 1 cache")

        for i, day in enumerate(days):
            view = HistoricalMarketView(day)

            # 1. Apply exits on today's OHLC FIRST (this uses today's bar).
            self._try_exits_for_bar(view)

            # 2. Compute signals on today's close.
            equity = self._mark_to_market(view)
            if equity <= 0:
                if verbose:
                    print(f"{day.date()}: account blown out, stopping")
                self.equity_curve.append((day, equity))
                break

            # 3. For each symbol, check approved signal; entries fill at next open.
            for sym in syms:
                try:
                    sig = frozen_v9_signal(view, sym)
                except Exception as e:
                    if verbose:
                        print(f"  {day.date()} {sym}: signal error {e}")
                    continue
                if sig is None or not sig.approved:
                    continue
                skip_reason = self._open_position(sig, view, equity)
                if skip_reason and verbose:
                    print(f"  {day.date()} {sym} {sig.direction} conf={sig.confidence_pct:.0f}%: skipped — {skip_reason}")

            # 4. Mark-to-market for the daily equity curve.
            equity = self._mark_to_market(view)
            self.equity_curve.append((day, equity))
            if verbose and i % 250 == 0:
                print(f"  {day.date()} equity={equity:,.0f} open={len(self.positions)} closed={len(self.closed)}")

        return BacktestResult(
            config=self.config,
            equity_curve=pd.DataFrame(self.equity_curve, columns=["date", "equity"]),
            trades=pd.DataFrame([asdict(t) for t in self.closed]),
            final_open_positions=len(self.positions),
        )


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    config: BacktestConfig
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    final_open_positions: int

    def summary(self) -> dict:
        eq = self.equity_curve
        if eq.empty:
            return {"final_equity": 0, "n_trades": 0}
        start_eq = self.config.initial_capital
        final_eq = float(eq["equity"].iloc[-1])
        total_return = (final_eq / start_eq - 1) * 100
        daily_ret = eq["equity"].pct_change().dropna()
        sharpe = None
        if len(daily_ret) > 30 and daily_ret.std() > 0:
            sharpe = float(daily_ret.mean() / daily_ret.std() * np.sqrt(252))
        peak = eq["equity"].cummax()
        dd = (eq["equity"] / peak - 1) * 100
        max_dd = float(dd.min())
        trades = self.trades
        win_rate = None
        avg_hold = None
        if not trades.empty:
            wins = (trades["pnl_eur"] > 0).sum()
            win_rate = float(wins / len(trades) * 100)
            avg_hold = float(trades["hold_days"].mean())
        return {
            "start_equity": start_eq,
            "final_equity": round(final_eq, 2),
            "total_return_pct": round(total_return, 2),
            "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
            "max_drawdown_pct": round(max_dd, 2),
            "n_trades": len(trades),
            "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
            "avg_hold_days": round(avg_hold, 2) if avg_hold is not None else None,
            "final_open_positions": self.final_open_positions,
        }

    def write_csvs(self, out_dir: str | Path) -> None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.equity_curve.to_csv(out / "equity_curve.csv", index=False)
        self.trades.to_csv(out / "trades.csv", index=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=BACKTEST_START)
    parser.add_argument("--end", default=BACKTEST_END)
    parser.add_argument("--capital", type=float, default=10_000.0)
    parser.add_argument("--out", default="paper/results/phase4_frozen_v9",
                        help="output directory")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--universe", default=None,
                        help="Comma-separated symbol list; default = full universe")
    args = parser.parse_args()

    uni = tuple(args.universe.split(",")) if args.universe else None
    cfg = BacktestConfig(
        start=args.start, end=args.end, initial_capital=args.capital,
        universe_override=uni,
    )
    bt = Backtest(cfg)
    print(f"Running backtest {args.start} → {args.end} "
          f"(universe={'all 25' if uni is None else len(uni)})")
    result = bt.run(verbose=args.verbose)
    print("\n--- Summary ---")
    for k, v in result.summary().items():
        print(f"  {k:24s} {v}")
    result.write_csvs(args.out)
    print(f"\nWrote CSVs to {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
