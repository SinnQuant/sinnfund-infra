# INC-0011 — Stage 4 returned HTTP 503 despite a healthy Stage 3 report

- **Event period:** 2026-10-24
- **Category:** Cross-stage schema compatibility / API
- **Status:** Resolved with validator change; retest on redeploy

## Symptom and impact
The Stage 4 Uvicorn process was listening on `127.0.0.1:8093`, but `/health`, `/api/report`, and `/api/dates` all returned **HTTP 503**:

```json
{"detail":"Stage 3 report invalid or unreadable"}
```

At the same time, Stage 3 at `127.0.0.1:8096/health` returned **HTTP 200** with 25 accounts and 100 scenarios; its report existed as `/var/lib/sinn-stage3/latest.json`, was readable by `svc-lseg`, and had schema version 1, `stage=historical_simulation_var`, `as_of=2026-10-22`.

## Diagnosis
The Stage 4 account-ID validator used a pattern equivalent to:

```python
re.fullmatch(r'[A-Za-z0-9_-]{1,64}', account)
```

Stage 1 generated non-sensitive aliases containing spaces, e.g. `Account 5CCF9F67`. The pattern rejected the valid alias, causing the generic Stage 4 error path. 

## Fix
Expand the allowed identifier characters to include spaces in the *data validation* regex (without using aliases in filesystem paths). Restart `sinn-stage4-api.service`. Later dashboard output showed all 25 accounts with risk data, consistent with recovery.

## Prevent recurrence
- Add Stage 3 → Stage 4 contract tests with account aliases containing spaces.
- Return actionable sanitized validation errors in service logs while keeping sensitive reports private.
- Exercise `/health`, `/api/report`, `/api/dates`, and the frontend after every deployment.
- Avoid assuming `503` means the underlying dataset is missing; test schema and permissions separately.

## Related decisions
[ADR-0019](../decisions/0019-read-only-stage4-over-stage3-artifacts.md) · [ADR-0013](../decisions/0013-audit-flex-accounting-before-var.md)
