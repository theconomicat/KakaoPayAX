#!/usr/bin/env python3
"""Search a public market-source catalog and optionally probe selected URLs.

The default catalog is The Econmicat, a curated public list of finance tools.
This does not fetch every site during a normal workflow. It returns candidate
sources by category/query so Codex can visit only the sources needed for the
current research question.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from public_page_reader import read_public_page  # noqa: E402


DEFAULT_CATALOG_URL = "https://www.theconomicat.com/"
SOCIAL_DOMAINS = ("x.com", "twitter.com", "reddit.com", "gall.dcinside.com", "fmkorea.com")


@dataclass
class CatalogItem:
    category: str
    name: str
    url: str
    source_catalog: str


class SourceCatalogParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.category = "uncategorized"
        self.heading_tag = ""
        self.heading_parts: list[str] = []
        self.current_href = ""
        self.current_text_parts: list[str] = []
        self.items: list[CatalogItem] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in {"h2", "h3"}:
            self.heading_tag = tag
            self.heading_parts = []
        if tag == "a":
            self.current_href = attrs_dict.get("href") or ""
            self.current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self.heading_tag:
            self.heading_parts.append(data)
        if self.current_href:
            self.current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.heading_tag and tag == self.heading_tag:
            heading = _normalize(" ".join(self.heading_parts), limit=120)
            if heading:
                self.category = heading
            self.heading_tag = ""
            self.heading_parts = []
        if tag == "a" and self.current_href:
            name = _normalize(" ".join(self.current_text_parts), limit=200)
            url = urljoin(self.base_url, self.current_href)
            if name and url.startswith(("http://", "https://")):
                self.items.append(CatalogItem(self.category, name, url, self.base_url))
            self.current_href = ""
            self.current_text_parts = []


def _normalize(value: str, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", html.unescape(value)).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def load_catalog(catalog_url: str = DEFAULT_CATALOG_URL, timeout: int = 12) -> list[CatalogItem]:
    request = Request(catalog_url, headers={"User-Agent": "Mozilla/5.0 KPSAnalystWorkbench/0.3"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public catalog URL
        charset = response.headers.get_content_charset() or "utf-8"
        content = response.read(1_500_000).decode(charset, errors="replace")
    parser = SourceCatalogParser(catalog_url)
    parser.feed(content)
    seen: set[str] = set()
    deduped = []
    for item in parser.items:
        key = item.url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def search_catalog(
    items: list[CatalogItem],
    query: str = "",
    category: str = "",
    include_social: bool = False,
    limit: int = 20,
) -> list[CatalogItem]:
    query_terms = [term.lower() for term in query.split() if term.strip()]
    category_term = category.lower().strip()
    matches = []
    for item in items:
        haystack = f"{item.category} {item.name} {item.url}".lower()
        if category_term and category_term not in item.category.lower():
            continue
        if query_terms and not all(term in haystack for term in query_terms):
            continue
        if not include_social and any(domain in item.url.lower() for domain in SOCIAL_DOMAINS):
            continue
        matches.append(item)
    return matches[:limit]


def item_to_source(
    item: CatalogItem,
    timeout: int,
    browser: bool = False,
    max_attempts: int | None = 6,
) -> dict[str, Any]:
    result = read_public_page(item.url, timeout=timeout, use_browser=browser, max_attempts=max_attempts)
    return {
        "type": _source_type(item.category),
        "name": item.name,
        "url": result.get("final_url", item.url),
        "access_status": result.get("access_status", "blocked"),
        "retrieval_method": "source_catalog_probe",
        "claims": [result.get("excerpt", "")[:700]] if result.get("excerpt") else [],
        "numeric_facts": [],
        "caveats": [result.get("error")] if result.get("error") else [],
        "metadata": result.get("metadata", {}),
        "trace": result.get("trace", []),
        "browser_probe": result.get("browser_probe", {}),
        "catalog": asdict(item),
    }


def _source_type(category: str) -> str:
    mapping = {
        "속보": "news",
        "언론사": "news",
        "코인": "news",
        "심리 지수": "market_data",
        "차트": "market_data",
        "스크리너": "market_data",
        "마켓맵": "market_data",
        "예측 시장": "market_data",
        "경제 캘린더": "market_data",
        "금리 & 채권": "market_data",
        "어닝": "market_data",
        "애널리스트": "analyst_reference",
        "재무제표": "financials",
        "기관 포트폴리오": "financials",
        "옵션 플로우": "market_data",
        "내부자 거래": "disclosure",
        "커뮤니티": "unknown",
    }
    return mapping.get(category, "unknown")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
    parser.add_argument("--query", default="")
    parser.add_argument("--category", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--include-social", action="store_true")
    parser.add_argument("--probe", action="store_true", help="Read only the selected URLs and return source objects.")
    parser.add_argument("--browser", action="store_true", help="When probing, try optional Playwright rendering after public HTTP routes.")
    parser.add_argument("--max-attempts", type=int, default=6)
    parser.add_argument("--exhaustive", action="store_true", help="Try every public route when probing instead of the fast default attempt budget.")
    args = parser.parse_args(argv)
    max_attempts = None if args.exhaustive else args.max_attempts

    try:
        items = load_catalog(args.catalog_url, timeout=args.timeout)
        selected = search_catalog(items, args.query, args.category, args.include_social, args.limit)
        payload: dict[str, Any] = {
            "request": {
                "catalog_url": args.catalog_url,
                "query": args.query,
                "category": args.category,
                "limit": args.limit,
                "include_social": args.include_social,
                "probe": args.probe,
                "browser": args.browser,
                "max_attempts": max_attempts,
            },
            "access_status": "ok",
            "total_catalog_items": len(items),
            "items": [asdict(item) for item in selected],
            "sources": [item_to_source(item, args.timeout, args.browser, max_attempts) for item in selected] if args.probe else [],
            "error": "",
        }
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        payload = {
            "request": {
                "catalog_url": args.catalog_url,
                "query": args.query,
                "category": args.category,
                "limit": args.limit,
                "include_social": args.include_social,
                "probe": args.probe,
                "browser": args.browser,
                "max_attempts": max_attempts,
            },
            "access_status": "blocked",
            "total_catalog_items": 0,
            "items": [],
            "sources": [],
            "error": str(exc),
        }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
