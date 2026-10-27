# 2026-10-16 — Read-only portfolio reporting website

**Type:** design / implementation  
**Status:** completed

## Context from previous discussions

- Discussed automating public portfolio visibility without exposing trade-submission capability.
- Considered Nginx and FastAPI separation from trading/prediction endpoints.

- The goal was not to invent the first portfolio website: an existing locally hosted site was unreliable and difficult to maintain independently of its author.
- Earlier students waited for instructor-distributed weekly reports unless they had Bloomberg access; the new site aimed to reduce that information bottleneck.
- Trade staging and low-frequency research predictions were related ideas but not part of the public read-only UI.

## What was I trying to accomplish?

start deploying information to the internet.

## What I actually did / tested

- [x] connect the portfolio size ingesting with a website display
- [x] set up DNS subdomain from my domain `sinnfund.jkoh.dev`

## What I learned — in my own words

starting to make architectural decisions about data handling such as should files be saved locally or delivered through API and networking details like which services should be exposed.
