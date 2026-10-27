# ADR-0024: Maintain ADRs and a living engineering record alongside code

- **Date:** 2026-10-26
- **Status:** Accepted — record initiated with this set

## Context

The project accumulated important architectural pivots, debugging lessons and security/governance decisions across many ChatGPT conversations, code iterations, server operations and stakeholder discussions. Without a record, rationale and chronology become difficult to reconstruct.

## Options considered

- Rely on chat history and memory.
- Write one retrospective case study at completion.
- Maintain a dated engineering journal and numbered ADRs in the project repository.

## Decision

Create `docs/decisions/` with one ADR per consequential decision; keep a chronological index and distinguish accepted, proposed and superseded states. Add an engineering journal for implementation events and incidents, and keep documents linked to real commits/tests once available.

## Rationale

A durable, reviewable record improves onboarding, debugging, operational continuity, institutional accountability and evidence of actual technical ownership.

## Consequences and limitations

## Follow-up / revisit criteria

Commit these files to a private canonical repository, correct the chronology against Git/server logs, add commit/PR/issue links, and update status as implementation or approvals change.

