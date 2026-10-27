# INC-0005 — LSEG history job failed under service environment and SDK parameters

- **Event period:** Around 2026-10-24 (history-service development)
- **Category:** SDK compatibility / systemd environment
- **Status:** Configuration fixes identified; verify production service after redeployment

## Observed behavior
The new historical-price service encountered errors while running as the non-login `svc-lseg` account:

1. SDK initialization referenced a missing configuration file under `/home/svc-lseg/lseg-data.config.json`, even though the service account did not have the expected home configuration.
2. A `get_history()` call failed with a `TypeError` when `use_field_names_in_headers=True` was passed to the installed LSEG Data Library version.
3. A separate deployment detail involved the actual `venv/` path versus documentation/examples using `.venv/`.

## Investigation and changes
- Proposed setting `HOME=/var/lib/lseg-history` and `LD_LIB_CONFIG_PATH=/var/lib/lseg-history`, with a readable SDK config file at that location.
- Removed the unsupported `use_field_names_in_headers` argument from the 2.x `get_history()` call.
- Reconciled the installed venv path before invoking the service.
- Kept the historical refresh separate from the live stream to reduce session conflicts.

Confirm the installed service environment and SDK configuration with the documented smoke test.

## Reproduction / verification
```bash
sudo systemctl cat lseg-history-refresh.service
sudo journalctl -u lseg-history-refresh.service -n 80 --no-pager
sudo -u svc-lseg /opt/lseg-history/venv/bin/python \
  /opt/lseg-history/history_api.py refresh --symbol AVGO
```

If the deployment uses `.venv/`, use the executable confirmed by `systemctl cat` rather than copying the path above blindly.

## Prevention
Pin SDK major versions, test with the actual systemd user and environment, and run a one-symbol smoke test before full refresh. Do not expose licensed raw price history via public Nginx routes without permission.

## Related decisions
[ADR-0012](../decisions/0012-lseg-history-private-sqlite-cache.md) · [ADR-0009](../decisions/0009-service-accounts-and-operator-access.md)
