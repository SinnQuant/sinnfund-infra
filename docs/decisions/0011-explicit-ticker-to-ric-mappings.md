# ADR-0011: Maintain an explicit IBKR-symbol-to-LSEG-RIC mapping

- **Date:** 2026-10-20
- **Status:** Accepted (provisional identifier linkage)

## Context

IBKR tickers and LSEG RICs do not share a universal spelling or primary-listing convention. Examples include Tokyo equities and exchange suffixes for US-listed ETFs/equities. Some identifiers are ambiguous across markets.

## Options considered

- Guess LSEG RIC from a ticker at every request.
- Maintain a curated `LSEG_SYMBOLS` mapping.
- Use definitive IBKR contract-ID-to-RIC mapping for all assets (desirable but not yet fully implemented).

## Decision

Store symbol-to-RIC pairs in `/opt/lseg-feed/lseg-symbols.env`, e.g. `4063.T=/4063.T` and `AAAU=/AAAU.K`. Verify that the historical record uses the corresponding eligible RIC; detect identifier collisions rather than silently pairing unrelated securities.

## Rationale

Explicit configuration makes operational exceptions inspectable and repeatable; guessing a RIC can silently corrupt return attribution.

## Consequences and limitations

A ticker-only join remains provisional despite collision checks. Corporate actions, listings and RIC changes can invalidate mappings. Future mapping should use stable IBKR contract identifiers and a reviewed vendor identifier table.

## Follow-up / revisit criteria

Build a reconciliation audit listing conid, IBKR symbol, RIC, currency, asset class and active dates; review mappings on changes.

