#!/usr/bin/env python3
"""Parse archived IBKR Flex XML reports without creating or modifying files.

Reads: /var/lib/flex-ingest/flex/data/YYYYMMDD/<book>.xml.gz
Usage:
    python3 parse_flex_positions.py                # newest date, print JSON
    python3 parse_flex_positions.py --date 20261013
    python3 parse_flex_positions.py --include-lots # include individual tax lots

For other Python programs, import parse_archives(paths) to get
(positions, lots) as lists of dictionaries. Financial values remain strings.
"""

import argparse
import gzip
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

STATE_DIR = Path(os.environ.get("STATE_DIRECTORY", "/var/lib/flex-ingest").split(":")[0])
DEFAULT_ARCHIVE_DIR = STATE_DIR / "flex" / "data"

FIELDS = {
    "conid": "conid",
    "symbol": "symbol",
    "description": "description",
    "asset_category": "assetCategory",
    "currency": "currency",
    "side": "side",
    "quantity": "position",
    "multiplier": "multiplier",
    "mark_price": "markPrice",
    "market_value": "positionValue",
    "cost_basis_price": "costBasisPrice",
    "cost_basis_money": "costBasisMoney",
    "unrealized_pnl": "fifoPnlUnrealized",
    "percent_of_nav": "percentOfNAV",
    "listing_exchange": "listingExchange",
    "isin": "isin",
    "figi": "figi",
}
LOT_FIELDS = {
    "open_datetime": "openDateTime",
    "holding_period_datetime": "holdingPeriodDateTime",
    "originating_order_id": "originatingOrderID",
    "originating_transaction_id": "originatingTransactionID",
}


def latest_date(archive_dir: Path) -> str:
    dates = [
        p.name for p in archive_dir.iterdir()
        if p.is_dir() and re.fullmatch(r"\d{8}", p.name)
        and any(p.glob("*.xml.gz"))
    ]
    if not dates:
        raise ValueError(f"No dated XML archives found in {archive_dir}")
    return max(dates)


def parse_archives(files: list[Path]) -> tuple[list[dict], list[dict]]:
    """Return (summary_positions, tax_lots), without writing any files."""
    positions, lots = [], []
    seen = {}  # Avoid counting the same account twice across books.

    for path in files:
        book = path.name.removesuffix(".xml.gz")
        with gzip.open(path, "rb") as stream:
            root = ET.parse(stream).getroot()
        if root.tag != "FlexQueryResponse":
            raise ValueError(f"Unexpected XML root {root.tag!r} in {path}")

        for statement in root.iter("FlexStatement"):
            account = statement.get("accountId", "")
            date = statement.get("toDate", "")
            key = (account, statement.get("fromDate", ""), date)
            if key in seen:
                print(f"Skipping duplicate account {account} in {path.name}; "
                      f"already read from {seen[key]}", file=sys.stderr)
                continue
            seen[key] = path.name

            for element in statement.findall("./OpenPositions/OpenPosition"):
                row = {
                    "report_date": element.get("reportDate") or date,
                    "book": book,
                    "account_id": element.get("accountId") or account,
                    **{name: element.get(attribute, "")
                       for name, attribute in FIELDS.items()},
                }
                detail = element.get("levelOfDetail", "SUMMARY")
                if detail == "SUMMARY":
                    positions.append(row)
                elif detail == "LOT":
                    lots.append({
                        **row,
                        **{name: element.get(attribute, "")
                           for name, attribute in LOT_FIELDS.items()},
                    })
                else:
                    print(f"Skipping unknown levelOfDetail={detail!r} in {path.name}",
                          file=sys.stderr)
    return positions, lots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Report day YYYYMMDD (default: newest archive)")
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--include-lots", action="store_true",
                        help="Include individual tax lots in JSON output")
    args = parser.parse_args()

    if not args.archive_dir.is_dir():
        parser.error(f"Archive directory not found: {args.archive_dir}")
    date = args.date or latest_date(args.archive_dir)
    if not re.fullmatch(r"\d{8}", date):
        parser.error("--date must have format YYYYMMDD")
    files = sorted((args.archive_dir / date).glob("*.xml.gz"))
    if not files:
        parser.error(f"No .xml.gz files found for {date} in {args.archive_dir}")

    positions, lots = parse_archives(files)
    if not positions and lots:
        parser.error("LOT records found but no SUMMARY records: configure "
                     "the IBKR Flex query to include SUMMARY level")

    result = {"date": date, "positions": positions}
    if args.include_lots:
        result["lots"] = lots
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ET.ParseError, ValueError) as exc:
        sys.exit(f"Error: {exc}")

