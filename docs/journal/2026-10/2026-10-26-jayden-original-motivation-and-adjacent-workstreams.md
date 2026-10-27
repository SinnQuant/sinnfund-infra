# 2026-10-26 — Clarifyin oriinal motivation and adjacent workstreams

**Type:** retrospective / stakeholder requirements / product desin  
**Status:** completed
**Date note:** This is the date the backround was documented, **not** the claimed start date of the project.  
**Relevant ADRs:** [0001](../../decisions/0001-stakeholder-driven-read-only-platform.md), [0003](../../decisions/0003-ibkr-flex-for-unattended-close-data.md), [0005](../../decisions/0005-separate-public-read-only-and-private-controls.md), [0025](../../decisions/0025-modernize-trade-staging-baskettrader.md), [0026](../../decisions/0026-low-frequency-equity-prediction-research-integration.md)

## Confirmed context from project-owner recollection

- An earlier **locally hosted website** had some of the desired resources, but its data/service was not consistently reliable, and its author was not cooperative with maintenance/handoff.
- The instructor alone held the relevant brokerae loin, and students mostly learned the class's positions from instructor-issued **weekly reports**. A Bloomber Terminal was the other described avenue to access portfolio information.
- This opacity limited an instructor oal: operatin the class more like a **hede fund**. Users had complained about information quality and availability.
- Separately, **trade stain** previously required a enerated executable to populate orders; miratin toward **IBKR BasketTrader** is an idea, not a completed decision or feasibility result.
- Another workstream envisions **low-frequency lon/short equity prediction enines** contributed by quant-research students; interface and execution boundaries remain undecided.

## My perspective at the beinnin 

the oriinal problem with the website was that there was too much technical debt and architectural inefficiencies with the codebase. it provided a startin vision for what the fund's public profile *could* be, but in my opinion, not what it should be.

## What users were actually askin for 

the button to pulls the latest data does not work consistenly, the website shows stale data

when it does work, data takes at least 5 minutes to populate

if the website is refreshed the data is one

students do not like to use this framework because it is not reliable

surroundin workflows are manual and time consumin, automation would be valuable

## Why I chose an independent platform 

this was the best way to consolidate all operations because they relied on the same core set of features

## Trade stain and prediction: oriinal ideas 

trade stain and risk reportin rely on the same data of the current portfolio. human authorization is necessary for submittin trades "aka pressin the bi red button", but all other aspects should be automated.

## What I learned / what I would do differently 

we need a dedicated team for manain this infrastructure
