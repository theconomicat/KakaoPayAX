#!/usr/bin/env python3
"""Fetch a list of public URLs into source objects."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from public_page_reader import read_public_page  # noqa: E402


def fetch_sources(urls: list[str], browser: bool = False, max_attempts: int | None = 6) -> list[dict[str, Any]]:
    sources = []
    for url in urls:
        result = read_public_page(url, use_browser=browser, max_attempts=max_attempts)
        sources.append(
            {
                "type": "unknown",
                "name": result.get("title") or url,
                "url": result.get("final_url", url),
                "access_status": result.get("access_status", "blocked"),
                "retrieval_method": result.get("retrieval_method", "urllib"),
                "claims": [result.get("excerpt", "")[:500]] if result.get("excerpt") else [],
                "numeric_facts": [],
                "caveats": [result.get("error")] if result.get("error") else [],
                "metadata": result.get("metadata", {}),
                "trace": result.get("trace", []),
                "browser_probe": result.get("browser_probe", {}),
            }
        )
    return sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--browser", action="store_true", help="Try optional Playwright rendering after public HTTP routes.")
    parser.add_argument("--max-attempts", type=int, default=6)
    parser.add_argument("--exhaustive", action="store_true", help="Try every public route instead of the fast default attempt budget.")
    args = parser.parse_args(argv)
    json.dump(
        fetch_sources(args.urls, args.browser, None if args.exhaustive else args.max_attempts),
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
