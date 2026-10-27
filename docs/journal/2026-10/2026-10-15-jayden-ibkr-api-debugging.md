# 2026-10-15 — IBKR Flex API failures

**Type:** debugging  
**Status:** completed
**Links to commits / ADRs:** [ ]

## Context from previous discussions

- Observed SendRequest/GetStatement errors, including 1001 and 1025.
- Investigated configuration and differences between server and alternate outbound-IP behavior.

## What was I trying to accomplish?

figure out why the requests performed so inconsistently. i likely hit some form of rate limit because of repeated testing.

## What I actually did / tested

- [x] documented error messages nicely and approached BR/team with corrections. we called IBKR support and got a help ticket submitted


## What I learned — in my own words

i need to communicate with the team and be more approachable.

## Next steps and links

- [ ] integrate their fixes when we get a response
- [ ] continue working with limited support as of now
