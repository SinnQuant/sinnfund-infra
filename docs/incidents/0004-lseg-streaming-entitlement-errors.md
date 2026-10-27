# INC-0004 — LSEG streaming price requests initially returned NotEntitled

- **Event period:** Approximately 2026-10-16 to 2026-10-20
- **Category:** Market-data entitlement / integration
- **Status:** Mitigated for tested delayed US instruments

## Observed behavior and impact
Initial LSEG requests for US equities, including AAPL.O, MSFT.O and NVDA.O, returned `NotEntitled PE(74)`. As a result, the proposed live-position view could not assume those price fields were available from the first service configuration.

## Investigation
The entitlement path was changed to the available delayed market-data service (`ELEKTRON_DD`). The operator subsequently observed successful snapshot prices and streaming updates for sampled US equities. This established that the SDK session could retrieve at least a subset of the required delayed fields; it did **not** establish complete entitlement across every portfolio instrument or a right to redistribute prices publicly.

## Mitigation
Use an explicit ticker-to-RIC mapping, keep LSEG authentication server-side, and show missing or stale price values rather than substituting an unverified quote. Streaming and historical endpoints are separate datasets and may have separate entitlements.

## Remaining risks / follow-up
- Independently validate every required RIC and its bid/ask/last fields under the intended account.
- Enforce stale-quote and session-health indicators in the live portfolio view.
- Confirm delayed-data licensing and public redistribution terms with the institutional LSEG license administrator.
- Protect the LSEG feed API (`127.0.0.1:8091`) from public exposure.

## Related decisions
[ADR-0010](../decisions/0010-lseg-as-independent-market-data-source.md) · [ADR-0011](../decisions/0011-explicit-ticker-to-ric-mappings.md)
