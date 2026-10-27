# INC-0007 — Archived Flex statements omitted NAV/base-currency sections

- **Event period:** Identified around 2026-10-24 for report date 2026-10-22
- **Category:** Source-data completeness / accounting
- **Status:** Open; requires saved Flex Query change and revalidation
- **Severity:** High for NAV-normalized committee metrics

## Observed behavior
Stage 1 successfully parsed 25 reporting accounts but reported `NAV=None` for all. The raw XML inventory showed `CashReport` and `CashReportCurrency` records but **no `AccountInformation`, `EquitySummaryByReportDateInBase`, or `ChangeInNAV`** elements in the inspected source. `CashReportCurrency.endingCash` is a cash balance, not total NAV.

The parser's original `SECTIONS` whitelist filtered derived CSV/JSON exports, but the raw gzip archive was saved before that filtering. The missing official NAV in the inspected raw archive is therefore not explained by the derived-export whitelist.

## Impact
The pipeline could generate provisional dollar VaR for known-valued securities, but could not provide official account NAV, VaR/NAV, or gross leverage. Missing base currency also prevented reliable USD conversions for some non-USD holdings.

## Required remediation (not yet completed)
1. Update the **saved IBKR Activity Flex Query** to request account information and the Net Asset Value Summary in Base (and optionally Change in NAV), subject to available report fields.
2. Generate a new report and inspect actual XML tags before modifying the parser.
3. Preserve older archives when re-fetching; do not silently overwrite historical source data.
4. Re-run Stage 1 audit, reconcile account and fund NAV to a broker-authorized statement, then rebuild Stage 3.

## Acceptance criteria
Every expected account has a correctly dated and correctly denominated official NAV or an explicit justified exception. A parsed cash balance alone is **not** sufficient.

## Related decisions
[ADR-0007](../decisions/0007-archive-raw-flex-xml.md) · [ADR-0013](../decisions/0013-audit-flex-accounting-before-var.md) · [ADR-0018](../decisions/0018-publish-dollar-risk-without-nav.md)
