# LSEG Delayed Market Data Feed

Private, read-only HTTP API for delayed LSEG equity and ETF prices. The service authenticates to LSEG Data Platform (EDP), maintains a streaming subscription during the NYSE market-data window, and exposes the most recent quotes from an in-memory cache to other services on the same machine.

**Production location:** `/opt/lseg-feed`  
**systemd unit:** `lseg-feed.service`  
**HTTP bind:** `127.0.0.1:8091`  
**Primary entrypoint:** `feed_api.py`

This README describes the supplied implementation of `feed_api.py`, `flex_lseg_ric.py`, `lseg-symbols.env`, and the current systemd unit. It does not assume that every configured RIC is entitled or has a price.

## 1. Architecture

```text
IBKR Flex daily XML archives
  /var/lib/flex-ingest/flex/data/YYYYMMDD/*.xml.gz
         |
         | optional symbol discovery (once per LSEG connection)
         v
  flex_lseg_ric.py  ---> IBKR ticker -> delayed LSEG RIC mapping
                                    |
LSEG EDP OAuth V1 (App Key, User ID, Password)
         |                          |
         v                          v
  LSEG pricing stream -----> PriceStore (thread-safe, in memory)
                                     |
                +--------------------+-----------------+
                |                    |                 |
          GET /prices          GET /prices/{symbol}  GET /health
                |
                v
     flex-web-live / parse_flex_positions_live.py
      (one bulk request for portfolio repricing)
```

- FastAPI/Uvicorn remains running **24/7**.
- A single background worker thread owns the LSEG Platform session and price stream.
- The worker normally connects only between NYSE market open and **20 minutes after the scheduled market close**; it sleeps outside that window without terminating the HTTP server.
- A localhost-only `POST /refresh` can request **one** temporary off-hours stream refresh.
- The HTTP API never provides LSEG credentials or trading/order operations.
- The cache is **in memory only**: a service restart clears received quotes.

**Pricing designation:** Subscriptions use slash-prefixed RICs such as `/AAPL.O`. These are **delayed**, not real-time quotes. Individual entitlements and data availability still apply.

## 2. Files

| File | Purpose |
|---|---|
| `feed_api.py` | FastAPI routes, thread-safe quote cache, EDP session/stream worker, NYSE schedule, manual refresh |
| `flex_lseg_ric.py` | Extract SUMMARY positions from Flex XML and resolve candidate delayed RICs using LSEG discovery |
| `.env` | LSEG credentials and service settings (sensitive; do not commit) |
| `lseg-symbols.env` | Explicit IBKR ticker-to-LSEG RIC map for the initial universe |
| `venv/` | Isolated Python environment |
| `/etc/systemd/system/lseg-feed.service` | Long-running service running as `svc-lseg` |
| `/etc/systemd/system/lseg-feed.timer` | **Legacy market-open timer**; not needed with the always-on API design |

## 3. Requirements and installation

Requires Linux with systemd, Python supported by the installed `lseg-data` SDK, access to the LSEG EDP service, and credentials entitled to the required API and delayed RICs. The supplied code imports `lseg-data`, `fastapi`, `uvicorn`, `python-dotenv`, and `exchange-calendars`.

```bash
cd /opt/lseg-feed
python3 -m venv venv
./venv/bin/python -m pip install \
  lseg-data fastapi uvicorn python-dotenv 'exchange-calendars>=4.12,<5'
```

If a `requirements.txt` is installed alongside the application, prefer:

```bash
/opt/lseg-feed/venv/bin/python -m pip install -r /opt/lseg-feed/requirements.txt
```

The latest Flex archive directory must be readable by the service account when automatic discovery is enabled.

## 4. Configuration

`feed_api.py` calls `load_dotenv()` on `/opt/lseg-feed/.env` with `override=False`. Environment variables supplied by systemd take precedence over values loaded directly from `.env`.

Example `/opt/lseg-feed/.env` (substitute actual credentials; never check in):

```dotenv
LSEG_APP_KEY=YOUR_EDP_APPLICATION_KEY
LSEG_USER_ID=YOUR_PLATFORM_USER_ID
LSEG_PASSWORD=YOUR_PLATFORM_PASSWORD

LSEG_PORT=8091
LSEG_PUBLISH_SECONDS=60
LSEG_POST_CLOSE_MINUTES=20

# Optional: regenerate the universe from the newest archived Flex holdings.
LSEG_AUTO_RESOLVE_FLEX=1
FLEX_ARCHIVE_DIR=/var/lib/flex-ingest/flex/data
```

For explicit symbols, supply `LSEG_SYMBOLS` in `lseg-symbols.env`, for example:

```dotenv
LSEG_SYMBOLS=AAPL=/AAPL.O,MSFT=/MSFT.O,NVDA=/NVDA.O,UBER=/UBER.K
```

The mapping format is `IBKR_TICKER=/DELAYED_LSEG_RIC`, comma-separated. The ticker is the key clients use to retrieve a price. The `/` prefix is required for the delayed RIC configuration.

**Important precedence detail:** The supplied systemd service declares:

```ini
EnvironmentFile=/opt/lseg-feed/lseg-symbols.env
EnvironmentFile=/opt/lseg-feed/.env
```

If **both** files define `LSEG_SYMBOLS`, the **later** `.env` value wins. Remove the old `LSEG_SYMBOLS` from `.env` if the service keeps starting with the original three tickers rather than the expanded universe. `load_dotenv(override=False)` will not reverse this precedence.

### Automatic discovery from Flex

With `LSEG_AUTO_RESOLVE_FLEX=1`:

1. Once an EDP session opens, the worker finds the newest dated archive directory under `FLEX_ARCHIVE_DIR`.
2. `flex_lseg_ric.py` reads `SUMMARY`-level `OpenPosition` records.
3. LSEG symbol conversion returns candidate RIC mappings, checking available ticker, ISIN, asset-category, and listing data.
4. `PriceStore.replace_symbols()` installs the resolved map and discards quotes for removed/changed contracts.
5. The worker subscribes to the resulting RICs.

This resolver excludes many options, warrants, ambiguous listings, and unverified securities rather than inferring a potentially wrong price. It logs unresolved symbols. The mapping is **refreshed on the next session connection**, not continuously as holdings change throughout an active session. Symbol conversion requires permission to use LSEG discovery.

If automatic discovery is disabled or an EDP connection has not yet been established, the configured `LSEG_SYMBOLS` mapping is used.

## 5. Market-hours and connection lifecycle

Trading times are calculated with the **NYSE (`XNYS`) exchange calendar**, including weekends, NYSE holidays, daylight-saving transitions, and early closes.

| Period | HTTP API | LSEG stream | Quotes |
|---|---|---|---|
| Before NYSE open | Available | Paused | Last cached quotes, if any |
| Regular trading session | Available | Connected when healthy | Updated from delayed stream |
| Close to close + 20 minutes (default) | Available | Connected | Allows delayed final prices to arrive |
| After feed window, weekends, NYSE holidays | Available | Disconnected | Retained in memory, marked disconnected |
| Manual refresh outside hours | Available | Temporary connection | Fetches available initial quote images, then disconnects |

The worker tries to reconnect after transient stream failures (backoff up to 120 seconds while the feed window is active). Filesystem permission failures are logged with a traceback and are not retried repeatedly during that market window.

**Scope of the schedule:** The gate uses NYSE hours for the entire universe. Japanese or other non-US symbols in the mapping will **not** receive a stream session based on their local exchanges' operating hours. A separate scheduling/connection policy is needed for those markets.

## 6. HTTP API

The server binds **only** to `127.0.0.1`, by default on port `8091`. The endpoints have no built-in login for normal GET requests; do not publish them through Nginx.

### `GET /health`

```bash
curl -sS http://127.0.0.1:8091/health | python3 -m json.tool
```

Important response fields:

| Field | Meaning |
|---|---|
| `ok` | Whether the API considers the paused state healthy, or an active stream has recent cached quotes |
| `market_open` | Whether the NYSE regular cash session is open |
| `feed_window_open` | Whether the market session plus post-close buffer is active |
| `next_market_open` | Calendar-calculated next/current session opening time |
| `market_close` | Scheduled close for the active session; otherwise may be `null` |
| `connected` | Whether the worker reports an active LSEG stream |
| `state` | Internal state, such as `market_closed`, `connecting`, `streaming`, `reconnecting`, or `manual_refresh` |
| `last_snapshot_at` | UTC timestamp of last published cache snapshot; not the exchange trade timestamp |
| `snapshot_age_seconds` | Age of last cache publication |
| `symbols_with_prices` | Number of symbols with stored quote records |
| `symbols_configured` | Number of configured tickers |
| `errors` | Per-symbol stream status/error messages, e.g. `NotEntitled` |

`/health` returns HTTP **200** while intentionally `market_closed`, even when no quotes have been cached; it can return **503** while connecting or when a live connection has no recent usable snapshot. `ok: true` after hours does **not** mean prices are fresh.

### `GET /prices`

Returns the complete latest snapshot, including connection metadata, configured ticker/RIC mappings, a `quotes` dictionary keyed by **IBKR ticker**, and per-ticker errors.

```bash
curl -sS http://127.0.0.1:8091/prices | python3 -m json.tool
```

Example shape (illustrative prices only):

```json
{
  "source": "lseg",
  "feed": "delayed_streaming",
  "delayed": true,
  "connected": false,
  "connection_state": "market_closed",
  "snapshot_at": "2026-10-16T20:20:00+00:00",
  "snapshot_age_seconds": 7200.0,
  "configured": {"AAPL": "/AAPL.O"},
  "quotes": {
    "AAPL": {
      "symbol": "AAPL",
      "ric": "/AAPL.O",
      "price": 123.45,
      "bid": 123.44,
      "ask": 123.46,
      "mid": 123.45,
      "trade_time": "20:05:00",
      "snapshot_at": "2026-10-16T20:20:00+00:00",
      "source": "lseg",
      "delayed": true,
      "last_stream_event_at": "2026-10-16T20:20:00+00:00"
    }
  },
  "errors": {}
}
```

**Data meaning:** `price` is `TRDPRC_1` (last trade), not bid/ask midpoint; `mid` is computed when valid bid and ask values exist. Some records may contain `price: null` when only bid or ask is available. `trade_time` comes from `TRDTIM_1`, which may not include the trading date. `snapshot_at` and `snapshot_age_seconds` describe **when the cache was published**, not the age of the last exchange transaction.

Bulk filtering is also supported:

```bash
curl -sS 'http://127.0.0.1:8091/prices?symbols=AAPL,MSFT,IREN'
```

This is one local HTTP request even for many securities. The `quotes` and `errors` dictionaries are filtered; the remaining response metadata is unchanged.

### `GET /prices/{symbol}`

```bash
curl -sS http://127.0.0.1:8091/prices/IREN
```

- `200`: configured and a quote record is cached.
- `404`: symbol not configured.
- `503`: configured, but no usable quote record yet.

### `POST /refresh` (administrative; localhost-only)

```bash
curl -sS -X POST http://127.0.0.1:8091/refresh | python3 -m json.tool
```

- Outside feed hours: queues a **one-shot** streaming snapshot attempt and returns HTTP `202` with `queued: true`.
- Inside feed hours: returns `queued: false` because normal streaming should be active.
- A queued refresh is asynchronous: the response does **not** imply that prices have arrived. Check `/health` and `/prices` afterward.
- The one-shot worker waits up to 60 seconds, potentially less if progress stalls. It cannot guarantee prices for all configured RICs, particularly after hours.

The handler checks for a loopback client address. **Do not reverse proxy `/refresh`**: a request forwarded by a local proxy may appear to originate from `127.0.0.1`, defeating this check.

## 7. Integration with `flex-web-live`

The companion parser `parse_flex_positions_live.py` makes **one** request to `GET http://127.0.0.1:8091/prices` per report load, then revalues applicable summary positions and tax lots from the latest archived Flex data.

Its current fallback behavior is:

| Condition | Position pricing |
|---|---|
| Connected and snapshot age <= 180 seconds | Use LSEG delayed price |
| Cached snapshot age <= 7 days | Use cached LSEG price even when disconnected |
| No usable quote, stale cache, unavailable API, unsupported asset class | Retain original IBKR Flex price |

The parser records `psuedo-live updated` (`1`/`0`, spelling retained for compatibility) and `price_source` (`lseg_delayed`, `lseg_cached`, `flex`). It does not modify the underlying `.xml.gz` archives.

This is indicative portfolio revaluation, **not** official IBKR account NAV. Options, warrants, unmatched symbols, unverified price units/currencies, and individual symbol entitlements can prevent updates.

## 8. systemd deployment

The supplied long-running service is:

```ini
[Unit]
Description=LSEG Delayed Market Data API
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=svc-lseg
Group=svc-lseg
WorkingDirectory=/opt/lseg-feed
ExecStart=/opt/lseg-feed/venv/bin/python /opt/lseg-feed/feed_api.py
EnvironmentFile=/opt/lseg-feed/lseg-symbols.env
EnvironmentFile=/opt/lseg-feed/.env
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=15
ProtectSystem=full

[Install]
WantedBy=multi-user.target
```

### Always-on deployment: disable the legacy timer

Because the Python worker now handles the NYSE trading schedule, the service should start at boot and stay available. The uploaded `lseg-feed.timer` is from the earlier **start-at-market-open** design; keeping that timer is unnecessary and can cause confusion about the intended lifecycle.

```bash
sudo systemctl disable --now lseg-feed.timer
sudo systemctl daemon-reload
sudo systemctl enable --now lseg-feed.service
sudo systemctl restart lseg-feed.service
```

The service should **not** depend on a timer for market-open connections. During a normal market closure, the FastAPI process should continue to serve `/health` and any cached `/prices` data.

Inspect it with:

```bash
systemctl status lseg-feed.service --no-pager -l
sudo journalctl -u lseg-feed.service -n 80 --no-pager -l
sudo ss -ltnp | grep ':8091'
```

### Permissions and secrets

The service runs as `svc-lseg`, not the application owner. Keep its access limited to reading code, credentials, and the necessary Flex archives.

```bash
id svc-lseg
sudo chown root:svc-lseg /opt/lseg-feed/.env
sudo chmod 640 /opt/lseg-feed/.env
sudo chmod 755 /opt/lseg-feed
sudo chmod -R go-w /opt/lseg-feed/venv
sudo -u svc-lseg test -r /opt/lseg-feed/.env && echo 'Credentials readable'
```

When using automatic symbol resolution, grant **read-only** traversal/access to `/var/lib/flex-ingest/flex/data` and its archive files for `svc-lseg`, accounting for each parent directory's permissions. Do not make secrets or the entire application directory world-writable. This implementation does not need to write `lseg-symbols.env` during streaming.

## 9. Troubleshooting

| Symptom | Likely cause / action |
|---|---|
| `status=217/USER` | `User=svc-lseg` does not exist or systemd cannot initialize it; check `getent passwd svc-lseg` |
| `PermissionError` after OAuth success | Service user cannot read Flex archives, module/configuration, or another local file; inspect full traceback |
| `symbols_configured: 3` instead of hundreds | Wrong `LSEG_SYMBOLS` environment value; check `EnvironmentFile` order and old `.env` entries |
| `market_closed`, `symbols_with_prices: 0` | Normal if the process started after hours and has never populated its in-memory cache; call localhost `/refresh` once or wait until the feed window |
| `connected: false` after close | Normal; API remains online while worker sleeps |
| `404` on `/prices/IREN` | `IREN` is not in current `store.symbols` |
| `503` on `/prices/IREN` | Ticker is configured but has no cached quote yet |
| `NotEntitled`, `Access Denied` | LSEG market-data entitlement missing for that specific RIC; check delayed slash-prefixed RICs and TAMU permissions |
| Manual `/refresh` queued but no prices | Stream did not return entitled initial images during the temporary window; inspect `errors` and worker logs |
| Quotes disappear after `systemctl restart` | Expected: quotes exist only in memory; no disk-backed cache is implemented |
| `/health` shows recent `snapshot_age_seconds`, but a trade is old | Cache-publication time is not the exchange trade timestamp; examine instrument `trade_time` and status |
| Updates for Japanese symbols not timely | Current scheduler gates all subscriptions by NYSE calendar rather than Japanese market hours |

If needed, execute locally in the existing venv:

```bash
cd /opt/lseg-feed
./venv/bin/python feed_api.py
```

Stop the systemd-managed process first to avoid a port collision.

## 10. Security and licensing

- Bind to loopback (`127.0.0.1:8091`). Allow only local services to consume raw quotes.
- Do **not** proxy the full LSEG feed API or its administrative `/refresh` endpoint to the public internet.
- Store the App Key, EDP User ID, and password in the protected `.env` file; never include credentials in URLs, source control, or logs.
- Neither opening an EDP session nor holding a streaming scope proves entitlement to every exchange/RIC.
- TAMU's academic LSEG agreement may restrict server-side use, storage, internal display, and redistribution. Confirm authorization before sharing the derived pricing in a multi-user dashboard.
- LSEG prices are delayed and should be labeled accordingly; `connected=true` does not make the exchange quotes real time.

## 11. Current limitations

1. **No persistent price cache:** restart empties all quotes, and `/refresh` cannot guarantee an off-hours price for every symbol.
2. **Single market-hours calendar:** the worker uses NYSE sessions even for foreign-listed securities.
3. **Indicative price freshness:** the API exposes cache timestamps and a possibly date-less trade time, not a validated last-trade UTC instant for every instrument.
4. **Symbol mapping coverage:** some options, warrants, foreign currencies, and ambiguous listings are unresolved by design.
5. **One active session/worker:** keep `workers=1` and avoid launching multiple application instances using the same EDP credentials unless explicitly authorized.

The current design is suitable as a private delayed quote cache feeding the pseudo-live Flex dashboard, provided market-data access and use are authorized.
