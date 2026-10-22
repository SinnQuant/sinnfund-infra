"""Translate IBKR Flex OpenPosition rows into ticker -> delayed LSEG RIC mappings.

Requires an already-open *default* LSEG Platform session for symbol conversion.
Use the resulting mapping with lseg-feed/feed_api.py (LSEG_SYMBOLS).
Does not guess suffixes or silently map non-equity assets.
"""
from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable


# Nasdaq RICs are commonly .O. Do NOT enforce ".N" for NYSE:
# LSEG symbol conversion legitimately returns bare primary RICs (e.g. BAC)
# or .K for some NYSE listings. Confirm exact identity via ISIN/ticker.
_EXPECTED_SUFFIX = {
    "NASDAQ": ".O", "NASDAQ.NMS": ".O", "NASDAQ.NCM": ".O",
    "NASDAQ.NGM": ".O",
}
_RIC_LIKE = re.compile(r"^[A-Za-z0-9^_-]+\.[A-Za-z]{1,3}$")
_VALID_SYMBOL = re.compile(r"^[A-Za-z0-9.^_-]{1,32}$")


def read_flex_positions(*paths: str | Path) -> list[dict[str, str]]:
    """Read SUMMARY positions from flex.py's archived .xml.gz report(s)."""
    positions: list[dict[str, str]] = []
    for path in paths:
        with gzip.open(path, "rb") as f:
            root = ET.parse(f).getroot()
        positions.extend(dict(node.attrib) for node in root.iter("OpenPosition")
                         if node.get("levelOfDetail") == "SUMMARY")
    return positions


def flex_to_lseg_symbols(
    positions: Iterable[dict[str, str]],
    overrides: dict[str, str] | None = None,
    converter: Callable | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return (symbol -> /delayed.RIC, symbol -> reason_if_unresolved).

    Calls LSEG symbology lookup once for ordinary US tickers and once for
    already-RIC-like symbols (e.g. 4063.T), using the open EDP session.

    overrides can be indexed by IBKR conid (preferred) or symbol:
        {"123456": "IWM", "VWSc": "VWS.CO"}
    An override must be independently checked against the *exact* security.

    Matching checks: asset category, returned ticker, ISIN if available, and
    conventional Nasdaq suffix. NYSE's best-match RIC may be bare, .K or .N.
    Rejects unusual share-class/stale RICs pending manual confirmation.
    This is still a candidate map: a streaming refresh must confirm it works;
    exchange, currency and issuer identity should be reviewed.
    """
    if converter is None:
        from lseg.data.discovery import convert_symbols as converter
        from lseg.data.discovery import SymbolTypes
    else:
        # Injecting a converter makes offline testing possible; production
        # follows the library's SymbolTypes constants.
        from lseg.data.discovery import SymbolTypes

    overrides = overrides or {}
    mapping: dict[str, str] = {}
    unresolved: dict[str, str] = {}
    candidates: dict[str, dict] = {}
    symbol_conids: dict[str, set[str]] = defaultdict(set)

    for p in positions:
        symbol = (p.get("symbol") or "").strip()
        conid = str(p.get("conid") or "")
        if not symbol:
            unresolved[f"<blank>:{conid}"] = "missing IBKR symbol"
            continue
        if p.get("levelOfDetail") not in (None, "SUMMARY"):
            continue
        symbol_conids[symbol].add(conid or symbol)
        asset = (p.get("assetCategory") or "").upper()
        desc = (p.get("description") or "").upper()
        if asset not in ("STK", "ETF"):
            unresolved[symbol] = f"not a confirmed stock/ETF (assetCategory={asset or 'missing'})"
            continue
        if "WARRANT" in desc or not _VALID_SYMBOL.fullmatch(symbol):
            unresolved[symbol] = "warrant or nonstandard symbol: requires explicit mapping"
            continue
        candidates[symbol] = p

    # A ticker alone cannot distinguish different contracts/security IDs.
    for symbol, ids in symbol_conids.items():
        if len(ids) > 1:
            candidates.pop(symbol, None)
            unresolved[symbol] = "multiple IBKR conids share this symbol; use conid-level mapping"

    to_lookup: list[str] = []
    ric_like: list[str] = []
    for symbol, p in candidates.items():
        manual = overrides.get(str(p.get("conid") or "")) or overrides.get(symbol)
        if manual:
            ric = manual.strip().lstrip("/")
            if not ric or any(ch.isspace() or ch == "," for ch in ric):
                unresolved[symbol] = "invalid manual RIC"
            else:
                mapping[symbol] = "/" + ric
            continue
        if _RIC_LIKE.fullmatch(symbol):
            ric_like.append(symbol)
        elif (p.get("currency") or "").upper() == "USD":
            to_lookup.append(symbol)
        else:
            unresolved[symbol] = "non-USD / unknown listing; provide verified RIC override"

    def lookup(symbols: list[str], kind: object, *, us: bool = False):
        if not symbols:
            return None
        opts = dict(symbols=symbols, from_symbol_type=kind,
                    to_symbol_types=[SymbolTypes.RIC, SymbolTypes.ISIN,
                                     SymbolTypes.TICKER_SYMBOL])
        if us:
            opts["preferred_country_code"] = "USA"  # *preference*, not restriction
        return converter(**opts)

    resp_by_kind = [
        (to_lookup, lookup(to_lookup, SymbolTypes.TICKER_SYMBOL, us=True)),
        (ric_like, lookup(ric_like, SymbolTypes.RIC)),
    ]
    for originals, response in resp_by_kind:
        if response is None:
            continue
        df = response if hasattr(response, "loc") else response.data.df
        for symbol in originals:
            if symbol in unresolved:
                continue
            try:
                row = df.loc[symbol]
            except (KeyError, TypeError):
                unresolved[symbol] = "LSEG symbol lookup returned no match"
                continue
            # Reject multiple matches rather than selecting an arbitrary row.
            if getattr(row, "ndim", 1) != 1:
                unresolved[symbol] = "LSEG lookup returned multiple matches"
                continue

            def value(name: str) -> str:
                v = row.get(name)
                if v is None or str(v).lower() in ("nan", "<na>", "none", "nat"):
                    return ""
                return str(v).strip()

            ric = value("RIC")
            if not ric or "," in ric or any(c.isspace() for c in ric):
                unresolved[symbol] = "LSEG lookup returned no valid RIC"
                continue
            # A primary conversion can point to a former ticker / special
            # class. Do not automatically subscribe to those as common stocks.
            if "^" in ric or len(ric) > 64:
                unresolved[symbol] = f"unusual LSEG RIC={ric}; verify instrument manually"
                continue
            p = candidates[symbol]
            isin = (p.get("isin") or "").upper()
            returned_isin = value("IssueISIN").upper()
            if isin and returned_isin != isin:
                unresolved[symbol] = "ISIN mismatch/missing; review cross-listing manually"
                continue
            ticker = value("TickerSymbol")
            if ticker and symbol not in ric_like and ticker.upper() != symbol.upper():
                unresolved[symbol] = "LSEG ticker mismatch; manual review needed"
                continue
            if symbol not in ric_like and (p.get("currency") or "").upper() == "USD":
                root = ric.split(".", 1)[0]
                if root.upper() != symbol.upper():
                    unresolved[symbol] = f"RIC={ric} does not match IBKR ticker; manual review needed"
                    continue
            if symbol in ric_like and ric != symbol:
                unresolved[symbol] = "symbol resembles a RIC, but LSEG returned a different RIC"
                continue
            exchange = (p.get("listingExchange") or "").upper()
            expected = _EXPECTED_SUFFIX.get(exchange)
            if expected and not ric.upper().endswith(expected):
                unresolved[symbol] = f"listingExchange={exchange} but returned RIC={ric}"
                continue
            mapping[symbol] = "/" + ric.lstrip("/")

    # The existing feed API keys quotes by ticker and disallows duplicated RICs.
    ric_to_symbol: dict[str, str] = {}
    for symbol, ric in list(mapping.items()):
        if ric in ric_to_symbol:
            other = ric_to_symbol.pop(ric)
            mapping.pop(symbol)
            mapping.pop(other, None)
            unresolved[symbol] = f"same LSEG RIC as {other}; check cross-listing"
            unresolved[other] = f"same LSEG RIC as {symbol}; check cross-listing"
        else:
            ric_to_symbol[ric] = symbol
    return mapping, unresolved


def env_line(mapping: dict[str, str]) -> str:
    """Output accepted by the existing feed_api.py LSEG_SYMBOLS parser."""
    return "LSEG_SYMBOLS=" + ",".join(f"{sym}={ric}" for sym, ric in sorted(mapping.items()))
