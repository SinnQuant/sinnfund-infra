# ADR-0003: Use IBKR Flex Web Service for unattended end-of-day portfolio ingestion

- **Date:** 2026-10-13
- **Status:** Accepted

## Context

At project inception, students depended on instructor-distributed weekly reports or access to a Bloomberg Terminal for portfolio visibility. The instructor held the direct brokerage login. This made unattended, permissioned extraction of the fund's positions a prerequisite for a more transparent, consistently updated class-facing website. This is the *original use case*; it does not mean the Flex token grants brokerage execution permission.

SINN Fund needs automated account positions, tax lots, trades, and cash information without requiring a person to complete an interactive brokerage login at every run. Flex statements are reports, not an execution interface.

## Options considered

- IBKR Flex Web Service using a saved query ID and token.
- Interactive Client Portal or TWS-related APIs.
- Downloading brokerage statements manually.

## Decision

Use the **Activity Flex Web Service** `SendRequest`/`GetStatement` workflow with configured token and saved query ID to obtain daily account reporting data. Treat it as an end-of-day accounting source, never as a live trading feed.

## Rationale

The token/query configuration permits unattended, read-only report retrieval. The alternative trading APIs have different authentication/session and operational requirements, and manual downloads do not scale.

## Consequences and limitations

Benefits: automatable reports and reproducible snapshots. Risks: saved query contents control which fields exist; API failure codes and outbound-IP behavior can stop ingestion; reports may be stale or incomplete and require explicit audits.

## Follow-up / revisit criteria

Record the saved query's selected sections, error/retry policy, and retention. Ensure NAV and account-information sections are included once Stage 1 is repaired.

