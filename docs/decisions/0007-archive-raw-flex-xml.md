# ADR-0007: Treat raw compressed Flex XML as the immutable reporting source

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

The Flex API returns an XML report that can contain more detail than the initial website's view models. Narrow parsers and exports may omit information such as accounting metadata without the upstream report being truncated.

## Options considered

- Retain only derived positions/lots/trades/cash.
- Save the complete Flex response and derive views on demand or later.
- Request data repeatedly for every downstream feature.

## Decision

Archive the complete returned `FlexQueryResponse` in gzip under `/var/lib/flex-ingest/flex/data/YYYYMMDD/<book>.xml.gz`. Keep parsing and CSV/JSON projection downstream and separate from the archived original.

## Rationale

An unmodified report makes reprocessing, auditing and parser changes possible. This helped distinguish absent NAV *in the configured query* from fields filtered out by an older downstream `SECTIONS` whitelist.

## Consequences and limitations

Provides provenance, backfill ability and less vendor re-querying; adds data retention and access-control obligations. Do not silently overwrite original archives during query changes.

## Follow-up / revisit criteria

Version or checksum archival outputs, document query settings, retain access controls, and record provenance for every derived snapshot.

