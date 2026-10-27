# ADR-0015: Use 100 validated historical scenarios in the initial prototype

- **Date:** 2026-10-24
- **Status:** Accepted — prototype parameter

## Context

Initial planning sought 500 return scenarios, but the readily validated data only supported a substantially shorter window for a large share of tickers. The user explicitly chose 100 trading days to proceed with end-to-end testing.

## Options considered

- Block development until 500 aligned return scenarios are available.
- Adopt 100 coherent daily shocks now and mark tail outputs provisional.
- Fabricate or forward-fill missing observations to reach 500.

## Decision

Set Stage 2 `--lookback 100 --anchor IVV` for the first integrated build and use its exactly 100 scenarios in Stage 3. Preserve the option to increase lookback after market-data remediation. Do not synthesize absent returns.

## Rationale

Unblocks integration while retaining an honest data-quality boundary.

## Consequences and limitations

One-day 99% VaR and ES draw on approximately the worst one to three observations and are statistically unstable; 95% VaR should be the primary prototype number. The packaged Stage 2 unit originally defaulted to 500, so installed service settings need explicit correction before automation.

## Follow-up / revisit criteria

Validate the 100-row return matrix, change installed build service to 100, and later expand to 250/500+ days with documented coverage and backtests.

