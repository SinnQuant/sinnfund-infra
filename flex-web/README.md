# IBKR Flex Closing Dashboard — `web.py`

## Overview

`web.py` serves a read-only portfolio dashboard using the newest archived Interactive Brokers (IBKR) Flex XML statements. It displays previous-close positions, account holdings, unrealized P&L, and expandable tax-lot details.

The dashboard uses FastAPI and Uvicorn behind Nginx. It does not contact IBKR or LSEG, require API credentials, or modify archived files.

### Why Archived Flex Reports?

The dashboard reads **previous-close portfolio data** already downloaded by `flex-ingest`, avoiding additional brokerage requests or authentication. Archived statements remain the source of truth, and the dashboard works independently of the live pricing service.

Unlike `flex-web-live`, this application does **not** revalue positions using delayed quotes. All displayed prices, position values, and P&L come from the Flex statement.

## Functions

| Function | Purpose |
|---|---|
| `latest_date()` | Finds the newest dated archive directory containing compressed XML statements. |
| `parse_archives()` | Reads Flex XML archives, separates summary positions from tax lots, and skips duplicate account statements across books. |
| `load_report()` | Loads the newest report date, parses its archives, and returns positions, lots, and report metadata. |
| `index()` | Handles `GET /`, embeds report JSON in the HTML dashboard, and returns HTTP 503 if archive loading fails. |
| `healthz()` | Handles `GET /healthz`, checking that a dated archive is available without parsing every statement. |
| `main()` | Starts Uvicorn when `web.py` is run directly, defaulting to `127.0.0.1:8001`. |

The browser-side `render()` function handles account filtering, search, sorting, and expandable per-position tax lots. Tax lots are associated with summary positions using account ID and IBKR contract ID (`conid`).

## Data Storage

The dashboard reads the existing compressed reports from:

```text
/opt/flex-web/
├── web.py
├── parse_flex_positions.py
├── requirements.txt
└── venv/

/var/lib/flex-ingest/flex/data/
└── YYYYMMDD/
    └── <book>.xml.gz
```

The default archive path can be overridden with `FLEX_ARCHIVE_DIR`. All parsing is performed in memory; no reports are created, changed, or deleted by this service.

The newest available archive date is selected **when the dashboard is requested**, so a newly ingested report can appear without restarting the application.

## Systemd Automation

**`flex-web.service`** runs the FastAPI application as the dedicated `svc-flex` account. Uvicorn listens locally on port `8001`, with Nginx exposing the dashboard through `/close/`.

An example service command is:

```ini
WorkingDirectory=/opt/flex-web
ExecStart=/opt/flex-web/venv/bin/uvicorn web:app --host 127.0.0.1 --port 8001 --no-access-log
```

This is a **continuously running web service**, so it does not need its own systemd timer. The separate `flex-ingest.timer` schedules daily archival downloads; `flex-web` reads those archives as they become available.

The application's endpoints are:

| Endpoint | Purpose |
|---|---|
| `GET /` | Render the latest closing-positions dashboard. |
| `GET /healthz` | Return `ok` when a dated Flex archive is available, otherwise HTTP 503. |

### Management

```bash
# Inspect service status
systemctl status flex-web.service

# Restart after code changes
sudo systemctl restart flex-web.service

# View recent logs
journalctl -u flex-web.service -n 50

# Check the local health endpoint
curl -i http://127.0.0.1:8001/healthz

# Parse a specific reporting date directly
/opt/flex-web/venv/bin/python /opt/flex-web/parse_flex_positions.py --date 20261020 --include-lots
```

The service handles HTTP requests; `parse_flex_positions.py` handles read-only XML parsing; `flex-ingest` separately handles report retrieval and archiving.

**Security:** The application has no built-in authentication. Keep Uvicorn bound to `127.0.0.1`, protect the public Nginx route, and grant `svc-flex` read-only access to the required Flex archive files.
