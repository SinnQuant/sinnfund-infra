# ADR-0001: Build an independently maintained, transparent fund information platform

- **Date:** 2026-10-13
- **Status:** Accepted

## Context and original problem

The instructor wants the class to operate more like a **hedge fund**, where participants can observe portfolio exposures and evaluate one another's investment decisions with timely information. At project inception, students largely could not inspect the class's aggregate bets independently. The instructor was the sole person with the relevant brokerage login and circulated **weekly reports**; until those reports arrived, positions and decisions were effectively opaque to the class. A Bloomberg Terminal was described as the only other practical way participants could gather portfolio information outside instructor-provided reports.

An **existing locally hosted portfolio website** was already present. However, project stakeholders reported inconsistent availability/reliability, and its author was not cooperative with maintenance or handoff. The existing site therefore did not provide a dependable, independently operable source of truth. Users had raised complaints about poor data availability and transparency. 

The core requirement is not simply to build another website: it is to eliminate a *single-person reporting bottleneck* and establish reliable, repeatable, appropriately authorized access to fund information. This also enables students, board members, researchers, and instructors to coordinate around the same dated snapshot.

## Options considered

- Continue relying on instructor-generated weekly reports and the Bloomberg Terminal.
- Maintain or depend on the incumbent author's locally hosted website without reliable operational handoff.
- Build an independently maintained, centrally hosted read-only portfolio reporting platform with automated brokerage ingestion.
- Combine portfolio viewing and unrestricted trading controls into one service (rejected due to access risk).

## Decision

Build a **centrally maintained, read-only-first portfolio information platform** that automates end-of-day brokerage reporting, provides more timely and consistent visibility than manual weekly dissemination, and supports future analytics. Maintain explicit dates, sources, and data-quality statuses. Reserve all trade submission and account modification for separate authorized workflows.

## Rationale

The project must serve the instructor's hedge-fund-like educational goal while reducing dependence on the incumbent website author and the instructor's manual distribution cadence. Stable data access is a prerequisite for risk reporting, research evaluation, and any later trading workflow. Independent operations and auditable snapshots matter as much as a convenient UI.

## Consequences and limitations

- **Benefits:** Better class visibility, repeatable reports, a service that can be operated and handed off, and a common base for risk analytics and research.
- **Responsibilities:** Monitoring, access control, backups, reconciliation to brokerage reports, a clear data owner, and a process to flag missing or stale data.
- **Boundaries:** Class transparency does **not** automatically authorize unrestricted Internet publication of account data or redistribution of LSEG prices. Instructor/fund-owner approval, licensing, and institutional security are distinct gates.

## Follow-up / revisit criteria

Define expected freshness (end-of-day versus intraday), stakeholder roles, quality indicators, and an operating handoff plan. Determine how student feedback and instructor expectations translate into acceptance tests. See ADR-0025 (trade staging) and ADR-0026 (research prediction workflow) for adjacent ideas, neither of which is part of the existing read-only risk pipeline.

