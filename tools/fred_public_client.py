#!/usr/bin/env python3
"""No-key FRED graph CSV reader for public macro series."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import io
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_SERIES = {
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "DGS2": "2-Year Treasury Constant Maturity Rate",
    "T10Y2Y": "10-Year Treasury Minus 2-Year Treasury",
    "FEDFUNDS": "Effective Federal Funds Rate",
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
    "UNRATE": "Unemployment Rate",
    "DCOILWTICO": "WTI Crude Oil Price",
}


def parse_fred_csv(text: str, series_id: str, limit: int = 90) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        raw_date = row.get("observation_date") or row.get("DATE") or row.get("date")
        raw_value = row.get(series_id) or row.get("value") or row.get("VALUE")
        if not raw_date or raw_value in {None, "", "."}:
            continue
        try:
            parsed_date = date.fromisoformat(raw_date)
            value = float(raw_value)
        except ValueError:
            continue
        rows.append({"date": parsed_date.isoformat(), "value": value})
    rows = rows[-limit:]
    return {
        "series_id": series_id,
        "observations": rows,
        "latest": rows[-1] if rows else None,
        "observation_count": len(rows),
    }


def read_fred_series(series_id: str, limit: int = 90, timeout: int = 12) -> dict[str, Any]:
    normalized = series_id.upper().strip()
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={quote(normalized)}"
    request = Request(
        url,
        headers={
            "User-Agent": "KPSAnalystWorkbench/0.4 (no-key FRED public CSV reader)",
            "Accept": "text/csv,*/*",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public FRED CSV endpoint
            text = response.read(2_000_000).decode("utf-8", errors="replace")
            parsed = parse_fred_csv(text, normalized, limit=limit)
            return {
                "access_status": "ok" if parsed["observations"] else "partial",
                "provider": "fred_public_csv",
                "name": DEFAULT_SERIES.get(normalized, normalized),
                "url": response.url,
                "status_code": response.status,
                **parsed,
                "error": "" if parsed["observations"] else "No numeric observations were returned.",
            }
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        fallback = read_fred_series_with_curl_cffi(url, normalized, limit=limit, timeout=timeout)
        if fallback.get("access_status") == "ok":
            fallback["fallback_after"] = f"urllib: {exc}"
            return fallback
        return {
            "access_status": "blocked",
            "provider": "fred_public_csv",
            "name": DEFAULT_SERIES.get(normalized, normalized),
            "url": url,
            "status_code": getattr(exc, "code", None),
            "series_id": normalized,
            "observations": [],
            "latest": None,
            "observation_count": 0,
            "error": str(exc),
        }


def read_fred_series_with_curl_cffi(url: str, series_id: str, limit: int = 90, timeout: int = 12) -> dict[str, Any]:
    try:
        from curl_cffi import requests  # type: ignore
    except Exception as exc:  # noqa: BLE001 - optional dependency
        return {
            "access_status": "blocked",
            "provider": "fred_public_csv_curl_cffi",
            "url": url,
            "series_id": series_id,
            "observations": [],
            "latest": None,
            "observation_count": 0,
            "error": f"optional dependency unavailable: {exc}",
        }
    try:
        response = requests.get(
            url,
            impersonate="chrome",
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 KPSAnalystWorkbench/0.4"},
        )
        response.raise_for_status()
        parsed = parse_fred_csv(response.text, series_id, limit=limit)
        return {
            "access_status": "ok" if parsed["observations"] else "partial",
            "provider": "fred_public_csv_curl_cffi",
            "name": DEFAULT_SERIES.get(series_id, series_id),
            "url": url,
            "status_code": response.status_code,
            **parsed,
            "error": "" if parsed["observations"] else "No numeric observations were returned.",
        }
    except Exception as exc:  # noqa: BLE001 - optional dependency fallback
        return {
            "access_status": "blocked",
            "provider": "fred_public_csv_curl_cffi",
            "url": url,
            "series_id": series_id,
            "observations": [],
            "latest": None,
            "observation_count": 0,
            "error": str(exc),
        }


def series_to_source(result: dict[str, Any]) -> dict[str, Any]:
    latest = result.get("latest") or {}
    facts = []
    if latest:
        facts.append(f"latest={latest.get('value')}")
        facts.append(f"latest_date={latest.get('date')}")
    facts.append(f"observations={result.get('observation_count', 0)}")
    return {
        "type": "macro_series",
        "name": f"FRED: {result.get('name') or result.get('series_id')}",
        "url": result.get("url", ""),
        "access_status": result.get("access_status", "blocked"),
        "retrieval_method": "fred_public_csv",
        "claims": [f"{result.get('series_id')} latest value: {latest}"] if latest else [],
        "numeric_facts": facts,
        "caveats": ["FRED graph CSV public route; no API key used."],
        "fred": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("series_id")
    parser.add_argument("--limit", type=int, default=90)
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args(argv)
    json.dump(read_fred_series(args.series_id, args.limit, args.timeout), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
