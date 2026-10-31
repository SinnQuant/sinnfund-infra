# Prediction API Operations

FastAPI service for legacy predictions, authenticated research signals, and the separate paper-order
inbox.

**Production location:** `/opt/prediction-api`

**systemd unit:** `prediction-api.service`

**HTTP bind:** `127.0.0.1:8003`

**Public prefix:** `https://sinnfund.jkoh.dev/prediction/`

This runbook documents the deployed `/signals` key and request workflow. The deployed
`signal_ledger.py` is not yet present on this repository's `main` branch; do not rebuild production
from Git until that source difference is reconciled. This document does not change or deploy the
service.

## 1. Key scopes and storage

The API uses a separate random bearer key for each human identity. A caller-supplied name is never
accepted as proof of identity.

| Scope | Server hash file | Allowed operations |
|---|---|---|
| Sender | `/opt/prediction-api/signal-data/senders.htpasswd` | Create, read, edit, and delete owned signals |
| Exporter | `/opt/prediction-api/signal-data/exporters.htpasswd` | Consume pending LIVE signals into a target CSV |

The username in the hash file becomes the signal's audit identity. Names must match
`[A-Za-z0-9_.-]{1,64}`. The API reads the files on every request, so rotation and revocation take
effect without restarting the service.

The existing implementation accepts standard `htpasswd` `{SHA}` entries. These hashes are not
appropriate for human passwords. They are used here only with independently generated 256-bit
random keys. Treat the hash files as sensitive, keep them out of Git, and use mode `0600` locally
and `0640` with group `trading-dev` on the server.

## 2. Issue or rotate a sender key

Run these commands on the operator's Mac from the repository root. macOS already supplies
`/usr/sbin/htpasswd` and `openssl`.

Only one operator may change a scope's hash file at a time. Immediately before every issue,
rotation, or revocation, copy the current live file; never reuse a previously downloaded copy.
This prevents one operator from accidentally removing keys issued by another operator.

```bash
umask 077
mkdir -p data/private
SENDER_FILE=data/private/signal-senders.htpasswd

if ssh sinnfund 'test -f /opt/prediction-api/signal-data/senders.htpasswd'; then
  scp sinnfund:/opt/prediction-api/signal-data/senders.htpasswd "$SENDER_FILE"
else
  touch "$SENDER_FILE"
fi
chmod 600 "$SENDER_FILE"
```

Issue a new key, or rotate an existing name by running the same command with that name:

```bash
printf 'Sender name: '
read -r SIGNAL_SENDER
printf '%s\n' "$SIGNAL_SENDER" | grep -Eq '^[A-Za-z0-9_.-]{1,64}$' || {
  printf 'Invalid sender name\n' >&2
  return 1 2>/dev/null || exit 1
}

SIGNAL_API_KEY=$(openssl rand -hex 32)
printf '%s\n' "$SIGNAL_API_KEY" |
  /usr/sbin/htpasswd -is "$SENDER_FILE" "$SIGNAL_SENDER"

printf 'Copy this key now through a private channel: %s\n' "$SIGNAL_API_KEY"
```

Install the complete hash file atomically:

```bash
scp "$SENDER_FILE" \
  sinnfund:/opt/prediction-api/signal-data/.senders.htpasswd.upload

ssh sinnfund '
  set -eu
  path=/opt/prediction-api/signal-data/.senders.htpasswd.upload
  chgrp trading-dev "$path"
  chmod 640 "$path"
  mv "$path" /opt/prediction-api/signal-data/senders.htpasswd
'
```

The plaintext key is shown once and cannot be recovered from the hash file. After securely handing
it to its owner, remove it from the current shell:

```bash
unset SIGNAL_API_KEY
```

## 3. Issue an exporter key

Exporter keys are deliberately separate because export consumes every pending LIVE signal. Repeat
the sender procedure with these substitutions:

| Sender value | Exporter value |
|---|---|
| `SIGNAL_SENDER` | `SIGNAL_EXPORTER` |
| `signal-senders.htpasswd` | `signal-exporters.htpasswd` |
| `senders.htpasswd` | `exporters.htpasswd` |
| `.senders.htpasswd.upload` | `.exporters.htpasswd.upload` |

Do not put the same plaintext key in both files.

## 4. Verify a sender key without writing data

Read the key without adding it to shell history, then request an intentionally nonexistent signal:

```bash
read -rs SIGNAL_API_KEY
export SIGNAL_API_KEY
printf '\n'

code=$(curl -sS -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $SIGNAL_API_KEY" \
  https://sinnfund.jkoh.dev/prediction/signals/key-check-does-not-exist)

test "$code" = 404 && printf 'Sender key accepted\n' || {
  printf 'Unexpected HTTP status: %s\n' "$code" >&2
  exit 1
}
```

`404` is expected: authentication succeeded, but that signal is not owned by the caller. `401`
means the key is invalid or revoked; `503` means the sender hash file is not configured.

## 5. Create, read, edit, and delete a signal

The signal API intentionally uses only GET and POST. Replace the shell values below with the
intended signal; do not submit examples to production.

```bash
API=https://sinnfund.jkoh.dev/prediction
SIGNAL_ID=YOUR_UNIQUE_SIGNAL_ID
SIGNAL_DESTINATION=LIVE
SIGNAL_TICKER=YOUR_TICKER
SIGNAL_PRICE=123.45
SIGNAL_TIMESTAMP=$(date +%s)
```

Create:

```bash
printf '{"signal_id":"%s","destination":"%s","ticker":"%s","price":%s,"timestamp":%s}\n' \
  "$SIGNAL_ID" "$SIGNAL_DESTINATION" "$SIGNAL_TICKER" \
  "$SIGNAL_PRICE" "$SIGNAL_TIMESTAMP" |
curl --fail-with-body -sS \
  -H "Authorization: Bearer $SIGNAL_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @- "$API/signals" |
python3 -m json.tool
```

List compact summaries for every signal owned by this sender:

```bash
curl --fail-with-body -sS \
  -H "Authorization: Bearer $SIGNAL_API_KEY" \
  "$API/signals" |
python3 -m json.tool
```

Read the current revision and complete audit history:

```bash
curl --fail-with-body -sS \
  -H "Authorization: Bearer $SIGNAL_API_KEY" \
  "$API/signals/$SIGNAL_ID" |
python3 -m json.tool
```

Edit using the revision returned by GET:

```bash
CURRENT_REVISION=1
NEW_SIGNAL_PRICE=125.00

printf '{"signal_id":"%s","revision":%s,"price":%s}\n' \
  "$SIGNAL_ID" "$CURRENT_REVISION" "$NEW_SIGNAL_PRICE" |
curl --fail-with-body -sS \
  -H "Authorization: Bearer $SIGNAL_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @- "$API/signals/edit" |
python3 -m json.tool
```

Delete using the latest revision returned by GET:

```bash
CURRENT_REVISION=2

printf '{"signal_id":"%s","revision":%s}\n' "$SIGNAL_ID" "$CURRENT_REVISION" |
curl --fail-with-body -sS \
  -H "Authorization: Bearer $SIGNAL_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @- "$API/signals/delete" |
python3 -m json.tool
```

Delete is audited, not physical erasure. A final GET returns `status: "deleted"` and the complete
create/edit/delete history. Deleted signals are no longer pending or exportable. Create, edit, and
delete also accept arrays of up to 100 unique signals.

## 6. Automate with the bundled client

`tools/signal_client.py` is a standard-library client for create, list, GET by ID, edit, and delete.
It does not automate export because export consumes every pending LIVE signal and needs a
separately approved schedule.

Save the sender key once. The prompt is hidden, and the client writes the key to
`~/.config/sinnfund/signal-sender.key` with mode `0600`:

```bash
python3 services/prediction-api/tools/signal_client.py configure-key
```

Normal use needs no environment variables. The create timestamp defaults to the current time;
edit and delete fetch the current revision themselves:

```bash
python3 services/prediction-api/tools/signal_client.py \
  create YOUR_SIGNAL_ID LIVE YOUR_TICKER 123.45
python3 services/prediction-api/tools/signal_client.py list
python3 services/prediction-api/tools/signal_client.py get YOUR_SIGNAL_ID
python3 services/prediction-api/tools/signal_client.py \
  edit YOUR_SIGNAL_ID --price 125.00
python3 services/prediction-api/tools/signal_client.py delete YOUR_SIGNAL_ID
```

If the sender owns exactly one signal that is still deletable, no ID lookup is needed:

```bash
python3 services/prediction-api/tools/signal_client.py delete
```

The no-ID delete stops without changing anything when zero or multiple signals are deletable.
`delete-only` remains as a compatible alias.

For a scheduled job, run `configure-key` once as the same operating-system user that will run the
job. Then save this example outside the repository as `send_signal.sh`:

```bash
#!/bin/sh
set -eu

if [ "$#" -ne 4 ]; then
  printf 'usage: %s SIGNAL_ID LIVE_OR_PAPER TICKER TARGET_PRICE\n' "$0" >&2
  exit 2
fi

exec python3 /path/to/sinnfund-infra/services/prediction-api/tools/signal_client.py \
  create "$1" "$2" "$3" "$4"
```

Example automation call:

```bash
./send_signal.sh "model-$(date +%s)" LIVE EXAMPLE 123.45
```

Use a made-up/public instrument when testing. The caller remains responsible for generating a
unique ID. Pass an explicit timestamp after the target price only when the forecast time differs
from the send time. To use another private key location, set `SIGNAL_API_KEY_FILE`; ephemeral jobs
may instead set `SIGNAL_API_KEY`. Never set both, put a key in command arguments, or commit a key.
Do not automatically retry a request under a new ID: a lost response may still mean the original
signal was accepted. Retry the same ID, which is idempotent, then GET it. Automated edits and
deletes must use the current revision; the client fetches it when the revision argument is omitted.
A concurrent change still returns `409` rather than deleting a newer revision.

Run the offline client tests with:

```bash
python3 -m unittest discover services/prediction-api/tests
```

## 7. Export pending LIVE signals

Export is a privileged, state-changing operation. It compares every pending LIVE target with one
batched quote request, writes `account,symbol,target`, and consumes the pending set only after the
CSV write succeeds. Do not use export to test a credential.

```bash
read -rs SIGNAL_EXPORTER_KEY
export SIGNAL_EXPORTER_KEY
printf '\n'

curl --fail-with-body -sS -X POST \
  -H "Authorization: Bearer $SIGNAL_EXPORTER_KEY" \
  https://sinnfund.jkoh.dev/prediction/signals/export |
python3 -m json.tool

unset SIGNAL_EXPORTER_KEY
```

Run this only at the approved export time. A schedule and download endpoint are not documented as
deployed. Exact target/current equality is retained as an audited `no_direction` rejection.

## 8. List, revoke, and recover keys

Coordinate with other key operators, then rerun the download block in section 2 immediately before
listing or revoking a sender. Use the exporter filenames from section 3 for an exporter.

List identities without displaying hashes:

```bash
cut -d: -f1 data/private/signal-senders.htpasswd
```

Revoke an identity locally, then repeat the atomic install command from section 2:

```bash
/usr/sbin/htpasswd -D data/private/signal-senders.htpasswd SENDER_NAME
```

Revocation takes effect as soon as the new hash file is renamed into place. Existing signals and
their audit owner remain unchanged. A lost key cannot be recovered; rotate the same name to a new
random key. A deleted username may be reissued later, but that identity will continue to match its
existing audit records.

## 9. Troubleshooting

| Symptom | Meaning / action |
|---|---|
| `No saved signal API key` | Run `signal_client.py configure-key` once as the current operating-system user |
| `Set only one of SIGNAL_API_KEY or SIGNAL_API_KEY_FILE` | Both overrides are set. Unset one, or unset both to use the saved default key |
| Older client says `Set exactly one of SIGNAL_API_KEY or SIGNAL_API_KEY_FILE` | Update the client and run `configure-key`; the current client uses a private saved key by default |
| `401 Invalid signal API credential` | Wrong, revoked, or wrong-scope key; confirm the intended username exists in the correct local hash file and reinstall it |
| `404 signal not found` | Authentication succeeded, but the ID is absent or belongs to another sender |
| `409 signal revision changed` | GET the signal and retry only with the returned current revision |
| `409 only pending or no_direction signals can be edited/deleted` | The signal is already exported, deleted, or otherwise final |
| `503 ...htpasswd is not configured` | Install the corresponding sender/exporter hash file |
| `htpasswd: cannot modify file ... use -c` | Create the empty local file with `touch`; do not use `-c` against an existing multi-user file |
| Key works locally but not after install | Verify remote group/mode and that the upload was atomically renamed to the exact active filename |

Check service state without exposing credentials:

```bash
ssh sinnfund 'systemctl is-active prediction-api.service'
curl -fsS https://sinnfund.jkoh.dev/prediction/openapi.json >/dev/null
```

Never print server hash contents, bearer keys, runtime configuration, account identifiers, or
signal data into tickets, pull requests, logs, or chat.
