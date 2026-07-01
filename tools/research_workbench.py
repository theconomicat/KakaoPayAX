#!/usr/bin/env python3
"""Production-oriented public-source research workflow.

This combines live public URL reads with structured fixture-backed financial and
market context. It requires no API keys.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from collectors.byul_public import fetch_byul_bundle  # noqa: E402
from collectors.dart_public import build_dart_public_bundle  # noqa: E402
from collectors.kind_public import build_kind_public_bundle  # noqa: E402
from build_source_packet import build_packet  # noqa: E402
from filing_parser import parse_filing_target, to_source as filing_to_source  # noqa: E402
from public_page_reader import read_public_page  # noqa: E402


def classify_source(url: str, title: str) -> str:
    haystack = f"{url} {title}".lower()
    if any(token in haystack for token in ["opendart", "dart.fss", "kind.krx", "disclosure"]):
        return "disclosure"
    if any(token in haystack for token in ["research", "리서치", "industry", "quint"]):
        return "analyst_reference"
    if any(token in haystack for token in ["management", "routine", "report", "보고서"]):
        return "financials"
    if any(token in haystack for token in ["news", "뉴스", "press"]):
        return "news"
    return "unknown"


def result_to_source(result: dict[str, Any], source_type: str | None = None) -> dict[str, Any]:
    excerpt = result.get("excerpt", "")
    claims = []
    if excerpt:
        claims.append(excerpt[:700])
    caveats = []
    if result.get("error"):
        caveats.append(result["error"])
    if result.get("access_status") == "partial":
        caveats.append("Only partial text or metadata was available.")
    return {
        "type": source_type or classify_source(result.get("final_url", ""), result.get("title", "")),
        "name": result.get("title") or result.get("final_url") or result.get("target", "Untitled source"),
        "url": result.get("final_url") or result.get("target", ""),
        "access_status": result.get("access_status", "blocked"),
        "retrieval_method": result.get("retrieval_method", "public_page_reader"),
        "claims": claims,
        "numeric_facts": [],
        "caveats": caveats,
    }


def load_base_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_live_packet(config: dict[str, Any], fixture_path: Path) -> dict[str, Any]:
    packet = load_base_fixture(fixture_path)
    packet["mode"] = "public_url_live_plus_fixture_context"
    packet["company"].update(config.get("company", {}))
    packet["request"].update(config.get("request", {}))
    live_sources = []
    for item in config.get("urls", []):
        if isinstance(item, str):
            url = item
            source_type = None
        else:
            url = item["url"]
            source_type = item.get("type")
        result = read_public_page(url)
        live_sources.append(result_to_source(result, source_type))
    if config.get("include_fixture_sources", False):
        packet["sources"] = live_sources + packet.get("sources", [])
    else:
        packet["sources"] = live_sources + config.get("extra_sources", [])

    filing_sources = []
    for item in config.get("filing_urls", []):
        if isinstance(item, str):
            target = item
            source_type = "disclosure"
        else:
            target = item["url"]
            source_type = item.get("type", "disclosure")
        result = parse_filing_target(
            target,
            timeout=int(config.get("filing_timeout", 12)),
            max_tables=int(config.get("filing_max_tables", 8)),
            max_rows=int(config.get("filing_max_rows", 20)),
        )
        filing_sources.append(filing_to_source(result, source_type))

    packet["sources"].extend(filing_sources)

    if config.get("dart_public"):
        dart_bundle = build_dart_public_bundle(config["dart_public"], timeout=int(config.get("filing_timeout", 12)))
        packet["sources"].extend(dart_bundle.get("sources", []))
        packet.setdefault("market_intelligence", {})["dart_public"] = {
            "request": dart_bundle.get("request", {}),
            "access_status": dart_bundle.get("access_status"),
            "reports": dart_bundle.get("reports", []),
            "error": dart_bundle.get("error", ""),
        }

    if config.get("kind_public"):
        kind_bundle = build_kind_public_bundle(config["kind_public"], timeout=int(config.get("filing_timeout", 12)))
        packet["sources"].extend(kind_bundle.get("sources", []))
        packet.setdefault("market_intelligence", {})["kind_public"] = {
            "request": kind_bundle.get("request", {}),
            "access_status": kind_bundle.get("access_status"),
            "company_resolution": kind_bundle.get("company_resolution"),
            "disclosures": kind_bundle.get("disclosures", []),
            "error": kind_bundle.get("error", ""),
        }

    if config.get("byul"):
        byul_bundle = fetch_byul_bundle(config["byul"], timeout=int(config.get("byul_timeout", 12)))
        packet["sources"].extend(byul_bundle.get("sources", []))
        packet.setdefault("market_intelligence", {}).update(byul_bundle.get("market_intelligence", {}))

    if "financials" in config:
        packet["financials"] = config["financials"]
    if "market_data" in config:
        packet["market_data"] = config["market_data"]
    packet["follow_up_questions"] = config.get("follow_up_questions", packet.get("follow_up_questions", []))
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="JSON config with company/request/urls")
    parser.add_argument("--fixture", default="examples/sample_raw_sources.json")
    parser.add_argument("--raw-output", required=True, help="Write merged source JSON")
    parser.add_argument("--packet-output", required=True, help="Write Markdown packet")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    fixture_path = Path(args.fixture)
    raw_output = Path(args.raw_output)
    packet_output = Path(args.packet_output)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    merged = build_live_packet(config, fixture_path)
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    packet_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    packet_output.write_text(build_packet(merged), encoding="utf-8")
    print(f"Wrote {raw_output}")
    print(f"Wrote {packet_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
