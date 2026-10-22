# IBKR Flex Live Dashboard — `web-live.py`

## Overview

`web-live.py` serves a read-only portfolio dashboard using archived Interactive Brokers (IBKR) Flex XML statements and delayed London Stock Exchange Group (LSEG) prices. It displays account holdings, position values, unrealized P&L, and expandable tax lots.

The dashboard reads the newest archived Flex reporting date, retrieves prices from the local `lseg-feed` API, and revalues eligible stock positions and lots in memory. **The original Flex XML archives are never modified.**

### Why Combine Flex and LSEG?

IBKR Flex reports provide reliable end-of-day positions, account data, cost basis, and tax lots, but their prices are not current. LSEG provides approximately 15-minute delayed quotes for updating those valuations without requiring a live IBKR trading session.

The parser makes **one HTTP request to `/prices` per dashboard report**, regardless of the number of accounts or positions. The web application makes a separate request to `/health` to display the last LSEG snapshot timestamp. No LSEG credentials are stored or used by `flex-web-live`.

## Functions

| Function | Purpose |
|---|---|
| `get_lseg_last_snapshot_at()` | Reads `last_snapshot_at` from the local LSEG `/health` endpoint for display in the dashboard header. |
| `load_report()` | Finds the newest Flex archive date, loads all books, parses positions and lots, and attaches the LSEG snapshot timestamp. |
| `index()` | Serves the HTML portfolio dashboard at `/`, including embedded report data. |
| `healthz()` | Checks for available Flex archives at `/healthz` without requesting LSEG prices. |
| `Handler.do_GET()` | Handles `/` and `/healthz` when using the optional built-in HTTP server. |
| `Handler.respond()` | Sends responses and security headers for the built-in HTTP server. |
| `main()` in `web-live.py` | Starts the optional built-in HTTP server; production uses Uvicorn instead. |
| `latest_date()` | Selects the newest dated directory containing compressed Flex XML statements. |
| `parse_archives()` | Parses summary positions and tax lots, removes duplicate account statements, retrieves one LSEG price snapshot, and calculates updated valuations. |
| `main()` in `parse_flex_positions_live.py` | Provides a command-line interface for exporting parsed positions and optionally lots as JSON. |

### Price Selection

| Priority | Condition | `price_source` |
|---|---|---|
| 1 | LSEG connected; snapshot no more than 180 seconds old | `lseg_delayed` |
| 2 | LSEG snapshot available and no more than 7 days old | `lseg_cached` |
| 3 | No usable LSEG price or API unavailable | `flex` |

Only `STK` records with valid, positive LSEG last-trade prices are revalued. The parser updates `mark_price`, `market_value`, and `unrealized_pnl`; options, warrants, unmatched symbols, and invalid quotes retain their Flex values. The `psuedo-live updated` flag indicates whether a replacement price was applied (the spelling matches the existing code). `percent_of_nav` remains based on the archived Flex statement.

Cached quotes are held by `lseg-feed`; if its in-memory cache is empty after a restart, the dashboard falls back to Flex prices until new quotes are available.

## Data Storage

The application reads archived reports from `/var/lib/flex-ingest/flex/data/` by default. `FLEX_ARCHIVE_DIR` can override this directory, and `LSEG_HEALTH_URL` can override the health endpoint (default `http://127.0.0.1:8091/health`). The parser's price endpoint is `http://127.0.0.1:8091/prices`.

```text
/opt/flex-web-live/
├── web-live.py
├── parse_flex_positions_live.py
├── requirements.txt
└── venv/

/var/lib/flex-ingest/flex/data/
└── YYYYMMDD/
    └── <book>.xml.gz
```

The dashboard stores no new positions or price files. All parsing and revaluation occur on page requests, using the latest archive and current or cached LSEG API response.

## Systemd Automation

**`flex-web-live.service`** runs the FastAPI application continuously under the dedicated `svc-flex` service account. Uvicorn listens on `127.0.0.1:8002`; Nginx exposes the dashboard at `/live/` on the fund website.

The configured service launches:

```bash
/opt/flex-web-live/venv/bin/uvicorn web-live:app --host 127.0.0.1 --port 8002
```

**No `flex-web-live.timer` is needed.** The dashboard stays running and reads the latest archives on demand. Separately, `flex-ingest.timer` schedules IBKR report downloads, while `lseg-feed.service` manages delayed quote subscriptions and their market-hours schedule.

The web application has no built-in authentication. Keep the Uvicorn listener on loopback and enforce appropriate access control at Nginx or another reverse proxy.

### Management

```bash
# Inspect service status
systemctl status flex-web-live.service

# Restart after code changes
sudo systemctl restart flex-web-live.service

# View application logs
journalctl -u flex-web-live.service -n 50

# Test local health endpoint
curl -i http://127.0.0.1:8002/healthz

# Inspect LSEG feed and cached prices
curl -s http://127.0.0.1:8091/health
curl -s http://127.0.0.1:8091/prices
```

The ingestion service archives the underlying holdings; `lseg-feed` supplies delayed prices; `parse_flex_positions_live.py` combines them; and `web-live.py` renders the read-only dashboard.
