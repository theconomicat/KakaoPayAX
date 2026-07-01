#!/usr/bin/env python3
"""Run all production smoke checks for KPS Analyst Workbench."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    run(
        [
            sys.executable,
            "tools/build_source_packet.py",
            "--input",
            "examples/sample_raw_sources.json",
            "--output",
            "outputs/research_source_packet.md",
        ]
    )
    run([sys.executable, "tools/technical_indicators.py", "--input", "examples/sample_prices.csv"])
    run(
        [
            sys.executable,
            "tools/public_page_reader.py",
            "README.md",
        ]
    )
    run(
        [
            sys.executable,
            "tools/source_fetcher.py",
            "README.md",
        ]
    )
    run(
        [
            sys.executable,
            "tools/source_catalog.py",
            "--query",
            "Yahoo Finance",
            "--limit",
            "3",
        ]
    )
    run([sys.executable, "tools/market_data_reader.py", "000660.KS", "--period", "1mo"])
    run(
        [
            sys.executable,
            "tools/filing_parser.py",
            "--target",
            "examples/sample_dart_filing.html",
        ]
    )
    run(
        [
            sys.executable,
            "tools/dart_public_client.py",
            "search",
            "--company",
            "삼성전자",
            "--start-date",
            "20250101",
            "--end-date",
            "20260701",
            "--report-name",
            "사업보고서",
            "--limit",
            "1",
        ]
    )
    run(
        [
            sys.executable,
            "tools/dart_public_client.py",
            "xbrl",
            "--rcp-no",
            "20260310002820",
            "--max-roles",
            "2",
        ]
    )
    run(
        [
            sys.executable,
            "tools/kind_public_client.py",
            "search",
            "--company",
            "삼성전자",
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-07-01",
            "--report-name",
            "사업보고서",
            "--limit",
            "1",
        ]
    )
    run(
        [
            sys.executable,
            "tools/byul_client.py",
            "news",
            "--limit",
            "2",
            "--min-importance",
            "3",
        ]
    )
    run(
        [
            sys.executable,
            "tools/byul_client.py",
            "indices",
            "--indexes",
            "fear-greed",
            "vix",
            "kospi-volatility",
        ]
    )
    run(
        [
            sys.executable,
            "tools/research_workbench.py",
            "--config",
            "examples/live_public_sources.json",
            "--raw-output",
            "outputs/live_public_sources_packet.json",
            "--packet-output",
            "outputs/live_public_sources_packet.md",
        ]
    )
    packet = (ROOT / "outputs" / "live_public_sources_packet.md").read_text(encoding="utf-8")
    required = [
        "Research Source Packet",
        "Source Map",
        "Evidence Quality Checklist",
        "Filing Table Extraction",
        "Byul Market Intelligence",
        "Draft Analyst Memo",
        "Guardrail Notice",
    ]
    missing = [item for item in required if item not in packet]
    if missing:
        raise SystemExit(f"missing packet sections: {missing}")
    raw = json.loads((ROOT / "outputs" / "live_public_sources_packet.json").read_text(encoding="utf-8"))
    if not raw.get("sources"):
        raise SystemExit("no sources captured")
    if not any(source.get("financial_statement_rows") for source in raw["sources"]):
        raise SystemExit("no filing table rows captured")
    if not any(source.get("retrieval_method") == "opendart_xbrl_viewer" for source in raw["sources"]):
        raise SystemExit("no OpenDART XBRL viewer sources captured")
    if not any(source.get("retrieval_method") == "kind_external_html" for source in raw["sources"]):
        raise SystemExit("no KIND original HTML sources captured")
    if not any(source.get("retrieval_method") == "byul_api" for source in raw["sources"]):
        raise SystemExit("no Byul API sources captured")
    print("smoke check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
