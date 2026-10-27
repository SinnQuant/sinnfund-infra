# SINN Fund — Project motivation, stakeholders, and workstreams

**Date:** 2026-10-26  
**Status:** Product context and workstream roadmap

## Why the system exists

The instructor wants the class to resemble a functioning hedge fund: students should be able to understand exposures, evaluate decisions and work from reliable shared portfolio information. Before this initiative, the instructor alone controlled the relevant brokerage login and distributed weekly reports. Between reports, the class's positions and bets were effectively a black box for most participants. A Bloomberg Terminal was described as the only other practical way of gathering portfolio information.

A **locally hosted website already existed** but was not a dependable solution: stakeholders reported inconsistent service/data quality, and the original author was not cooperative in maintaining or handing off the system. Students/users raised complaints about missing transparency and unreliable data. 

The new platform is meant to solve the **access, continuity and reliability problem**, not merely replace one web interface with another. It should make information available on a predictable cadence, identify the reporting timestamp/source, detect incomplete data, and be operable by the organization rather than dependent on a single individual.

## Stakeholders and needs

| Stakeholder | Need / responsibility | Distinction |
| --- | --- | --- |
| Instructor / fund owner | Official source/permissions for brokerage data and trades; class oversight | Direct brokerage login is not the same as read-only data access |
| Student investors / class | Access to reasonably timely, consistent holdings and fund reporting | Transparency for participants is not automatic permission for Internet publication |
| Quant-research students | Future pathway to contribute low-frequency long/short equity predictions | Prediction data is not an authorized order |
| Fund leadership / board | Reliable monitoring and auditability across accounts | Risk figures must disclose unvalued or excluded exposures |
| Platform operators | Monitor ingestion, recover failures, document the deployment and manage access | Operational ownership should survive a developer handoff |
| TAMU / licensed data owners | Approve funding, security posture and data sharing where applicable | A funded EC2 instance does not itself authorize public data distribution |

## Workstream A — Portfolio visibility and risk reporting (implemented, provisional)

```text
IBKR Flex archives + LSEG market data
             |
             v
  Portfolio views / accounting (Stage 1)
             |
             +---- LSEG history QA (Stage 2)
             |                 |
             +------ Stage 3 VaR/ES
                             |
                       Stage 4 website
```

Purpose: provide repeatable, dated, read-only positions, valuations and risk estimates without relying on instructor-created weekly reports. This includes the existing close/live views and the newer Stage 1–4 risk pipeline. Existing Stage 3 results remain **provisional** while official NAV, certain USD conversions and unsupported positions are unresolved.

**Non-goals:** no brokerage order submission, no requirement for sub-second execution, and no promise that all positions can be modeled as ordinary equities.

## Workstream B — Trade staging (existing legacy workflow; modernization proposed)

**Previous workflow:** populate trade orders by running a generated executable. **Idea:** migrate the staging workflow to **IBKR BasketTrader, if supported**, so orders can be prepared and reviewed without relying on the generated executable. BasketTrader integration remains proposed; the existing execution controls are unchanged.

Proposed boundaries: stage proposed orders, validate identifiers/quantities/permissions, obtain review/authorization, and separate submission/execution from both staging and public reporting. See [ADR-0025](../decisions/0025-modernize-trade-staging-baskettrader.md).

## Workstream C — Prediction research (future integration concept)

Quant-research students may connect **low-frequency equity long/short prediction engines**. A future interface could accept versioned research signals for evaluation and possible authorized staging; signal generation itself is neither a trade nor approval to execute. The data contract, approval procedure and operational integration remain future design work. See [ADR-0026](../decisions/0026-low-frequency-equity-prediction-research-integration.md).

## Design principles implied by the original problem

1. **Predictable transparency:** Stakeholders should not have to wait for one person's manually generated weekly report to see authorized portfolio views.
2. **Observable data quality:** Show source, effective date, last successful update and completeness/coverage warnings; do not silently publish stale values as current.
3. **Ownership and handoff:** Document service accounts, runbooks, incident process and recovery paths so the platform is not hostage to a single author.
4. **Strict privileges:** Reporting is read-only; prediction/research contribution, trade staging, approval and execution are separate permission levels.
5. **Auditability:** Preserve dated raw broker statements and model artifacts; distinguish data from estimates, proposals and actual executions.
6. **Publication rights:** Verify what the instructor/fund authorizes for classroom access versus public Internet access and what IBKR/LSEG agreements permit.

## Acceptance criteria to agree with stakeholders (not yet signed off)

- Define reporting SLA/freshness: how quickly the close report should become visible and what happens after a failed ingest.
- Verify account and position completeness against instructor-approved statements and display data provenance.
- Choose intended audience (class only, designated board, or public) and enforce appropriate access.
- Document how student complaints are captured and whether reliability/transparency has improved against a measured baseline.
- Establish a staged trade approval workflow separately from research-signal ingestion and the risk dashboard.

## Related records

- [ADR-0001 — Platform motivation](../decisions/0001-stakeholder-driven-read-only-platform.md)
- [ADR-0003 — Automated Flex ingestion](../decisions/0003-ibkr-flex-for-unattended-close-data.md)
- [ADR-0005 — Public data vs trade controls](../decisions/0005-separate-public-read-only-and-private-controls.md)
- [ADR-0025 — Trade staging concept](../decisions/0025-modernize-trade-staging-baskettrader.md)
- [ADR-0026 — Prediction research concept](../decisions/0026-low-frequency-equity-prediction-research-integration.md)
