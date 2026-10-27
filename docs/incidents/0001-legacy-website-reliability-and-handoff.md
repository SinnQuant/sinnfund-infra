# INC-0001 — Pre-existing portfolio website was unreliable and difficult to hand off

- **Event period:** Before the new platform launched
- **Recorded:** 2026-10-26
- **Category:** Service reliability / institutional ownership
- **Status:** Problem motivating replacement; no measured closure criteria yet
- **Severity:** Portfolio information reliability and class transparency

## Observed behavior and impact
A locally hosted portfolio-information website already existed. The project owner reported inconsistent availability or data quality, difficulty obtaining cooperation from the original author, and complaints from users. A single instructor controlled the relevant brokerage login and delivered weekly reports, leaving class participants without dependable access to current holdings between reports. Bloomberg Terminal access was described as the only other practical information route.

## Investigation and underlying constraints
- Existing ownership and deployment procedures were not dependable enough to support a handoff.
- The brokerage login and weekly reporting were centralized; broad trading access was not an appropriate substitute for read-only visibility.
- The instructor wanted classroom processes to resemble a hedge fund, making information asymmetry an operational limitation.

## Response / architectural change
Developed an independently operated, read-only data platform with scheduled IBKR Flex ingestion, a market-data service, dated reports, and explicit operational documentation. Trading authority remains separate from viewing positions.

## Remaining risks / follow-up
- Agree on audience and authorized publication of account/position data; student visibility does not automatically authorize public Internet exposure.
- Establish measurable freshness, uptime and completeness targets, plus stakeholder feedback channels.
- Define durable ownership, handoff and escalation procedures independent of one student or instructor.
- Confirm whether the previous service can be decommissioned and what historical information must be retained.

## Related decisions
[ADR-0001](../decisions/0001-stakeholder-driven-read-only-platform.md) · [ADR-0002](../decisions/0002-single-ubuntu-vps-first.md) · [Project vision](../product/project-vision.md)
