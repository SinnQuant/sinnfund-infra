# SINN Fund Infrastructure

Source code, configuration templates, and deployment documentation for the SINN Fund portfolio dashboards, market-data feed, prediction API, and website hosted at `sinnfund.jkoh.dev`.

This repository is the **version-controlled source**, not the live application directory. Production services run from `/opt/`; Nginx serves the static website from `/var/www/sinnfund/`. Runtime data and credentials remain outside Git.

## Architecture

```text
Interactive Brokers (IBKR) Flex Web Service
                    │
                    ▼
           flex-ingest.service  ◄── flex-ingest.timer
                    │
                    ▼
 /var/lib/flex-ingest/flex/data/YYYYMMDD/<book>.xml.gz
                    │
         ┌──────────┴──────────────┐
         ▼                         ▼
   flex-web :8001         flex-web-live :8002 ◄──── lseg-feed :8091
   Closing marks         Delayed / cached marks          ▲
         │                         │                     │
         │                         │               LSEG Data API
         ▼                         ▼
      /close/                   /live/
         └──────────────┬──────────┘
                        │
                 Nginx HTTPS proxy  ◄── prediction-api :8003 (/prediction/)
                        │
             sinnfund.jkoh.dev
                        ▲
           /var/www/sinnfund/index.html (/)
```

The ingestion service downloads and archives reports. The two dashboards **read the same archived XML without modifying it**. `flex-web-live` requests delayed or cached prices from the localhost-only LSEG service and falls back to Flex closing marks when suitable prices are unavailable. The prediction API is a separate application.

## Components

| Directory | Purpose | Production location | systemd unit | Listening address / route |
|---|---|---|---|---|
| `flex-ingest/` | Scheduled retrieval and archiving of IBKR Flex reports | `/opt/flex-ingest/` | `flex-ingest.service`, `flex-ingest.timer` | No HTTP listener |
| `flex-web/` | Read-only previous-close positions and tax-lot dashboard | `/opt/flex-web/` | `flex-web.service` | `127.0.0.1:8001` → `/close/` |
| `flex-web-live/` | Read-only dashboard repriced with delayed/cached LSEG quotes | `/opt/flex-web-live/` | `flex-web-live.service` | `127.0.0.1:8002` → `/live/` |
| `lseg-feed/` | Market-data connection and local pricing API | `/opt/lseg-feed/` | `lseg-feed.service` | `127.0.0.1:8091` (internal only) |
| `prediction-api/` | Prediction and paper-signal API | `/opt/prediction-api/` | Check installed unit name | `127.0.0.1:8003` → `/prediction/` |
| `website/` | Static landing page | `/var/www/sinnfund/` | Served by Nginx | `/` |
| `deploy/nginx/` | Version-controlled Nginx virtual host | `/etc/nginx/sites-available/` | `nginx.service` | HTTPS site and reverse proxy |

Service-specific setup, implementation details, and dependencies are documented in the README in each component directory. `notes.md` contains additional project notes.

## Repository layout

```text
sinnfund-infra/
├── README.md
├── .gitignore
├── deploy/
│   └── nginx/
│       └── sinnfund.jkoh.dev
├── website/
│   ├── index.html
│   └── deploy.sh
├── flex-ingest/
│   ├── flex-ingest.py
│   ├── requirements.txt
│   ├── README.md
│   └── deploy/
├── flex-web/
│   ├── web.py
│   ├── parse_flex_positions.py
│   ├── requirements.txt
│   ├── README.md
│   └── deploy/
├── flex-web-live/
│   ├── web-live.py
│   ├── parse_flex_positions_live.py
│   ├── requirements.txt
│   ├── README.md
│   └── deploy/
├── lseg-feed/
│   ├── feed_api.py
│   ├── flex_lseg_ric.py
│   ├── requirements.txt
│   ├── README.md
│   └── deploy/
├── prediction-api/
└── notes.md
```

## Data and configuration

| Location | Contents | Git policy |
|---|---|---|
| `/var/lib/flex-ingest/flex/data/YYYYMMDD/<book>.xml.gz` | Archived IBKR statements; source of truth for the dashboards | **Never commit** |
| `/opt/flex-ingest/.env` | Flex Web Service credentials and query configuration | **Never commit** |
| `/opt/lseg-feed/.env` | LSEG authentication credentials | **Never commit** |
| `/opt/lseg-feed/lseg-symbols.env` | Configured symbol/RIC mappings | Keep out of Git in the current setup; use a sanitized example if needed |
| `prediction-api/data/`, `logs/`, `submitted_predictions/` | Generated predictions and runtime state | **Never commit** |
| `venv/`, `.venv/`, `__pycache__/` | Python environments and generated files | **Never commit** |

No IBKR or LSEG account session is needed to **display already archived** closing positions. `flex-web-live` contacts only the local LSEG API; its credentials belong to `lseg-feed`, not to the dashboard.

## Deployment

### Application services

Changes pushed to GitHub **do not automatically update** running services. Deploy reviewed changes from this repository into the corresponding `/opt/<service>/` directory, preserving production `.env` files, state, and virtual environments. Then restart the affected service.

For example, for a change to the previous-close dashboard:

```bash
# Run from the repository root on the VPS.
sudo install -m 644 flex-web/web.py /opt/flex-web/web.py
sudo install -m 644 flex-web/parse_flex_positions.py /opt/flex-web/parse_flex_positions.py
sudo systemctl restart flex-web.service
sudo systemctl status flex-web.service --no-pager
```

For dependency changes, install the updated `requirements.txt` into the service's existing virtual environment as part of deployment. For modifications to `.service` or `.timer` units, install the reviewed unit file into `/etc/systemd/system/`, run `sudo systemctl daemon-reload`, then restart or re-enable the relevant unit as needed.

**Do not** recursively copy a repository over `/opt` or overwrite production secrets and data. Source-code updates should preserve intended ownership and service-account access.

### Website

```bash
# Run from the repository root.
sudo install -m 644 website/index.html /var/www/sinnfund/index.html
```

Nginx serves this file directly; an Nginx reload is not required for a normal HTML update. Review `website/deploy.sh` before using it, as its behavior depends on its current contents.

### Nginx

The active site configuration should be:

```text
/etc/nginx/sites-available/sinnfund.jkoh.dev
/etc/nginx/sites-enabled/sinnfund.jkoh.dev
    -> /etc/nginx/sites-available/sinnfund.jkoh.dev
```

Deploy the reviewed configuration, validate it, then reload:

```bash
sudo cp -a /etc/nginx/sites-available/sinnfund.jkoh.dev \
  /etc/nginx/sites-available/sinnfund.jkoh.dev.bak
sudo install -m 644 deploy/nginx/sinnfund.jkoh.dev \
  /etc/nginx/sites-available/sinnfund.jkoh.dev
sudo nginx -t && sudo systemctl reload nginx
```

If validation fails, restore the backup and re-test before reloading. The global `/etc/nginx/nginx.conf` remains separate; its wildcard include loads enabled sites.

## Operations

```bash
# View services and scheduled ingestion.
systemctl status flex-ingest.service flex-web.service flex-web-live.service lseg-feed.service
systemctl list-timers flex-ingest.timer

# Run an ingestion cycle manually (independent of the timer).
sudo systemctl start flex-ingest.service

# Inspect recent logs.
journalctl -u flex-ingest.service -n 50 --no-pager
journalctl -u flex-web.service -n 50 --no-pager
journalctl -u flex-web-live.service -n 50 --no-pager
journalctl -u lseg-feed.service -n 50 --no-pager

# Check the two dashboards without going through Nginx.
curl -fsS http://127.0.0.1:8001/healthz
curl -fsS http://127.0.0.1:8002/healthz

# Inspect the market-data service's health/status.
curl -i http://127.0.0.1:8091/health

# Check the HTTPS landing page.
curl -I https://sinnfund.jkoh.dev/
```

The dashboard `/healthz` endpoints check archive availability. The LSEG `/health` endpoint may report a disconnected or closed-market state outside streaming hours; inspect its JSON rather than assuming market connectivity is required around the clock. The LSEG API runs continuously using `lseg-feed.service`; **no `lseg-feed.timer` is required**.

## Security and access

- **Private repository:** restrict access to authorized contributors. Avoid committing secrets, private keys, portfolio archives, generated predictions, or logs. Audit staged changes before the first commit and every subsequent push.
- **Human developers:** use individual Linux accounts and the `trading-dev` group for appropriately shared source files.
- **Service accounts:** `svc-flex` runs the read-only Flex dashboards and needs archive read access; `svc-lseg` runs the LSEG API and needs access to its own credentials. Keep service accounts non-login and grant only required filesystem permissions. Check each installed systemd unit for its actual `User=` value.
- **Network boundaries:** bind Python APIs to `127.0.0.1` and expose only intended paths through Nginx. The internal LSEG pricing API should not have a public reverse-proxy route.
- **Authentication:** the dashboard applications do not implement user authentication. Protect sensitive portfolio pages at the reverse proxy or other access-control layer before exposing them to untrusted users.
- **Deployment authority:** write access to code executed by a credential-bearing service can effectively grant access to that service's secrets. Limit who can modify and deploy such code.

## Development workflow

Use a feature branch for changes, review the diff, then merge into `main`. On the VPS, deploy the approved revision explicitly and verify service logs and application health.

```bash
git switch -c feature/example-change
# Edit files and review the diff.
git add <changed-files>
git diff --cached --check
git diff --cached
git commit -m "Describe the change"
git push -u origin feature/example-change
```

For environment-specific setup or troubleshooting, consult the individual component READMEs and the checked-in systemd unit files under each component's `deploy/` directory.
