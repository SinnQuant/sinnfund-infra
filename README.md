# SINN Fund Infrastructure

Version-controlled source, configuration templates, and operating documentation for the SINN Fund portfolio dashboards, market-data feed, prediction API, and website at `sinnfund.jkoh.dev`.

The project addresses the fund's need for dependable portfolio visibility between instructor-distributed reports. It separates **read-only portfolio reporting** from research signals and any future trade-staging or execution workflow. See [Project Vision](docs/product/project-vision.md) for the motivation and planned workstreams.

> **Repository scope:** This repository contains the applications listed below. The historical VaR/risk pipeline is **intentionally maintained outside this repository at present**. Its design decisions and operational history appear in `docs/`, but its application code, generated reports, and deployment units are not included here. This is a deliberate boundary, not a missing installation step.

This is the **version-controlled source**, not the live application directory. Production services run under `/opt/`, the static website is served from `/var/www/sinnfund/`, and runtime state and credentials remain outside Git. Repository structure does not determine deployment paths.

## Architecture

```text
  Interactive Brokers (IBKR) Flex Web Service
                       |
                       v
                flex-ingest.service <--- flex-ingest.timer
                       |
                       v
    /var/lib/flex-ingest/flex/data/YYYYMMDD/<book>.xml.gz
                       |
              +--------+--------+
              |                 |
              v                 v
       flex-web :8001    flex-web-live :8002 <--- lseg-feed :8091
       Flex close marks  Delayed/cached marks     ^
              |                 |                 |
              |                 |            LSEG Data API
              v                 v
           /close/            /live/
              |                 |
              +--------+--------+
                       |
              Nginx HTTPS reverse proxy <--- prediction-api :8003
                       |                      /prediction/
                       v
                sinnfund.jkoh.dev
                       |
                       v
                Static website (/)
                /var/www/sinnfund/index.html
```

The ingestion service downloads and archives complete Flex XML reports. Both dashboards read the same archived reports without modifying them. `flex-web-live` requests delayed/cached prices from the localhost-only LSEG API and falls back to Flex closing marks when suitable quotes are unavailable. The prediction API is a separate application, not an authorization path for trade execution.

## Components

| Repository directory | Purpose | Production location | systemd unit | Listener / public route |
|---|---|---|---|---|
| `services/flex-ingest/` | Scheduled IBKR Flex retrieval and raw XML archiving | `/opt/flex-ingest/` | `flex-ingest.service`, `flex-ingest.timer` | No HTTP listener |
| `services/flex-web/` | Read-only previous-close positions and tax-lot dashboard | `/opt/flex-web/` | `flex-web.service` | `127.0.0.1:8001` → `/close/` |
| `services/flex-web-live/` | Read-only dashboard repriced using delayed/cached LSEG quotes | `/opt/flex-web-live/` | `flex-web-live.service` | `127.0.0.1:8002` → `/live/` |
| `services/lseg-feed/` | LSEG session, RIC normalization, local pricing API | `/opt/lseg-feed/` | `lseg-feed.service` | `127.0.0.1:8091` (internal only) |
| `services/prediction-api/` | Prediction and paper-signal API | `/opt/prediction-api/` | Verify installed unit name | `127.0.0.1:8003` → `/prediction/` |
| `website/` | Static landing page | `/var/www/sinnfund/` | Served by Nginx | `/` |
| `deploy/nginx/` | Version-controlled Nginx virtual host | `/etc/nginx/sites-available/` | `nginx.service` | HTTPS entry point and reverse proxy |

Each application maintains its own `requirements.txt`, supporting scripts, and deployment documentation where present. Its checked-in `deploy/` folder contains systemd unit templates; production units live under `/etc/systemd/system/`.

## Repository layout

```text
sinnfund-infra/
├── README.md
├── .gitignore
├── services/
│   ├── flex-ingest/
│   │   ├── flex-ingest.py
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── README.md
│   │   └── deploy/
│   ├── flex-web/
│   │   ├── web.py
│   │   ├── parse_flex_positions.py
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   └── deploy/
│   ├── flex-web-live/
│   │   ├── web-live.py
│   │   ├── parse_flex_positions_live.py
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   └── deploy/
│   ├── lseg-feed/
│   │   ├── feed_api.py
│   │   ├── flex_lseg_ric.py
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── README.md
│   │   └── deploy/
│   └── prediction-api/
│       ├── app.py
│       ├── paper_signals.py
│       ├── requirements.txt
│       └── notes.txt
├── website/
│   ├── index.html
│   └── deploy.sh
├── deploy/
│   └── nginx/
│       └── sinnfund.jkoh.dev
└── docs/
    ├── notes.md
    ├── product/
    │   └── project-vision.md
    ├── decisions/
    │   ├── README.md
    │   └── 0001–0026-*.md
    ├── incidents/
    │   ├── README.md
    │   ├── _template.md
    │   └── 0001–0012-*.md
    └── journal/
        ├── README.md
        ├── _templates/
        └── 2026-10/
```

The `services/` paths above reflect the reorganized source layout. Deployed application paths under `/opt/` are unchanged.

## Engineering documentation

| Documentation | Purpose |
|---|---|
| [Project vision](docs/product/project-vision.md) | Original transparency problem, intended users, and related workstreams |
| [Architecture decisions](docs/decisions/README.md) | Why major architecture and workflow choices were made |
| [Incident reports](docs/incidents/README.md) | Failures, investigations, fixes, and follow-up actions |
| [Engineering journal](docs/journal/README.md) | Dated development sessions and personal technical reflections |
| [Additional notes](docs/notes.md) | Working project notes |

Some ADRs and incidents discuss the risk/VaR prototype and proposed TAMU Kion/AWS hosting. Those records document the broader project history and **do not imply that the corresponding services or cloud resources are included in, or deployed from, this repository**. Trade staging through IBKR BasketTrader and researcher prediction integration are also separate workstreams; neither grants the public dashboards trading authority.

## Runtime data and configuration

| Location | Contents | Git policy |
|---|---|---|
| `/var/lib/flex-ingest/flex/data/YYYYMMDD/<book>.xml.gz` | Archived IBKR statements used by the dashboards | **Never commit** |
| `/opt/flex-ingest/.env` | Flex API token and saved query configuration | **Never commit** |
| `/opt/lseg-feed/.env` | LSEG authentication credentials | **Never commit** |
| `/opt/lseg-feed/lseg-symbols.env` | Active instrument-to-RIC mapping | Keep out of Git in the current setup; use sanitized examples |
| `/opt/prediction-api/data/`, `logs/`, `submitted_predictions/` | Prediction outputs and operational state, when configured | **Never commit** |
| `venv/`, `.venv/`, `__pycache__/` | Local Python environments and generated files | **Never commit** |

No live IBKR or LSEG session is required to display positions from an already archived Flex report. The live dashboard contacts the private LSEG API rather than storing LSEG credentials in the website service.

## Deployment

Pushing to GitHub **does not automatically deploy** code. Copy reviewed files from the repository into the corresponding `/opt/<service>/` installation, preserving `.env` files, virtual environments, application ownership, and runtime state. Restart only the affected service.

### Example: previous-close dashboard

```bash
# Run from the repository root on the VPS.
sudo install -m 644 services/flex-web/web.py /opt/flex-web/web.py
sudo install -m 644 services/flex-web/parse_flex_positions.py   /opt/flex-web/parse_flex_positions.py
sudo systemctl restart flex-web.service
sudo systemctl status flex-web.service --no-pager
```

For dependency changes, install the service's updated `requirements.txt` into its existing virtual environment. For `.service` or `.timer` changes, install the reviewed unit under `/etc/systemd/system/`, run `sudo systemctl daemon-reload`, and restart or enable the relevant unit as appropriate.

Do **not** recursively overwrite `/opt/` with the repository: production secrets, runtime data, and intended service-account ownership must be preserved.

### Static website

```bash
sudo install -m 644 website/index.html /var/www/sinnfund/index.html
```

Nginx serves the static HTML directly; an Nginx reload is not normally required for an HTML-only update. Review `website/deploy.sh` before using it.

### Nginx

The site is expected to use a configuration at `/etc/nginx/sites-available/sinnfund.jkoh.dev`, enabled by a symlink under `/etc/nginx/sites-enabled/`.

```bash
sudo cp -a /etc/nginx/sites-available/sinnfund.jkoh.dev   /etc/nginx/sites-available/sinnfund.jkoh.dev.bak
sudo install -m 644 deploy/nginx/sinnfund.jkoh.dev   /etc/nginx/sites-available/sinnfund.jkoh.dev
sudo nginx -t && sudo systemctl reload nginx
```

If validation fails, restore the backup and re-test. Keep the Nginx configuration aligned with the applications actually deployed; do not add risk-service routes just because risk-related ADRs exist.

## Operations and checks

```bash
# Service status and ingestion schedule
systemctl status flex-ingest.service flex-web.service flex-web-live.service lseg-feed.service
systemctl list-timers flex-ingest.timer

# Optional manual ingestion (runs against the configured broker query)
sudo systemctl start flex-ingest.service

# Recent logs
journalctl -u flex-ingest.service -n 50 --no-pager
journalctl -u flex-web.service -n 50 --no-pager
journalctl -u flex-web-live.service -n 50 --no-pager
journalctl -u lseg-feed.service -n 50 --no-pager

# Local service health
curl -fsS http://127.0.0.1:8001/healthz
curl -fsS http://127.0.0.1:8002/healthz
curl -i http://127.0.0.1:8091/health

# Public HTTPS landing page
curl -I https://sinnfund.jkoh.dev/
```

The dashboard health endpoints check availability of archived data. The LSEG health response can indicate disconnected or closed-market status outside streaming hours; inspect the response rather than assuming a 24/7 live market stream. `lseg-feed.service` is a persistent service; it does not require an `lseg-feed.timer`.

## Security and access

- **Repository:** Keep nonpublic source and operational documents restricted to authorized contributors; review staged changes before pushing. Never commit API tokens, private keys, actual account archives, or generated predictions.
- **Human operators:** Use individual accounts and appropriately scoped group access (such as `trading-dev`) rather than sharing credentials.
- **Service accounts:** Keep production services on their configured limited-permission identities. Verify the actual `User=` and `Group=` in installed systemd units; `svc-flex` and `svc-lseg` have separate responsibilities.
- **Networking:** Bind application APIs to `127.0.0.1`; publish only intended Nginx routes. Do not expose the LSEG pricing API directly.
- **Website visibility:** Read-only does not mean public disclosure is approved. These dashboard applications do not implement their own login; enforce access restrictions at an approved gateway or reverse proxy where required.
- **Data rights:** Confirm brokerage-data disclosure authorization and LSEG licensing requirements before making holdings or vendor-derived prices publicly accessible.
- **Code deployment:** Limit write/deploy permissions for code executed by credential-bearing services.

## Development workflow

Use a feature branch, inspect the staged diff, and merge reviewed changes to `main`. On the VPS, deploy the approved revision explicitly and verify health and logs.

```bash
git switch -c feature/example-change
# Make changes.
git add <changed-files>
git diff --cached --check
git diff --cached
git commit -m "Describe the change"
git push -u origin feature/example-change
```

For service-specific setup and troubleshooting, see the README and deployment unit files in each `services/<name>/` directory.
