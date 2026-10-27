# SINN Fund — Engineering Journal

This is a **working notebook**, not a polished status report. Write in your own words; honest uncertainty and failed approaches are valuable.

## One file per meaningful work session

1. Copy `docs/journal/_templates/work-session.md` to `docs/journal/YYYY-MM/YYYY-MM-DD-topic.md`.
2. Begin a session by filling in the **question / goal** (one or two lines).
3. During the session, record key experiments, unexpected findings, links, and decisions. You do **not** need to document every command.
4. End by writing **What I learned** and **What I would do differently** yourself (two to five sentences is enough), plus the next step.
5. Commit the record with the relevant code when appropriate. Link an ADR for decisions expected to outlive the session.

If a session is mostly debugging, design, deployment, or stakeholder coordination, use the corresponding specialized template instead. Keep the same naming convention. For multiple sessions on one day, use a suffix or time: `2026-10-24-1430-stage3.md`.

## What belongs where?

| Record | Purpose |
| --- | --- |
| Session journal | What happened, what you observed, and what *you* learned |
| Architecture Decision Record (`docs/decisions/`) | A durable architectural decision and its tradeoffs |
| Git commit or PR | The exact code changes and tests |
| GitHub issue | An outstanding task, defect, or acceptance criterion |
| Runbook | Current, repeatable operational instructions |

Link these resources rather than duplicating them verbatim. If an incident reveals an enduring decision, link a separate ADR.

## Minimal entry (5 minutes)

If you're busy, fill in just:

```markdown
# [Date] — [Topic]
- **Objective:**
- **Changed / investigated:**
- **Evidence / result:**
- **Decision or open question:**
- **What I learned (in my words):**
- **Next action:**
```

## Session entries

The `2026-10/` directory contains dated work-session records. Add observations, relevant commits and follow-up actions as the project progresses.

## Security / confidentiality

Do not commit secrets, `.env` values, API tokens, SSH private keys, confidential account-level financial data, sensitive logs, nonpublic LSEG exports, or unapproved TAMU security details. Use redacted excerpts and references to secured systems. Keep the repository private unless ownership, distribution rights, and publication approvals have been resolved.

## Suggested session tags

`#ingestion` · `#market-data` · `#risk-model` · `#backend` · `#deployment` · `#security` · `#stakeholders` · `#documentation`
