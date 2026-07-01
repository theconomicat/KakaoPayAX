#!/usr/bin/env python3
"""Read a public page or local HTML file and return a conservative JSON summary.

This is a public-source helper, not a paywall/login/CAPTCHA bypasser. It uses a
small adaptive chain inspired by public-source readers such as insane-search:
normal browser-shaped requests first, then no-auth public URL variants/readers,
then optional TLS/browser rendering when locally available.
"""
from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


MAX_READ_BYTES = 1_500_000
MIN_OK_TEXT_LENGTH = 200

DESKTOP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.2 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

CHALLENGE_MARKERS = (
    "access denied",
    "akamai bot manager",
    "bot detection",
    "captcha",
    "cf-chl",
    "cf-browser-verification",
    "attention required! | cloudflare",
    "cloudflare ray id",
    "datadome",
    "ddos-guard",
    "enable javascript",
    "just a moment",
    "perimeterx",
    "verify you are human",
)

AUTH_MARKERS = (
    "authentication required",
    "log in to continue",
    "login required",
    "paywall",
    "sign in to continue",
    "subscribe to continue",
    "subscription required",
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_ignored = False
        self.in_jsonld = False
        self.title_parts: list[str] = []
        self.meta_parts: list[str] = []
        self.jsonld_parts: list[str] = []
        self.text_parts: list[str] = []
        self._current_tag = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._current_tag = tag.lower()
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if self._current_tag == "meta":
            key = attrs_dict.get("name") or attrs_dict.get("property")
            if key in {"description", "og:description", "twitter:description", "og:title", "twitter:title"}:
                content = " ".join(html.unescape(attrs_dict.get("content", "")).split())
                if content:
                    self.meta_parts.append(content)
        if self._current_tag == "script" and "ld+json" in attrs_dict.get("type", "").lower():
            self.in_jsonld = True
            return
        if self._current_tag in {"script", "style", "noscript", "svg"}:
            self.in_ignored = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self.in_jsonld:
            self.in_jsonld = False
        if tag in {"script", "style", "noscript", "svg"}:
            self.in_ignored = False
        self._current_tag = ""

    def handle_data(self, data: str) -> None:
        if self.in_jsonld:
            self.jsonld_parts.append(data)
            return
        if self.in_ignored:
            return
        stripped = " ".join(html.unescape(data).split())
        if not stripped:
            return
        if self._current_tag == "title":
            self.title_parts.append(stripped)
        elif len(stripped) > 2:
            self.text_parts.append(stripped)


def _normalize_text(value: str, limit: int = 4000) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        return value[:limit].rstrip() + "..."
    return value


def _decode_response_body(raw: bytes, charset: str | None) -> str:
    return raw.decode(charset or "utf-8", errors="replace")


def _read_http_attempt(url: str, timeout: int, headers: dict[str, str], label: str) -> dict[str, Any]:
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - user requested URL reader
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(MAX_READ_BYTES)
            return {
                "url": url,
                "status_code": response.status,
                "content": _decode_response_body(raw, charset),
                "final_url": response.url,
                "retrieval_method": f"urllib:{label}",
                "error": "",
            }
    except HTTPError as exc:
        charset = exc.headers.get_content_charset() if exc.headers else "utf-8"
        raw = exc.read(min(MAX_READ_BYTES, 300_000))
        return {
            "url": url,
            "status_code": exc.code,
            "content": _decode_response_body(raw, charset),
            "final_url": url,
            "retrieval_method": f"urllib:{label}",
            "error": str(exc),
        }
    except (URLError, OSError, TimeoutError, ValueError) as exc:
        return {
            "url": url,
            "status_code": None,
            "content": "",
            "final_url": url,
            "retrieval_method": f"urllib:{label}",
            "error": str(exc),
        }


def _read_curl_cffi_attempt(url: str, timeout: int, impersonate: str) -> dict[str, Any]:
    try:
        from curl_cffi import requests as curl_requests  # type: ignore
    except ImportError as exc:
        return {
            "url": url,
            "status_code": None,
            "content": "",
            "final_url": url,
            "retrieval_method": f"curl_cffi:{impersonate}",
            "error": f"optional dependency unavailable: {exc}",
        }

    try:
        response = curl_requests.get(
            url,
            timeout=timeout,
            impersonate=impersonate,
            headers=DESKTOP_HEADERS,
            allow_redirects=True,
        )
        response.encoding = response.encoding or "utf-8"
        return {
            "url": url,
            "status_code": response.status_code,
            "content": response.text[:MAX_READ_BYTES],
            "final_url": response.url,
            "retrieval_method": f"curl_cffi:{impersonate}",
            "error": "",
        }
    except Exception as exc:  # pragma: no cover - optional transport varies by host
        return {
            "url": url,
            "status_code": None,
            "content": "",
            "final_url": url,
            "retrieval_method": f"curl_cffi:{impersonate}",
            "error": str(exc),
        }


def _read_local(path: str) -> tuple[int | None, str, str]:
    local_path = Path(path)
    return None, local_path.read_text(encoding="utf-8"), str(local_path.resolve())


def _jsonld_summary(parts: list[str]) -> list[str]:
    summaries: list[str] = []

    def visit(value: Any) -> None:
        if len(summaries) >= 12:
            return
        if isinstance(value, dict):
            for key in ("name", "headline", "description", "articleBody", "datePublished"):
                item = value.get(key)
                if isinstance(item, str):
                    normalized = _normalize_text(item, limit=500)
                    if normalized:
                        summaries.append(normalized)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for raw in parts:
        try:
            visit(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return summaries


def _extract_text(content: str) -> tuple[str, str, int]:
    parser = TextExtractor()
    parser.feed(content)
    title = _normalize_text(" ".join(parser.title_parts), limit=300)
    metadata_parts = parser.meta_parts + _jsonld_summary(parser.jsonld_parts)
    text = _normalize_text(" ".join(parser.text_parts + metadata_parts), limit=4000)
    return title, text, len(text)


def _extract_metadata(content: str) -> dict[str, Any]:
    parser = TextExtractor()
    parser.feed(content)
    return {
        "meta": parser.meta_parts[:10],
        "json_ld": _jsonld_summary(parser.jsonld_parts)[:12],
    }


def _contains_any(value: str, markers: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in markers)


def _classify_access(status_code: int | None, content: str, text_length: int, error: str) -> str:
    lowered = content[:50_000].lower()
    if status_code in {401, 402} or _contains_any(lowered, AUTH_MARKERS):
        return "auth_required"
    if status_code == 403 and ("login" in lowered or "subscribe" in lowered):
        return "auth_required"
    if status_code and status_code >= 400:
        return "blocked"
    if _contains_any(lowered, CHALLENGE_MARKERS):
        return "blocked"
    if text_length >= MIN_OK_TEXT_LENGTH:
        return "ok"
    if text_length > 0:
        return "partial"
    return "blocked" if error else "partial"


def _result_from_attempt(target: str, attempt: dict[str, Any], trace: list[dict[str, Any]]) -> dict[str, Any]:
    title, text, text_length = _extract_text(attempt.get("content", ""))
    if attempt.get("retrieval_method") == "local_file":
        access_status = "ok" if text_length >= MIN_OK_TEXT_LENGTH else "partial"
    else:
        access_status = _classify_access(
            attempt.get("status_code"),
            attempt.get("content", ""),
            text_length,
            attempt.get("error", ""),
        )
    return {
        "target": target,
        "final_url": attempt.get("final_url", target),
        "access_status": access_status,
        "status_code": attempt.get("status_code"),
        "retrieval_method": attempt.get("retrieval_method", "unknown"),
        "title": title,
        "excerpt": text,
        "text_length": text_length,
        "metadata": _extract_metadata(attempt.get("content", "")),
        "error": attempt.get("error", ""),
        "trace": trace,
    }


def _trace_entry(attempt: dict[str, Any]) -> dict[str, Any]:
    _, text, text_length = _extract_text(attempt.get("content", ""))
    return {
        "url": attempt.get("url"),
        "final_url": attempt.get("final_url"),
        "status_code": attempt.get("status_code"),
        "retrieval_method": attempt.get("retrieval_method"),
        "access_status": _classify_access(
            attempt.get("status_code"),
            attempt.get("content", ""),
            text_length,
            attempt.get("error", ""),
        ),
        "text_length": text_length,
        "error": attempt.get("error", ""),
    }


def _mobile_subdomain_url(parsed) -> str:
    host = parsed.netloc
    if host.startswith("www."):
        host = "m." + host[4:]
    elif not host.startswith("m."):
        host = "m." + host
    return urlunparse(parsed._replace(netloc=host))


def _append_path_suffix(parsed, suffix: str) -> str:
    path = parsed.path.rstrip("/") or "/"
    if suffix.startswith("."):
        path = path + suffix
    else:
        path = path.rstrip("/") + "/" + suffix
    return urlunparse(parsed._replace(path=path, query=""))


def _public_url_variants(url: str) -> list[tuple[str, str]]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []

    variants = [
        ("original", url),
        ("mobile_subdomain", _mobile_subdomain_url(parsed)),
        ("rss", _append_path_suffix(parsed, "rss")),
        ("feed", _append_path_suffix(parsed, "feed")),
    ]
    if not parsed.path.endswith((".json", ".xml", ".rss")):
        variants.append(("json_suffix", _append_path_suffix(parsed, ".json")))
    variants.append(("jina_reader", f"https://r.jina.ai/{url}"))

    seen: set[str] = set()
    deduped = []
    for label, candidate in variants:
        key = candidate.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, candidate))
    return deduped


def _attempt_playwright(target: str, timeout: int) -> dict[str, Any]:
    script_path = Path(__file__).with_name("playwright_probe.mjs")
    try:
        completed = subprocess.run(
            ["node", str(script_path), target, str(timeout * 1000)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout + 8,
        )
        payload = json.loads(completed.stdout)
        return {
            "url": target,
            "status_code": payload.get("status_code"),
            "content": payload.get("excerpt", ""),
            "final_url": payload.get("final_url", target),
            "retrieval_method": "playwright",
            "error": payload.get("error", ""),
            "playwright": payload,
        }
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {
            "url": target,
            "status_code": None,
            "content": "",
            "final_url": target,
            "retrieval_method": "playwright",
            "error": str(exc),
        }


def _best_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    status_rank = {"ok": 4, "partial": 3, "auth_required": 2, "blocked": 1}
    return max(results, key=lambda item: (status_rank.get(item["access_status"], 0), item["text_length"]))


def read_public_page(
    target: str,
    timeout: int = 12,
    adaptive: bool = True,
    use_browser: bool = False,
    max_attempts: int | None = 6,
) -> dict[str, Any]:
    try:
        if not target.startswith(("http://", "https://")):
            status_code, content, final_url = _read_local(target)
            trace = [
                {
                    "url": target,
                    "final_url": final_url,
                    "status_code": status_code,
                    "retrieval_method": "local_file",
                    "access_status": "ok",
                    "text_length": len(content),
                    "error": "",
                }
            ]
            return _result_from_attempt(
                target,
                {
                    "url": target,
                    "status_code": status_code,
                    "content": content,
                    "final_url": final_url,
                    "retrieval_method": "local_file",
                    "error": "",
                },
                trace,
            )
    except (OSError, TimeoutError, ValueError) as exc:
        return {
            "target": target,
            "final_url": target,
            "access_status": "blocked",
            "status_code": None,
            "retrieval_method": "urllib",
            "title": "",
            "excerpt": "",
            "text_length": 0,
            "error": str(exc),
            "trace": [],
        }

    trace: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    per_attempt_timeout = max(2, min(timeout, 5))
    attempts: list[tuple[str, str, dict[str, str]]] = [("original_desktop", target, DESKTOP_HEADERS)]
    if adaptive:
        attempts.append(("original_mobile", target, MOBILE_HEADERS))
        attempts.extend((label, candidate, DESKTOP_HEADERS) for label, candidate in _public_url_variants(target)[1:])
    if max_attempts is not None:
        attempts = attempts[:max_attempts]

    for label, url, headers in attempts:
        attempt = _read_http_attempt(url, per_attempt_timeout, headers, label)
        trace.append(_trace_entry(attempt))
        result = _result_from_attempt(target, attempt, list(trace))
        results.append(result)
        if result["access_status"] == "ok":
            return result

    if adaptive:
        for impersonate in ("safari", "chrome", "firefox"):
            if max_attempts is not None and len(trace) >= max_attempts:
                break
            attempt = _read_curl_cffi_attempt(target, per_attempt_timeout, impersonate)
            trace.append(_trace_entry(attempt))
            result = _result_from_attempt(target, attempt, list(trace))
            results.append(result)
            if result["access_status"] == "ok":
                return result

    if use_browser:
        attempt = _attempt_playwright(target, timeout)
        trace.append(_trace_entry(attempt))
        result = _result_from_attempt(target, attempt, list(trace))
        if "playwright" in attempt:
            result["browser_probe"] = attempt["playwright"]
        results.append(result)
        if result["access_status"] == "ok":
            return result

    best = _best_result(results) if results else {
        "target": target,
        "final_url": target,
        "access_status": "blocked",
        "status_code": None,
        "retrieval_method": "urllib",
        "title": "",
        "excerpt": "",
        "text_length": 0,
        "error": "no public access attempts were run",
        "trace": trace,
    }
    best["trace"] = trace
    return best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Public URL or local HTML/text file")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--no-adaptive", action="store_true")
    parser.add_argument("--browser", action="store_true", help="Try optional Playwright rendering after public HTTP routes.")
    parser.add_argument("--max-attempts", type=int, default=6)
    parser.add_argument("--exhaustive", action="store_true", help="Try every public route instead of the fast default attempt budget.")
    args = parser.parse_args(argv)
    json.dump(
        read_public_page(
            args.target,
            args.timeout,
            adaptive=not args.no_adaptive,
            use_browser=args.browser,
            max_attempts=None if args.exhaustive else args.max_attempts,
        ),
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
