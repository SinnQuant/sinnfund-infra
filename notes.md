# Production Service Access — `trading-dev`

## Overview

The `trading-dev` Linux group allows authorized developers to manage selected production systemd services without full root access.

**Permissions:**
- Modify designated application files under `/opt` without sudo.
- Start, stop, and restart approved systemd services using `sudo` without a password.
- View service status and accessible logs.
- Cannot modify systemd unit definitions or manage unapproved services unless granted separately.

## 1. Administrator Setup

### Add developers

```bash
sudo groupadd -f trading-dev
sudo usermod -aG trading-dev enoch
```

Developers must log out and log back in for group membership to take effect.

### Configure application directory permissions

For each approved application directory:

```bash
sudo chgrp -R trading-dev /opt/<app>
sudo chmod -R g+rwX /opt/<app>
sudo find /opt/<app> -type d -exec chmod g+s {} +
```

Set a cooperative umask (`0002`) or default ACLs if multiple developers will create files. Do not grant group write access to all of `/opt`.

### Configure sudoers

**File:** `/etc/sudoers.d/trading-dev`

Edit using:

```bash
sudo visudo -f /etc/sudoers.d/trading-dev
```

Example configuration:

```sudoers
Cmnd_Alias TRADING_SERVICES = \
    /usr/bin/systemctl start prediction-api.service, \
    /usr/bin/systemctl stop prediction-api.service, \
    /usr/bin/systemctl restart prediction-api.service

%trading-dev ALL=(root) NOPASSWD: TRADING_SERVICES
```

Validate:

```bash
sudo visudo -c
```

## 2. Adding a New Production Service (Admin)

**Files to modify:**

| File / Directory | Purpose |
|---|---|
| `/etc/systemd/system/<service>.service` | Create or modify service definition |
| `/etc/sudoers.d/trading-dev` | Authorize management commands |
| `/opt/<app>/` | Application files and group permissions |

**Procedure:**

1. Create the service unit under `/etc/systemd/system/`, using a dedicated non-root `User=`.

2. Reload systemd:

   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable and start the service if required:

   ```bash
   sudo systemctl enable --now <service>.service
   ```

4. Add the new service commands to the `TRADING_SERVICES` alias in `/etc/sudoers.d/trading-dev` using `visudo`.

   Example additions:

   ```sudoers
   /usr/bin/systemctl start new-api.service, \
   /usr/bin/systemctl stop new-api.service, \
   /usr/bin/systemctl restart new-api.service
   ```

5. Validate the configuration:

   ```bash
   sudo visudo -c
   sudo systemctl status new-api.service
   sudo -l -U enoch
   ```

No systemd reload is necessary when only sudoers permissions change.

**Security:** Keep systemd unit definitions root-owned. Do not authorize unrestricted `systemctl` or run group-writable application code as root.

## 3. Developer Usage and Verification

### Step 1 — Verify group membership

```bash
id -nG
```

Expected: `trading-dev` appears in the group list.

### Step 2 — Verify sudo permissions

```bash
sudo -l
```

Expected output includes:

```text
(root) NOPASSWD: /usr/bin/systemctl restart prediction-api.service
```

### Step 3 — Restart an authorized service

```bash
sudo -n systemctl restart prediction-api.service
```

The `-n` flag prevents password prompting. The command should succeed without requesting authentication.

**Important:** Run `sudo systemctl`, not plain `systemctl`. The latter uses PolicyKit authorization instead of the configured sudoers permissions.

### Step 4 — Verify service health

```bash
systemctl status prediction-api.service
systemctl is-active prediction-api.service
journalctl -u prediction-api.service -n 50 --no-pager
```

Expected: `active (running)` for a continuously running service, and `active` from `is-active`. Confirm application health separately if applicable.

Journal access may require additional permissions.

### Step 5 — Verify access to application files

```bash
cd /opt/<app>
ls -ld .
touch .permission-test
rm .permission-test
```

The file creation and removal should succeed without sudo.

## 4. Troubleshooting

| Issue | Likely cause |
|---|---|
| Password requested by plain `systemctl` | PolicyKit is being used; run `sudo systemctl` |
| `sudo` says command not allowed | Service/operation missing from sudoers |
| Group not visible in `id -nG` | User needs to log out and back in |
| Cannot modify application files | Directory group or write permissions incorrect |
| Service cannot restart | Check `systemctl status` and `journalctl` |
| Service unit changes not recognized | Admin must run `systemctl daemon-reload` |

## 5. Permission Policy

- **Developers:** Manage approved services and update designated `/opt` application code.
- **Administrators:** Modify service definitions, sudoers policies, service identities, and system configuration.
- **Production processes:** Execute using dedicated unprivileged service accounts.
- **Secrets:** Must remain protected; developers who can deploy executable code can potentially access secrets available to that service account.

All permissions are assigned to the shared `trading-dev` group. New developers only require group membership, while new services require an administrator to update the sudoers allowlist.
