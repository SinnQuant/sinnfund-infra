# ADR-0017: Exclude unsupported positions rather than invent stock-like risk

- **Date:** 2026-10-24
- **Status:** Accepted — interim model scope

## Context

Portfolio holdings include options, warrants, foreign-currency stocks, and instruments with insufficient history. A simple linear stock-return shock is not a valid substitute for nonlinear derivative repricing or a missing FX conversion.

## Options considered

- Treat every position as a vanilla stock and assign any convenient return.
- Give absent series zero returns or silently remove them.
- Model only explicitly supported, well-valued securities and disclose exclusions.

## Decision

In Stage 3, model USD-denominated `STK` rows (including applicable ETFs) with reliable signed USD values and valid Stage 2 returns. Leave options/warrants, unknown-valued, non-USD and missing-return positions outside the modeled P&L; classify and disclose every exclusion by reason and known value.

## Rationale

A transparently incomplete model is preferable to false precision. It permits an actionable prototype without representing unsupported instruments as risk-free.

## Consequences and limitations

Portfolio risk is materially partial: as of Oct 22, approximately $208,923 of *known-valued* gross exposure was excluded, while ten positions had unresolved USD values. The exact true modeled percentage is undefined while valuations are missing.

## Follow-up / revisit criteria

Prioritize correcting missing ordinary equities/FX valuations and build a separate options/warrant repricer; avoid conflating 'LSEG doesn't have data' with 'model does not support this instrument'.

