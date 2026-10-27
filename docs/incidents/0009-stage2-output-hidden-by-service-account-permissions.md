# INC-0009 — Stage 2 output appeared missing because directory was restricted

- **Event period:** Approximately 2026-10-24
- **Category:** Filesystem permissions / operator usability
- **Status:** Resolved by inspecting output as authorized service user

## Symptom
After running `market_stage2.py build --lookback 100 --anchor IVV --as-of 2026-10-22`, the operator initially reported that no output files were produced. The parent directory had permissions similar to:

```text
drwxr-x---  svc-lseg svc-lseg  /var/lib/sinn-stage2/
```

The operator later verified the data was present. The build output existed; the issue was output discovery and service-account permissions.

## Diagnostic approach
```bash
sudo find /var/lib/sinn-stage2 -maxdepth 2 -type f
sudo -u svc-lseg ls -lah /var/lib/sinn-stage2/2026-10-22/
```

Expected `manifest.json`, `daily_closes.csv`, and `daily_returns.csv` under the dated output directory. Check the process exit code before diagnosing a write failure.

## Resolution and prevention
Use an authorized account or `sudo` to inspect service-owned files; do not make the data world-readable merely to ease troubleshooting. Document canonical output paths and file permissions in the runbook and distinguish `audit` (no output) from `build` (writes files).

## Related decisions
[ADR-0009](../decisions/0009-service-accounts-and-operator-access.md) · [ADR-0014](../decisions/0014-strict-synchronized-market-scenarios.md)
