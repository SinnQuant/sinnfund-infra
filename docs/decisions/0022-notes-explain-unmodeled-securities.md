# ADR-0022: Annotate model exceptions on the website without altering VaR logic

- **Date:** 2026-10-24
- **Status:** Accepted — presentation-only

## Context

The dashboard reports uncovered positions, but stakeholders need an accessible explanation of whether the cause is missing market data, missing FX/accounting metadata or unsupported derivatives. The user explicitly requested a notes-only change, not a change to estimates.

## Options considered

- Hide account-specific exceptions.
- Automatically impute missing risk to remove gaps.
- Add report-dated explanatory notes while leaving Stage 1–3 unchanged.

## Decision

Add dated explanatory text to Stage 4's 'Model exceptions & committee notes', distinguishing options/warrants not supported by the linear equity model, JPY/CAD values unresolved in Stage 1, and missing validated return history for specific equities such as SPNS. Preserve source-calculated exclusions and nulls.

## Rationale

Improves interpretability and prevents the reader from inferring that LSEG was necessarily missing data whenever Stage 3 excluded a position.

## Consequences and limitations

Hard-coded annotations are accurate only for the Oct 22 report and must be labeled as such; they should not automatically explain future holdings without fresh audit data.

## Follow-up / revisit criteria

Eventually generate account-specific notes from the structured Stage 3 exclusion diagnostics instead of maintaining static symbol text.

