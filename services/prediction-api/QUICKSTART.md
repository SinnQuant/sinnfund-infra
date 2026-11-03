# Signal API quick start

Use this guide for the JKoh draft/test API. The longer [operations guide](README.md) explains
permissions, batch requests, export, and recovery.

## 0. Get the tools on your computer

Each signal sender clones the infrastructure repository once:

```bash
git clone https://github.com/SinnQuant/sinnfund-infra.git
cd sinnfund-infra
```

The client uses only Python's standard library. A sender does not need server SSH access. An
operator must issue the sender's key in step 1; the sender then saves it locally in step 2.

## 1. Make API keys

If you are already logged into JKoh, run:

```bash
cd /opt/prediction-api
python3 tools/signal_keys.py create
```

Or run it from the `sinnfund-infra` repository root on your Mac; that version connects to JKoh over
SSH:

```bash
python3 services/prediction-api/tools/signal_keys.py create
```

It asks:

```text
Key type (sender/exporter) [sender]:
How many keys should I create [1]:
Name for key 1:
```

Choose `sender` for people who send and manage their own signals. Choose `exporter` only for the
operator allowed to consume every pending LIVE signal into a CSV. The command updates the server
and prints each new key once. Copy each key to its owner through a private channel.

List names or revoke keys with the same interactive workflow:

```bash
python3 services/prediction-api/tools/signal_keys.py list
python3 services/prediction-api/tools/signal_keys.py revoke
```

The repository version requires SSH access to the API server. JKoh is the default; set
`SIGNAL_HOST` to the approved SSH alias when operating another environment.

## 2. Save your sender key once

On JKoh, the key owner runs:

```bash
python3 tools/signal_client.py save-key
```

From the `sinnfund-infra` repository root on a Mac, use:

```bash
python3 services/prediction-api/tools/signal_client.py save-key
```

Paste the issued key at the hidden prompt. It is saved for that operating-system user with private
permissions. `save-key` does not create or grant a key; step 1 does that.

For the commands below, set the path that matches where you are running:

```bash
# JKoh
CLIENT=tools/signal_client.py

# Or the sinnfund-infra repository root
CLIENT=services/prediction-api/tools/signal_client.py
```

## 3. Send a LIVE signal

Use a unique ID, destination, instrument, and target price. The timestamp defaults to now:

```bash
python3 "$CLIENT" create example-1 LIVE EXA 123.45
```

The signal stays pending. It does not create a trade. A later authorized export compares the target
with a fresh current price, writes `0.05` for LONG or `-0.05` for SHORT, and consumes the pending
LIVE signal only after the CSV succeeds.

## 4. See what you sent

List compact summaries for every signal owned by your key:

```bash
python3 "$CLIENT" list
```

See one signal, including its current revision and audit history:

```bash
python3 "$CLIENT" get example-1
```

## 5. Edit a signal

The client gets the latest revision automatically:

```bash
python3 "$CLIENT" edit example-1 --price 125.00
```

Other editable fields are `--destination`, `--ticker`, `--timestamp`, and `--limit-price`. Only a
pending LIVE signal or an exact-price `no_direction` rejection can be edited.

## 6. Delete a signal

```bash
python3 "$CLIENT" delete example-1
```

Delete is audited removal from the pending queue, not erasure of history. It is not a broker-order
cancellation. If exactly one owned signal is deletable, `python3 "$CLIENT" delete` can find it
without an ID.

## 7. Send a PAPER signal

This queues a real order for the configured IBKR paper account. It is not a harmless API test.
Supply a future forecast time and a separate entry limit:

```bash
FUTURE_UNIX_TIME=$(($(date +%s) + 86400))
python3 "$CLIENT" create paper-example-1 PAPER EXA 123.45 \
  "$FUTURE_UNIX_TIME" --limit-price 120.00
```

The API obtains a fresh current quote and derives LONG or SHORT from current price versus target.
Once queued, the PAPER signal is immutable. The current client does not cancel broker orders.

## 8. Automate from a script

Run `save-key` once as the same operating-system user that will run the job. Then use the
[copy-pasteable shell script](README.md#automation-example). Retry a failed request with the same
signal ID; never invent a new ID after a timeout because the first request may have succeeded.

For raw GET/POST examples, arrays of up to 100 signals, and scheduled LIVE export, see the
[complete operations guide](README.md#5-create-read-edit-and-delete-a-signal).
