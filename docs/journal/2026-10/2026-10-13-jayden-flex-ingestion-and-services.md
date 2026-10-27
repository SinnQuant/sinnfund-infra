# 2026-10-13 — Flex ingestion and service ownership

**Type:** implementation / operations  
**Status:** completed

## Context from previous discussions

- Automated archival of IBKR Flex statements and Linux service management.
- Systemd scheduling, read-only reports, and service-account permissions.

- Original problem (retrospectively clarified Oct 26): instructor-controlled brokerage login and weekly reports left class bets opaque between reports; Bloomberg Terminal was the only other described practical source.
- An incumbent locally hosted website existed, but stakeholders described unreliable data/service and difficult operator handoff; user complaints motivated independent hosting and automated reporting.
- Instructor wanted class practices to resemble a hedge fund with more transparent, consistent information.


## What was I trying to accomplish?

pull data from interactive brokers using the flex query web API token i was given.

## What I actually did / tested

- [x] developed PoC Python script to pull data at a regular interval
- [x] adapted Enoch provided script for full daily automation

## What I learned — in my own words

flex web tokens are not very well documented or supported. we may have to contact IBKR support to understand this IP restriction of error code 1025 i keep getting.

using systemd commands for managing services and timers efficiently. this is a lot more readable than cronjobs.

once we finish this, we can start displaying the ingested information with a nice web UI.
