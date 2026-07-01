#!/usr/bin/env python3
"""No-key SEC EDGAR public lookup and companyfacts reader."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


SEC_USER_AGENT = os.environ.get("KPS_SEC_USER_AGENT", "KPSAnalystWorkbench/0.4 research-contact@example.com")
TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

IMPORTANT_FACTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
]


def normalize_cik(value: str | int) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain at least one digit.")
    return digits.zfill(10)


def fetch_json(url: str, timeout: int = 12) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": SEC_USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public SEC endpoint
        return json.loads(response.read(8_000_000).decode("utf-8", errors="replace"))


def _ticker_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = []
        for value in payload.values():
            if isinstance(value, dict):
                rows.append(value)
        return rows
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def find_company(payload: Any, query: str, limit: int = 10) -> list[dict[str, Any]]:
    normalized = query.lower().strip()
    rows = []
    for row in _ticker_rows(payload):
        ticker = str(row.get("ticker", "")).lower()
        title = str(row.get("title", "")).lower()
        if normalized == ticker or normalized in ticker or normalized in title:
            rows.append(
                {
                    "ticker": row.get("ticker"),
                    "title": row.get("title"),
                    "cik": normalize_cik(row.get("cik_str", "")),
                }
            )
    return rows[:limit]


def lookup_company(query: str, limit: int = 10, timeout: int = 12) -> dict[str, Any]:
    url = TICKER_URL
    try:
        payload = fetch_json(url, timeout=timeout)
        matches = find_company(payload, query, limit=limit)
        return {
            "access_status": "ok" if matches else "not_found",
            "provider": "sec_company_tickers",
            "url": url,
            "query": query,
            "matches": matches,
            "error": "" if matches else "No SEC ticker match found.",
        }
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        return {
            "access_status": "blocked",
            "provider": "sec_company_tickers",
            "url": url,
            "query": query,
            "matches": [],
            "error": str(exc),
        }


def summarize_companyfacts(payload: dict[str, Any], fact_names: list[str] | None = None, limit: int = 4) -> list[dict[str, Any]]:
    facts = payload.get("facts", {}).get("us-gaap", {})
    selected = fact_names or IMPORTANT_FACTS
    summaries = []
    for fact_name in selected:
        fact = facts.get(fact_name)
        if not isinstance(fact, dict):
            continue
        units = fact.get("units", {})
        unit_name = "USD" if "USD" in units else next(iter(units), "")
        values = units.get(unit_name, [])
        if not isinstance(values, list):
            continue
        cleaned = []
        for row in values:
            if not isinstance(row, dict) or row.get("val") is None:
                continue
            cleaned.append(
                {
                    "fy": row.get("fy"),
                    "fp": row.get("fp"),
                    "form": row.get("form"),
                    "filed": row.get("filed"),
                    "end": row.get("end"),
                    "val": row.get("val"),
                    "unit": unit_name,
                }
            )
        cleaned.sort(key=lambda item: (str(item.get("end") or ""), str(item.get("filed") or "")))
        if cleaned:
            summaries.append(
                {
                    "fact": fact_name,
                    "label": fact.get("label") or fact_name,
                    "description": fact.get("description", "")[:500],
                    "latest": cleaned[-limit:],
                }
            )
    return summaries


def read_companyfacts(cik: str, timeout: int = 12, limit: int = 4) -> dict[str, Any]:
    normalized = normalize_cik(cik)
    url = COMPANYFACTS_URL.format(cik=quote(normalized))
    try:
        payload = fetch_json(url, timeout=timeout)
        facts = summarize_companyfacts(payload, limit=limit)
        return {
            "access_status": "ok" if facts else "partial",
            "provider": "sec_companyfacts",
            "url": url,
            "cik": normalized,
            "entity_name": payload.get("entityName"),
            "facts": facts,
            "error": "" if facts else "No selected us-gaap facts were found.",
        }
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        return {
            "access_status": "auth_required" if getattr(exc, "code", None) in {401, 403} else "blocked",
            "provider": "sec_companyfacts",
            "url": url,
            "cik": normalized,
            "entity_name": "",
            "facts": [],
            "error": str(exc),
        }


def companyfacts_to_source(result: dict[str, Any]) -> dict[str, Any]:
    facts = []
    claims = []
    for fact in result.get("facts", [])[:8]:
        latest = fact.get("latest", [])[-1:] or []
        if latest:
            item = latest[0]
            facts.append(f"{fact.get('fact')}={item.get('val')} {item.get('unit')} end={item.get('end')}")
            claims.append(f"{fact.get('label')}: latest selected filing value is {item}.")
    return {
        "type": "financials",
        "name": f"SEC Companyfacts: {result.get('entity_name') or result.get('cik')}",
        "url": result.get("url", ""),
        "access_status": result.get("access_status", "blocked"),
        "retrieval_method": "sec_companyfacts_public",
        "claims": claims,
        "numeric_facts": facts,
        "caveats": ["SEC companyfacts public endpoint; no API key used."],
        "sec": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    lookup = subparsers.add_parser("lookup")
    lookup.add_argument("query")
    lookup.add_argument("--limit", type=int, default=10)
    lookup.add_argument("--timeout", type=int, default=12)
    facts = subparsers.add_parser("facts")
    facts.add_argument("cik")
    facts.add_argument("--limit", type=int, default=4)
    facts.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args(argv)

    if args.command == "lookup":
        payload = lookup_company(args.query, args.limit, args.timeout)
    else:
        payload = read_companyfacts(args.cik, args.timeout, args.limit)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
