# ADR-0002: Host the first iteration on one Ubuntu Linux VM

- **Date:** 2026-10-13
- **Status:** Accepted

## Context

A locally hosted incumbent website already existed but was described as unreliable and difficult to maintain independently of its original author. The new platform needed a host controlled by the operating team, rather than recreating a single-person operational dependency. 

The platform initially comprised small Python services, scheduled ingest jobs, local state, and Nginx. Engineering velocity and operational simplicity mattered more than horizontal scalability. It was deployed on a Hetzner Ubuntu VPS.

## Options considered

- One Linux VM running all services.
- Managed cloud services, separate application/database hosts, and container orchestration.
- Local/manual execution without continuously hosted services.

## Decision

Run the initial system on **one Ubuntu VM** with predictable filesystem paths, systemd units and Nginx. Use independent processes and ports for distinct functions, without distributed-service infrastructure.

## Rationale

The workload is modest, and one VM makes debugging, deployment, and cross-service access straightforward. It preserves portability to another Ubuntu VM.

## Consequences and limitations

Pros: low coordination overhead, straightforward backup and inspection, fewer dependencies. Costs: single point of failure, shared resource contention, manual host security and backups, and migration work later.

## Follow-up / revisit criteria

Measure CPU/RAM/disk/network usage, establish snapshots and off-host backups, and revisit separation if scale or security requirements justify it.

