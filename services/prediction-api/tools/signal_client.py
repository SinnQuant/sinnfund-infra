#!/usr/bin/env python3
"""Small GET/POST client for authenticated research signals."""

import argparse
import getpass
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://sinnfund.jkoh.dev/prediction"
DEFAULT_KEY_FILE = Path("~/.config/sinnfund/signal-sender.key")
SIGNAL_ID = re.compile(r"^[A-Za-z0-9_-]{1,48}$")
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9 .-]{0,19}$")


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def positive_price(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a positive finite number")
    return number


def matching(pattern, label):
    def parse(value):
        if not pattern.fullmatch(value):
            raise argparse.ArgumentTypeError(f"invalid {label}")
        return value
    return parse


def credential():
    token = os.getenv("SIGNAL_API_KEY")
    filename = os.getenv("SIGNAL_API_KEY_FILE")
    if token and filename:
        raise SystemExit("Set only one of SIGNAL_API_KEY or SIGNAL_API_KEY_FILE")
    if not token and not filename:
        filename = str(DEFAULT_KEY_FILE.expanduser())
    if filename:
        path = Path(filename).expanduser()
        try:
            mode = path.stat().st_mode
        except OSError as error:
            if path == DEFAULT_KEY_FILE.expanduser() and isinstance(error, FileNotFoundError):
                raise SystemExit("No saved signal API key; run signal_client.py configure-key") from None
            raise SystemExit(f"Cannot read SIGNAL_API_KEY_FILE: {error.strerror}") from None
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise SystemExit("SIGNAL_API_KEY_FILE must be a regular file with mode 0600")
        try:
            token = path.read_text().strip()
        except OSError as error:
            raise SystemExit(f"Cannot read SIGNAL_API_KEY_FILE: {error.strerror}") from None
    if len(token) < 32:
        raise SystemExit("Signal API key is missing or too short")
    return token


def configure_key():
    path = DEFAULT_KEY_FILE.expanduser()
    token = getpass.getpass("Signal API key: ").strip()
    if len(token) < 32:
        raise SystemExit("Signal API key is missing or too short")
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.parent.chmod(0o700)
    temporary = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(token + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass
    print(f"Saved private key to {path}")
    return 0


def api_request(method, path, token, body=None, opener=None):
    data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
    request = Request(
        os.getenv("SIGNAL_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/") + path,
        data=data,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with (opener or urlopen)(request, timeout=15) as response:
            return json.loads(response.read())
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise SystemExit(f"HTTP {error.code}: {detail}") from None
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SystemExit(f"Signal API request failed ({type(error).__name__})") from None


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    signal_id = matching(SIGNAL_ID, "signal ID")
    ticker = matching(TICKER, "ticker")

    create = commands.add_parser("create")
    create.add_argument("signal_id", type=signal_id)
    create.add_argument("destination", choices=("LIVE", "PAPER"))
    create.add_argument("ticker", type=ticker)
    create.add_argument("price", type=positive_price)
    create.add_argument("timestamp", type=positive_int, nargs="?")

    commands.add_parser("list")

    get = commands.add_parser("get")
    get.add_argument("signal_id", type=signal_id)

    edit = commands.add_parser("edit")
    edit.add_argument("signal_id", type=signal_id)
    edit.add_argument("revision", type=positive_int, nargs="?")
    edit.add_argument("--destination", choices=("LIVE", "PAPER"))
    edit.add_argument("--ticker", type=ticker)
    edit.add_argument("--price", type=positive_price)
    edit.add_argument("--timestamp", type=positive_int)

    delete = commands.add_parser("delete")
    delete.add_argument("signal_id", type=signal_id, nargs="?")
    delete.add_argument("revision", type=positive_int, nargs="?")
    commands.add_parser("delete-only")
    commands.add_parser("configure-key")
    return result


def main(argv=None, opener=None):
    arguments = parser().parse_args(argv)
    if arguments.command == "configure-key":
        return configure_key()
    token = credential()
    if arguments.command == "create":
        body = {name: getattr(arguments, name) for name in
                ("signal_id", "destination", "ticker", "price", "timestamp")}
        if body["timestamp"] is None:
            body["timestamp"] = int(time.time())
        response = api_request("POST", "/signals", token, body, opener)
    elif arguments.command == "list":
        response = api_request("GET", "/signals", token, opener=opener)
    elif arguments.command == "get":
        response = api_request("GET", "/signals/" + quote(arguments.signal_id), token, opener=opener)
    elif arguments.command == "edit":
        fields = {name: getattr(arguments, name) for name in
                  ("destination", "ticker", "price", "timestamp")
                  if getattr(arguments, name) is not None}
        if not fields:
            parser().error("edit requires at least one changed field")
        revision = arguments.revision
        if revision is None:
            current = api_request("GET", "/signals/" + quote(arguments.signal_id),
                                  token, opener=opener)
            revision = current["revision"]
        response = api_request("POST", "/signals/edit", token,
                               {"signal_id": arguments.signal_id,
                                "revision": revision, **fields}, opener)
    elif arguments.command == "delete":
        if arguments.signal_id is None:
            response = delete_only(token, opener)
        else:
            revision = arguments.revision
            if revision is None:
                current = api_request("GET", "/signals/" + quote(arguments.signal_id),
                                      token, opener=opener)
                revision = current["revision"]
            response = api_request("POST", "/signals/delete", token,
                                   {"signal_id": arguments.signal_id,
                                    "revision": revision}, opener)
    else:
        response = delete_only(token, opener)
    json.dump(response, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def delete_only(token, opener=None):
    signals = api_request("GET", "/signals", token, opener=opener)
    deletable = [item for item in signals if item.get("status") == "pending" or
                 item.get("status") == "rejected" and item.get("reason") == "no_direction"]
    if len(deletable) != 1:
        raise SystemExit(f"Expected exactly one deletable signal; found {len(deletable)}")
    item = deletable[0]
    return api_request("POST", "/signals/delete", token,
                       {"signal_id": item["signal"]["signal_id"],
                        "revision": item["revision"]}, opener)


if __name__ == "__main__":
    raise SystemExit(main())
