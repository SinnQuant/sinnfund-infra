# ADR-0010: Use LSEG for market prices separately from IBKR accounting reports

- **Date:** 2026-10-20
- **Status:** Accepted

## Context

Once the project sought to move beyond instructor-controlled weekly reporting and the unreliable incumbent website, portfolio positions alone were not enough: reproducible market values and risk calculations also required a second, independently available market-data source. This extends—not replaces—the original transparency objective.

IBKR Flex delivers end-of-day account reporting but not the continuous quote stream or independent historical daily series needed by the website and risk engine. SINN Fund had access to LSEG EDP/Data Library entitlements.

## Options considered

- Treat Flex close prices as the only market data.
- Use an IBKR trading/session API for quotes.
- Use the existing LSEG market-data service for streaming/snapshots and history.

## Decision

Use **IBKR Flex for positions, lots and accounting**; use **LSEG** for delayed/live pricing and historical market shocks. Maintain a separate private LSEG feed application (not the Flex importer).

## Rationale

Keeps account truth and market data in independently testable components. Successful LSEG streaming was established after resolving `NotEntitled` issues with the appropriate service/network/field selections.

## Consequences and limitations

Two independent data providers and licenses increase integration/mapping work. Streaming quotes do not establish market-history availability or public redistribution rights.

## Follow-up / revisit criteria

Maintain entitlement tests and symbol mappings, document quote timestamps and delayed/live semantics, and confirm LSEG license conditions before publishing prices.

