# INC-0008 — Stage 2 market-history audit excluded 10 of 320 mapped instruments

- **Event period:** 2026-10-24, 2026-10-22 reporting snapshot
- **Category:** Data quality / model input validation
- **Status:** Exceptions disclosed; modeling gaps remain open

## Observed audit result
Command: `market_stage2.py audit --lookback 100 --anchor IVV --as-of 2026-10-22`

```text
eligible=310/320
calendar_gaps: 5
insufficient_history: 2
outlier_review: 3
```

Exceptions included Japanese listings `4063.T`, `8136.T`, and `9501.T` (US-anchor calendar gaps); `CCXI` and `ZSPC` (calendar gaps); `HONA` and `SPCX` (insufficient history); and `AMLX`, `MRNA`, and `PSQL` (outlier review). A flagged outlier is **not proof of incorrect market data**: it may reflect real news, split/corporate actions, mapping mistakes or a data adjustment issue.

## Impact
The Stage 2 matrix contains 100 synchronized historical daily returns for eligible names only. Ineligible securities must be excluded from Stage 3 rather than filled with fabricated returns. Instrument coverage (`310/320 = 96.875%`) does **not** equal portfolio exposure coverage.

## Response
- Selected 100 scenarios for the prototype rather than an initially planned 500.
- Preserved strict checks for missing prices and large changes; Stage 3 consumes only validated columns.
- Stage 4 discloses that 100-scenario 99% tail estimates have very small effective sample sizes.

## Follow-up
- Verify historical RIC mapping, exchange calendars, corporate-action adjustments and recent listings individually.
- Add native-market calendars and FX-aware risk treatment for non-USD stocks rather than assuming US trading-day coverage.
- Expand lookback only after the data and model checks pass, with risk impact comparisons before changing committee metrics.

## Related decisions
[ADR-0014](../decisions/0014-strict-synchronized-market-scenarios.md) · [ADR-0015](../decisions/0015-hundred-scenarios-for-prototype.md)
