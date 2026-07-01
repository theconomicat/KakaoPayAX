#!/usr/bin/env python3
"""CLI for API-key-free DART report and XBRL viewer extraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from collectors.dart_public import (  # noqa: E402
    build_dart_public_bundle,
    dump_json,
    fetch_report_documents,
    fetch_xbrl_roles,
    search_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=12)
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search")
    search.add_argument("--company", required=True)
    search.add_argument("--start-date", required=True)
    search.add_argument("--end-date", required=True)
    search.add_argument("--report-name", default="사업보고서")
    search.add_argument("--limit", type=int, default=5)

    docs = sub.add_parser("documents")
    docs.add_argument("--rcp-no", required=True)
    docs.add_argument("--max-documents", type=int, default=6)

    xbrl = sub.add_parser("xbrl")
    xbrl.add_argument("--rcp-no", required=True)
    xbrl.add_argument("--max-roles", type=int, default=5)

    bundle = sub.add_parser("bundle")
    bundle.add_argument("--config")
    bundle.add_argument("--company")
    bundle.add_argument("--start-date")
    bundle.add_argument("--end-date")
    bundle.add_argument("--report-name", default="사업보고서")
    bundle.add_argument("--max-reports", type=int, default=1)
    bundle.add_argument("--max-documents", type=int, default=6)
    bundle.add_argument("--max-xbrl-roles", type=int, default=5)
    bundle.add_argument("--max-tables", type=int, default=8)
    bundle.add_argument("--max-rows", type=int, default=30)
    bundle.add_argument("--no-xbrl", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "search":
        payload = search_reports(args.company, args.start_date, args.end_date, args.report_name, args.limit, args.timeout)
    elif args.command == "documents":
        payload = fetch_report_documents(args.rcp_no, args.timeout, args.max_documents)
    elif args.command == "xbrl":
        payload = fetch_xbrl_roles(args.rcp_no, args.timeout, args.max_roles)
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
                "max_reports": args.max_reports,
                "max_documents": args.max_documents,
                "max_xbrl_roles": args.max_xbrl_roles,
                "max_tables": args.max_tables,
                "max_rows": args.max_rows,
                "include_xbrl": not args.no_xbrl,
            }
        payload = build_dart_public_bundle(config, timeout=args.timeout)
    dump_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
