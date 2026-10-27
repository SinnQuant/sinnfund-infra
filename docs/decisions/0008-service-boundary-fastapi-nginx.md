# ADR-0008: Use small FastAPI services behind one Nginx HTTPS entry point

- **Date:** 2026-10-16
- **Status:** Accepted

## Context

The core read-only website is intended to remove a transparency bottleneck for class participants. Trade staging and low-frequency quant-research prediction engines are **adjacent, planned workstreams**, not proof that the deployed reporting/risk services execute trades. Maintaining separable HTTP services preserves this important authorization boundary.

The project evolved separate close-of-day portfolio reporting, live market data/portfolio views and prediction services, all on a single host and domain.

## Options considered

- One monolithic web server combining all endpoints.
- Small Python/FastAPI applications on loopback ports with Nginx URL routing.
- Publicly listen on each application port.

## Decision

Run separate FastAPI/Uvicorn applications on `127.0.0.1` ports, fronted by Nginx HTTPS and path-based routes. The known presentation routes include `/close/`, `/live/`, and subsequently `/var/`; the risk dashboard uses port 8093.

## Rationale

Retains independent code/process lifecycles while keeping one external origin and TLS endpoint. Services can be inspected and restarted separately.

## Consequences and limitations

Requires careful proxy path handling (notably trailing-slash behavior) and port/service ownership; internal HTTP APIs must not accidentally be opened to the internet.

## Follow-up / revisit criteria

Document exact Nginx routes and systemd unit ownership; make separate protected namespaces for state-changing endpoints.

