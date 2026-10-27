# ADR-0012: Cache LSEG daily historical closes in SQLite on the host

- **Date:** 2026-10-24
- **Status:** Accepted

## Context

Historical risk estimation needs a reproducible multi-symbol dataset. Fetching live history directly during every risk computation would couple calculation time to credentials, entitlements, network failures and rate limits.

## Options considered

- Fetch all historical prices during every VaR calculation.
- Write a local SQLite daily-price cache from a separate periodic LSEG ingestion job.
- Introduce a managed database before the prototype is validated.

## Decision

Create a **separate LSEG history service** that periodically refreshes historical daily prices and caches `symbol, ric, date, close` in `/var/lib/lseg-history/prices.sqlite3`. Run a scheduled refresh (documented as 06:30 Eastern Tue–Sat). Keep the history API/cache private.

## Rationale

Makes market-data collection independent from scenario construction and enables deterministic re-runs for archived holdings.

## Consequences and limitations

Cache freshness and corporate-action adjustments must be checked. Streaming entitlement does not guarantee history entitlement. SQLite is adequate for current scale but needs disciplined backups and write/read concurrency management.

## Follow-up / revisit criteria

Record SDK version, entitlements, close adjustment semantics and currency; add cache-health checks and preserve data-provider redistribution limits.

