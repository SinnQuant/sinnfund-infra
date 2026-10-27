# ADR-0005: Separate publicly readable reporting from privileged trade controls

- **Date:** 2026-10-13
- **Status:** Accepted (security boundary; trade-staging implementation ongoing)

## Context

The read-only platform's founding problem was poor class-wide visibility: the instructor alone controlled direct brokerage login and distributed weekly reports; the original locally hosted site was considered unreliable. This motivates **view access**, not broader authority to trade.

Two adjacent workflows are discussed but not part of the read-only risk pipeline:

1. **Trade staging:** Historically, populating orders required running a generated executable. The team is *considering* migration to IBKR BasketTrader, subject to product compatibility, authorized brokerage access, and an agreed review/approval process.
2. **Prediction research:** Other quant researchers may connect low-frequency equity long/short prediction engines. Any interface that turns forecasts into staged orders requires further design and authorization; the idea does not establish automatic execution.

The platform also includes API keys and LSEG-licensed feeds.

## Options considered

- A single unrestricted web API.
- Independent read-only reporting services and a protected trade-control API.
- Restrict the entire platform to administrators, preventing planned stakeholder access.

## Decision

Keep the `/close/`, `/live/`, and eventual `/var/` reporting surfaces **read-only**. Design trade staging and research prediction integration as separate workstreams, not implicit features of the read-only website. Require separate authorization for staging/submitting trades. Keep credentials and internal price-history/analysis endpoints outside public Nginx exposure by default.

## Rationale

This honors the stated reporting use case while limiting the consequences of unauthenticated requests.

## Consequences and limitations

Reduces attack surface for modifications, but public positions and model diagnostics may themselves be sensitive. A read-only endpoint is not automatically approved for public distribution; fund and data-provider permissions remain separate gates.

## Follow-up / revisit criteria

Before any production staging or execution capability, define user roles, authentication, approval and audit logs, CSRF/rate-limit controls, brokerage-account permissions, and production/sandbox separation. Evaluate IBKR BasketTrader feasibility separately (ADR-0025); scope prediction-signal input separately (ADR-0026).

