#!/usr/bin/env python3
"""Interactively create, list, or revoke signal API keys locally or over SSH."""

import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile


DEFAULT_HOST = "sinnfund"
REMOTE_ROOT = "/opt/prediction-api/signal-data"
FILES = {"sender": "senders.htpasswd", "exporter": "exporters.htpasswd"}
NAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
HOST = re.compile(r"^[A-Za-z0-9_.@:-]+$")


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_scope():
    while True:
        value = ask("Key type (sender/exporter)", "sender")
        if value in FILES:
            return value
        print("Enter sender or exporter.")


def ask_count(action):
    while True:
        value = ask(f"How many keys should I {action}", "1")
        try:
            number = int(value)
        except ValueError:
            number = 0
        if 1 <= number <= 100:
            return number
        print("Enter a number from 1 to 100.")


def ask_names(count):
    names = []
    while len(names) < count:
        name = ask(f"Name for key {len(names) + 1}")
        if not name or not NAME.fullmatch(name):
            print("Use 1-64 letters, numbers, dots, underscores, or dashes.")
        elif name in names:
            print("Each name must be unique.")
        else:
            names.append(name)
    return names


def host():
    value = os.getenv("SIGNAL_HOST", DEFAULT_HOST)
    if not HOST.fullmatch(value):
        raise SystemExit("SIGNAL_HOST is invalid")
    return value


def local_server():
    root = Path(REMOTE_ROOT)
    return "SIGNAL_HOST" not in os.environ and root.is_dir() and os.access(root, os.W_OK)


def run(command, check=True):
    try:
        return subprocess.run(command, check=check, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise SystemExit("SSH operation failed; verify the key list before retrying") from None
    except OSError:
        raise SystemExit("Could not run ssh or scp") from None


def download(scope, destination):
    filename = FILES[scope]
    remote = f"{REMOTE_ROOT}/{filename}"
    if local_server():
        source = Path(remote)
        if source.is_file():
            shutil.copyfile(source, destination)
        elif source.exists() or not os.access(REMOTE_ROOT, os.W_OK):
            raise SystemExit("Could not check the server key file; nothing changed")
        else:
            destination.write_text("")
        destination.chmod(0o600)
        return
    server = host()
    check = (f"if [ -f {remote} ]; then exit 0; "
             f"elif [ -e {remote} ]; then exit 3; "
             f"elif [ -d {REMOTE_ROOT} ] && [ -w {REMOTE_ROOT} ]; then exit 1; "
             "else exit 4; fi")
    status = run(["ssh", server, check], check=False).returncode
    if status == 0:
        run(["scp", f"{server}:{remote}", str(destination)])
    elif status == 1:
        destination.write_text("")
    else:
        raise SystemExit("Could not check the server key file; nothing changed")
    destination.chmod(0o600)


def install(scope, source):
    filename = FILES[scope]
    upload = f"{REMOTE_ROOT}/.{filename}.upload"
    if local_server():
        try:
            shutil.copyfile(source, upload)
            os.chmod(upload, 0o640)
            os.replace(upload, f"{REMOTE_ROOT}/{filename}")
        except OSError:
            Path(upload).unlink(missing_ok=True)
            raise SystemExit("Local key install failed; nothing was replaced") from None
        return
    server = host()
    run(["scp", str(source), f"{server}:{upload}"])
    run(["ssh", server, f"set -eu; chgrp trading-dev {upload}; chmod 640 {upload}; "
         f"mv {upload} {REMOTE_ROOT}/{filename}"])


def entries(path):
    result = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#") or ":" not in line:
            continue
        name, digest = line.split(":", 1)
        if NAME.fullmatch(name) and digest.startswith("{SHA}"):
            result.append((name, digest))
    return result


def save_entries(path, values):
    path.write_text("".join(f"{name}:{digest}\n" for name, digest in values))
    path.chmod(0o600)


def digest(token):
    value = base64.b64encode(hashlib.sha1(token.encode()).digest()).decode()
    return "{SHA}" + value


def create():
    scope = ask_scope()
    count = ask_count("create")
    names = ask_names(count)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / FILES[scope]
        download(scope, path)
        current = dict(entries(path))
        existing = [name for name in names if name in current]
        if existing:
            joined = ", ".join(existing)
            if ask(f"Rotate existing key(s) {joined}? (yes/no)", "no") != "yes":
                raise SystemExit("Nothing changed")
        created = []
        for name in names:
            token = secrets.token_hex(32)
            current[name] = digest(token)
            created.append((name, token))
        save_entries(path, current.items())
        install(scope, path)
    print("\nCreated keys. Copy them now; they cannot be recovered:\n")
    for name, token in created:
        print(f"{name}: {token}")


def list_keys():
    scope = ask_scope()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / FILES[scope]
        download(scope, path)
        names = [name for name, _ in entries(path)]
    if names:
        print("\n".join(names))
    else:
        print("No keys found.")


def revoke():
    scope = ask_scope()
    count = ask_count("revoke")
    names = ask_names(count)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / FILES[scope]
        download(scope, path)
        current = dict(entries(path))
        missing = [name for name in names if name not in current]
        if missing:
            raise SystemExit("Key name not found: " + ", ".join(missing))
        for name in names:
            del current[name]
        save_entries(path, current.items())
        install(scope, path)
    print("Revoked: " + ", ".join(names))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "list", "revoke"))
    command = parser.parse_args(argv).command
    {"create": create, "list": list_keys, "revoke": revoke}[command]()


if __name__ == "__main__":
    main()
