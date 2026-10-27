# ADR-0013: Separate and audit IBKR portfolio accounting before calculating risk

- **Date:** 2026-10-24
- **Status:** Accepted

## Context

The first-generation `risk_engine.py` understated recognized exposure and could not obtain reliable NAV because of faulty currency/base assumptions. It was unsafe to treat unverified portfolio values as validated risk inputs.

## Options considered

- Patch the original monolithic risk engine and continue publishing results.
- Create an explicit Stage 1 accounting/position normalization and audit layer.
- Infer account NAV from sum of securities' market values or cash balances.

## Decision

Introduce **Stage 1**, reading full archived Flex XML and using `OpenPosition` `SUMMARY` rows only, preserving signed values, account boundaries and asset/currency attributes. Extract official account NAV/base currency only when explicit source fields support it; otherwise output `null` and audit issues. Never infer NAV from `CashReportCurrency.endingCash` or gross securities exposure.

## Rationale

This isolates accounting errors from risk methodology, prevents lot double-counting and exposes exact missing source fields.

## Consequences and limitations

On Oct 22 snapshot, 25 accounts were found and known-valued gross exposure was approximately $5.74M, versus roughly $2.56M in an earlier defective model. Official NAV and some FX values remain unresolved until saved Flex query/valuation corrections are completed.

## Follow-up / revisit criteria

Update Flex saved query to include account information and NAV summary, then rerun Stage 1 audit against archived/resubmitted statements without overwriting evidence. Verify foreign-currency conversion and ten unvalued positions.

