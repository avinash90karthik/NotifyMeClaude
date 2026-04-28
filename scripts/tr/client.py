"""Shared pytr client helpers — websocket lifecycle, response drainage,
common subscription patterns. All other tr/* modules build on this.

Why a shared module: pytr's API returns 3-tuples from recv() and requires
manual drainage of websocket messages. Every direct user runs into the
same boilerplate (resume_websession, drain N messages, isinstance checks
on tuple-vs-list). This module centralises that.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from pytr.api import TradeRepublicApi


@asynccontextmanager
async def tr_session():
    """Async context manager: resume websession, yield API, close on exit.

    Usage:
        async with tr_session() as tr:
            await tr.order_overview()
            ...
    """
    tr = TradeRepublicApi(save_cookies=True)
    tr.resume_websession()
    try:
        yield tr
    finally:
        await tr.close()


async def drain_until(
    tr: TradeRepublicApi,
    predicate,
    max_messages: int = 15,
    timeout_per_msg: float = 2.0,
) -> Any | None:
    """Drain recv() messages until `predicate(payload)` returns truthy.
    Returns the matching payload or None on timeout.

    `predicate` receives the dict payload (msg[2]) and should return a
    non-None value to stop draining. That value is returned.
    """
    for _ in range(max_messages):
        try:
            msg = await asyncio.wait_for(tr.recv(), timeout=timeout_per_msg)
        except asyncio.TimeoutError:
            return None
        if isinstance(msg, (tuple, list)) and len(msg) >= 3:
            payload = msg[2]
            result = predicate(payload)
            if result:
                return result
    return None


async def fetch_active_orders(tr: TradeRepublicApi) -> list[dict]:
    """Return all active orders. Drains messages until the orders payload
    arrives (TR sometimes sends partial updates first)."""
    await tr.order_overview()
    last: list[dict] = []
    for _ in range(15):
        try:
            msg = await asyncio.wait_for(tr.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            break
        if isinstance(msg, (tuple, list)) and len(msg) >= 3 and isinstance(msg[2], dict):
            payload = msg[2]
            if "orders" in payload:
                last = [o for o in payload["orders"] if o.get("status") == "active"]
    return last


async def fetch_position(tr: TradeRepublicApi, isin: str) -> dict | None:
    """Return the position dict for one ISIN (or None if not held)."""
    await tr.compact_portfolio()
    for _ in range(10):
        try:
            msg = await asyncio.wait_for(tr.recv(), timeout=3.0)
        except asyncio.TimeoutError:
            break
        if isinstance(msg, (tuple, list)) and len(msg) >= 3 and isinstance(msg[2], dict):
            payload = msg[2]
            if "positions" in payload:
                for pos in payload["positions"]:
                    if pos.get("instrumentId") == isin:
                        return pos
                return None
    return None


async def fetch_quote(
    tr: TradeRepublicApi, isin: str, exchange: str = "TUB"
) -> tuple[float, float] | None:
    """Return (bid, ask) for an instrument on a given exchange.

    Default exchange TUB (HSBC turbo certs). Use 'LSX' for stocks/ETFs,
    'XETR' for German blue-chips."""
    await tr.ticker(isin, exchange=exchange)
    for _ in range(8):
        try:
            msg = await asyncio.wait_for(tr.recv(), timeout=3.0)
        except asyncio.TimeoutError:
            break
        if isinstance(msg, (tuple, list)) and len(msg) >= 3 and isinstance(msg[2], dict):
            payload = msg[2]
            if "bid" in payload and "ask" in payload:
                bid = float(payload["bid"]["price"])
                ask = float(payload["ask"]["price"])
                return bid, ask
    return None


async def fetch_price_alarms(tr: TradeRepublicApi) -> list[dict]:
    """Return all active price alarms across all ISINs."""
    await tr.price_alarm_overview()
    for _ in range(8):
        try:
            msg = await asyncio.wait_for(tr.recv(), timeout=3.0)
        except asyncio.TimeoutError:
            break
        if isinstance(msg, (tuple, list)) and len(msg) >= 3 and isinstance(msg[2], list):
            return msg[2]
    return []


def parse_order_response(msg: Any) -> dict:
    """Extract the response payload from a recv() message. Returns dict
    with keys: order_id (str|None), error (str|None), raw (dict)."""
    out = {"order_id": None, "error": None, "raw": None}
    if not isinstance(msg, (tuple, list)) or len(msg) < 3:
        return out
    payload = msg[2]
    if not isinstance(payload, dict):
        return out
    out["raw"] = payload
    if "orderId" in payload:
        out["order_id"] = payload["orderId"]
    if payload.get("status") == "failed":
        out["error"] = payload.get("message") or payload.get("error", {}).get("message")
    return out
