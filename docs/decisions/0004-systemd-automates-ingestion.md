# ADR-0004: Use systemd services and timers for scheduled ingestion

- **Date:** 2026-10-13
- **Status:** Accepted

## Context

The instructor-controlled weekly reporting cadence left students without reliable visibility between reports, and the incumbent local website was described as inconsistent. Automation needed to replace human-triggered retrieval with a reproducible, monitored schedule; a timer firing does not itself guarantee a successful, complete statement.

Daily fund statements and market data must arrive without operator login. The initial deployment already uses a persistent Ubuntu host, making systemd an available scheduler and supervisor.

## Options considered

- `systemd` service/timer units.
- Cron jobs.
- Ad hoc SSH/manual execution or a separate workflow orchestrator.

## Decision

Package recurring ingestion as a **oneshot systemd service plus a calendar timer**, with journal logs, controlled service identity and a timer tied to the reporting schedule. The Flex timer evolved to an early-morning Tuesday–Saturday Eastern schedule for prior-day statements.

## Rationale

systemd integrates restart/error reporting, unit permissions and persistent missed-run handling (`Persistent=true`) without adding infrastructure.

## Consequences and limitations

Benefits: reproducible operator commands (`systemctl`, `journalctl`) and unattended operation. Tradeoffs: `OnCalendar` alone does not establish data freshness or a dependency graph; provider failure can still yield missing reports.

## Follow-up / revisit criteria

Record the *installed* unit schedules rather than assuming a historical version. Add freshness assertions, alerting and an ordered dependency chain before treating daily results as production-grade.

