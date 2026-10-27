# ADR-0014: Validate and align historical price returns before risk calculation

- **Date:** 2026-10-24
- **Status:** Accepted

## Context

Even when LSEG supplies a daily price history, symbols can have insufficient records, exchange-holiday mismatches, stale RIC mappings, non-trading days or suspect price jumps. Reusing inconsistent dates would make portfolio scenario totals mathematically misleading.

## Options considered

- Forward-fill or interpolate missing returns.
- Combine each ticker's latest N observations regardless of calendar.
- Validate a common anchor calendar and exclude incomplete or suspicious series.

## Decision

Create **Stage 2**: read the local LSEG SQLite cache and explicit mappings; use IVV's trading calendar as the common anchor; require N+1 accepted closes for N aligned one-day returns; reject calendar gaps, insufficient history, RIC conflicts and flagged outliers. Publish a dated `manifest.json`, `daily_closes.csv` and `daily_returns.csv`.

## Rationale

Each return row then represents one coherent market shock across the modeled universe, with clear inclusion/exclusion provenance.

## Consequences and limitations

Strict US-anchor alignment excludes legitimate Tokyo or other-market securities with different holidays; additional calendars/FX treatment are future work. Instrument count coverage alone is not exposure-weighted coverage.

## Follow-up / revisit criteria

Review exclusion manifest, align holidays by defensible financial methodology, and validate price-adjustment/dividend/corporate-action treatment.

