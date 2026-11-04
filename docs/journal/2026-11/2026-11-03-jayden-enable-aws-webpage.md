# 2026-11-03 — Deploying index.html onto AWS server

**Environment:** TAMU Kion-AWS
**Change / version:** [pre-prod]

## Objective and preflight

- **Why deploy now:** ensure AWS server is internet accessible
- **Access / secrets / firewall / data permissions checked:** add WebServerGroup AWS security group

## Changes made

- modified index.html to check health endpoints
- created sinnfund-prod subdomain
- added WebServerGroup AWS security group
- copied nginx config
- reinstalled SSL certificates

## Verification and outcome

| Check | Result / evidence |
| --- | --- |
| Service status | DONE | HTTP response 200
| Health endpoint | DONE | health endpoints not uploaded yet
| Data freshness / completeness | DONE | results available from 0.0.0.0
| Security boundary (private/public) | public | https://sinnfund-prod.jkoh.dev
| Rollback possible | DONE | there is nothing to rollback to 

## Problems / unresolved risks

config security group properly

## What I learned — my own words

i underestimated the planning needed for a seemingly simple migration, it required more certificate changes and modifications than i anticipated

## Handoff / next step

[ ] port the rest of the existing code: live, close
