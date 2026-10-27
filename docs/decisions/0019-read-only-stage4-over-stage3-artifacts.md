# ADR-0019: Publish a read-only Stage 4 dashboard over versioned Stage 3 reports

- **Date:** 2026-10-24
- **Status:** Accepted

## Context

The original goal is dependable portfolio transparency for the class and intended fund stakeholders, in contrast with dependence on the instructor's weekly reports and an inconsistent legacy local website. The VaR view is an extension of that information-access project; displaying risk analytics does not make the dashboard an order-entry or research-signal execution portal.

The original `/var/` website consumed an obsolete risk-engine JSON schema. The new Stage 3 writes account and fund metrics, dated reports and scenario P&L in a clearer contract.

## Options considered

- Recompute VaR inside every HTTP request.
- Keep using the old `/var/lib/sinn-risk/report.json` format.
- Make Stage 4 a strictly read-only presentation adapter over Stage 3 artifacts.

## Decision

Use a separate FastAPI/Uvicorn website on `127.0.0.1:8093`, behind the existing Nginx `/var/` route, reading `/var/lib/sinn-stage3/latest.json` and dated `report.json`/`scenario_pnl.csv`. Stage 4 exposes a selector, distribution, per-account comparison, risk profile and model exceptions without trading/write routes.

## Rationale

Reporting remains available if LSEG/IBKR APIs are temporarily unreachable, and model code does not have to run in response to untrusted web requests.

## Consequences and limitations

The interface must validate Stage 3 schema and account labels; an overly restrictive account-identifier regular expression initially produced HTTP 503 until patched to support whitespace. Public release still requires data ownership and licensing review.

## Follow-up / revisit criteria

Keep Stage 4's account-ID patch in version control and tests; preserve null values and exclude raw credentials, identifiers and vendor price history from public endpoints.

