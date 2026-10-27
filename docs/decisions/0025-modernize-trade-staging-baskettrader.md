# ADR-0025: Evaluate replacing generated trade-staging executable with IBKR BasketTrader

- **Date:** 2026-10-26
- **Status:** Proposed — evaluation only; no BasketTrader migration recorded

## Context

A separate SINN Fund **trade-staging** workflow previously required users to run a **generated executable** to populate orders. This creates an operator dependency and is distinct from the read-only Flex/LSEG/Stage 1–4 reporting pipeline. The project owner is considering migration to **Interactive Brokers BasketTrader**, if technically and operationally feasible.

The existing instructor-owned brokerage login and financial consequences of trade submission make authorization and review central. BasketTrader compatibility, import formats, account structure and workflow require feasibility testing.

## Alternatives being evaluated

- Retain the generated executable and document/maintain it.
- Generate a supported basket/order-import file for a human to review and import using BasketTrader, if supported.
- Build a separately authenticated staging interface or integration with approved brokerage tooling.

## Proposed direction

**Investigate BasketTrader as a replacement for manual executable-based order population**, starting with a non-executing, human-reviewed staging prototype. Keep staging separate from actual order submission, and keep execution outside public reporting APIs.

## Rationale

Reduce fragile manual steps and improve visibility/auditability of proposed trades, while keeping the instructor or another authorized operator in control of execution.

## Risks and constraints

- BasketTrader support, import format, entitlement, account permissions, and workflow details require feasibility testing.
- Staging data, proposed allocations, and account access may be sensitive even before execution.
- Do not conflate saved/staged orders with authorized or filled trades.
- Approval ownership, order validation, rollback, and audit logging require explicit design.

## Validation / decision gate

Demonstrate an end-to-end *sandbox or non-executing* basket import with validation of symbols, accounts, quantities, short permissions, and operator approval. Record a separate accepted ADR after feasibility is proven.

