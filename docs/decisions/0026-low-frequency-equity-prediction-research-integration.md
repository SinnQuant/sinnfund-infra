# ADR-0026: Define a future interface for low-frequency long/short equity prediction research

- **Date:** 2026-10-26
- **Status:** Proposed — research integration concept; no end-to-end trade workflow confirmed

## Context

SINN Fund has a separate **prediction** project: quant-research students are expected to connect prediction engines producing **low-frequency long/short equity signals**. The model cadence, input and signal contracts, evaluation process, ownership, and whether signals become trade candidates remain design tasks.

This is related to the broader hedge-fund-like classroom goal, but it is **not** part of the operating read-only Flex/LSEG/Stage 1–4 risk pipeline, and should not be portrayed as automated brokerage execution.

## Alternatives being evaluated

- Researchers produce offline reports or files for human review.
- Researchers submit standardized prediction/signal artifacts to a restricted API or staging queue.
- Direct prediction-to-order submission (not selected; would introduce authorization and execution risk).

## Proposed direction

Define a **versioned, authenticated, non-executing research-signal contract** (instrument ID, long/short direction, generated-at time, intended horizon, model/version/provenance, optional confidence, and approval state). Let authorized reviewers decide whether a signal should be considered for the separate trade-staging process. Specific schema fields and technology remain proposals.

## Rationale

A common interface can support multiple student research teams without requiring direct brokerage credentials, while preserving reproducibility, accountability, and a boundary between research and trading.

## Risks and constraints

- Avoid conflating predictions, staged orders, accepted trades, and executed trades.
- Resolve researcher access permissions, strategy confidentiality, model evaluation, data licensing, and account-level trade authorization before deploying.
- Because this is low-frequency research, do not invent real-time latency requirements.

## Validation / decision gate

Agree on sample signal schema, ownership, review process, data retention and evaluation criteria; demonstrate one synthetic, non-executing model submission. Create a new accepted ADR only once an integration decision is made.

