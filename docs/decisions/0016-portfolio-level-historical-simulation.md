# ADR-0016: Calculate VaR by aggregating signed per-account scenario P&Ls

- **Date:** 2026-10-24
- **Status:** Accepted — provisional model

## Context

Investment committee reporting requires both account-level and fund-level downside-risk estimates. Summing account VaR numbers incorrectly ignores offsets between accounts, and modeling shorts with absolute values loses the sign of risk exposure.

## Options considered

- Sum standalone account VaRs to estimate total fund VaR.
- Apply synchronized historical asset returns to **signed** current dollar exposures and sum scenario P&L before quantiles.
- Introduce full Monte Carlo pricing before core accounting is reliable.

## Decision

Stage 3 uses frozen holdings for the reporting date: `PnL[a,t] = sum_i(V[a,i] * r[i,t])`, including signed short exposure. Combine `PnL[fund,t] = sum_a PnL[a,t]`, then calculate empirical 95%/99% one-day VaR, Expected Shortfall and other risk measures on the loss distribution.

## Rationale

Preserves diversification and long/short netting under identical historical shocks, with a transparent audit trail of daily scenario P&L.

## Consequences and limitations

Outputs describe hypothetical shocks to today's positions, **not actual historical fund returns** or a maximum possible loss. The 100-day tail remains unstable and the method is only as complete as instrument coverage.

## Follow-up / revisit criteria

Verify account-versus-fund scenario reconciliation and independent test portfolios; add VaR backtesting when actual forward dates are available.

