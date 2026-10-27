# ADR-0021: Retire the first-generation VaR engine rather than carry two risk-report pipelines

- **Date:** 2026-10-24
- **Status:** Accepted — executed in operator procedure

## Context

The original `/opt/sinn-risk/` pipeline generated its own `/var/lib/sinn-risk/report.json` and could disagree with the validated Stage 1–3 output. Running two risk engines behind similar paths causes ambiguous figures and operational confusion.

## Options considered

- Continue serving both risk engines.
- Keep the obsolete engine and patch its accounting behavior.
- Switch the UI to Stage 3 artifacts and retire the old implementation/reports.

## Decision

Stage 4 consumes new Stage 3 artifacts. Stop/remove the old `sinn-risk-*` service, scripts and generated reports after the cutover. **Do not remove `/opt/lseg-history/` or `/var/lib/lseg-history/`**: Stage 2 still requires the historical cache/refresh job.

## Rationale

One authoritative calculation path reduces chances of displaying conflicting VaR numbers, while preserving the ingest components that remain dependencies.

## Consequences and limitations

Deletion is irreversible and must target only identified obsolete units/paths; backups and a service inventory are needed before clean-up. 

## Follow-up / revisit criteria

Retain a superseded-design note with rationale and old limitations; verify all Nginx routes and service units after cleanup.

