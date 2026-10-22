#!/usr/bin/env python3
"""Read-only web dashboard for the newest IBKR Flex XML archive.

Runs alongside parse_flex_positions.py. Requires FastAPI and Uvicorn.

Usage (ASGI, recommended):
  uvicorn web:app --host 127.0.0.1 --port 8001
  FLEX_ARCHIVE_DIR=/path/to/flex/data uvicorn web:app --host 127.0.0.1 --port 8001

Alternative:
  python3 web.py --host 127.0.0.1 --port 8001

For private data, keep the default loopback binding and access through an
SSH tunnel or an authenticated reverse proxy. No built-in authentication.
"""

import argparse
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
import uvicorn

from parse_flex_positions import DEFAULT_ARCHIVE_DIR, latest_date, parse_archives

ARCHIVE_DIR = Path(os.environ.get("FLEX_ARCHIVE_DIR", str(DEFAULT_ARCHIVE_DIR)))

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio • Flex Archive</title>
<style>
  :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; --bg:#0b1019; --surface:#151c29; --surface2:#1b2533; --border:#2d3949; --text:#e8eef6; --muted:#9cacbf; --accent:#8ab4ff; --green:#71d4aa; --red:#ff9a9a; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); }
  .container { max-width:1450px; margin:0 auto; padding:32px 24px 64px; }
  .eyebrow { text-transform:uppercase; color:var(--accent); font-size:11px; font-weight:700; letter-spacing:.16em; }
  h1 { font-size:clamp(25px,3vw,36px); font-weight:680; letter-spacing:-.035em; margin:7px 0 6px; }
  .subtitle { color:var(--muted); margin:0; font-size:14px; }
  .header { display:flex; justify-content:space-between; gap:20px; align-items:center; flex-wrap:wrap; }
  .pill { padding:8px 11px; border-radius:999px; color:var(--muted); border:1px solid var(--border); font-size:12px; }
  .stats { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:13px; margin:26px 0 26px; }
  .stat { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:17px 19px; }
  .stat-label { font-size:12px; color:var(--muted); margin-bottom:7px; }
  .stat-value { font-size:24px; font-weight:650; font-variant-numeric:tabular-nums; }
  .pane { background:var(--surface); border:1px solid var(--border); border-radius:14px; overflow:hidden; }
  .toolbar { display:flex; gap:13px; justify-content:flex-end; align-items:center; padding:14px; flex-wrap:wrap; }
  .controls { display:flex; gap:9px; flex-wrap:wrap; }
  input, select { min-height:38px; background:var(--bg); color:var(--text); border:1px solid var(--border); border-radius:8px; padding:7px 12px; font:inherit; font-size:13px; }
  input { width:min(250px, 70vw); }
  input::placeholder { color:#8392a6; }
  input:focus, select:focus, button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  .table-wrap { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { color:var(--muted); font-size:11px; letter-spacing:.03em; text-align:left; font-weight:650; background:#172131; white-space:nowrap; }
  th button { border:0; background:transparent; color:inherit; padding:11px 12px; cursor:pointer; font:inherit; font-size:inherit; font-weight:inherit; text-align:inherit; white-space:nowrap; }
  th button:hover { color:var(--accent); }
  td { padding:11px 12px; border-top:1px solid var(--border); vertical-align:middle; white-space:nowrap; }
  tr:hover td { background:#1a2534; }
  .sym { font-size:14px; font-weight:700; }
  .desc { color:var(--muted); font-size:11px; max-width:180px; overflow:hidden; text-overflow:ellipsis; margin-top:3px; }
  .num { text-align:right; font-variant-numeric:tabular-nums; }
  .pos { color:var(--green); } .neg { color:var(--red); }
  .price-status { font-size:12px; font-weight:700; }
  .price-status.close { color:var(--muted); }
  .direction { font-size:11px; font-weight:700; border-radius:5px; padding:4px 7px; background:#263647; }
  .direction.short { color:#f1b1b1; } .direction.long { color:#9cd9bd; }
  .expand { color:var(--accent); border:0; background:transparent; padding:4px 0; cursor:pointer; text-decoration:underline; text-underline-offset:3px; }
  .details td { white-space:normal; background:#121b29; padding:18px; }
  .detail-heading { margin:0 0 10px; font-size:13px; }
  .lot-table { margin-bottom:18px; border:1px solid var(--border); }
  .lot-table th, .lot-table td { padding:9px 10px; }
  .detail-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(185px,1fr)); gap:14px 22px; }
  .detail-name { color:var(--muted); font-size:11px; margin-bottom:4px; }
  .detail-value { font-size:12px; overflow-wrap:anywhere; }
  .empty { text-align:center; color:var(--muted); padding:35px; }
  .footer { color:var(--muted); font-size:12px; margin-top:16px; line-height:1.5; }
  @media (max-width:700px) { .stats { grid-template-columns:repeat(2,1fr); } .container { padding:20px 12px 44px; } .toolbar { padding:14px; } }
</style>
</head>
<body>
<main class="container">
  <div class="header"><div>
    <div class="eyebrow">IBKR FLEX / ARCHIVED POSITIONS</div>
    <h1>Portfolio positions</h1>
    <p class="subtitle">Read-only report snapshots · Not live market prices</p>
  </div><div class="pill" id="asof"></div></div>

  <section class="stats" aria-label="Report summary">
    <div class="stat"><div class="stat-label">Open positions</div><div class="stat-value" id="count">—</div></div>
    <div class="stat"><div class="stat-label">Accounts with positions</div><div class="stat-value" id="accounts">—</div></div>
    <div class="stat"><div class="stat-label">Books</div><div class="stat-value" id="books">—</div></div>
    <div class="stat"><div class="stat-label">Individual tax lots</div><div class="stat-value" id="lots-count">—</div></div>
  </section>

  <section class="pane">
    <div class="toolbar">
      <div class="controls">
        <input id="search" type="search" placeholder="Search symbol, account, name…" aria-label="Search rows">
        <select id="account-filter" aria-label="Filter by account"><option value="">All accounts</option></select>
      </div>
    </div>
    <div class="table-wrap"><table><thead id="head"></thead><tbody id="body"></tbody></table></div>
  </section>
  <p class="footer" id="footer"></p>
</main>
<script id="portfolio-data" type="application/json">__PAYLOAD__</script>
<script>
(() => {
  "use strict";
  const data = JSON.parse(document.getElementById("portfolio-data").textContent);
  const positions = data.positions || [], lots = data.lots || [];
  const lotsByPosition = new Map();
  const positionKey = row => JSON.stringify([row.account_id, row.conid]);
  for (const lot of lots) {
    const key = positionKey(lot);
    if (!lotsByPosition.has(key)) lotsByPosition.set(key, []);
    lotsByPosition.get(key).push(lot);
  }
  const $ = id => document.getElementById(id);
  const date = data.date || "";
  const formattedDate = /^\d{8}$/.test(date) ? `${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}` : date;
  $("asof").textContent = `Report date: ${formattedDate}`;
  $("count").textContent = positions.length.toLocaleString();
  $("accounts").textContent = new Set(positions.map(x => x.account_id)).size.toLocaleString();
  $("books").textContent = new Set([...positions,...lots].map(x => x.book)).size.toLocaleString();
  $("lots-count").textContent = lots.length.toLocaleString();
  const accounts = [...new Set([...positions,...lots].map(x => x.account_id))].filter(Boolean).sort();
  for (const acct of accounts) { const o = document.createElement("option"); o.value=acct; o.textContent=acct; $("account-filter").append(o); }

  const positionColumns = [
    { key:"symbol", label:"Symbol" }, { key:"account_id", label:"Account" },
    { key:"side", label:"Side" }, { key:"quantity", label:"Qty", numeric:true },
    { key:"cost_basis_price", label:"Avg cost", numeric:true },
    { key:"mark_price", label:"Price", numeric:true },
    { key:"market_value", label:"Value", numeric:true },
    { key:"unrealized_pnl", label:"Unrealized P&L", numeric:true },
    { key:"percent_of_nav", label:"NAV% (close)", numeric:true },
    { key:"price_source", label:"Price source" }
  ];
  const lotValueColumns = [
    { key:"open_datetime", label:"Date bought" },
    { key:"quantity", label:"Qty", numeric:true },
    { key:"cost_basis_price", label:"Cost / share", numeric:true },
    { key:"cost_basis_money", label:"Cost basis", numeric:true },
    { key:"mark_price", label:"Closing price", numeric:true },
    { key:"market_value", label:"Closing value", numeric:true },
    { key:"unrealized_pnl", label:"Unrealized P&L", numeric:true }
  ];
  let sortKey="symbol", descending=false, expanded=null;
  const num = v => v === "" || v == null ? NaN : Number(v);
  const fmt = (v, key) => {
    if (v == null || v === "") return "—";
    if (key === "open_datetime" && /^\d{8}/.test(String(v)))
      return `${String(v).slice(0,4)}-${String(v).slice(4,6)}-${String(v).slice(6,8)}`;
    const n = num(v); if (!Number.isFinite(n)) return String(v);
    if (key === "percent_of_nav") return `${n.toFixed(2)}%`;
    if (key === "quantity") return new Intl.NumberFormat("en-US", {maximumFractionDigits:5}).format(n);
    if (key === "mark_price") return new Intl.NumberFormat("en-US", {minimumFractionDigits:2, maximumFractionDigits:4}).format(n);
    return new Intl.NumberFormat("en-US", {minimumFractionDigits:2, maximumFractionDigits:2}).format(n);
  };
  const detailLabels = { book:"Book", conid:"IBKR Contract ID", description:"Description", asset_category:"Asset category", currency:"Currency", report_date:"Report date", multiplier:"Multiplier", percent_of_nav:"% NAV at close", cost_basis_money:"Cost basis total", listing_exchange:"Exchange", isin:"ISIN", figi:"FIGI" };
  const el = (tag, cls, value) => { const out=document.createElement(tag); if(cls) out.className=cls; if(value !== undefined) out.textContent=String(value); return out; };

  function render() {
    const rows = positions;
    const columns = positionColumns;
    const search = $("search").value.trim().toLowerCase();
    const account = $("account-filter").value;
    const filtered = rows.filter(p => (!account || p.account_id===account) && (!search || [p.symbol,p.description,p.account_id,p.conid,p.book].some(v => String(v||"").toLowerCase().includes(search))));
    filtered.sort((a,b) => {
      const x=a[sortKey]??"", y=b[sortKey]??"";
      const nx=num(x), ny=num(y);
      const cmp=Number.isFinite(nx) && Number.isFinite(ny) ? nx-ny : String(x).localeCompare(String(y),undefined,{numeric:true,sensitivity:"base"});
      return descending ? -cmp : cmp;
    });
    $("head").replaceChildren(); $("body").replaceChildren();
    const tr=el("tr");
    for (const c of [...columns, {key:"details",label:"Details"}]) {
      const th=el("th"); if(c.numeric) th.className="num";
      if(c.key === "details") {th.textContent=c.label;}
      else { const btn=el("button", "",c.label + (c.key===sortKey ? (descending ? " ↓":" ↑") : "")); btn.type="button"; btn.onclick=() => { if(sortKey===c.key) descending=!descending; else {sortKey=c.key;descending=false;} render(); }; th.append(btn); }
      tr.append(th);
    }
    $("head").append(tr);
    if (!filtered.length) { const row=el("tr"); const cell=el("td","empty","No matching records"); cell.colSpan=columns.length+1;row.append(cell);$("body").append(row); }
    for (let i=0; i<filtered.length; i++) {
      const p=filtered[i], row=el("tr");
      for (const c of columns) {
        const td=el("td", c.numeric ? "num" : "");
        if (c.key === "symbol") {td.append(el("div","sym",p.symbol||"—")); td.append(el("div","desc",p.description||""));}
        else if(c.key === "side") { const s=el("span",`direction ${String(p.side||"").toLowerCase()}`,p.side||"—");td.append(s); }
        else if(c.key === "price_source") {
          td.append(el("span", "price-status close", "Flex close"));
          td.title = "IBKR Flex closing mark";
        }
        else { td.textContent=c.numeric || c.key === "open_datetime" ? fmt(p[c.key],c.key) : (p[c.key]||"—"); }
        if(c.key === "unrealized_pnl" && Number.isFinite(num(p[c.key]))) td.classList.add(num(p[c.key])>=0 ? "pos":"neg");
        row.append(td);
      }
      const dt=el("td"); const button=el("button","expand",expanded===p?"Hide":"View");button.type="button";
      button.setAttribute("aria-expanded",String(expanded===p));
      button.onclick=() => {expanded=expanded===p?null:p;render();}; dt.append(button);row.append(dt);$("body").append(row);
      if(expanded===p) {
        const er=el("tr","details"), cell=el("td"), grid=el("div","detail-grid");cell.colSpan=columns.length+1;
        const matchedLots = lotsByPosition.get(positionKey(p)) || [];
        cell.append(el("h3", "detail-heading", `Tax lots (${matchedLots.length}) · ${p.currency || "currency unavailable"}`));
        const table = el("table", "lot-table"), header = el("tr");
        for (const column of lotValueColumns) header.append(el("th", column.numeric ? "num" : "", column.label));
        const head = el("thead"); head.append(header); table.append(head);
        const body = el("tbody");
        for (const lot of matchedLots) {
          const row = el("tr");
          for (const column of lotValueColumns) {
            const value = el("td", column.numeric ? "num" : "", fmt(lot[column.key], column.key));
            if (column.key === "unrealized_pnl" && Number.isFinite(num(lot[column.key])))
              value.classList.add(num(lot[column.key]) >= 0 ? "pos" : "neg");
            row.append(value);
          }
          body.append(row);
        }
        if (!matchedLots.length) {
          const row=el("tr"), value=el("td","empty","No tax-lot detail in the Flex report");
          value.colSpan=lotValueColumns.length;row.append(value);body.append(row);
        }
        table.append(body); cell.append(table);
        cell.append(el("h3", "detail-heading", "Position details"));
        for (const [key,label] of Object.entries(detailLabels)) {
          if (!Object.prototype.hasOwnProperty.call(p,key)) continue;
          const item=el("div");item.append(el("div","detail-name",label));item.append(el("div","detail-value",p[key] || "—"));grid.append(item);
        }
        er.append(cell);cell.append(grid);$("body").append(er);
      }
    }
    $("footer").textContent = `Showing ${filtered.length.toLocaleString()} of ${rows.length.toLocaleString()} positions · ${data.files} XML archive(s). Statement prices are not live; expand a position to see its tax lots.`;
  }
  $("search").addEventListener("input",render);$("account-filter").addEventListener("change",render); render();
})();
</script>
</body>
</html>'''


def load_report(archive_dir: Path) -> dict:
    if not archive_dir.is_dir():
        raise FileNotFoundError(f"Archive directory not found: {archive_dir}")
    date = latest_date(archive_dir)
    paths = sorted((archive_dir / date).glob("*.xml.gz"))
    positions, lots = parse_archives(paths)
    return {"date": date, "files": len(paths), "positions": positions, "lots": lots}


# ASGI entrypoint. Nginx can continue proxying /close/ to 127.0.0.1:8001.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

WEB_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
}


@app.get("/", response_class=HTMLResponse)
def index():
    try:
        report = load_report(ARCHIVE_DIR)
    except Exception:
        logging.exception("Could not read Flex archive")
        return PlainTextResponse(
            "Flex archive unavailable; inspect server logs.\n",
            status_code=503,
            headers=WEB_HEADERS,
        )

    # Escape XML-derived values before embedding them in an inline JSON script.
    payload = (
        json.dumps(report, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return HTMLResponse(HTML.replace("__PAYLOAD__", payload), headers=WEB_HEADERS)


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    try:
        # Check archive availability without parsing all reports.
        latest_date(ARCHIVE_DIR)
    except Exception:
        return PlainTextResponse(
            "Flex archive unavailable\n", status_code=503, headers=WEB_HEADERS
        )
    return PlainTextResponse("ok\n", headers=WEB_HEADERS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8001, help="Default: 8001")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    uvicorn.run(app, host=args.host, port=args.port, workers=1, access_log=False)


if __name__ == "__main__":
    main()
