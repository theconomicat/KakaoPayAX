#!/usr/bin/env python3
"""Build a Research Source Packet and optional draft memo from structured sources."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from financial_snapshot import summarize_financials  # noqa: E402
from technical_indicators import summarize_prices  # noqa: E402


GUARDRAIL_NOTICE = (
    "This material is a research workflow draft based on public or sample sources. "
    "It is not investment advice, a recommendation, or a target price."
)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"


def _fmt_num(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _md_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def _source_table(sources: list[dict[str, Any]]) -> str:
    lines = [
        "| Type | Source | URL | Access | Method | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for item in sources:
        lines.append(
            "| {type} | {name} | {url} | {status} | {method} | {notes} |".format(
                type=_md_cell(item.get("type", "unknown")),
                name=_md_cell(item.get("name", "")),
                url=_md_cell(item.get("url", "fixture")),
                status=_md_cell(item.get("access_status", "fixture")),
                method=_md_cell(item.get("retrieval_method", "fixture")),
                notes=_md_cell("; ".join(item.get("caveats", [])) or "-"),
            )
        )
    return "\n".join(lines)


def _claims_section(title: str, sources: list[dict[str, Any]], source_type: str) -> str:
    selected = [item for item in sources if item.get("type") == source_type]
    if not selected:
        return f"## {title}\n\nNo {source_type} sources were supplied.\n"
    blocks = [f"## {title}"]
    for index, item in enumerate(selected, 1):
        blocks.append(f"\n### {index}. {item.get('name', 'Untitled source')}")
        blocks.append(f"- URL: {item.get('url', 'fixture')}")
        blocks.append(f"- Access status: {item.get('access_status', 'fixture')}")
        claims = item.get("claims", [])
        if claims:
            blocks.append("- Extracted claims:")
            for claim in claims:
                blocks.append(f"  - {claim}")
        facts = item.get("numeric_facts", [])
        if facts:
            blocks.append("- Numeric facts:")
            for fact in facts:
                blocks.append(f"  - {fact}")
        caveats = item.get("caveats", [])
        if caveats:
            blocks.append("- Caveats:")
            for caveat in caveats:
                blocks.append(f"  - {caveat}")
    blocks.append("")
    return "\n".join(blocks)


def _evidence_quality_section(sources: list[dict[str, Any]]) -> str:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for source in sources:
        source_type = str(source.get("type", "unknown"))
        status = str(source.get("access_status", "unknown"))
        by_type[source_type] = by_type.get(source_type, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
    lines = ["## Evidence Quality Checklist"]
    lines.append(f"- Sources captured: {len(sources)}")
    lines.append("- Source type mix: " + (", ".join(f"{key}={value}" for key, value in sorted(by_type.items())) or "n/a"))
    lines.append("- Access status mix: " + (", ".join(f"{key}={value}" for key, value in sorted(by_status.items())) or "n/a"))
    if any(source.get("type") in {"disclosure", "financials"} for source in sources):
        lines.append("- Primary evidence present: disclosure or financial source exists.")
    else:
        lines.append("- Primary evidence gap: no disclosure or financial source is present.")
    if any(source.get("retrieval_method") == "byul_api" for source in sources):
        lines.append("- Market intelligence present: Byul public API source exists.")
    if any(source.get("financial_statement_rows") for source in sources):
        lines.append("- Filing table extraction present: financial statement rows were extracted.")
    lines.append("- Analyst must review blocked, partial, or fixture-only evidence before publication.")
    lines.append("")
    return "\n".join(lines)


def _filing_tables_section(sources: list[dict[str, Any]]) -> str:
    filing_sources = [source for source in sources if source.get("tables") or source.get("financial_statement_rows")]
    if not filing_sources:
        return "## Filing Table Extraction\n\nNo filing tables were extracted.\n"
    lines = ["## Filing Table Extraction"]
    for source in filing_sources:
        lines.append(f"\n### {source.get('name', 'Filing source')}")
        lines.append(f"- URL: {source.get('url', 'n/a')}")
        lines.append(f"- Retrieval: {source.get('retrieval_method', 'n/a')} / {source.get('access_status', 'n/a')}")
        tables = source.get("tables", [])
        lines.append(f"- Extracted tables: {len(tables)}")
        for table in tables[:3]:
            caption = table.get("caption") or f"table {table.get('index', '?')}"
            lines.append(
                "- {caption}: rows={rows}, columns={columns}, numeric_cells={numeric}".format(
                    caption=caption,
                    rows=table.get("row_count", 0),
                    columns=table.get("column_count", 0),
                    numeric=table.get("numeric_cell_count", 0),
                )
            )
            for row in table.get("financial_rows", [])[:5]:
                values = ", ".join(str(value) for value in row.get("values", [])[:4])
                lines.append(f"  - {row.get('line_item', 'line item')}: {values}")
    lines.append("")
    return "\n".join(lines)


def _byul_market_intelligence_section(data: dict[str, Any]) -> str:
    byul = data.get("market_intelligence", {}).get("byul")
    if not byul:
        return "## Byul Market Intelligence\n\nNo Byul market intelligence was supplied.\n"
    lines = ["## Byul Market Intelligence"]

    news = byul.get("news", {})
    news_items = news.get("items", []) if isinstance(news, dict) else []
    if news_items:
        lines.append("\n### Latest / Filtered News")
        for item in news_items[:5]:
            title = item.get("title") or item.get("originalTitle") or "Untitled news"
            score = item.get("importanceScore", "n/a")
            symbols = ", ".join(str(symbol) for symbol in item.get("symbols", [])[:6]) or "n/a"
            lines.append(f"- {title} | importance={score} | symbols={symbols}")

    calendar = byul.get("calendar", {})
    calendar_items = calendar.get("items", []) if isinstance(calendar, dict) else []
    if calendar_items:
        lines.append("\n### Economic Calendar")
        for item in calendar_items[:6]:
            name = item.get("event_name") or item.get("kevent") or item.get("event") or "Calendar event"
            lines.append(
                "- {name} | time={time} | importance={importance} | actual={actual} | forecast={forecast}".format(
                    name=name,
                    time=item.get("event_time") or item.get("time") or "n/a",
                    importance=item.get("importance") or item.get("importance_numeric") or "n/a",
                    actual=item.get("actual"),
                    forecast=item.get("forecast"),
                )
            )

    earnings = byul.get("earnings", {})
    earnings_items = earnings.get("items", []) if isinstance(earnings, dict) else []
    earnings_news = earnings.get("news_items", []) if isinstance(earnings, dict) else []
    if earnings_items or earnings_news:
        lines.append("\n### Earnings Watch")
        for item in earnings_items[:5]:
            name = item.get("event_name") or item.get("kevent") or item.get("event") or "Earnings event"
            lines.append(f"- Calendar: {name} | {item.get('event_time') or item.get('time') or 'n/a'}")
        for item in earnings_news[:5]:
            title = item.get("title") or item.get("originalTitle") or "Earnings news"
            lines.append(f"- News: {title} | importance={item.get('importanceScore', 'n/a')}")

    indices = byul.get("indices", {})
    index_results = indices.get("results", {}) if isinstance(indices, dict) else {}
    if index_results:
        lines.append("\n### Sentiment / Volatility Indices")
        for index_id, result in index_results.items():
            payload = result.get("data", {}) if isinstance(result, dict) else {}
            inner = payload.get("data", payload) if isinstance(payload, dict) else {}
            if not isinstance(inner, dict):
                inner = {}
            value = inner.get("value", inner.get("quote", "n/a"))
            label = inner.get("value_classification") or inner.get("volatility_level") or inner.get("market_sentiment") or "n/a"
            lines.append(f"- {index_id}: value={value}, label={label}, access={result.get('access_status', 'n/a')}")

    lines.append("")
    return "\n".join(lines)


def _investor_lenses(data: dict[str, Any], financial_summary: dict[str, Any]) -> str:
    company = data.get("company", {}).get("name", "the company")
    lenses = [
        (
            "Buffett-style Value Lens",
            [
                "Check whether cash generation, balance-sheet strength, and return durability are supported by sources.",
                f"Current operating margin from supplied data: {_fmt_pct((financial_summary.get('operating_margin') or 0) * 100 if financial_summary.get('operating_margin') is not None else None)}.",
                "Do not infer intrinsic value without a valuation model and sourced assumptions.",
            ],
        ),
        (
            "Fisher-style Quality Growth Lens",
            [
                f"Review whether {company}'s growth narrative is supported by product, customer, and capacity evidence.",
                "Look for R&D, management commentary, long-term demand, and competitive position sources.",
            ],
        ),
        (
            "Lynch-style Understandability Lens",
            [
                "Summarize the business story in plain language and identify what an individual investor can verify.",
                "Separate observable demand signals from market hype.",
            ],
        ),
        (
            "Risk-first Lens",
            [
                "Check cycle, regulation, FX, rates, customer concentration, supply chain, and accounting-quality risks.",
                "List missing sources before forming a high-confidence view.",
            ],
        ),
    ]
    lines = ["## Investor Lens Notes"]
    for name, bullets in lenses:
        lines.append(f"\n### {name}")
        for bullet in bullets:
            lines.append(f"- {bullet}")
    lines.append("")
    return "\n".join(lines)


def build_packet(data: dict[str, Any]) -> str:
    company = data.get("company", {})
    request = data.get("request", {})
    sources = data.get("sources", [])
    financial_summary = summarize_financials(data.get("financials", {}))
    technical_summary = summarize_prices(data.get("market_data", {}).get("prices", []))

    lines = [
        f"# Research Source Packet: {company.get('name', 'Unknown Company')}",
        "",
        "## Request Interpretation",
        f"- Target: {company.get('name', 'unknown')} ({company.get('ticker', 'n/a')})",
        f"- Market: {company.get('market', 'n/a')}",
        f"- Topic: {request.get('topic', 'n/a')}",
        f"- Period: {request.get('period', 'n/a')}",
        f"- Mode: {data.get('mode', 'demo')}",
        "",
        "## Source Map",
        _source_table(sources),
        "",
        _evidence_quality_section(sources),
        _claims_section("News and Market Narrative Sources", sources, "news"),
        _claims_section("Disclosure and Filing Sources", sources, "disclosure"),
        _filing_tables_section(sources),
        _byul_market_intelligence_section(data),
        "## Financial Snapshot",
        f"- Period: {financial_summary.get('period', 'n/a')}",
        f"- Source: {financial_summary.get('source', 'unknown')}",
        f"- Revenue change: {_fmt_pct(financial_summary.get('revenue_change_pct'))}",
        f"- Operating profit change: {_fmt_pct(financial_summary.get('operating_profit_change_pct'))}",
        f"- Net income change: {_fmt_pct(financial_summary.get('net_income_change_pct'))}",
        f"- Operating margin: {_fmt_pct((financial_summary.get('operating_margin') or 0) * 100 if financial_summary.get('operating_margin') is not None else None)}",
        f"- Net margin: {_fmt_pct((financial_summary.get('net_margin') or 0) * 100 if financial_summary.get('net_margin') is not None else None)}",
        f"- Debt to equity: {_fmt_num(financial_summary.get('debt_to_equity'))}",
        "- Notes:",
    ]
    for note in financial_summary.get("notes", []):
        lines.append(f"  - {note}")

    lines.extend(
        [
            "",
            "## Market and Technical Signals",
            f"- Observations: {technical_summary.get('observations', 0)}",
            f"- Latest close: {_fmt_num(technical_summary.get('latest_close'))}",
            f"- SMA 5: {_fmt_num(technical_summary.get('sma_5'))}",
            f"- SMA 20: {_fmt_num(technical_summary.get('sma_20'))}",
            f"- RSI 14: {_fmt_num(technical_summary.get('rsi_14'))}",
            f"- MACD histogram: {_fmt_num(technical_summary.get('macd', {}).get('histogram'))}",
            "- Interpretation:",
        ]
    )
    for item in technical_summary.get("interpretation", []):
        lines.append(f"  - {item}")

    lines.extend(["", _investor_lenses(data, financial_summary)])
    lines.extend(
        [
            "## Draft Analyst Memo",
            f"{company.get('name', 'The company')} research preparation should focus on source verification before conclusion writing. The supplied packet shows the analyst where narrative claims, filing evidence, financial snapshots, and market signals align or remain incomplete.",
            "",
            "### What Changed",
            "- Use the news and disclosure sections above as the first-pass event map.",
            "- Use financial and technical sections as context, not as a recommendation engine.",
            "",
            "### Analyst Follow-up",
        ]
    )
    followups = data.get("follow_up_questions", [])
    if not followups:
        followups = [
            "Which claims require primary-source confirmation?",
            "Which financial metrics need a live filing refresh?",
            "Which competitor or industry data should be added next?",
        ]
    for question in followups:
        lines.append(f"- {question}")

    gaps = []
    for source in sources:
        if source.get("access_status") not in {"ok", "fixture"}:
            gaps.append(f"{source.get('name', 'Unknown source')}: {source.get('access_status')}")
    if not gaps:
        gaps.append("No access failures in the supplied sources.")

    lines.extend(["", "## Conflicts, Gaps, and Follow-up Questions"])
    for gap in gaps:
        lines.append(f"- {gap}")
    lines.extend(["", "## Guardrail Notice", GUARDRAIL_NOTICE, ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Structured source JSON")
    parser.add_argument("--output", required=True, help="Markdown output path")
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    packet = build_packet(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(packet, encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
