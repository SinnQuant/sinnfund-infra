# IBKR Flex Ingestion — `flex-ingest.py`

## Overview

`flex-ingest.py` automates the retrieval of portfolio data from the Interactive Brokers (IBKR) Flex Web Service API. It retrieves XML statements for multiple accounts and archives them for downstream portfolio analysis.

### Why Flex Web Service?

We use Flex Web Service primarily for **unattended automation**. Unlike the Client Portal Web API or TWS API, Flex uses a token and Query ID without requiring interactive login, an active brokerage session, or recurring manual authentication.

Flex tokens are read-only and cannot execute trades. The tradeoff is that Flex provides historical/end-of-day reports rather than live market data.

## Functions

| Function | Purpose |
|---|---|
| `load_env()` | Loads credentials from `.env`. |
| `require()` | Checks for required environment variables. |
| `books()` | Maps tokens and Query IDs to individual books. |
| `http_get()` | Sends HTTP requests using the shared `api.py` client. |
| `result_label()` | Classifies API responses for logging. |
| `status()` | Extracts status and error codes from XML responses. |
| `is_report()` | Checks whether a response contains a Flex report. |
| `pull()` | Calls `SendRequest`, then polls `GetStatement` until the report is available. |
| `parse()` | Extracts positions, lots, trades, cash, and account IDs from XML. |
| `write_gz()` | Atomically saves compressed XML files. |
| `save()` | Archives a report under its date and book name. |
| `windows()` | Splits historical date ranges into chunks of up to 365 days. |
| `archived()` | Lists reports already downloaded for a date. |
| `latest_day()` | Finds the most recent archived reporting date. |
| `load()` | Reads archived XML and combines accounts without double-counting. |
| `export_csv()` | Exports parsed statement sections to CSV. |
| `last_weekday()` | Determines the previous weekday in Eastern Time. |
| `pull_book()` | Downloads, archives, and summarizes one book. |
| `pull_history()` | Downloads a historical report chunk. |
| `counts()` | Reports the number of records in each section. |
| `run_jobs()` | Coordinates downloads, respecting shared-token sequencing and configured parallelism. |
| `rebuild_history()` | Invokes `history.py` to rebuild historical NAV data. |
| `main()` | Handles CLI arguments, selects jobs, and runs ingestion. |

## Data Storage

Credentials are loaded from `/opt/flex-ingest/.env` using `IBKR_TOKEN` and `IBKR_QUERY_ID`.

In the documented implementation, files are stored relative to the script directory:

```text
/opt/flex-ingest/
├── flex-ingest.py
├── .env
/var/lib/flex-ingest/flex/data
│   ├── YYYYMMDD/<book>.xml.gz
```

The original compressed XML is retained as the source of truth. Subsequent parsing does not require additional IBKR API requests.

## Systemd Automation

Two systemd units automate execution:

**`flex-ingest.service`** defines how the script runs. It executes Python as the dedicated `svc-flex` service account, allowing ingestion to run independently of SSH sessions or logged-in developers.

**`flex-ingest.timer`** schedules the service using `OnCalendar`, configured for weekday execution in `America/New_York`. Systemd automatically starts the oneshot service at the scheduled time. `Persistent=true` allows a missed scheduled invocation to run when the timer is reactivated.

The script defaults to retrieving the previous weekday's report and skips already archived files unless `--force` is specified. In the current code, report-date parameters are omitted from `SendRequest`, so the Flex Query's saved configuration controls the requested report period.

### Management

```bash
# Inspect schedule
systemctl list-timers flex-ingest.timer

# Manually execute ingestion
sudo systemctl start flex-ingest.service

# View execution logs
journalctl -u flex-ingest.service -n 50

# Inspect service status
systemctl status flex-ingest.service
```

The timer handles scheduling; the service handles execution; `flex-ingest.py` handles ingestion and archiving.
