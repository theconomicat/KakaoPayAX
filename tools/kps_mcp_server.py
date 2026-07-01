#!/usr/bin/env python3
"""Minimal no-key MCP server for KPS Analyst Workbench public tools.

The server uses JSON-RPC over stdio and wraps deterministic local tools. It does
not require API keys, credentials, or a network service running in the
background.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from fred_public_client import read_fred_series  # noqa: E402
from market_data_reader import read_market_data  # noqa: E402
from openbb_public_sources import search_providers  # noqa: E402
from public_page_reader import read_public_page  # noqa: E402
from sec_edgar_client import lookup_company, read_companyfacts  # noqa: E402
from source_catalog import load_catalog, search_catalog  # noqa: E402


TOOLS = [
    {
        "name": "openbb_public_sources",
        "description": "Search OpenBB-inspired no-key public provider candidates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "category": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
    },
    {
        "name": "source_catalog_search",
        "description": "Search The Econmicat public finance source catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "category": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
    },
    {
        "name": "market_data",
        "description": "Fetch no-key Yahoo chart OHLCV data for a ticker.",
        "inputSchema": {
            "type": "object",
            "required": ["ticker"],
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string"},
                "interval": {"type": "string"},
            },
        },
    },
    {
        "name": "fred_series",
        "description": "Fetch a no-key FRED graph CSV macro series.",
        "inputSchema": {
            "type": "object",
            "required": ["series_id"],
            "properties": {
                "series_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 365},
            },
        },
    },
    {
        "name": "sec_lookup",
        "description": "Find SEC CIK candidates by ticker or company name.",
        "inputSchema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
    },
    {
        "name": "sec_companyfacts",
        "description": "Fetch selected SEC companyfacts by CIK.",
        "inputSchema": {
            "type": "object",
            "required": ["cik"],
            "properties": {
                "cik": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 12},
            },
        },
    },
    {
        "name": "public_page_read",
        "description": "Read a public page with traceable access status.",
        "inputSchema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string"},
                "browser": {"type": "boolean"},
                "max_attempts": {"type": "integer", "minimum": 1, "maximum": 12},
            },
        },
    },
]


def _int_arg(args: dict[str, Any], key: str, default: int, minimum: int = 1, maximum: int = 1000) -> int:
    try:
        value = int(args.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "openbb_public_sources":
        return {
            "providers": search_providers(
                query=str(args.get("query", "")),
                category=str(args.get("category", "")),
                limit=_int_arg(args, "limit", 10, 1, 20),
            )
        }
    if name == "source_catalog_search":
        items = load_catalog()
        selected = search_catalog(
            items,
            query=str(args.get("query", "")),
            category=str(args.get("category", "")),
            limit=_int_arg(args, "limit", 10, 1, 20),
        )
        return {"items": [item.__dict__ for item in selected]}
    if name == "market_data":
        return read_market_data(
            ticker=str(args["ticker"]),
            period=str(args.get("period", "1mo")),
            interval=str(args.get("interval", "1d")),
            provider="yahoo",
        )
    if name == "fred_series":
        return read_fred_series(str(args["series_id"]), limit=_int_arg(args, "limit", 90, 1, 365))
    if name == "sec_lookup":
        return lookup_company(str(args["query"]), limit=_int_arg(args, "limit", 10, 1, 20))
    if name == "sec_companyfacts":
        return read_companyfacts(str(args["cik"]), limit=_int_arg(args, "limit", 4, 1, 12))
    if name == "public_page_read":
        return read_public_page(
            str(args["url"]),
            use_browser=bool(args.get("browser", False)),
            max_attempts=_int_arg(args, "max_attempts", 6, 1, 12),
        )
    raise ValueError(f"unknown tool: {name}")


def result_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(payload: dict[str, Any]) -> dict[str, Any] | None:
    method = payload.get("method")
    request_id = payload.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return result_response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "kps-public-finance", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return result_response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = payload.get("params") or {}
        name = str(params.get("name", ""))
        args = params.get("arguments") or {}
        try:
            output = call_tool(name, args)
        except Exception as exc:  # noqa: BLE001 - MCP tools should return structured errors
            return error_response(request_id, -32000, str(exc))
        return result_response(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(output, ensure_ascii=False, indent=2),
                    }
                ],
                "isError": False,
            },
        )
    return error_response(request_id, -32601, f"method not found: {method}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            response = handle_request(payload)
        except json.JSONDecodeError as exc:
            response = error_response(None, -32700, str(exc))
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
