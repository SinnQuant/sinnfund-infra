# ADR-0018: Keep valid dollar-risk estimates when NAV is unknown, without fabricating percentages

- **Date:** 2026-10-24
- **Status:** Accepted — provisional reporting

## Context

The configured IBKR Flex XML did not include NAV summaries or explicit account-base metadata for all accounts. Yet an independently modeled subset of positions can yield dollar scenario P&L and VaR.

## Options considered

- Block all risk reporting until NAV extraction is repaired.
- Derive fake NAV from cash or gross positions to provide ratios.
- Report dollar risk on covered holdings while showing NAV-based metrics as unavailable.

## Decision

Produce dollar VaR/ES for modeled exposures, mark fund/account status as `partial_coverage`/`ready_provisional`, and leave NAV, leverage and VaR-as-%NAV as `null` until official account NAV is verified. Expose missing-value counts and known exclusions prominently.

## Rationale

Provides early committee utility while preserving financial honesty and the ability to distinguish 'unknown' from 'zero'.

## Consequences and limitations

The resulting dashboard is a research/prototype risk report, not a fully reconciled official fund-risk statement. A successful build or HTTP 200 is not proof of accounting completeness.

## Follow-up / revisit criteria

Repair saved Flex NAV/account-information fields and USD conversion, recompute dated Stage 3 reports, and independently reconcile totals to broker statements.

