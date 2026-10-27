# INC-0010 — VaR model covered only a subset of portfolio exposures

- **Event period:** 2026-10-24, 2026-10-22 report
- **Category:** Model completeness / finance risk
- **Status:** Open; transparently disclosed in Stage 4
- **Severity:** High for interpretation of dollar VaR

## Observed report
- 25 accounts; 400 reported position rows; 100 market shocks.
- **$5,741,031** in *known-valued* gross exposure.
- **$5,532,108** of that gross was modeled; **$208,923** in known-valued gross was excluded.
- **10 unvalued positions**: true total exposure coverage could not be computed.
- Provisional fund VaR95 **$65,183** and VaR99 **$91,281**; the dollar figures exclude unsupported/unvalued risks.

## Exclusion mechanisms
1. `nonlinear_or_unsupported_asset`: options, warrants, and other instruments for which a simple stock-return shock is not an adequate risk model.
2. `not_in_validated_stage2_returns`: missing or rejected 100-day series; e.g., SPNS had $2,911.15 known exposure but no eligible return column. Do not assume a specific corporate-action cause without independent verification.
3. `unknown_valuation`: currency/account metadata or FX conversion not resolved for holdings such as `4063.T`, `8136.T`, `ARA`, and `ATZ`.

Account `16537BCE` had $15,394 in known gross exposure and zero modeled positions because both positions were derivatives. Account `5EE62A8E` had roughly 40.21% modeled coverage, largely from 20 unsupported instrument rows plus one missing return series. These are **known model limitations**, not evidence that LSEG lacks all of those instruments.

## Response
Stage 3 refuses to invent returns, preserves signed exposures, and carries exclusions to the fund report. Stage 4 explicitly labels partial coverage, missing NAV, and individual exception reasons. The website note is not a correction to model completeness.

## Follow-up
- Fix Stage 1 valuation and NAV independently.
- Audit symbol/conid-to-RIC joins and unusual corporate actions.
- Add an appropriately tested nonlinear option/warrant and FX shock framework if comprehensive VaR is required.
- Validate scenario aggregation and explain that a successful API request is not a complete risk sign-off.

## Related decisions
[ADR-0017](../decisions/0017-conservative-model-exclusions.md) · [ADR-0018](../decisions/0018-publish-dollar-risk-without-nav.md) · [ADR-0022](../decisions/0022-notes-explain-unmodeled-securities.md)
