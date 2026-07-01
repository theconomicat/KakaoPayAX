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


def run_json(cmd: list[str]) -> dict:
    print("+", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    print(completed.stdout)
    return json.loads(completed.stdout)


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
    openbb_sources = run_json(
        [
            sys.executable,
            "tools/openbb_public_sources.py",
            "--query",
            "SEC FRED",
            "--limit",
            "5",
        ]
    )
    provider_names = {provider["name"] for provider in openbb_sources.get("providers", [])}
    if "SEC EDGAR companyfacts" not in provider_names or "FRED graph CSV" not in provider_names:
        raise SystemExit("OpenBB-inspired provider catalog did not return SEC and FRED candidates")
    run([sys.executable, "tools/market_data_reader.py", "000660.KS", "--period", "1mo"])
    fred = run_json([sys.executable, "tools/fred_public_client.py", "DGS10", "--limit", "2"])
    if fred.get("access_status") != "ok" or not fred.get("latest"):
        raise SystemExit("FRED public CSV route failed")
    sec_lookup = run_json([sys.executable, "tools/sec_edgar_client.py", "lookup", "AAPL", "--limit", "2"])
    if sec_lookup.get("access_status") != "ok" or not sec_lookup.get("matches"):
        raise SystemExit("SEC ticker lookup failed")
    sec_facts = run_json([sys.executable, "tools/sec_edgar_client.py", "facts", "0000320193", "--limit", "1"])
    if sec_facts.get("access_status") != "ok" or not sec_facts.get("facts"):
        raise SystemExit("SEC companyfacts failed")
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
    log_manifest = run_json([sys.executable, "scripts/check_logs.py", "logs"])
    if log_manifest.get("status") != "ok":
        raise SystemExit("log validation failed")
    mcp = subprocess.run(
        [sys.executable, "tools/kps_mcp_server.py"],
        cwd=ROOT,
        input='{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n',
        capture_output=True,
        text=True,
        check=True,
    )
    mcp_response = json.loads(mcp.stdout.splitlines()[0])
    tool_names = {tool["name"] for tool in mcp_response["result"]["tools"]}
    for tool_name in {"openbb_public_sources", "fred_series", "sec_companyfacts"}:
        if tool_name not in tool_names:
            raise SystemExit(f"MCP tool missing: {tool_name}")
    print("smoke check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
