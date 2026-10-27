# ADR-0006: Plan cloud migration as a like-for-like VM lift-and-shift

- **Date:** 2026-10-13
- **Status:** Proposed — not yet deployed

## Context

The Hetzner deployment is functional but institutional hosting, administration, and potentially outgoing-IP behavior motivated exploring AWS. A cloud redesign could create multiple simultaneous moving parts and complicate troubleshooting.

## Options considered

- Migrate one Ubuntu VM with existing services.
- Redesign at once around microservices, managed databases, Kubernetes, or serverless.
- Remain indefinitely on the original host.

## Decision

**First migration milestone:** reproduce the existing single-host stack on an Ubuntu EC2 instance, with consistent filesystem structure, Python virtual environments, systemd units, Nginx routes, and DNS cutover. **Do not add microservices or rewrite the application as part of this first move.**

## Rationale

Functional equivalence offers a clear test criterion and isolates cloud/network issues from application redesign.

## Consequences and limitations

Preserves a single-host failure domain and manual operations temporarily, but minimizes technical migration risk. AWS/Kion provisioning, networking, institutional funding, and data-use approvals remain outstanding; the move has not been recorded as completed.

## Follow-up / revisit criteria

Secure approved cloud account and funding; provision VM; test IBKR and LSEG outbound authentication from the new IP; transfer state with secure methods; validate systemd/API/HTTPS; migrate DNS with rollback.

