# 2026-10-22 — Historical portfolio risk design

**Type:** design  
**Status:** completed

## Context from previous discussions

- Work on combining portfolio exposures with market data for VaR.
- Considerations included data consistency, historical window, and exclusion reporting.

## What was I trying to accomplish?

develop a risk profile for each account so leadership can quickly identify problems when they occur.

## What I actually did / tested

- [x] developed python script to create estimation of risk using old website metrics

## What I learned — in my own words

this is more complicated than it looks because we do not have perfect information and securities change over time ie get delisted, use different currencies, etc...
