#!/usr/bin/env python3
"""Bounded source-catalog probe with optional public network-candidate follow-up.

This is the deterministic loop behind the agentic workflow:

1. Search The Econmicat source catalog.
2. Probe selected source pages.
3. If Playwright exposes public JSON/RSS/API candidates, follow a bounded number
   of those public candidates.

It never logs in, pays, solves CAPTCHA, or reuses private credentials.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from public_page_reader import DESKTOP_HEADERS, read_public_page  # noqa: E402
from source_catalog import load_catalog, search_catalog, _source_type  # noqa: E402


SKIP_URL_MARKERS = (
    "/static/",
    "/images/",
    "/logos/",
    "/api/users/",
    "/api/watchlist/",
    "/api/portfolio/",
    "/followingstocks",
    "/bff/prod/header/",
    "/config/prod/popups/",
)

SKIP_SUFFIXES = (".svg", ".png", ".jpg", ".jpeg", ".webp", ".css", ".js")

FOLLOWABLE_MARKERS = (
    "application/json",
    "application/rss",
    "application/xml",
    "text/xml",
    "/api/",
    "graphql",
    ".json",
    "/payload.json",
    "/feed",
    "/rss",
)


def is_followable_candidate(candidate: dict[str, Any]) -> bool:
    url = str(candidate.get("url", ""))
    content_type = str(candidate.get("content_type", ""))
    method = str(candidate.get("method", "GET")).upper()
    status_code = candidate.get("status_code")
    haystack = f"{url} {content_type}".lower()
    lower_url = url.lower().split("?", 1)[0]
    if method != "GET":
        return False
    if status_code and int(status_code) >= 400:
        return False
    if any(marker in haystack for marker in SKIP_URL_MARKERS):
        return False
    if lower_url.endswith(SKIP_SUFFIXES):
        return False
    return any(marker in haystack for marker in FOLLOWABLE_MARKERS)


def candidate_priority(candidate: dict[str, Any]) -> int:
    url = str(candidate.get("url", "")).lower()
    content_type = str(candidate.get("content_type", "")).lower()
    if "/payload.json" in url:
        return 0
    if "application/json" in content_type and "/api/" not in url:
        return 1
    if "application/json" in content_type:
        return 2
    if any(marker in url for marker in ("/rss", "/feed", ".json")):
        return 3
    return 9


def public_browser_probe_view(browser_probe: dict[str, Any]) -> dict[str, Any]:
    """Keep only public follow-up candidates in the persisted probe view."""
    if not browser_probe:
        return {}
    visible = dict(browser_probe)
    candidates = browser_probe.get("network_candidates", [])
    visible["network_candidates"] = [
        candidate for candidate in candidates if is_followable_candidate(candidate)
    ][:20]
    return visible


def _normalize_json_value(value: Any, limit: int = 1200) -> Any:
    if isinstance(value, dict):
        normalized = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 20:
                normalized["..."] = "truncated"
                break
            normalized[key] = _normalize_json_value(item, limit)
        return normalized
    if isinstance(value, list):
        return [_normalize_json_value(item, limit) for item in value[:8]]
    if isinstance(value, str):
        return value[:limit]
    return value


def fetch_public_candidate(url: str, timeout: int = 8, referer: str = "") -> dict[str, Any]:
    headers = dict(DESKTOP_HEADERS)
    if referer:
        headers["Referer"] = referer
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public candidate URL
            content_type = response.headers.get("content-type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(800_000)
            text = raw.decode(charset, errors="replace")
            payload: dict[str, Any] | None = None
            if "json" in content_type.lower() or url.lower().endswith(".json"):
                try:
                    payload = _normalize_json_value(json.loads(text))
                except json.JSONDecodeError:
                    payload = None
            return {
                "type": "public_network_candidate",
                "name": url,
                "url": response.url,
                "access_status": "ok",
                "retrieval_method": "public_network_candidate_follow",
                "claims": [text[:700]] if text else [],
                "numeric_facts": [],
                "caveats": [],
                "status_code": response.status,
                "content_type": content_type,
                "json_preview": payload,
            }
    except HTTPError as exc:
        return {
            "type": "public_network_candidate",
            "name": url,
            "url": url,
            "access_status": "auth_required" if exc.code in {401, 402, 403} else "blocked",
            "retrieval_method": "public_network_candidate_follow",
            "claims": [],
            "numeric_facts": [],
            "caveats": [str(exc)],
            "status_code": exc.code,
            "content_type": "",
            "json_preview": None,
        }
    except (URLError, OSError, TimeoutError, ValueError) as exc:
        return {
            "type": "public_network_candidate",
            "name": url,
            "url": url,
            "access_status": "blocked",
            "retrieval_method": "public_network_candidate_follow",
            "claims": [],
            "numeric_facts": [],
            "caveats": [str(exc)],
            "status_code": None,
            "content_type": "",
            "json_preview": None,
        }


def probe_catalog_sources(
    query: str,
    category: str = "",
    limit: int = 3,
    timeout: int = 8,
    max_attempts: int = 6,
    max_follow: int = 5,
    catalog_url: str = "https://www.theconomicat.com/",
) -> dict[str, Any]:
    items = search_catalog(load_catalog(catalog_url, timeout=timeout), query, category, False, limit)
    primary_sources = []
    followed_sources = []
    for item in items:
        result = read_public_page(item.url, timeout=timeout, use_browser=True, max_attempts=max_attempts)
        browser_probe = result.get("browser_probe", {})
        primary = {
            "type": _source_type(item.category),
            "name": item.name,
            "url": result.get("final_url", item.url),
            "access_status": result.get("access_status", "blocked"),
            "retrieval_method": result.get("retrieval_method", "public_page_reader"),
            "claims": [result.get("excerpt", "")[:900]] if result.get("excerpt") else [],
            "numeric_facts": [],
            "caveats": [result.get("error")] if result.get("error") else [],
            "metadata": result.get("metadata", {}),
            "trace": result.get("trace", []),
            "catalog": asdict(item),
            "browser_probe": public_browser_probe_view(browser_probe),
        }
        primary_sources.append(primary)

        candidates = browser_probe.get("network_candidates", [])
        followed_count = 0
        seen: set[str] = set()
        for candidate in sorted(candidates, key=candidate_priority):
            if followed_count >= max_follow:
                break
            if not is_followable_candidate(candidate):
                continue
            url = str(candidate.get("url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            followed = fetch_public_candidate(url, timeout=timeout, referer=item.url)
            followed["parent_source"] = item.url
            followed["network_candidate"] = candidate
            followed_sources.append(followed)
            followed_count += 1

    return {
        "request": {
            "query": query,
            "category": category,
            "limit": limit,
            "timeout": timeout,
            "max_attempts": max_attempts,
            "max_follow": max_follow,
            "catalog_url": catalog_url,
        },
        "catalog_items": [asdict(item) for item in items],
        "sources": primary_sources + followed_sources,
        "primary_sources": primary_sources,
        "followed_sources": followed_sources,
        "summary": {
            "catalog_items": len(items),
            "primary_sources": len(primary_sources),
            "followed_sources": len(followed_sources),
            "ok_sources": sum(1 for source in primary_sources + followed_sources if source.get("access_status") == "ok"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--category", default="")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=8)
    parser.add_argument("--max-attempts", type=int, default=6)
    parser.add_argument("--max-follow", type=int, default=5)
    parser.add_argument("--catalog-url", default="https://www.theconomicat.com/")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    payload = probe_catalog_sources(
        query=args.query,
        category=args.category,
        limit=args.limit,
        timeout=args.timeout,
        max_attempts=args.max_attempts,
        max_follow=args.max_follow,
        catalog_url=args.catalog_url,
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
