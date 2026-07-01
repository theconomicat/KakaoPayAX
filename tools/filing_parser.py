#!/usr/bin/env python3
"""Parse public filing pages and financial-statement tables.

This tool is intentionally conservative:
- It reads public URLs or local HTML/text files.
- It extracts visible text and HTML tables with no required dependencies.
- It does not bypass login, paywalls, CAPTCHA, or access controls.
"""
from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FINANCIAL_TERMS = [
    "매출",
    "영업수익",
    "영업이익",
    "당기순이익",
    "순이익",
    "자산",
    "부채",
    "자본",
    "현금",
    "영업활동",
    "revenue",
    "sales",
    "operating profit",
    "operating income",
    "net income",
    "assets",
    "liabilities",
    "equity",
    "cash",
    "operating cash",
]


class FilingHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_ignored = False
        self.current_tag = ""
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.tables: list[dict[str, Any]] = []

        self.table_depth = 0
        self.current_table: dict[str, Any] | None = None
        self.current_row: list[str] | None = None
        self.current_row_header_flags: list[bool] | None = None
        self.current_cell_parts: list[str] | None = None
        self.current_cell_is_header = False
        self.in_caption = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self.current_tag = tag
        if tag in {"script", "style", "noscript", "svg"}:
            self.in_ignored = True
            return
        if tag == "table":
            if self.table_depth == 0:
                self.current_table = {"caption": "", "rows": [], "header_flags": []}
            self.table_depth += 1
            return
        if self.table_depth == 1 and tag == "caption":
            self.in_caption = True
            return
        if self.table_depth == 1 and tag == "tr":
            self.current_row = []
            self.current_row_header_flags = []
            return
        if self.table_depth == 1 and tag in {"td", "th"}:
            self.current_cell_parts = []
            self.current_cell_is_header = tag == "th"

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self.in_ignored = False
            return
        if self.table_depth == 1 and tag == "caption":
            self.in_caption = False
            return
        if self.table_depth == 1 and tag in {"td", "th"} and self.current_cell_parts is not None:
            cell = normalize_text(" ".join(self.current_cell_parts), limit=500)
            if self.current_row is not None:
                self.current_row.append(cell)
            if self.current_row_header_flags is not None:
                self.current_row_header_flags.append(self.current_cell_is_header)
            self.current_cell_parts = None
            self.current_cell_is_header = False
            return
        if self.table_depth == 1 and tag == "tr":
            if self.current_table is not None and self.current_row:
                self.current_table["rows"].append(self.current_row)
                self.current_table["header_flags"].append(self.current_row_header_flags or [])
            self.current_row = None
            self.current_row_header_flags = None
            return
        if tag == "table" and self.table_depth > 0:
            self.table_depth -= 1
            if self.table_depth == 0 and self.current_table is not None:
                self.tables.append(self.current_table)
                self.current_table = None
            return
        self.current_tag = ""

    def handle_data(self, data: str) -> None:
        if self.in_ignored:
            return
        stripped = normalize_text(html.unescape(data), limit=500)
        if not stripped:
            return
        if self.current_cell_parts is not None:
            self.current_cell_parts.append(stripped)
            return
        if self.in_caption and self.current_table is not None:
            caption = " ".join([self.current_table.get("caption", ""), stripped]).strip()
            self.current_table["caption"] = normalize_text(caption, limit=300)
            return
        if self.table_depth:
            return
        if self.current_tag == "title":
            self.title_parts.append(stripped)
        elif len(stripped) > 1:
            self.text_parts.append(stripped)


def normalize_text(value: str, limit: int = 4000) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        return value[:limit].rstrip() + "..."
    return value


def parse_number(value: str) -> float | None:
    if not value:
        return None
    raw = value.strip()
    multiplier = 1.0
    if "%" in raw:
        multiplier = 0.01
    negative = raw.startswith("(") and raw.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", raw)
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        number = float(cleaned) * multiplier
    except ValueError:
        return None
    if negative and number > 0:
        number = -number
    return number


def _financial_score(row: list[str]) -> int:
    haystack = " ".join(row).lower()
    return sum(1 for term in FINANCIAL_TERMS if term.lower() in haystack)


def _clean_rows(rows: list[list[str]]) -> list[list[str]]:
    cleaned = []
    for row in rows:
        cells = [normalize_text(cell, limit=500) for cell in row]
        if any(cells):
            cleaned.append(cells)
    return cleaned


def normalize_table(table: dict[str, Any], index: int, max_rows: int) -> dict[str, Any]:
    rows = _clean_rows(table.get("rows", []))
    header_flags = table.get("header_flags", [])
    headers: list[str] = []
    body = rows
    if rows:
        first_flags = header_flags[0] if header_flags else []
        if any(first_flags) or _financial_score(rows[0]) == 0:
            headers = rows[0]
            body = rows[1:]

    financial_rows = []
    numeric_cell_count = 0
    for row in body:
        value_cells = row[1:] if len(row) > 1 else row
        numeric_values = [parse_number(cell) for cell in value_cells]
        numeric_values = [item for item in numeric_values if item is not None]
        numeric_cell_count += len(numeric_values)
        if numeric_values and _financial_score(row) > 0:
            financial_rows.append(
                {
                    "line_item": row[0] if row else "",
                    "values": row[1:] if len(row) > 1 else row,
                    "numeric_values": numeric_values,
                    "row": row,
                }
            )

    return {
        "index": index,
        "caption": table.get("caption", ""),
        "headers": headers,
        "rows": body[:max_rows],
        "row_count": len(body),
        "column_count": max((len(row) for row in rows), default=0),
        "numeric_cell_count": numeric_cell_count,
        "financial_rows": financial_rows[:max_rows],
    }


def read_target(target: str, timeout: int) -> tuple[int | None, str, str, str, str]:
    if target.startswith(("http://", "https://")):
        request = Request(
            target,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 KPSAnalystWorkbench/0.2 "
                    "(public filing parser)"
                )
            },
        )
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public URL reader
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(3_000_000)
            return response.status, raw.decode(charset, errors="replace"), response.url, "urllib", ""
    path = Path(target)
    return None, path.read_text(encoding="utf-8"), target, "local_file", ""


def parse_filing_target(target: str, timeout: int = 12, max_tables: int = 8, max_rows: int = 20) -> dict[str, Any]:
    try:
        status_code, content, final_url, method, error = read_target(target, timeout)
    except HTTPError as exc:
        return {
            "target": target,
            "final_url": target,
            "access_status": "auth_required" if exc.code in {401, 403} else "blocked",
            "status_code": exc.code,
            "retrieval_method": "urllib",
            "title": "",
            "text_excerpt": "",
            "tables": [],
            "financial_statement_rows": [],
            "error": str(exc),
        }
    except (URLError, OSError, TimeoutError, ValueError) as exc:
        return {
            "target": target,
            "final_url": target,
            "access_status": "blocked",
            "status_code": None,
            "retrieval_method": "urllib",
            "title": "",
            "text_excerpt": "",
            "tables": [],
            "financial_statement_rows": [],
            "error": str(exc),
        }

    parser = FilingHtmlParser()
    parser.feed(content)
    tables = [
        normalize_table(table, index + 1, max_rows)
        for index, table in enumerate(parser.tables[:max_tables])
    ]
    financial_rows = []
    for table in tables:
        for row in table["financial_rows"]:
            enriched = dict(row)
            enriched["table_index"] = table["index"]
            enriched["table_caption"] = table.get("caption", "")
            financial_rows.append(enriched)
    text_excerpt = normalize_text(" ".join(parser.text_parts), limit=3000)
    access_status = "ok" if text_excerpt or tables else "partial"
    return {
        "target": target,
        "final_url": final_url,
        "access_status": access_status,
        "status_code": status_code,
        "retrieval_method": method,
        "title": normalize_text(" ".join(parser.title_parts), limit=300),
        "text_excerpt": text_excerpt,
        "tables": tables,
        "financial_statement_rows": financial_rows[:max_rows],
        "error": error,
    }


def to_source(result: dict[str, Any], source_type: str = "disclosure") -> dict[str, Any]:
    claims = []
    if result.get("text_excerpt"):
        claims.append(result["text_excerpt"][:700])
    if result.get("tables"):
        claims.append(f"Extracted {len(result['tables'])} HTML/API table(s).")
    numeric_facts = []
    for row in result.get("financial_statement_rows", [])[:8]:
        numeric_facts.append(
            "{line_item}: {values}".format(
                line_item=row.get("line_item", "financial row"),
                values=", ".join(str(value) for value in row.get("values", [])[:4]),
            )
        )
    caveats = []
    if result.get("error"):
        caveats.append(result["error"])
    return {
        "type": source_type,
        "name": result.get("title") or result.get("final_url") or result.get("target", "Filing source"),
        "url": result.get("final_url") or result.get("target", ""),
        "access_status": result.get("access_status", "blocked"),
        "retrieval_method": result.get("retrieval_method", "filing_parser"),
        "claims": claims,
        "numeric_facts": numeric_facts,
        "caveats": caveats,
        "tables": result.get("tables", []),
        "financial_statement_rows": result.get("financial_statement_rows", []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Public DART/KIND/company URL or local HTML file")
    parser.add_argument("--source-type", default="disclosure")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--max-tables", type=int, default=8)
    parser.add_argument("--max-rows", type=int, default=20)
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args(argv)

    results = []
    if args.target:
        results.append(parse_filing_target(args.target, args.timeout, args.max_tables, args.max_rows))
    if not results:
        parser.error("provide --target")

    payload: dict[str, Any] = {
        "results": results,
        "sources": [to_source(result, args.source_type) for result in results],
    }
    if args.source_only:
        payload = {"sources": payload["sources"]}
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
