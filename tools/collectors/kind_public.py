"""Collect KIND disclosures and original filing HTML without API keys."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from ..filing_parser import parse_filing_target, to_source as filing_to_source
except ImportError:  # pragma: no cover - direct script fallback
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from filing_parser import parse_filing_target, to_source as filing_to_source  # type: ignore


KIND_BASE = "https://kind.krx.co.kr"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


@dataclass
class KindCompany:
    query: str
    name: str
    short_code: str
    rep_isu_srt_cd: str
    isu_cd: str
    market_type: str
    industry: str


@dataclass
class KindDisclosure:
    acpt_no: str
    doc_no: str
    company: str
    company_code: str
    submitted_at: str
    title: str
    submitter: str
    market: str
    url: str
    source_family: str = "kind_public_search"


def _normalize(value: str, limit: int = 1000) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def _read_url(url: str, timeout: int = 12, data: dict[str, Any] | None = None, referer: str | None = None) -> tuple[int, str, str]:
    encoded = None
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json",
        "Referer": referer or f"{KIND_BASE}/main.do?method=loadInitPage&scrnmode=1",
    }
    if data is not None:
        encoded = urlencode({key: str(value) for key, value in data.items() if value is not None}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = Request(url, data=encoded, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public KIND pages
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(5_000_000)
            return response.status, raw.decode(charset, errors="replace"), response.url
    except (HTTPError, URLError, OSError, TimeoutError):
        return _read_url_with_curl(url, timeout, encoded.decode("utf-8") if encoded else None, referer)


def _read_url_with_curl(url: str, timeout: int, encoded_body: str | None = None, referer: str | None = None) -> tuple[int, str, str]:
    command = [
        "curl",
        "-sS",
        "-L",
        "--connect-timeout",
        str(timeout),
        "--max-time",
        str(timeout),
        "-A",
        USER_AGENT,
        "-H",
        f"Referer: {referer or KIND_BASE}",
        "-w",
        "\n__HTTP_STATUS__:%{http_code}\n__URL_EFFECTIVE__:%{url_effective}\n",
    ]
    if encoded_body is not None:
        command.extend(
            [
                "-H",
                "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
                "-H",
                "X-Requested-With: XMLHttpRequest",
                "--data",
                encoded_body,
            ]
        )
    command.append(url)
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    output = completed.stdout or ""
    marker = "\n__HTTP_STATUS__:"
    url_marker = "\n__URL_EFFECTIVE__:"
    if marker not in output or url_marker not in output:
        raise OSError(completed.stderr.strip() or "curl returned no status marker")
    body, remainder = output.rsplit(marker, 1)
    status_raw, final_url = remainder.split(url_marker, 1)
    status_code = int(status_raw.strip().splitlines()[0])
    final_url = final_url.strip().splitlines()[0]
    if completed.returncode != 0 or status_code >= 400:
        raise OSError(completed.stderr.strip() or f"curl HTTP {status_code}")
    return status_code, body, final_url


def resolve_company(query: str, timeout: int = 12) -> dict[str, Any]:
    url = f"{KIND_BASE}/common/stockisu.do?method=akcIsuName&q={urlencode({'q': query})[2:]}"
    try:
        status, body, final_url = _read_url(url, timeout)
        payload = json.loads(body)
    except (HTTPError, URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return {
            "query": query,
            "access_status": "blocked",
            "status_code": None,
            "url": url,
            "company": None,
            "candidates": [],
            "error": str(exc),
        }

    candidates = payload.get("resultList", []) if isinstance(payload, dict) else []
    selected = _select_company_candidate(query, candidates)
    company = None
    if selected:
        company = KindCompany(
            query=query,
            name=selected.get("isuKorAbbrv", "") or selected.get("isuKorNm", ""),
            short_code=selected.get("isuSrtCd", ""),
            rep_isu_srt_cd=f"A{selected.get('isuSrtCd', '')}",
            isu_cd=selected.get("isuCd", ""),
            market_type=str(selected.get("spotIsuTrdMktTpCd", "")),
            industry=selected.get("grpNm", ""),
        )
    return {
        "query": query,
        "access_status": "ok" if company else "partial",
        "status_code": status,
        "url": final_url,
        "company": asdict(company) if company else None,
        "candidates": candidates[:10],
        "error": "" if company else "No KIND company candidate found.",
    }


def _select_company_candidate(query: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    compact_query = query.replace(" ", "").lower()
    for candidate in candidates:
        names = [
            str(candidate.get("isuKorAbbrv", "")),
            str(candidate.get("isuKorNm", "")),
            str(candidate.get("isuSrtCd", "")),
        ]
        if any(compact_query == item.replace(" ", "").lower() for item in names):
            return candidate
    return candidates[0] if candidates else None


def parse_disclosure_rows(page: str) -> list[KindDisclosure]:
    disclosures: list[KindDisclosure] = []
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, flags=re.DOTALL | re.IGNORECASE):
        viewer_match = re.search(r"openDisclsViewer\('([^']*)'\s*,\s*'([^']*)'\)", row)
        if not viewer_match:
            continue
        acpt_no, doc_no = viewer_match.groups()
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE)
        normalized_cells = [_normalize(cell) for cell in cells]
        company = _first_match(r"id=[\"']companysum[\"'][^>]*title=['\"]([^'\"]+)['\"]", row)
        company_code = _first_match(r"companysummary_open\('([^']+)'\)", row)
        market = _first_match(r"class=['\"]vmiddle legend['\"][^>]*alt=['\"]([^'\"]+)['\"]", row)
        title = _first_match(r"openDisclsViewer\('[^']*'\s*,\s*'[^']*'\)[^>]*title=['\"]([^'\"]+)['\"]", row)
        if not title:
            title = normalized_cells[3] if len(normalized_cells) >= 5 else normalized_cells[2] if len(normalized_cells) >= 3 else ""
        submitted_at = _find_datetime(normalized_cells)
        submitter = normalized_cells[4] if len(normalized_cells) >= 5 else normalized_cells[3] if len(normalized_cells) >= 4 else ""
        disclosures.append(
            KindDisclosure(
                acpt_no=acpt_no,
                doc_no=doc_no,
                company=company or (normalized_cells[2] if len(normalized_cells) >= 5 else normalized_cells[1] if len(normalized_cells) >= 2 else ""),
                company_code=company_code,
                submitted_at=submitted_at,
                title=_normalize(title),
                submitter=submitter,
                market=market,
                url=build_viewer_url(acpt_no, doc_no),
            )
        )
    return disclosures


def _first_match(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return html.unescape(match.group(1).strip()) if match else default


def _find_datetime(cells: list[str]) -> str:
    for cell in cells:
        if re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", cell):
            return cell
    for cell in cells:
        if re.fullmatch(r"\d{2}:\d{2}", cell):
            return cell
    return ""


def build_viewer_url(acpt_no: str, doc_no: str = "") -> str:
    params = urlencode({"method": "search", "acptno": acpt_no, "docno": doc_no, "viewerhost": "", "viewerport": ""})
    return f"{KIND_BASE}/common/disclsviewer.do?{params}"


def search_company_disclosures(
    company: str,
    start_date: str,
    end_date: str,
    report_name: str | None = None,
    limit: int = 5,
    timeout: int = 12,
) -> dict[str, Any]:
    resolution = resolve_company(company, timeout)
    resolved = resolution.get("company") or {}
    if not resolved.get("rep_isu_srt_cd"):
        return {
            "request": {
                "company": company,
                "start_date": start_date,
                "end_date": end_date,
                "report_name": report_name,
                "limit": limit,
                "method": "kind_company_public_web",
            },
            "access_status": "blocked",
            "company_resolution": resolution,
            "disclosures": [],
            "error": resolution.get("error", "KIND company resolution failed."),
        }

    form: dict[str, Any] = {
        "method": "searchDisclosureByCorpSub",
        "forward": "searchdisclosurebycorp_sub",
        "searchCorpName": resolved.get("name") or company,
        "searchCodeType": "char",
        "repIsuSrtCd": resolved["rep_isu_srt_cd"],
        "fromDate": _kind_date(start_date),
        "toDate": _kind_date(end_date),
        "currentPageSize": max(limit, 15),
        "pageIndex": 1,
        "orderIndex": 1,
        "orderMode": 1,
        "orderStat": "D",
    }
    if report_name:
        compact_report_name = report_name.replace(" ", "")
        form["reportNm"] = compact_report_name
        form["reportNmTemp"] = report_name
    url = f"{KIND_BASE}/disclosure/searchdisclosurebycorp.do"
    try:
        status, page, final_url = _read_url(
            url,
            timeout,
            form,
            referer=f"{KIND_BASE}/disclosure/searchdisclosurebycorp.do?method=searchDisclosureByCorpMain",
        )
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        return {
            "request": {
                "company": company,
                "start_date": start_date,
                "end_date": end_date,
                "report_name": report_name,
                "limit": limit,
                "method": "kind_company_public_web",
            },
            "access_status": "blocked",
            "company_resolution": resolution,
            "disclosures": [],
            "error": str(exc),
        }
    disclosures = parse_disclosure_rows(page)[:limit]
    return {
        "request": {
            "company": company,
            "start_date": start_date,
            "end_date": end_date,
            "report_name": report_name,
            "limit": limit,
            "method": "kind_company_public_web",
            "status_code": status,
        },
        "access_status": "ok" if disclosures else "partial",
        "company_resolution": resolution,
        "url": final_url,
        "disclosures": [asdict(item) for item in disclosures],
        "error": "" if disclosures else "No matching KIND disclosures found.",
    }


def search_today_disclosures(limit: int = 10, timeout: int = 12) -> dict[str, Any]:
    form: dict[str, Any] = {
        "method": "searchTodayDisclosureSub",
        "forward": "todaydisclosure_sub",
        "currentPageSize": max(limit, 15),
        "pageIndex": 1,
        "orderIndex": 1,
        "orderMode": 1,
        "orderStat": "D",
    }
    url = f"{KIND_BASE}/disclosure/todaydisclosure.do"
    try:
        status, page, final_url = _read_url(
            url,
            timeout,
            form,
            referer=f"{KIND_BASE}/disclosure/todaydisclosure.do?method=searchTodayDisclosureMain",
        )
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        return {
            "request": {"limit": limit, "method": "kind_today_public_web"},
            "access_status": "blocked",
            "disclosures": [],
            "error": str(exc),
        }
    disclosures = parse_disclosure_rows(page)[:limit]
    return {
        "request": {"limit": limit, "method": "kind_today_public_web", "status_code": status},
        "access_status": "ok" if disclosures else "partial",
        "url": final_url,
        "disclosures": [asdict(item) for item in disclosures],
        "error": "" if disclosures else "No KIND today disclosures found.",
    }


def _kind_date(value: str) -> str:
    value = str(value)
    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def fetch_disclosure_document(
    acpt_no: str,
    doc_no: str = "",
    timeout: int = 12,
    max_tables: int = 12,
    max_rows: int = 20,
) -> dict[str, Any]:
    viewer_url = build_viewer_url(acpt_no, doc_no)
    try:
        status, viewer_page, final_viewer_url = _read_url(viewer_url, timeout)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        return {
            "acpt_no": acpt_no,
            "doc_no": doc_no,
            "access_status": "blocked",
            "status_code": None,
            "viewer_url": viewer_url,
            "content_url": "",
            "parsed": {},
            "error": str(exc),
        }
    title = _first_match(r"<title>(.*?)</title>", viewer_page)
    selected_doc_no = doc_no or _selected_doc_no(viewer_page)
    if not selected_doc_no:
        return {
            "acpt_no": acpt_no,
            "doc_no": doc_no,
            "access_status": "partial",
            "status_code": status,
            "viewer_url": final_viewer_url,
            "content_url": "",
            "parsed": {},
            "error": "No KIND main document number was detected.",
        }
    content_route = f"{KIND_BASE}/common/disclsviewer.do"
    try:
        _contents_status, contents_page, _contents_url = _read_url(
            content_route,
            timeout,
            {"method": "searchContents", "docNo": selected_doc_no},
            referer=final_viewer_url,
        )
        content_url = _content_url_from_set_path(contents_page)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        return {
            "acpt_no": acpt_no,
            "doc_no": selected_doc_no,
            "access_status": "blocked",
            "status_code": status,
            "viewer_url": final_viewer_url,
            "content_url": "",
            "parsed": {},
            "error": str(exc),
        }
    if not content_url:
        return {
            "acpt_no": acpt_no,
            "doc_no": selected_doc_no,
            "access_status": "partial",
            "status_code": status,
            "viewer_url": final_viewer_url,
            "content_url": "",
            "parsed": {},
            "error": "No KIND external content URL was detected.",
        }

    parsed = parse_filing_target(content_url, timeout=timeout, max_tables=max_tables, max_rows=max_rows)
    parsed["retrieval_method"] = "kind_external_html"
    if title and not parsed.get("title"):
        parsed["title"] = title
    return {
        "acpt_no": acpt_no,
        "doc_no": selected_doc_no,
        "access_status": parsed.get("access_status", "partial"),
        "status_code": status,
        "viewer_url": final_viewer_url,
        "content_url": content_url,
        "parsed": parsed,
        "error": parsed.get("error", ""),
    }


def _selected_doc_no(viewer_page: str) -> str:
    selected = re.search(r"<option\s+value=['\"]([^'\"]+)\|[^'\"]*['\"][^>]*selected", viewer_page, flags=re.IGNORECASE)
    if selected:
        return selected.group(1)
    first = re.search(r"<option\s+value=['\"](\d+)(?:\|[^'\"]*)?['\"]", viewer_page, flags=re.IGNORECASE)
    return first.group(1) if first else ""


def _content_url_from_set_path(contents_page: str) -> str:
    match = re.search(r"setPath\('([^']*)'\s*,\s*'([^']*)'", contents_page)
    if not match:
        return ""
    return html.unescape(match.group(2).strip())


def _source_from_disclosure(disclosure: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "disclosure",
        "name": f"KIND {disclosure.get('company', '')} {disclosure.get('title', '')}".strip(),
        "url": disclosure.get("url", ""),
        "access_status": "ok",
        "retrieval_method": "kind_public_search",
        "claims": [
            f"acpt_no={disclosure.get('acpt_no')} submitted_at={disclosure.get('submitted_at')}",
            f"submitter={disclosure.get('submitter')}",
        ],
        "numeric_facts": [],
        "caveats": ["KIND public disclosure search result; no API key used."],
        "kind": disclosure,
    }


def build_kind_public_bundle(config: dict[str, Any], timeout: int = 12) -> dict[str, Any]:
    mode = config.get("mode", "company" if config.get("company") else "today")
    if mode == "today":
        search = search_today_disclosures(limit=int(config.get("limit", config.get("max_reports", 5))), timeout=timeout)
    else:
        search = search_company_disclosures(
            company=config["company"],
            start_date=str(config.get("start_date", config.get("startDate", "2026-01-01"))),
            end_date=str(config.get("end_date", config.get("endDate", "2026-12-31"))),
            report_name=config.get("report_name", config.get("reportName")),
            limit=int(config.get("limit", config.get("max_reports", 3))),
            timeout=timeout,
        )

    sources: list[dict[str, Any]] = []
    disclosures_payload = search.get("disclosures", [])
    for disclosure in disclosures_payload:
        source = _source_from_disclosure(disclosure)
        sources.append(source)
        if not config.get("fetch_documents", True):
            continue
        document = fetch_disclosure_document(
            disclosure["acpt_no"],
            disclosure.get("doc_no", ""),
            timeout=timeout,
            max_tables=int(config.get("max_tables", 12)),
            max_rows=int(config.get("max_rows", 20)),
        )
        source["kind_document"] = {
            "doc_no": document.get("doc_no", ""),
            "content_url": document.get("content_url", ""),
            "access_status": document.get("access_status", ""),
            "error": document.get("error", ""),
        }
        parsed = document.get("parsed") or {}
        if parsed:
            parsed["retrieval_method"] = "kind_external_html"
            parsed["title"] = parsed.get("title") or disclosure.get("title", "")
            parsed_source = filing_to_source(parsed, "disclosure")
            parsed_source["name"] = f"KIND original HTML: {parsed_source.get('name', disclosure.get('title', ''))}"
            parsed_source.setdefault("caveats", []).append("Extracted from KIND original disclosure external HTML.")
            parsed_source["kind_document"] = document
            sources.append(parsed_source)

    return {
        "request": search.get("request", {}),
        "access_status": search.get("access_status", "blocked"),
        "company_resolution": search.get("company_resolution"),
        "disclosures": disclosures_payload,
        "sources": sources,
        "error": search.get("error", ""),
    }


def dump_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
