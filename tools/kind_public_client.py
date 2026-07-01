#!/usr/bin/env python3
"""CLI for API-key-free KIND disclosure search and original HTML extraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from collectors.kind_public import (  # noqa: E402
    build_kind_public_bundle,
    dump_json,
    fetch_disclosure_document,
    resolve_company,
    search_company_disclosures,
    search_today_disclosures,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=12)
    sub = parser.add_subparsers(dest="command", required=True)

    company = sub.add_parser("company")
    company.add_argument("--query", required=True)

    search = sub.add_parser("search")
    search.add_argument("--company", required=True)
    search.add_argument("--start-date", required=True)
    search.add_argument("--end-date", required=True)
    search.add_argument("--report-name")
    search.add_argument("--limit", type=int, default=5)

    today = sub.add_parser("today")
    today.add_argument("--limit", type=int, default=10)

    document = sub.add_parser("document")
    document.add_argument("--acpt-no", required=True)
    document.add_argument("--doc-no", default="")
    document.add_argument("--max-tables", type=int, default=12)
    document.add_argument("--max-rows", type=int, default=20)

    bundle = sub.add_parser("bundle")
    bundle.add_argument("--config")
    bundle.add_argument("--company")
    bundle.add_argument("--start-date")
    bundle.add_argument("--end-date")
    bundle.add_argument("--report-name")
    bundle.add_argument("--limit", type=int, default=3)
    bundle.add_argument("--max-tables", type=int, default=12)
    bundle.add_argument("--max-rows", type=int, default=20)
    bundle.add_argument("--no-documents", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "company":
        payload = resolve_company(args.query, args.timeout)
    elif args.command == "search":
        payload = search_company_disclosures(
            args.company,
            args.start_date,
            args.end_date,
            args.report_name,
            args.limit,
            args.timeout,
        )
    elif args.command == "today":
        payload = search_today_disclosures(args.limit, args.timeout)
    elif args.command == "document":
        payload = fetch_disclosure_document(args.acpt_no, args.doc_no, args.timeout, args.max_tables, args.max_rows)
    else:
        if args.config:
            with open(args.config, encoding="utf-8") as handle:
                config = json.load(handle)
        else:
            if not (args.company and args.start_date and args.end_date):
                parser.error("bundle requires --config or --company, --start-date, and --end-date")
            config = {
                "company": args.company,
                "start_date": args.start_date,
                "end_date": args.end_date,
                "report_name": args.report_name,
                "limit": args.limit,
                "max_tables": args.max_tables,
                "max_rows": args.max_rows,
                "fetch_documents": not args.no_documents,
            }
        payload = build_kind_public_bundle(config, timeout=args.timeout)
    dump_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
