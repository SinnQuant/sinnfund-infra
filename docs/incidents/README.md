# SINN Fund — Incident and failure investigations

**Updated:** 2026-10-26

These reports record system failures, investigations, corrective actions, and follow-up work. Root causes remain open where the incident investigation is ongoing.

## Incident register

| ID | Topic | Event window | Current assessment |
| --- | --- | --- | --- |
| [INC-0001](./0001-legacy-website-reliability-and-handoff.md) | Pre-existing website reliability and handoff | Before Oct 2026 (undated) | Background / open |
| [INC-0002](./0002-local-port-conflict-during-service-integration.md) | Existing API port conflict | Oct 13–16 | Mitigated |
| [INC-0003](./0003-ibkr-flex-rejected-requests-and-egress-ip-dependence.md) | IBKR Flex API 1001 / 1025 failures | Oct 14–16 | Unconfirmed cause |
| [INC-0004](./0004-lseg-streaming-entitlement-errors.md) | LSEG NotEntitled streaming requests | Oct 16–20 | Mitigated |
| [INC-0005](./0005-lseg-history-sdk-and-service-environment.md) | LSEG history SDK / service environment | Oct 24 | Fix identified; verification needed |
| [INC-0006](./0006-first-generation-var-exposure-undercount.md) | Legacy VaR gross-exposure undercount | Oct 24 | Legacy retired; audit pending |
| [INC-0007](./0007-ibkr-flex-archives-missing-official-nav.md) | NAV absent from Flex archives | Oct 24 | Open |
| [INC-0008](./0008-stage2-historical-market-coverage-exceptions.md) | Stage 2 excluded 10 historical series | Oct 24 | Open / disclosed |
| [INC-0009](./0009-stage2-output-hidden-by-service-account-permissions.md) | Stage 2 output visibility / permissions | Oct 24 | Resolved |
| [INC-0010](./0010-stage3-incomplete-position-and-model-coverage.md) | Stage 3 incomplete model coverage | Oct 24 | Open / disclosed |
| [INC-0011](./0011-stage4-http-503-account-id-validator.md) | Stage 4 HTTP 503 / account alias validation | Oct 24 | Resolved |
| [INC-0012](./0012-flex-ingest-unexpected-monday-run-and-failure.md) | Unexpected Flex ingest run and failure | Oct 26 | Open |

## How to use

1. Add an issue or incident entry when a failure affects correctness, availability, data freshness, security boundaries, or important operational behavior. Not every development bug is a production incident; severity is evidence-based.
2. Capture the **reported time, effective reporting date, expected behavior, actual behavior, and evidence**. Avoid confusing a historical risk scenario date with a service outage date.
3. Separate **observations**, **hypotheses**, and **verified root cause**. Never rewrite an inference as confirmed because a workaround appeared to help.
4. Document mitigation, user impact, remaining unknowns and testable follow-up actions. Link relevant ADRs and commits. An incident documents a failure; an ADR documents a consequential decision taken in response.
5. For daily reflections use `../journal/`. For a new incident, copy [`_template.md`](./_template.md), name it `0013-meaningful-slug.md`, and update this register.

## Important security / data practices

- Keep this directory **private** until approved for public release. It discusses brokerage-data workflows, service architecture, and operational weaknesses.
- Do not commit tokens, credentials, raw financial statements, individual brokerage account IDs, private DNS/network inventories, or complete licensed LSEG market-data exports. Prefer sanitized log excerpts.
- Avoid storing unredacted vendor API request URLs or response headers that may contain session information.
- Public case studies should use synthetic financial data and separate organizational permission checks.

## Verification remaining

The most significant open financial-control issues are official NAV/base-currency availability and full securities-model coverage. The most significant open operational question is the unexpected Flex job invocation on October 26. AWS/TAMU migration and BasketTrader/prediction integration are *proposals*, not incidents and not completed deployments.
