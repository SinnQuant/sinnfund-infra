# SINN Fund — Architecture Decision Records

Architecture decisions for the SINN Fund platform, from portfolio reporting and data ingestion through risk analytics, institutional hosting, and proposed research integrations.

## Decision register

| ADR | Milestone | Date | Status |
| --- | --- | --- | --- |
| [ADR-0001](./0001-stakeholder-driven-read-only-platform.md) | Build an auditable, stakeholder-facing fund data platform | 2026-10-13 | Accepted |
| [ADR-0002](./0002-single-ubuntu-vps-first.md) | Host the first iteration on one Ubuntu Linux VM | 2026-10-13 | Accepted |
| [ADR-0003](./0003-ibkr-flex-for-unattended-close-data.md) | Use IBKR Flex Web Service for unattended end-of-day portfolio ingestion | 2026-10-13 | Accepted |
| [ADR-0004](./0004-systemd-automates-ingestion.md) | Use systemd services and timers for scheduled ingestion | 2026-10-13 | Accepted |
| [ADR-0005](./0005-separate-public-read-only-and-private-controls.md) | Separate publicly readable reporting from privileged trade controls | 2026-10-13 | Accepted (security boundary; trade-staging implementation ongoing) |
| [ADR-0006](./0006-lift-and-shift-cloud-before-rearchitecture.md) | Plan cloud migration as a like-for-like VM lift-and-shift | 2026-10-13 | Proposed — not yet deployed |
| [ADR-0007](./0007-archive-raw-flex-xml.md) | Treat raw compressed Flex XML as the immutable reporting source | 2026-10-14 | Accepted |
| [ADR-0008](./0008-service-boundary-fastapi-nginx.md) | Use small FastAPI services behind one Nginx HTTPS entry point | 2026-10-16 | Accepted |
| [ADR-0009](./0009-service-accounts-and-operator-access.md) | Run services with restricted identities and controlled operator access | 2026-10-20 | Accepted in principle; implementation evolved |
| [ADR-0010](./0010-lseg-as-independent-market-data-source.md) | Use LSEG for market prices separately from IBKR accounting reports | 2026-10-20 | Accepted |
| [ADR-0011](./0011-explicit-ticker-to-ric-mappings.md) | Maintain an explicit IBKR-symbol-to-LSEG-RIC mapping | 2026-10-20 | Accepted (provisional identifier linkage) |
| [ADR-0012](./0012-lseg-history-private-sqlite-cache.md) | Cache LSEG daily historical closes in SQLite on the host | 2026-10-24 | Accepted |
| [ADR-0013](./0013-audit-flex-accounting-before-var.md) | Separate and audit IBKR portfolio accounting before calculating risk | 2026-10-24 | Accepted |
| [ADR-0014](./0014-strict-synchronized-market-scenarios.md) | Validate and align historical price returns before risk calculation | 2026-10-24 | Accepted |
| [ADR-0015](./0015-hundred-scenarios-for-prototype.md) | Use 100 validated historical scenarios in the initial prototype | 2026-10-24 | Accepted — prototype parameter |
| [ADR-0016](./0016-portfolio-level-historical-simulation.md) | Calculate VaR by aggregating signed per-account scenario P&Ls | 2026-10-24 | Accepted — provisional model |
| [ADR-0017](./0017-conservative-model-exclusions.md) | Exclude unsupported positions rather than invent stock-like risk | 2026-10-24 | Accepted — interim model scope |
| [ADR-0018](./0018-publish-dollar-risk-without-nav.md) | Keep valid dollar-risk estimates when NAV is unknown, without fabricating percentages | 2026-10-24 | Accepted — provisional reporting |
| [ADR-0019](./0019-read-only-stage4-over-stage3-artifacts.md) | Publish a read-only Stage 4 dashboard over versioned Stage 3 reports | 2026-10-24 | Accepted |
| [ADR-0020](./0020-dated-risk-snapshots-vs-price-history.md) | Treat historical scenarios and historical risk-report dates as different dimensions | 2026-10-24 | Accepted |
| [ADR-0021](./0021-retire-first-generation-risk-engine.md) | Retire the first-generation VaR engine rather than carry two risk-report pipelines | 2026-10-24 | Accepted — executed in operator procedure |
| [ADR-0022](./0022-notes-explain-unmodeled-securities.md) | Annotate model exceptions on the website without altering VaR logic | 2026-10-24 | Accepted — presentation-only |
| [ADR-0023](./0023-tamu-kion-governance-for-public-cloud.md) | Route institutional AWS hosting through TAMU Kion and governance | 2026-10-26 | Proposed — approvals pending |
| [ADR-0024](./0024-version-controlled-engineering-history.md) | Maintain ADRs and a living engineering record alongside code | 2026-10-26 | Accepted — record initiated with this set |
| [ADR-0025](./0025-modernize-trade-staging-baskettrader.md) | Evaluate BasketTrader instead of generated trade-staging executable | 2026-10-26 | Proposed — feasibility assessment pending |
| [ADR-0026](./0026-low-frequency-equity-prediction-research-integration.md) | Define low-frequency equity prediction integration | 2026-10-26 | Proposed — interface undecided |

## How to maintain these records

1. Record **Context → Options → Decision → Rationale → Consequences → Follow-up** when a consequential choice is made.
2. Keep accepted ADRs immutable in substance; mark an old ADR **Superseded** and link the new ADR if a decision changes.
3. Separate **proposed/under evaluation** from actually deployed functionality. Do not record organizational approval until it is granted.
4. Link GitHub issues, pull requests, commits, tests and incident reports to each decision.
5. Keep vendor credentials, account identifiers, contract-sensitive data, raw LSEG market data, and nonpublic financial details out of public repositories.

## Original project context

The initial motivation was not the absence of any website: a locally hosted version already existed, but stakeholders reported inconsistent data and poor maintainability/handoff. The instructor's sole brokerage login and weekly reports left the class without timely independent view of positions, despite an educational goal resembling hedge-fund operations. The read-only information platform, trade-staging modernization, and researcher prediction interface are separate workstreams; see `../product/project-vision.md`.

## Associated operational documentation

- Main project pipeline README (existing): `README.md`
- Deployment/service configuration and test evidence should be linked here after repository integration.
- Keep a separate journal under `docs/journal/` for day-to-day experiments, which are *not* automatically architecture decisions.
