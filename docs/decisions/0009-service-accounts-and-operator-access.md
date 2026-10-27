# ADR-0009: Run services with restricted identities and controlled operator access

- **Date:** 2026-10-20
- **Status:** Accepted in principle; implementation evolved

## Context

Several collaborators need to inspect portfolio artifacts and restart selected services, while API tokens and data caches must remain protected. The server previously had interactive-user and group-permission complications.

## Options considered

- Run all services as root or a human login.
- Dedicated service identities with a limited shared operator group and narrowly granted service control.
- Broad shared write permissions for convenience.

## Decision

Use dedicated non-login service users (notably `svc-lseg` for LSEG and risk stages), restrict data directories, and grant named operators only the access needed for logs, archived reports and unit management. Use explicit sudoers/polkit rules where necessary instead of blanket root access.

## Rationale

Clarifies the boundary between processes that consume vendor credentials, viewers of read-only portfolio artifacts, and people who can change system state.

## Consequences and limitations

More robust isolation, but introduces Unix group, `HOME`/SDK configuration, filesystem ACL and systemd hardening complexity. Existing permission rules must be audited independently rather than assumed correct.

## Follow-up / revisit criteria

Inventory user/group membership and exact sudoers entries, rotate credentials when operators change, and test each service under its actual systemd identity.

