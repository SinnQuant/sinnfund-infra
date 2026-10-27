# ADR-0020: Treat historical scenarios and historical risk-report dates as different dimensions

- **Date:** 2026-10-24
- **Status:** Accepted

## Context

Stage 2 contains a time series of asset shocks; Stage 3 applies those shocks to positions frozen at a particular reporting date. It is tempting to mislabel 100 shocked P&Ls as 100 days of *realized* performance or 100 separate portfolio risk estimates.

## Options considered

- Draw 100-day portfolio risk trends directly from the one dated return matrix.
- Archive independently computed risk reports per actual holdings date.
- Publish an implied history without source portfolio positions.

## Decision

Write immutable-by-convention dated Stage 3 outputs under `/var/lib/sinn-stage3/YYYY-MM-DD/`, plus `latest.json` for the current dashboard. The risk-profile chart uses **one estimate per report date**; the scenario chart uses **100 shocks for one portfolio date**.

## Rationale

Keeps committee charts semantically correct and supports future trend/backtest work when additional daily holdings snapshots become available.

## Consequences and limitations

Initially the profile has one point. Reproducing a 500-day risk *trend* needs many dated portfolios and enough prior market data for each reporting date, not just 500 return observations.

## Follow-up / revisit criteria

Add report provenance and data freshness to each dated artifact and implement automated daily backfill/backtesting only when matching inputs exist.

