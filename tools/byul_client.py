#!/usr/bin/env python3
"""Fetch Byul.ai public market intelligence for research packets."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URLS = [
    "https://api.byul.ai/api/v1",
    "https://api.byul.ai/v1",
]

INDEX_ENDPOINTS = {
    "fear-greed": "/fear-greed/cfng",
    "crypto-fear-greed": "/fear-greed/fng",
    "kospi-fear-greed": "/fear-greed/kospi-fng",
    "vix": "/vix",
    "kospi-volatility": "/vix/kospi",
    "dxy": "/fear-greed/dxy",
    "put-call-options": "/fear-greed/put-call-options",
    "junk-bond-demand": "/fear-greed/junk-bond-demand",
    "stock-price-breadth": "/fear-greed/stock-price-breadth",
    "safe-haven-demand": "/fear-greed/safe-haven-demand",
    "stock-price-strength": "/fear-greed/stock-price-strength",
    "market-momentum-sp500": "/fear-greed/market-momentum-sp500",
    "market-momentum-sp125": "/fear-greed/market-momentum-sp125",
}


def _clean_params(params: dict[str, Any]) -> dict[str, str]:
    cleaned = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            cleaned[key] = "true" if value else "false"
        else:
            cleaned[key] = str(value)
    return cleaned


def fetch_json(
    path: str,
    params: dict[str, Any] | None = None,
    base_urls: list[str] | None = None,
    timeout: int = 12,
) -> dict[str, Any]:
    bases = base_urls or DEFAULT_BASE_URLS
    query = urlencode(_clean_params(params or {}))
    errors = []
    for base in bases:
        url = base.rstrip("/") + "/" + path.lstrip("/")
        if query:
            url += "?" + query
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "KPSAnalystWorkbench/0.2 (byul public API client)",
                },
            )
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-provided public API
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
                return {
                    "url": url,
                    "access_status": "ok",
                    "status_code": response.status,
                    "headers": {
                        "x-ratelimit-limit": response.headers.get("x-ratelimit-limit"),
                        "x-ratelimit-remaining": response.headers.get("x-ratelimit-remaining"),
                        "x-ratelimit-reset": response.headers.get("x-ratelimit-reset"),
                        "x-ratelimit-policy": response.headers.get("x-ratelimit-policy"),
                        "cache-control": response.headers.get("cache-control"),
                    },
                    "data": payload,
                    "error": "",
                }
        except HTTPError as exc:
            errors.append(f"{url}: HTTP {exc.code}")
            if exc.code not in {404, 405}:
                curl_result = _fetch_json_with_curl(url, timeout)
                if curl_result.get("access_status") == "ok":
                    return curl_result
                return {
                    "url": url,
                    "access_status": "auth_required" if exc.code in {401, 403} else "blocked",
                    "status_code": exc.code,
                    "headers": {},
                    "data": {},
                    "error": str(exc),
                }
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {exc}")
            curl_result = _fetch_json_with_curl(url, timeout)
            if curl_result.get("access_status") == "ok":
                return curl_result
            errors.append(f"{url}: curl fallback failed: {curl_result.get('error')}")
    return {
        "url": bases[0].rstrip("/") + "/" + path.lstrip("/"),
        "access_status": "blocked",
        "status_code": None,
        "headers": {},
        "data": {},
        "error": "; ".join(errors),
    }


def _fetch_json_with_curl(url: str, timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                "curl",
                "-sS",
                "-L",
                "--connect-timeout",
                str(timeout),
                "--max-time",
                str(timeout),
                "-w",
                "\n__HTTP_STATUS__:%{http_code}\n",
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return {
            "url": url,
            "access_status": "blocked",
            "status_code": None,
            "headers": {},
            "data": {},
            "error": f"curl unavailable: {exc}",
        }
    output = completed.stdout or ""
    marker = "\n__HTTP_STATUS__:"
    if marker not in output:
        return {
            "url": url,
            "access_status": "blocked",
            "status_code": None,
            "headers": {},
            "data": {},
            "error": completed.stderr.strip() or "curl returned no HTTP status marker",
        }
    body, status_raw = output.rsplit(marker, 1)
    try:
        status_code = int(status_raw.strip().splitlines()[0])
    except (ValueError, IndexError):
        status_code = None
    if completed.returncode != 0 or status_code is None or status_code >= 400:
        return {
            "url": url,
            "access_status": "auth_required" if status_code in {401, 403} else "blocked",
            "status_code": status_code,
            "headers": {},
            "data": {},
            "error": completed.stderr.strip() or f"curl HTTP {status_code}",
        }
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return {
            "url": url,
            "access_status": "partial",
            "status_code": status_code,
            "headers": {},
            "data": {},
            "error": f"curl JSON decode failed: {exc}",
        }
    return {
        "url": url,
        "access_status": "ok",
        "status_code": status_code,
        "headers": {},
        "data": data,
        "error": "",
    }


def _items_from_news_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            return payload["items"]
        if isinstance(payload.get("data"), list):
            return payload["data"]
        if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("items"), list):
            return payload["data"]["items"]
    if isinstance(payload, list):
        return payload
    return []


def news_item_to_source(item: dict[str, Any], source_url: str) -> dict[str, Any]:
    title = item.get("title") or item.get("originalTitle") or "Byul news item"
    url = item.get("originalUrl") or item.get("url") or source_url
    key_points = item.get("keyPoints") or []
    content = item.get("content") or ""
    claims = []
    if content and content != "요약없음":
        claims.append(content[:700])
    for point in key_points[:4]:
        claims.append(str(point))
    numeric_facts = []
    if item.get("importanceScore") is not None:
        numeric_facts.append(f"importanceScore={item.get('importanceScore')}")
    if item.get("symbols"):
        numeric_facts.append("symbols=" + ",".join(str(symbol) for symbol in item.get("symbols", [])[:8]))
    if item.get("sentiment"):
        numeric_facts.append(f"sentiment={item.get('sentiment')}")
    if item.get("date"):
        numeric_facts.append(f"date={item.get('date')}")
    return {
        "type": "news",
        "name": title,
        "url": url,
        "access_status": "ok",
        "retrieval_method": "byul_api",
        "claims": claims,
        "numeric_facts": numeric_facts,
        "caveats": ["Byul public API normalized market-news record."],
        "byul": item,
    }


def calendar_item_to_source(item: dict[str, Any], source_url: str, source_type: str = "calendar") -> dict[str, Any]:
    title = item.get("event_name") or item.get("kevent") or item.get("event") or "Byul calendar event"
    facts = []
    for key in ["currency", "importance", "importance_numeric", "actual", "forecast", "previous", "event_time", "date", "time"]:
        if item.get(key) is not None:
            facts.append(f"{key}={item.get(key)}")
    return {
        "type": source_type,
        "name": title,
        "url": source_url,
        "access_status": "ok",
        "retrieval_method": "byul_api",
        "claims": [f"{title}: actual={item.get('actual')} forecast={item.get('forecast')} previous={item.get('previous')}"],
        "numeric_facts": facts,
        "caveats": ["Byul public economic-calendar record."],
        "byul": item,
    }


def index_result_to_source(index_id: str, result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data", {})
    inner = data.get("data", data) if isinstance(data, dict) else {}
    title = f"Byul market index: {index_id}"
    facts = []
    for key in [
        "value",
        "value_classification",
        "quote",
        "pct_change",
        "daily_change",
        "daily_change_percent",
        "volatility_level",
        "market_sentiment",
        "timestamp",
        "transact_time",
    ]:
        if isinstance(inner, dict) and inner.get(key) is not None:
            facts.append(f"{key}={inner.get(key)}")
    return {
        "type": "market_index",
        "name": title,
        "url": result.get("url", ""),
        "access_status": result.get("access_status", "blocked"),
        "retrieval_method": "byul_api",
        "claims": [f"{index_id} returned by Byul public market-index endpoint."],
        "numeric_facts": facts,
        "caveats": [result.get("error")] if result.get("error") else ["Byul public market-index record."],
        "byul": inner,
    }


def fetch_news_bundle(config: dict[str, Any], base_urls: list[str] | None = None, timeout: int = 12) -> dict[str, Any]:
    lang = config.get("lang", "ko")
    limit = min(int(config.get("limit", 5)), 100)
    min_importance = config.get("minImportance", config.get("min_importance", 3))
    common = {
        "lang": lang,
        "limit": limit,
        "minImportance": min_importance,
        "q": config.get("query") or config.get("q"),
        "category": config.get("category"),
        "startDate": config.get("startDate"),
        "endDate": config.get("endDate"),
    }
    endpoint = "/news"
    if config.get("symbol"):
        endpoint = f"/news/symbol/{config['symbol']}"
        common.pop("q", None)
        common.pop("category", None)
    elif config.get("kind") in {"top", "crypto", "korea"}:
        endpoint = f"/{config['kind']}"
    result = fetch_json(endpoint, common, base_urls, timeout)
    items = _items_from_news_payload(result.get("data"))
    return {
        "request": {"endpoint": endpoint, "params": _clean_params(common)},
        "result": result,
        "items": items,
        "sources": [news_item_to_source(item, result.get("url", "")) for item in items],
    }


def fetch_calendar_bundle(config: dict[str, Any], base_urls: list[str] | None = None, timeout: int = 12) -> dict[str, Any]:
    lang = config.get("lang", config.get("language", "ko"))
    range_name = config.get("range", "today")
    result = fetch_json(f"/economic-calendar/{range_name}", {"lang": lang}, base_urls, timeout)
    data = result.get("data", {})
    events = data.get("data", []) if isinstance(data, dict) else []
    if config.get("importance"):
        events = [event for event in events if event.get("importance") == config["importance"]]
    if config.get("currency"):
        events = [event for event in events if str(event.get("currency", "")).upper() == str(config["currency"]).upper()]
    limit = min(int(config.get("limit", 25)), 100)
    events = events[:limit]
    return {
        "request": {"endpoint": f"/economic-calendar/{range_name}", "params": {"lang": lang}},
        "result": result,
        "items": events,
        "sources": [calendar_item_to_source(item, result.get("url", "")) for item in events],
    }


def fetch_earnings_bundle(config: dict[str, Any], base_urls: list[str] | None = None, timeout: int = 12) -> dict[str, Any]:
    lang = config.get("lang", config.get("language", "ko"))
    calendar = fetch_calendar_bundle({**config, "lang": lang, "range": config.get("range", "this-week"), "limit": 100}, base_urls, timeout)
    terms = [term.lower() for term in config.get("terms", ["earnings", "실적", "eps", "매출", "guidance", "results"])]
    events = []
    for item in calendar.get("items", []):
        haystack = " ".join(str(item.get(key, "")) for key in ["event", "kevent", "event_name", "jevent"]).lower()
        if any(term in haystack for term in terms):
            events.append(item)
    news = fetch_news_bundle(
        {
            "lang": lang,
            "query": config.get("query", "earnings OR 실적"),
            "limit": config.get("news_limit", 5),
            "minImportance": config.get("minImportance", 3),
        },
        base_urls,
        timeout,
    )
    limit = min(int(config.get("limit", 20)), 100)
    events = events[:limit]
    sources = [calendar_item_to_source(item, calendar.get("result", {}).get("url", ""), "earnings_calendar") for item in events]
    sources.extend(news.get("sources", []))
    return {
        "request": {"calendar_range": config.get("range", "this-week"), "terms": terms},
        "calendar_result": calendar.get("result"),
        "news_result": news.get("result"),
        "items": events,
        "news_items": news.get("items", []),
        "sources": sources,
    }


def fetch_indices_bundle(config: dict[str, Any], base_urls: list[str] | None = None, timeout: int = 12) -> dict[str, Any]:
    indexes = config.get("indexes", ["fear-greed", "vix", "kospi-volatility"])
    results = {}
    sources = []
    for index_id in indexes[:8]:
        endpoint = INDEX_ENDPOINTS.get(index_id)
        if not endpoint:
            results[index_id] = {"access_status": "blocked", "error": f"unknown index id: {index_id}"}
            continue
        result = fetch_json(endpoint, {}, base_urls, timeout)
        results[index_id] = result
        sources.append(index_result_to_source(index_id, result))
    return {"request": {"indexes": indexes}, "results": results, "sources": sources}


def fetch_byul_bundle(config: dict[str, Any], timeout: int = 12) -> dict[str, Any]:
    base_urls = config.get("base_urls") or config.get("baseUrls") or DEFAULT_BASE_URLS
    intelligence: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    if config.get("news", True):
        news_config = config.get("news") if isinstance(config.get("news"), dict) else {}
        intelligence["news"] = fetch_news_bundle(news_config, base_urls, timeout)
        sources.extend(intelligence["news"].get("sources", []))
    if config.get("calendar"):
        calendar_config = config.get("calendar") if isinstance(config.get("calendar"), dict) else {}
        intelligence["calendar"] = fetch_calendar_bundle(calendar_config, base_urls, timeout)
        sources.extend(intelligence["calendar"].get("sources", []))
    if config.get("earnings"):
        earnings_config = config.get("earnings") if isinstance(config.get("earnings"), dict) else {}
        intelligence["earnings"] = fetch_earnings_bundle(earnings_config, base_urls, timeout)
        sources.extend(intelligence["earnings"].get("sources", []))
    if config.get("indices"):
        indices_config = config.get("indices") if isinstance(config.get("indices"), dict) else {"indexes": config.get("indices")}
        intelligence["indices"] = fetch_indices_bundle(indices_config, base_urls, timeout)
        sources.extend(intelligence["indices"].get("sources", []))
    return {"market_intelligence": {"byul": intelligence}, "sources": sources}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=12)
    sub = parser.add_subparsers(dest="command", required=True)

    news = sub.add_parser("news")
    news.add_argument("--symbol")
    news.add_argument("--kind", choices=["general", "top", "crypto", "korea"], default="general")
    news.add_argument("--query")
    news.add_argument("--category")
    news.add_argument("--lang", default="ko")
    news.add_argument("--limit", type=int, default=5)
    news.add_argument("--min-importance", type=int, default=3)
    news.add_argument("--start-date")
    news.add_argument("--end-date")

    calendar = sub.add_parser("calendar")
    calendar.add_argument("--range", default="today")
    calendar.add_argument("--lang", default="ko")
    calendar.add_argument("--importance")
    calendar.add_argument("--currency")
    calendar.add_argument("--limit", type=int, default=25)

    earnings = sub.add_parser("earnings")
    earnings.add_argument("--range", default="this-week")
    earnings.add_argument("--lang", default="ko")
    earnings.add_argument("--query", default="earnings OR 실적")
    earnings.add_argument("--limit", type=int, default=20)
    earnings.add_argument("--news-limit", type=int, default=5)
    earnings.add_argument("--min-importance", type=int, default=3)

    indices = sub.add_parser("indices")
    indices.add_argument("--indexes", nargs="+", default=["fear-greed", "vix", "kospi-volatility"])

    bundle = sub.add_parser("bundle")
    bundle.add_argument("--config", required=True)

    args = parser.parse_args(argv)
    if args.command == "news":
        payload = fetch_news_bundle(
            {
                "symbol": args.symbol,
                "kind": None if args.kind == "general" else args.kind,
                "query": args.query,
                "category": args.category,
                "lang": args.lang,
                "limit": args.limit,
                "minImportance": args.min_importance,
                "startDate": args.start_date,
                "endDate": args.end_date,
            },
            timeout=args.timeout,
        )
    elif args.command == "calendar":
        payload = fetch_calendar_bundle(vars(args), timeout=args.timeout)
    elif args.command == "earnings":
        payload = fetch_earnings_bundle(vars(args), timeout=args.timeout)
    elif args.command == "indices":
        payload = fetch_indices_bundle({"indexes": args.indexes}, timeout=args.timeout)
    else:
        with open(args.config, encoding="utf-8") as handle:
            payload = fetch_byul_bundle(json.load(handle), timeout=args.timeout)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
