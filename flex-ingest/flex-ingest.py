"""Download and archive one day's raw IBKR Flex XML reports.

Run automatically via flex-ingest.service or manually:
    python flex-ingest.py                    # today's date in New York
    python flex-ingest.py --date 20261014    # specific report date
    python flex-ingest.py --book main        # one configured book
    python flex-ingest.py --force            # replace already downloaded files

Credentials: /opt/flex-ingest/.env
Data:        /var/lib/flex-ingest/flex/data/YYYYMMDD/<book>.xml.gz
"""

import argparse
import datetime as dt
import gzip
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

BASE = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
ENV_FILE = Path("/opt/flex-ingest/.env")
DATA_DIR = Path(os.environ.get("STATE_DIRECTORY", "/var/lib/flex-ingest")) / "flex/data"
EASTERN = ZoneInfo("America/New_York")

POLL_SECONDS = 5
TIMEOUT_SECONDS = 600
SEND_WAITS = (0, 5, 15, 60)
RETRY_LATER = {"1001", "1009", "1018", "1021"}
STILL_BUILDING = "1019"

POLL_SECONDS = 15
TIMEOUT_SECONDS = 600

SEND_WAITS = (0, 60)

class FlexError(RuntimeError):
    pass


def books():
    """Pair comma-separated tokens and query IDs; one token may serve many IDs."""
    tokens = [x.strip() for x in os.getenv("IBKR_TOKEN", "").split(",")]
    queries = [x.strip() for x in os.getenv("IBKR_QUERY_ID", "").split(",")]
    if not all(tokens) or not all(queries):
        raise FlexError("IBKR_TOKEN and IBKR_QUERY_ID must both be set")
    if len(tokens) == 1:
        tokens *= len(queries)
    if len(tokens) != len(queries):
        raise FlexError("IBKR_TOKEN and IBKR_QUERY_ID counts do not match")
    return [("main" if i == 0 else f"book{i + 1}", token, query)
            for i, (token, query) in enumerate(zip(tokens, queries))]


def request(endpoint, params):
    """Make an HTTP request without exposing tokens in exception messages."""
    try:
        response = requests.get(f"{BASE}/{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        raise FlexError(f"{endpoint}: HTTP request failed") from None


def api_status(body):
    """Return the status, error code, and message from a Flex status response."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise FlexError("IBKR returned malformed XML") from None
    return (root.findtext("Status"), root.findtext("ErrorCode"),
            root.findtext("ErrorMessage"), root.findtext("ReferenceCode"))


def pull(token, query_id, day):
    """Request a report and poll until its raw XML is ready."""
    for delay in SEND_WAITS:
        time.sleep(delay)
        response = request("SendRequest", {
            "t": token, "q": query_id, "v": 3, "fd": day, "td": day,
        })
        status, code, message, reference = api_status(response)
        if status == "Success":
            if not reference:
                raise FlexError("SendRequest succeeded without a reference code")
            break
        if code not in RETRY_LATER:
            raise FlexError(f"SendRequest: {code or 'unknown'}: {message or 'failed'}")
    else:
        raise FlexError(f"SendRequest: {code or 'unknown'}: retries exhausted")

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        response = request("GetStatement", {"t": token, "q": reference, "v": 3})
        if b"<FlexQueryResponse" in response[:500]:
            return response
        status, code, message, _ = api_status(response)
        if code not in RETRY_LATER | {STILL_BUILDING}:
            raise FlexError(f"GetStatement: {code or status or 'unknown'}: {message or 'failed'}")
    raise FlexError("GetStatement: report not ready before timeout")


def save(day, name, xml):
    """Atomically write gzip output so incomplete downloads are not archived."""
    folder = DATA_DIR / day
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"{name}.xml.gz"
    temporary = folder / f".{name}.xml.gz.tmp"
    try:
        with gzip.open(temporary, "wb") as fh:
            fh.write(xml)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="YYYYMMDD; defaults to today in New York")
    parser.add_argument("--book", help="Only ingest one book, e.g. main or book2")
    parser.add_argument("--force", action="store_true", help="Replace existing files")
    args = parser.parse_args()

    # set default day
    now = dt.datetime.now(EASTERN)
    previous_day = now - dt.timedelta(days=1)
    day = args.date or previous_day.strftime("%Y%m%d")
    
    try:
        dt.datetime.strptime(day, "%Y%m%d")
    except ValueError:
        parser.error("--date must be a valid date in YYYYMMDD format")

    load_dotenv(ENV_FILE, override=False)
    configured = books()
    if args.book:
        configured = [entry for entry in configured if entry[0] == args.book]
        if not configured:
            parser.error(f"unknown book: {args.book}")

    failures = 0
    for name, token, query_id in configured:
        output = DATA_DIR / day / f"{name}.xml.gz"
        if output.is_file() and not args.force:
            print(f"{day} {name}: already archived ({output})")
            continue
        try:
            xml = pull(token, query_id, day)
            output = save(day, name, xml)
            print(f"{day} {name}: saved {len(xml)} bytes to {output}")
        except (FlexError, OSError) as exc:
            failures += 1
            print(f"{day} {name}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

