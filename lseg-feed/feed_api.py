#!/usr/bin/env python3
"""Private, read-only REST API for LSEG delayed pricing streams.

A single background thread owns the authenticated LSEG session and its stream.
HTTP handlers only read a thread-safe in-memory copy of the latest snapshot.
No LSEG credentials or trade/order functionality are exposed over HTTP.
"""

from __future__ import annotations

import logging
import math
import os
import re
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
import uvicorn

LOG = logging.getLogger("lseg_feed")
FIELDS = ["TRDPRC_1", "BID", "ASK", "TRDTIM_1"]
DEFAULT_SYMBOLS = "AAPL=/AAPL.O,MSFT=/MSFT.O,NVDA=/NVDA.O"
EASTERN = ZoneInfo("America/New_York")


@lru_cache(maxsize=1)
def nyse_calendar():
    """Exchange calendar includes NYSE holidays, DST, and early closes."""
    import exchange_calendars as xcals
    return xcals.get_calendar("XNYS")


def market_window(now: datetime | None = None, *, post_close_minutes: int = 20) -> dict:
    """Return the US regular-session streaming window (open through close+delay).

    This is a NYSE calendar, not a clock-based weekday approximation. Quotes
    from the delayed feed can arrive after the cash-session close.
    """
    if post_close_minutes < 0:
        raise ValueError("post_close_minutes must be nonnegative")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today_et = now.astimezone(EASTERN).date()
    cal = nyse_calendar()
    sessions = cal.sessions_in_range(today_et, today_et + timedelta(days=14))
    for label in sessions:
        market_open = cal.session_open(label).to_pydatetime()
        market_close = cal.session_close(label).to_pydatetime()
        end = market_close + timedelta(minutes=post_close_minutes)
        if now < market_open:
            return {
                "active": False, "regular_session_open": False,
                "stream_until": None, "market_close": None,
                "next_market_open": market_open.isoformat(),
                "wait_seconds": max(0.0, (market_open - now).total_seconds()),
            }
        if now < end:
            return {
                "active": True, "regular_session_open": now < market_close,
                "stream_until": end, "market_close": market_close.isoformat(),
                "next_market_open": market_open.isoformat(),
                "wait_seconds": 0.0,
            }
    raise RuntimeError("NYSE calendar does not contain an upcoming market session")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_symbols(spec: str) -> dict[str, str]:
    """Comma-separated TICKER=/DELAYED.RIC mappings; explicit RICs avoid .O/.N errors."""
    result: dict[str, str] = {}
    for part in spec.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"Expected TICKER=/RIC, got: {part!r}")
        symbol, ric = (item.strip() for item in part.split("=", 1))
        symbol = symbol.upper()
        if not re.fullmatch(r"[A-Z0-9.^_-]{1,32}", symbol):
            raise ValueError(f"Invalid ticker symbol: {symbol!r}")
        if not ric.startswith("/") or len(ric) == 1 or any(ch.isspace() for ch in ric):
            raise ValueError(f"Expected a delayed RIC beginning with '/': {ric!r}")
        if symbol in result or ric in result.values():
            raise ValueError(f"Duplicate ticker or RIC: {part!r}")
        result[symbol] = ric
    if not result:
        raise ValueError("LSEG_SYMBOLS is empty")
    return result


def clean_number(value: Any) -> float | None:
    """Normalize NumPy/pandas numeric fields and missing values for JSON."""
    try:
        if value is None or isinstance(value, bool):
            return None
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


class PriceStore:
    def __init__(self, symbols: dict[str, str]):
        self.symbols = symbols
        self.ric_to_symbol = {v: k for k, v in symbols.items()}
        self.lock = threading.Lock()
        self.quotes: dict[str, dict] = {}
        self.statuses: dict[str, dict] = {}
        self.last_events: dict[str, str] = {}
        self.last_snapshot_at: str | None = None
        self.last_snapshot_monotonic: float | None = None
        self.connected = False
        self.connection_state = "starting"
        self.market_open = False  # True only during the regular NYSE session.
        self.feed_window_open = False  # Includes post-close delayed-data buffer.
        self.next_market_open: str | None = None
        self.market_close: str | None = None

    def set_connection(self, connected: bool, status: str):
        with self.lock:
            self.connected = connected
            self.connection_state = status

    def set_market_window(self, window: dict):
        with self.lock:
            self.market_open = window["regular_session_open"]
            self.feed_window_open = window["active"]
            self.next_market_open = window["next_market_open"]
            self.market_close = window["market_close"]

    def replace_symbols(self, mapping: dict[str, str]):
        """Switch ticker universe without keeping quotes for old contracts."""
        if not mapping:
            raise ValueError("No LSEG RICs resolved")
        with self.lock:
            self.quotes = {sym: q for sym, q in self.quotes.items()
                           if mapping.get(sym) == q.get("ric")}
            self.statuses = {ric: s for ric, s in self.statuses.items()
                             if ric in mapping.values()}
            self.last_events = {ric: t for ric, t in self.last_events.items()
                                if ric in mapping.values()}
            self.symbols = mapping.copy()
            self.ric_to_symbol = {ric: sym for sym, ric in mapping.items()}

    def on_event(self, fields: Any, ric: str, stream: Any):
        if ric in self.ric_to_symbol:
            with self.lock:
                self.last_events[ric] = utc_now()
                self.statuses.pop(ric, None)

    def on_status(self, event: dict, ric: str, stream: Any):
        state = event.get("State", {}) if isinstance(event, dict) else {}
        code = state.get("Code", "unknown")
        stream_state = state.get("Stream", "unknown")
        text = str(state.get("Text", ""))[:200]
        LOG.warning("RIC %s: %s (%s): %s", ric, code, stream_state, text)
        with self.lock:
            self.statuses[ric] = {"code": code, "stream": stream_state, "message": text}
            if stream_state.lower() == "closed":
                self.last_events.pop(ric, None)

    @staticmethod
    def on_error(event: Any, stream: Any):
        LOG.error("LSEG stream callback error: %s", type(event).__name__)

    def publish(self, frame: Any):
        """Read cached pandas DataFrame; do not confuse snapshot time with exchange quote time."""
        now = utc_now()
        if frame is None or getattr(frame, "empty", True):
            return  # Do not present an empty poll as a fresh successful snapshot.
        try:
            rows = frame.to_dict(orient="records")
        except Exception as exc:
            raise RuntimeError("Unexpected LSEG get_snapshot() response") from exc

        updated: dict[str, dict] = {}
        for row in rows:
            ric = str(row.get("Instrument", ""))
            symbol = self.ric_to_symbol.get(ric)
            if not symbol:
                continue
            last = clean_number(row.get("TRDPRC_1"))
            bid = clean_number(row.get("BID"))
            ask = clean_number(row.get("ASK"))
            if last is None and bid is None and ask is None:
                continue
            mid = (bid + ask) / 2 if bid is not None and ask is not None and bid > 0 and ask > 0 else None
            trade_time = row.get("TRDTIM_1")
            updated[symbol] = {
                "symbol": symbol,
                "ric": ric,
                "price": last,  # last trade, not bid/ask midpoint
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "trade_time": None if trade_time is None or str(trade_time).lower() in ("nat", "nan") else str(trade_time),
                "snapshot_at": now,
                "source": "lseg",
                "delayed": True,
            }
        if updated:
            with self.lock:
                for symbol, quote in updated.items():
                    quote["last_stream_event_at"] = self.last_events.get(quote["ric"])
                    self.quotes[symbol] = quote
                self.last_snapshot_at = now
                self.last_snapshot_monotonic = time.monotonic()

    def read(self) -> dict:
        with self.lock:
            return {
                "source": "lseg",
                "feed": "delayed_streaming",
                "delayed": True,
                "connected": self.connected,
                "connection_state": self.connection_state,
                "market_open": self.market_open,
                "feed_window_open": self.feed_window_open,
                "next_market_open": self.next_market_open,
                "market_close": self.market_close,
                "snapshot_at": self.last_snapshot_at,
                "snapshot_age_seconds": (round(time.monotonic() - self.last_snapshot_monotonic, 1)
                                         if self.last_snapshot_monotonic is not None else None),
                "configured": self.symbols.copy(),
                "quotes": {k: v.copy() for k, v in self.quotes.items()},
                "errors": {self.ric_to_symbol.get(k, k): v.copy() for k, v in self.statuses.items()},
            }


def refresh_flex_symbols(store: PriceStore):
    """Optional: discover current positions once per session, while EDP is open.

    Uses the resolver introduced in the user's earlier Flex integration. No
    files are written and the service account only needs read access to XML.
    Enable with LSEG_AUTO_RESOLVE_FLEX=1; otherwise use LSEG_SYMBOLS from .env.
    """
    if os.environ.get("LSEG_AUTO_RESOLVE_FLEX", "0").lower() not in ("1", "true", "yes"):
        return
    from flex_lseg_ric import read_flex_positions, flex_to_lseg_symbols
    archive_dir = Path(os.environ.get("FLEX_ARCHIVE_DIR", "/var/lib/flex-ingest/flex/data"))
    latest = sorted((p for p in archive_dir.iterdir()
                     if p.is_dir() and re.fullmatch(r"\d{8}", p.name)
                     and any(p.glob("*.xml.gz"))))
    if not latest:
        raise FileNotFoundError(f"No Flex archives under {archive_dir}")
    paths = sorted(latest[-1].glob("*.xml.gz"))
    positions = read_flex_positions(*paths)
    mapping, unresolved = flex_to_lseg_symbols(positions)
    store.replace_symbols(mapping)
    LOG.info("Resolved %d LSEG symbols from Flex (%d unresolved)",
             len(mapping), len(unresolved))
    for symbol, reason in unresolved.items():
        LOG.warning("UNRESOLVED %s: %s", symbol, reason)


def worker(stop: threading.Event, store: PriceStore, *, interval: float = 60.0,
           post_close_minutes: int = 20,
           manual_refresh: threading.Event | None = None,
           manual_timeout_seconds: float = 60.0):
    """Only authenticate/stream in NYSE sessions; leave the HTTP API running.

    Keep quotes in memory when disconnected so /prices remains readable, but
    expose connected=false and original timestamps so stale data is explicit.
    """
    delay = 10.0
    while not stop.is_set():
        try:
            window = market_window(post_close_minutes=post_close_minutes)
        except Exception:
            LOG.exception("Cannot determine NYSE trading hours")
            store.set_connection(False, "calendar_error")
            if stop.wait(60):
                break
            continue

        store.set_market_window(window)
        # An explicit manual request bypasses the market-hours gate ONCE.
        # The API stays online and no persistent after-hours streaming begins.
        manual = False
        if not window["active"]:
            if manual_refresh is not None and manual_refresh.is_set():
                manual_refresh.clear()
                manual = True
                LOG.info("One-time manual off-hours pricing refresh requested")
            else:
                if store.read()["connection_state"] != "market_closed":
                    LOG.info("NYSE feed paused; next regular open %s", window["next_market_open"])
                store.set_connection(False, "market_closed")
                pause = min(300.0, max(0.1, window["wait_seconds"]))
                if manual_refresh is not None:
                    manual_refresh.wait(pause)  # Wake immediately on POST /refresh.
                else:
                    stop.wait(pause)
                continue

        if stop.is_set():
            break

        # The session is within NYSE regular hours or the configured delayed
        # quote buffer. Never authenticate before this point.
        session = None
        stream = None
        try:
            import lseg.data as ld
            store.set_connection(False, "connecting")
            session = ld.session.platform.Definition(
                app_key=os.environ["LSEG_APP_KEY"],
                grant=ld.session.platform.GrantPassword(
                    username=os.environ["LSEG_USER_ID"],
                    password=os.environ["LSEG_PASSWORD"],
                ),
                signon_control=True,
            ).get_session()
            session.open()
            if str(session.open_state) != "OpenState.Opened":
                raise RuntimeError("LSEG Platform session did not open")
            ld.session.set_default(session)

            refresh_flex_symbols(store)
            with store.lock:
                rics = list(store.symbols.values())
            stream = ld.content.pricing.Definition(universe=rics, fields=FIELDS).get_stream()
            stream.on_refresh(store.on_event)
            stream.on_update(store.on_event)
            stream.on_status(store.on_status)
            stream.on_error(store.on_error)
            stream.open()
            store.set_connection(True, "manual_refresh" if manual else "streaming")
            delay = 10.0

            if manual:
                # Allow the asynchronous initial refresh images to arrive.
                # No guarantee that every configured RIC has an entitled price.
                deadline = time.monotonic() + manual_timeout_seconds
                previous_count = -1
                last_progress = time.monotonic()
                started = time.monotonic()
                LOG.info("Manual snapshot: requesting %d delayed RIC(s)", len(rics))
                while not stop.is_set():
                    store.publish(stream.get_snapshot())
                    with store.lock:
                        count = len(store.quotes)
                    if count >= len(rics):
                        break
                    if count != previous_count:
                        previous_count = count
                        last_progress = time.monotonic()
                    elapsed = time.monotonic() - started
                    if (time.monotonic() >= deadline or
                        (elapsed >= 20.0 and count > 0 and
                         time.monotonic() - last_progress >= 10.0)):
                        break
                    if stop.wait(2.0):
                        break
                LOG.info("Manual snapshot completed: %d/%d symbols have prices",
                         len(store.read()["quotes"]), len(rics))
            else:
                LOG.info("Subscribed to %d delayed RIC(s); streaming through %s",
                         len(rics), window["stream_until"].isoformat())
                while not stop.is_set():
                    remaining = (window["stream_until"] - datetime.now(timezone.utc)).total_seconds()
                    if remaining <= 0:
                        break
                    store.publish(stream.get_snapshot())
                    if stop.wait(min(interval, remaining)):
                        break
        except PermissionError:
            LOG.exception("Local file permission denied in LSEG worker")
            store.set_connection(False, "permission_error")
            # Do not loop/retry filesystem failures. Let an operator fix access.
            if manual:
                store.set_connection(False, "market_closed")
            else:
                stop.wait(max(0.1, (window["stream_until"] - datetime.now(timezone.utc)).total_seconds()))
        except Exception as exc:
            # Do not include potentially sensitive SDK URLs/credentials in logs.
            LOG.error("LSEG worker failed (%s); will retry if the market is open",
                      type(exc).__name__)
            store.set_connection(False, "reconnecting")
            if not manual:
                remaining = (window["stream_until"] - datetime.now(timezone.utc)).total_seconds()
                if remaining > 0:
                    stop.wait(min(delay, remaining))
                delay = min(delay * 2, 120.0)
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
            if not stop.is_set():
                closed = manual or datetime.now(timezone.utc) >= window["stream_until"]
                store.set_connection(False, "market_closed" if closed
                                     else store.read()["connection_state"])
    store.set_connection(False, "stopped")


def make_app(symbols: dict[str, str], interval: float = 60.0, *,
             post_close_minutes: int = 20) -> FastAPI:
    store = PriceStore(symbols)
    stopped = threading.Event()
    manual_refresh = threading.Event()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        thread = threading.Thread(
            target=worker, args=(stopped, store), kwargs={"interval": interval, "post_close_minutes": post_close_minutes,
                                                        "manual_refresh": manual_refresh},
            name="lseg-stream", daemon=True,
        )
        thread.start()
        try:
            yield
        finally:
            stopped.set()
            manual_refresh.set()  # Wake worker immediately if paused.
            thread.join(timeout=5)

    app = FastAPI(title="LSEG Delayed Price Feed", lifespan=lifespan,
                  description="Private/read-only cache of delayed LSEG US equity RICs")
    app.state.price_store = store

    @app.post("/refresh", status_code=202)
    def refresh_once(request: Request):
        # Defense-in-depth; do not proxy this administrative endpoint publicly.
        if request.client is None or request.client.host not in ("127.0.0.1", "::1", "testclient"):
            raise HTTPException(status_code=403, detail="Local requests only")
        if market_window(post_close_minutes=post_close_minutes)["active"]:
            return {"queued": False, "reason": "Scheduled streaming window is already active"}
        if manual_refresh.is_set() or store.read()["connection_state"] == "manual_refresh":
            return {"queued": False, "reason": "Manual refresh already in progress or queued"}
        manual_refresh.set()
        return {"queued": True, "message": "One-time off-hours refresh requested"}

    @app.get("/health")
    def health():
        snapshot = store.read()
        max_age = max(120.0, 3 * interval)
        age = snapshot["snapshot_age_seconds"]
        # A deliberately paused market-closed feed is healthy as an API.
        live_healthy = snapshot["connected"] and bool(snapshot["quotes"]) and age is not None and age <= max_age
        healthy = snapshot["connection_state"] == "market_closed" or live_healthy
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={
                "ok": healthy,
                "market_open": snapshot["market_open"],
                "feed_window_open": snapshot["feed_window_open"],
                "next_market_open": snapshot["next_market_open"],
                "market_close": snapshot["market_close"],
                "connected": snapshot["connected"],
                "state": snapshot["connection_state"],
                "last_snapshot_at": snapshot["snapshot_at"],
                "snapshot_age_seconds": snapshot["snapshot_age_seconds"],
                "symbols_with_prices": len(snapshot["quotes"]),
                "symbols_configured": len(snapshot["configured"]),
                "errors": snapshot["errors"],
            },
        )

    @app.get("/prices")
    def prices(symbols: str | None = Query(None, description="Comma-separated tickers, e.g. AAPL,MSFT")):
        snapshot = store.read()
        if symbols is not None:
            requested = [s.strip().upper() for s in symbols.split(",") if s.strip()]
            snapshot["quotes"] = {k: v for k, v in snapshot["quotes"].items() if k in requested}
            snapshot["errors"] = {k: v for k, v in snapshot["errors"].items() if k in requested}
        return snapshot

    @app.get("/prices/{symbol}")
    def price(symbol: str):
        snapshot = store.read()
        symbol = symbol.upper()
        if symbol not in store.symbols:
            raise HTTPException(status_code=404, detail="Symbol not configured")
        if symbol not in snapshot["quotes"]:
            raise HTTPException(status_code=503, detail="No usable quote yet")
        return snapshot["quotes"][symbol]

    return app


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    required = ("LSEG_APP_KEY", "LSEG_USER_ID", "LSEG_PASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit(f"Missing credentials in .env: {', '.join(missing)}")
    symbols = parse_symbols(os.environ.get("LSEG_SYMBOLS", DEFAULT_SYMBOLS))
    interval = int(os.environ.get("LSEG_PUBLISH_SECONDS", "60"))
    if interval < 1:
        raise SystemExit("LSEG_PUBLISH_SECONDS must be positive")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    LOG.info("Starting read-only delayed feed for %d tickers", len(symbols))
    post_close_minutes = int(os.environ.get("LSEG_POST_CLOSE_MINUTES", "20"))
    if post_close_minutes < 0:
        raise SystemExit("LSEG_POST_CLOSE_MINUTES must be nonnegative")
    app = make_app(symbols, interval, post_close_minutes=post_close_minutes)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("LSEG_PORT", "8091")), workers=1)


if __name__ == "__main__":
    main()
