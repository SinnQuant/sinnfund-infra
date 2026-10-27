# INC-0012 — Flex ingest failed on a day the operator did not expect it to run

- **Event period:** 2026-10-26
- **Category:** Scheduling / operational observability
- **Status:** Open — root cause and intended schedule need confirmation

## Observed behavior
The operator showed `flex-ingest.service` in a failed state (`status=1/FAILURE`) around **2026-10-26 20:30 UTC**, with `TriggeredBy: flex-ingest.timer`. The service log contained a reference to `20261025`. The operator clarified that the ingestion job was **not supposed to run that day**.

The triggering mechanism remains under investigation. Inspect loaded timer settings, manual invocation history and persistent catch-up behavior; `TriggeredBy` alone does not identify the initiating action.

## Immediate questions
- What does the **currently loaded** `OnCalendar` expression say, and which timezone does systemd apply?
- Is `Persistent=true` causing a catch-up activation after the timer or host was inactive?
- Does the program's default reporting-date logic map Monday to Sunday when it should select Friday or an intended brokerage processing date?
- Was a manual `systemctl start` or another unit/timer invocation involved?

## Evidence-gathering commands
```bash
systemctl cat flex-ingest.timer flex-ingest.service
systemctl list-timers --all | grep flex-ingest
systemd-analyze calendar 'Tue..Sat *-*-* 06:10:00 America/New_York'
journalctl -u flex-ingest.timer -u flex-ingest.service \
  --since '2026-10-26 00:00:00' --no-pager
```

The sample `systemd-analyze` expression above is **illustrative**, not an assertion about the currently deployed schedule. Use the actual `OnCalendar` expression for final validation.

## Follow-up
Confirm intended trading-day/report-availability semantics, time zone and holiday calendar, record the actual loaded timer, and fix only after reproducing the trigger. Add idempotent file checks and separate alerts for unexpected runs versus legitimate missing reports.

## Related decisions
[ADR-0004](../decisions/0004-systemd-automates-ingestion.md) · [ADR-0007](../decisions/0007-archive-raw-flex-xml.md)
