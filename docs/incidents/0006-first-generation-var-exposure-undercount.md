# INC-0006 — First-generation VaR undercounted known gross exposure

- **Event period:** Investigated around 2026-10-24
- **Category:** Financial data correctness / valuation
- **Status:** Legacy engine retired; complete Stage 1 accounting reconciliation remains open
- **Severity:** High for committee interpretation

## Observed behavior and impact
The first-generation `risk_engine.py` reported roughly **$2.56 million** in gross exposure and produced dollar VaR estimates, while the later independent Stage 1 audit reported **$5,741,030.78** in known gross exposure for the 2026-10-22 snapshot. The first figure could materially understate the portfolio fraction represented in its VaR model. The discrepancy must be reconciled by date and valuation definition before treating either amount as fully audited.

## Recovered code-level cause
An earlier branch used the pattern:

```python
if currency == 'USD':
    usd = value if base == 'USD' else float('nan')
```

This incorrectly marked a USD-denominated security as unvalued whenever the *account base-currency metadata* was missing. Security currency and account base are different attributes; an explicitly USD-denominated market value does not become unknown simply because the account base is absent.

## Investigation and response
- Audited raw Flex XML independently of the first VaR engine.
- Counted `OpenPosition` rows with `levelOfDetail=SUMMARY` to avoid counting tax lots as additional positions.
- Separated **known gross**, **modeled gross**, **unknown-valued positions**, and **official NAV**.
- Rebuilt the pipeline as Stage 1 accounting → Stage 2 market data → Stage 3 VaR → Stage 4 reporting.
- Retired the legacy `sinn-risk` reports rather than continuing to display two competing versions.

## Open questions / corrective actions
- Validate Stage 1 valuations against an approved broker statement and account-level currencies.
- Confirm that the new gross amount includes all eligible accounts once and no duplicated positions/lots.
- Add fixed synthetic tests where `currency=USD` but base currency is absent; verify gross/net arithmetic for long and short exposures.
- Make dashboard model coverage and exclusions mandatory fields, not implicit success.

## Related decisions
[ADR-0013](../decisions/0013-audit-flex-accounting-before-var.md) · [ADR-0021](../decisions/0021-retire-first-generation-risk-engine.md)
