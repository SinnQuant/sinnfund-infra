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
from decimal import Decimal, InvalidOperation
import gzip
import json
import os
import re
import requests
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
    """Parse Flex archives and revalue positions/lots using one LSEG API call.

    Priority:
      1. Fresh LSEG delayed prices (connected, <= 180 seconds)
      2. Cached LSEG prices (<= 7 days)
      3. Original IBKR Flex prices

    All financial values remain strings. Original Flex values are preserved
    whenever a valid replacement price is unavailable.
    """
    positions, lots = [], []
    seen = {}

    for path in files:
        book = path.name.removesuffix(".xml.gz")

        with gzip.open(path, "rb") as stream:
            root = ET.parse(stream).getroot()

        if root.tag != "FlexQueryResponse":
            raise ValueError(
                f"Unexpected XML root {root.tag!r} in {path}"
            )

        for statement in root.iter("FlexStatement"):
            account = statement.get("accountId", "")
            date = statement.get("toDate", "")
            key = (account, statement.get("fromDate", ""), date)

            if key in seen:
                print(
                    f"Skipping duplicate account {account} in {path.name}; "
                    f"already read from {seen[key]}",
                    file=sys.stderr
                )
                continue

            seen[key] = path.name

            for element in statement.findall("./OpenPositions/OpenPosition"):
                row = {
                    "report_date": element.get("reportDate") or date,
                    "book": book,
                    "account_id": element.get("accountId") or account,
                    **{
                        name: element.get(attribute, "")
                        for name, attribute in FIELDS.items()
                    },
                }

                detail = element.get("levelOfDetail", "SUMMARY")

                if detail == "SUMMARY":
                    positions.append(row)

                elif detail == "LOT":
                    lots.append({
                        **row,
                        **{
                            name: element.get(attribute, "")
                            for name, attribute in LOT_FIELDS.items()
                        },
                    })

                else:
                    print(
                        f"Skipping unknown levelOfDetail={detail!r} "
                        f"in {path.name}",
                        file=sys.stderr
                    )

    # ---------------------------------------------------------
    # Fetch all LSEG prices with exactly ONE HTTP request.
    # ---------------------------------------------------------

    MAX_LIVE_AGE = 180
    MAX_CACHED_AGE = 7 * 24 * 3600

    quotes = {}
    price_source = "flex"

    try:
        response = requests.get(
            "http://127.0.0.1:8091/prices",
            timeout=5
        )
        response.raise_for_status()

        payload = response.json()
        age = payload.get("snapshot_age_seconds")
        available = payload.get("quotes")

        if isinstance(available, dict) and available and age is not None:
            age = float(age)

            if 0 <= age <= MAX_CACHED_AGE:

                quotes = available

                if (
                    payload.get("connected") is True
                    and age <= MAX_LIVE_AGE
                ):
                    price_source = "lseg_delayed"

                else:
                    price_source = "lseg_cached"
                    print(
                        f"Using cached LSEG prices "
                        f"({age / 3600:.2f} hours old)",
                        file=sys.stderr
                    )

            else:
                print(
                    "LSEG snapshot too old; retaining Flex prices",
                    file=sys.stderr
                )

        else:
            print(
                "No usable LSEG snapshot; retaining Flex prices",
                file=sys.stderr
            )

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        print(
            f"LSEG feed unavailable ({type(exc).__name__}); "
            "retaining Flex prices",
            file=sys.stderr
        )

    # ---------------------------------------------------------
    # Revalue positions and tax lots.
    # ---------------------------------------------------------

    for row in positions + lots:

        row["psuedo-live updated"] = 0
        row["price_source"] = "flex"

        symbol = row.get("symbol", "").upper()
        quote = quotes.get(symbol)

        if not isinstance(quote, dict):
            continue

        # Skip options, warrants, and unsupported asset classes.
        if row["asset_category"] != "STK":
            continue

        try:
            price = Decimal(str(quote["price"]))
            old_mark = Decimal(row["mark_price"])
            old_value = Decimal(row["market_value"])
            old_pnl = Decimal(row["unrealized_pnl"])
            quantity = Decimal(row["quantity"])
            multiplier = Decimal(row["multiplier"] or "1")

        except (
            KeyError,
            ValueError,
            TypeError,
            InvalidOperation,
        ):
            continue

        # Validate prices and numeric fields.
        values = (
            price,
            old_mark,
            old_value,
            old_pnl,
            quantity,
            multiplier,
        )

        if (
            not all(x.is_finite() for x in values)
            or price <= 0
            or old_mark <= 0
            or multiplier <= 0
        ):
            continue

        # Reject suspicious price-unit or instrument mismatches.
        ratio = price / old_mark

        if not Decimal("0.1") <= ratio <= Decimal("10"):
            continue

        # USD securities: quantity * multiplier * current price.
        # Non-USD: retain the approximate original FX/unit conversion.
        if row["currency"] == "USD":
            new_value = quantity * multiplier * price
        else:
            new_value = old_value * ratio

        new_value = new_value.quantize(
            Decimal("0.00000001")
        )

        # Adjust existing unrealized P&L by the change in value.
        # Works for both long and short positions.
        new_pnl = old_pnl + (new_value - old_value)

        row["mark_price"] = str(price)
        row["market_value"] = str(new_value)
        row["unrealized_pnl"] = str(new_pnl)

        row["psuedo-live updated"] = 1
        row["price_source"] = price_source

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
