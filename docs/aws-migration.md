# AWS Migration Guide — SINN Fund Infrastructure

Migrating the `sinnfund.jkoh.dev` stack from the single VPS (Hetzner) to AWS, with access restricted to the Texas A&M network.

**Decided strategy (see ADRs):** a like-for-like Ubuntu EC2 lift-and-shift with no application rearchitecture ([ADR-0006](decisions/0006-lift-and-shift-cloud-before-rearchitecture.md)), hosted in a **TAMU Kion-managed, university-funded AWS account** with the existing `sinnfund.jkoh.dev` address retained initially ([ADR-0023](decisions/0023-tamu-kion-governance-for-public-cloud.md), status: Proposed — approvals pending). This guide assumes that path; §4 covers the TAMU-specific network and governance details.

Related operational history: [INC-0003](incidents/0003-ibkr-flex-rejected-requests-and-egress-ip-dependence.md) (IBKR Flex behavior differing by outbound IP — read before cutover; see §5 Phase 3).

**Scope:** this guide covers the applications in this repository only. The historical VaR/risk pipeline is maintained outside this repository (see README); if it is ever co-hosted, it adds another outbound LSEG dependency to plan for, but it is not part of this migration.

## 1. Target architecture (lift-and-shift, recommended first step)

The current design already has the right security shape: one public entry point (Nginx, 443) and everything else on loopback. On AWS, a single EC2 instance reproduces this almost exactly — the systemd units, Nginx config, and `127.0.0.1` bindings carry over unchanged, and the AWS security group replaces the VPS provider's firewall.

```text
                 Texas A&M campus network / VPN users
                              │  (TCP 443 only)
                              ▼
                    ┌───────────────────┐
   Internet ──80──► │  Security Group   │  443 from TAMU CIDRs only
   (ACME/redirect)  │  (AWS firewall)   │  80  from 0.0.0.0/0 (redirect + cert renewal)
                    └────────┬──────────┘
                             ▼
        ┌────────────────────────────────────────────┐
        │  VPC 10.0.0.0/16                           │
        │  ┌──────────────────────────────────────┐  │
        │  │ Public subnet 10.0.1.0/24            │  │
        │  │  EC2 (Ubuntu 24.04)                 │  │
        │  │  Elastic IP                          │  │
        │  │                                      │  │
        │  │  Nginx :443 ──┬─► 127.0.0.1:8001     │  │  flex-web        /close/
        │  │               ├─► 127.0.0.1:8002     │  │  flex-web-live   /live/
        │  │               ├─► 127.0.0.1:8003     │  │  prediction-api  /prediction/
        │  │               └─► 127.0.0.1:8000     │  │  legacy app      /
        │  │                                      │  │
        │  │  127.0.0.1:8091 lseg-feed (internal) │  │
        │  │  systemd units + timer, unchanged    │  │
        │  └──────────────────────────────────────┘  │
        └────────────────────────────────────────────┘
              │                     │
              ▼                     ▼
   Outbound: IBKR Flex, LSEG   S3 (archive backup),
   (NAT/IGW, port 443)         Secrets Manager, CloudWatch
```

## 2. AWS services needed

### Core (required)

| Service | Purpose | Notes |
|---|---|---|
| **EC2** | Runs all services | `t3.small`/`t3.medium` is a reasonable start; match current VPS RAM. **Ubuntu 24.04** per ADR-0006 (like-for-like with the current host). |
| **VPC** | Network isolation | One VPC, one public subnet suffices for lift-and-shift. |
| **Security Groups** | AWS firewall | Replaces the VPS host firewall. See §3. |
| **Elastic IP** | Stable public IP | Keeps DNS stable across instance stops/replacement. |
| **IAM role** (instance profile) | Lets the instance reach Secrets Manager / S3 / CloudWatch without stored keys | No IAM users or access keys on the box. |
| **Secrets Manager** | Replaces `/opt/*/.env` files | IBKR Flex token, LSEG credentials. Services read at startup via `aws` CLI or SDK. |

### Strongly recommended

| Service | Purpose |
|---|---|
| **S3** | Backup of `/var/lib/flex-ingest/flex/data/` archives (nightly `aws s3 sync` from a cron/timer). Bucket: private, default encryption, versioning on. |
| **Session Manager (SSM)** | Shell access **without opening port 22**. Install the `amazon-ssm-agent` snap/deb on Ubuntu, remove SSH ingress entirely. This is the single biggest hardening win and simplifies TAMU firewall approval. |
| **CloudWatch Agent + Logs** | Ship `journalctl` output for the five services; set an alarm on `flex-ingest` failure. |

### Optional / later evolution

| Service | When to adopt |
|---|---|
| **ALB + ACM** | If you want AWS-managed TLS (no Certbot), path-based routing in the load balancer instead of Nginx, or multiple instances later. ALB supports the same `/close/`, `/live/`, `/prediction/` path rules. |
| **Route 53** | If you move `jkoh.dev` DNS to AWS; otherwise keep your current DNS provider and point an A record at the Elastic IP. |
| **EFS** | Only if you later split services across multiple instances and need shared archive storage. Not needed for single-instance. |
| **CloudFront** | Generally **skip** — the dashboards are private, not a public CDN use case. |

## 3. AWS networking (the "AWS firewall")

### Security groups

Security groups are stateful, instance-level firewalls. For the single-instance design you need **one** group:

**`sg-sinnfund-web`** (inbound):

| Port | Source | Reason |
|---|---|---|
| 443 | TAMU campus CIDRs + TAMU VPN CIDRs | User access through the TAMU network |
| 80  | `0.0.0.0/0` | Certbot HTTP-01 renewal + HTTP→HTTPS redirect (serves nothing sensitive) |
| 22  | *(none)* | Use SSM Session Manager instead |

Outbound: default all-allowed is acceptable initially (services must reach IBKR/LSEG/AWS APIs); tighten later if desired.

**Getting the TAMU CIDRs right** (verified against ARIN RDAP, 2026-10-30):

- TAMU's registered allocations include `128.194.0.0/16` (TAMU-NET) and `165.91.0.0/16` (TAMU-NET-02) — reasonable starting points, but **registered ≠ egressing**; ask Cloud Ops / NetOps for the official egress list.
- **Preferred:** ask Cloud Ops for an AWS *managed prefix list* of campus ranges to reference in the SG — it stays updated without redeploys.
- **The TAMU VPN egress range is separate from campus ranges** — get it explicitly or off-campus VPN users are blocked. This is the most common failure.
- Guest Wi-Fi / eduroam may egress from different ranges (possibly a third-party ISP); test each network at cutover.
- IPv6 ranges, if desired, are not covered by the IPv4 ARIN records above.
- Record the final approved ranges and their source in an ADR — this is a security-relevant decision.

**Critical:** ports 8000–8003 and 8091 never appear in any security group. The services keep their `127.0.0.1` bindings, so they are unreachable at the network level — same boundary as today. The lseg-feed "no public route" rule is preserved by doing nothing.

### If you later split services onto separate instances

Give each tier its own SG and reference SGs instead of CIDRs:

- `sg-web` (Nginx/ALB): 443 from TAMU CIDRs
- `sg-dash` (flex-web, flex-web-live, prediction-api): 8001–8003 **from `sg-web` only**
- `sg-lseg` (lseg-feed): 8091 **from `sg-dash` only**

SG-to-SG references keep the internal pricing API unreachable from anything but the dashboards.

### VPC layout

- 1 VPC (`10.0.0.0/16`), 1 public subnet with an Internet Gateway is enough for lift-and-shift.
- Add private subnets only if you adopt an ALB (ALB in public subnets → instances in private subnets, no public IPs at all). That is the stronger end-state design and worth doing if TAMU security review asks about public IPs on compute.

## 4. Texas A&M networking and governance

The AWS security group and the TAMU network policy are **separate layers**. Per ADR-0023, the chosen path is a **TAMU Kion-managed account**, so §4.2 is the operative scenario; §4.1 is retained as a fallback and for local testing.

**Why campus-only is not optional** (this rationale belongs in the TAMU security review):

- The dashboards have **no application-level authentication** — the IP restriction *is* the access control (see §6).
- Public exposure means anyone can watch the fund's positions change daily: front-running/mirroring risk and a disclosure problem the IBKR data-owner approval never contemplated.
- LSEG delayed-data licensing restricts redistribution by audience; "the general public" is almost certainly not covered.
- The legacy app on :8000 and prediction-api's signal endpoints add unauthenticated attack surface that should never face the open internet.
- Cost to users is near zero: off-campus users already have the TAMU VPN.

### 4.1 Fallback — personally funded AWS account, users come from campus

TAMU's firewall is not in your data path; you simply restrict who can reach your Elastic IP:

1. Get the exact campus and VPN egress CIDR ranges from TAMU IT / Networking (ask for "campus public IP ranges and VPN egress ranges" — e.g. the `165.91.0.0/16` block, **verify the current list**, don't rely on memory).
2. Put those CIDRs as the only sources for port 443 in `sg-sinnfund-web`.
3. Off-campus users connect to the TAMU VPN first; their traffic then egresses from an allowed range.

Limitation: campus users on guest Wi-Fi or eduroam may egress from different ranges — test from each network you care about.

### 4.2 Chosen path — TAMU Kion-managed AWS account (ADR-0023)

The account is provisioned through the university's enterprise AWS program (Kion). Expect constraints and plan conversations with TAMU teams early — per the 2026-10-26 planning session, the parties involved are **SINN leadership, TAMU Cloud Operations, TAMU IT Security, TAMU Infoblox (DNS), and TAMU Marketing**:

- The account may come with a **pre-built VPC** connected to campus via Direct Connect/VPN, private subnets, and no public IPs by default. In that case the clean design is: EC2 in a **private subnet with a campus-routable IP**, no Elastic IP at all, DNS `sinnfund.jkoh.dev` resolving to the private address — reachable only from campus/VPN.
- **Verify the allowable VPC/IP/security-group settings with Cloud Ops before building** (ADR-0023 follow-up item). Do not assume public subnets or Elastic IPs are permitted.
- **Inbound ports often require a firewall change request / IT security review** before anything is exposed, even to campus-only. Budget lead time for this ticket.
- They may mandate specific AMIs, endpoint agents (EDR), logging to a central account, and tagging. Ask for the account's guardrail documentation before building.
- Public internet exposure (any `0.0.0.0/0` rule, including port 80) may be prohibited — then use **DNS-01 validation** for Let's Encrypt (e.g. Route 53 plugin) or ACM on an internal ALB instead of Certbot HTTP-01.
- **Ask Cloud Ops how internet-bound traffic is routed:** directly out of the VPC, or through campus ("forced tunneling")? If the latter, outbound IBKR/LSEG connections pass through TAMU's egress filtering and must be allowed there too — and the INC-0003 egress IP becomes a TAMU address, not an AWS one.
- **DNS:** `sinnfund.jkoh.dev` is retained initially; a `tamu.edu` hostname is **not** a launch prerequisite (ADR-0023). Infoblox involvement is only needed if a TAMU hostname is later requested. Note that `jkoh.dev` is **Jayden's personal domain** — cutover (step 11) requires his cooperation, or migrating DNS hosting first. Confirm who holds the DNS credentials before scheduling cutover.

### 4.3 Non-technical approvals that can block launch (ADR-0023)

Funding the VM does not by itself grant permission to publish brokerage positions or commercial market data. Track these in parallel with the technical work; any one can block cutover:

- [ ] Faculty/staff system ownership and cost-center (fiscal) authorization
- [ ] Cloud Operations account provisioning (Kion)
- [ ] TAMU IT security review
- [ ] **IBKR data-owner authorization** to display archived positions on the new host
- [ ] **LSEG license clearance** for delayed/cached redistribution from the new environment

**Practical advice:** the build in §5 works in either scenario. Treat §4.2 as a networking-and-governance delta: possibly swap the public subnet/EIP for private subnets and re-point DNS, plus run the approval track above.

## 5. Migration steps

**Phase 1 — Build (no downtime risk)**
1. Create VPC, subnet, SG `sg-sinnfund-web`, IAM instance role (Secrets Manager + S3 + CloudWatch read/write as needed).
2. Launch EC2, attach Elastic IP. Verify SSM Session Manager access works, then confirm no SSH rule exists.
3. Install Nginx, Python 3, `amazon-cloudwatch-agent`; create `svc-flex` / `svc-lseg` accounts and the `trading-dev` group per `docs/notes.md` (the sudoers file and group permissions carry over unchanged).
4. Store the contents of `/opt/flex-ingest/.env` and `/opt/lseg-feed/.env` in Secrets Manager. Either keep syncing them to `/opt` at deploy time or add a small startup read — don't bake them into the AMI.

**Phase 2 — Data and code**
5. Install the repo code from `services/<service>/` into `/opt/<service>/` exactly as documented in `README.md`, create venvs, install requirements.
6. Copy the Flex archive: `rsync -avz /var/lib/flex-ingest/flex/data/ ...` (via SSM port forwarding, or stage through the private S3 bucket).
7. Install systemd units and the Nginx site; `daemon-reload`, enable services. Point TLS at new Certbot certs **after** DNS cutover, or copy `/etc/letsencrypt/` to keep existing certs.
8. Test internally: `curl http://127.0.0.1:8001/healthz`, `:8002/healthz`, `:8091/health`, and through Nginx with a temporary `/etc/hosts` entry mapping `sinnfund.jkoh.dev` to the Elastic IP.

**Phase 3 — Cutover**
9. Lower DNS TTL to 60s ahead of time.
10. **Egress-IP validation before trusting the new host (INC-0003):** IBKR Flex previously returned errors 1001/1025 that differed by outbound IP, and the root cause was never confirmed IBKR-side. An IBKR support ticket from 2026-10-15 was still pending at last record — check its resolution first; the response may explain the IP sensitivity. Then, from the **final TAMU egress address** (i.e., after NAT/routing is settled — see the forced-tunneling question in §4.2), run a controlled `SendRequest` + `GetStatement` test — a manual `sudo systemctl start flex-ingest.service` — and confirm a fresh dated archive lands. Keep validation tests **bounded**: repeated rapid retries were suspected of triggering the 1025 rate-limit condition. Do not assume migration fixes ingestion; if it fails from the new egress, resolve that **before** DNS cutover. Similarly verify lseg-feed streaming and authentication from the new IP.
11. Flip the `sinnfund.jkoh.dev` A record to the Elastic IP (or campus-routable private address in a fully private deployment).
12. Verify from a campus network and from the TAMU VPN; verify from a non-TAMU network that access is **denied**.
13. Keep the old VPS running (services stopped) for ~1 week as rollback, then decommission. Set up the nightly S3 archive sync and CloudWatch alarms before calling it done.

## 6. Security checklist (expect TAMU to ask)

- [ ] No port 22 in any security group (SSM only)
- [ ] 443 restricted to TAMU CIDRs; no `0.0.0.0/0` except port 80 (or nothing, in the private-subnet variant of §4.2)
- [ ] Ports 8000–8003, 8091 not in any SG; services still bound to `127.0.0.1`
- [ ] Secrets in Secrets Manager, none in AMI/user-data/Git
- [ ] IAM instance role is least-privilege; no static AWS keys on the instance
- [ ] EBS volume encrypted (default on modern instance types)
- [ ] S3 bucket private, versioned, with a lifecycle rule
- [ ] CloudWatch logs + alarms on ingestion failure **and on no fresh dated archive existing** (INC-0003 action item: alert when no dated raw archive is available, and expose data freshness to users)
- [ ] Dashboards still have no app-level auth — Nginx allow-rules or an ALB OIDC/Cognito front-end are your compensating control; document this in the TAMU security review
- [ ] AMI/image patched; enable automatic security updates
