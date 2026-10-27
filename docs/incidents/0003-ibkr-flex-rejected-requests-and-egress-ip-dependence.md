# INC-0003 — IBKR Flex requests returned 1001/1025 and differed by outbound IP

- **Event period:** Approximately 2026-10-14–2026-10-16
- **Category:** External API availability / ingestion
- **Status:** Intermittent failure investigated; definitive IBKR-side cause not confirmed

## Observed behavior and impact
Scheduled Flex ingestion produced IBKR error **1001**, followed by **1025** ("Too many failed attempts. Please review your configuration."). The problem persisted for roughly 24 hours in the reported debugging period. The IBKR browser `GetStatement` view also showed 1025 on 2026-10-15 at approximately 4:51 PM EDT. When ingestion fails, a new archive may not be generated and the website can display an older reporting date.

## Diagnostic work
1. Reviewed `SendRequest` / `GetStatement` calls, query ID, API token, and date arguments.
2. Compared requests initiated on the Hetzner host with requests from a local machine or through another outbound IP.
3. Found a failing path from the Hetzner egress IP and working paths from other locations using the same general workflow.
4. Distinguished a configured Flex report (controlled by query ID) from the token itself; the client `pull()` function was not found to strip NAV fields from raw XML.

## Assessment
**IP-specific restriction, throttling, or provider policy was a plausible explanation, not a confirmed root cause.** IBKR did not provide a definitive diagnosis in the available record. Error 1025 alone cannot establish a ban. Requests may also fail for account/query permissions or rate limits.

## Mitigation and outcome
The project retained raw Flex archival and scheduled retry procedures while evaluating alternate hosting and egress. Do **not** treat cloud migration as a guaranteed fix: repeat a controlled `SendRequest` and `GetStatement` test from the eventual TAMU cloud egress address before production cutover.

## Prevention / action items
- Log timestamp, stage (`SendRequest` vs `GetStatement`), response code, retry count and masked error text; never log full tokens or complete authenticated URLs.
- Bound retries and avoid escalating to persistent 1025 conditions.
- Alert when no dated raw archive is available, and expose data freshness to users.
- Track API permissions, query IDs and outbound IP changes in a private operations record.

## Related decisions
[ADR-0003](../decisions/0003-ibkr-flex-for-unattended-close-data.md) · [ADR-0006](../decisions/0006-lift-and-shift-cloud-before-rearchitecture.md) · [ADR-0007](../decisions/0007-archive-raw-flex-xml.md)
