# ADR-0023: Route institutional AWS hosting through TAMU Kion and governance

- **Date:** 2026-10-26
- **Status:** Proposed — approvals pending

## Context

The team is considering university cloud hosting partly to make the reporting system sustainable beyond a single student or locally hosted site. The earlier incumbent website's reported reliability/handoff difficulties make institutional sponsorship and long-term ownership especially material. Funding a VM does not itself grant permission to publish brokerage positions or commercial market data.

The fund is considering moving the single-host system from Hetzner to a TAMU-funded cloud account. The technical EC2 migration is straightforward; institutional sponsorship, costs, network policy, cloud access and data disclosure are separate approval questions.

## Options considered

- Self-fund a personal AWS account.
- Request a university-funded account through TAMU Kion and retain existing DNS initially.
- Immediately migrate to a formal TAMU-managed hostname and redesigned service stack.

## Decision

Pursue a funded **TAMU Kion-managed AWS account** for an Ubuntu EC2 lift-and-shift, subject to sponsor/fiscal authorization, Cloud Operations provisioning, appropriate IT security review, and IBKR/LSEG data-owner/license clearance. Retain the existing `sinnfund.jkoh.dev` address initially rather than requiring a `tamu.edu` hostname as a launch prerequisite.

## Rationale

Separates VM provisioning from the institutional questions that can actually block publication; minimizes nonessential DNS and rearchitecture changes.

## Consequences and limitations

Provisioning and approvals are pending: AWS account, EC2 instance, university funding, cloud-security review and public data-use authorization.

## Follow-up / revisit criteria

Get faculty/staff system ownership and cost-center approval; request cloud account; verify allowable VPC/IP/security-group settings; confirm outbound IBKR/LSEG access and public-data rights before cutover.

