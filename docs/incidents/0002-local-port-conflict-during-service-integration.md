# INC-0002 — Port 8000 was already occupied during website integration

- **Event period:** Around 2026-10-13 to 2026-10-16 (discussion dates)
- **Recorded:** 2026-10-26
- **Category:** Deployment / service discovery
- **Status:** Mitigated through separate local API ports

## Observed behavior and impact
The intended port `8000` was already used by the existing prediction API. Reusing it for the Flex portfolio website risked preventing a service from starting or replacing another application unexpectedly. This was a service-port allocation conflict during integration.

## Investigation
The server already hosted multiple Python applications under one domain. Port allocation and Nginx route ownership needed to be coordinated rather than assuming a free default port.

## Resolution / mitigation
The Flex close website was assigned `127.0.0.1:8001`, the live position view `127.0.0.1:8002`, and later services were allocated separate internal ports. Nginx fronts them by route; application ports remain loopback-only.

## Remaining risks / follow-up
- Maintain a version-controlled port and Nginx route registry.
- Confirm process ownership with `sudo ss -tlnp` before provisioning new services.
- For future migration, test all bound listeners before DNS cutover and avoid overlapping systemd units.
- Do not infer that the prediction engine's proposed research integration is complete solely from an existing service name.

## Related decisions
[ADR-0005](../decisions/0005-separate-public-read-only-and-private-controls.md) · [ADR-0008](../decisions/0008-service-boundary-fastapi-nginx.md)
