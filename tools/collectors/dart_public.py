"""Collect DART disclosure reports and XBRL fact tables without API keys."""
from __future__ import annotations

from dataclasses import dataclass, asdict
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


DART_BASE = "https://dart.fss.or.kr"
OPENDART_BASE = "https://opendart.fss.or.kr"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

FINANCIAL_TOC_TERMS = [
    "요약재무정보",
    "연결 재무상태표",
    "연결 손익계산서",
    "연결 포괄손익계산서",
    "연결 자본변동표",
    "연결 현금흐름표",
    "재무상태표",
    "손익계산서",
    "포괄손익계산서",
    "자본변동표",
    "현금흐름표",
]

XBRL_ROLE_TERMS = [
    "재무상태표",
    "손익계산서",
    "포괄손익계산서",
    "현금흐름표",
    "자본변동표",
]


@dataclass
class DartReport:
    company: str
    corp_code: str
    report_name: str
    rcp_no: str
    filing_date: str
    filer: str
    url: str
    xbrl_available: bool
    xbrl_url: str


@dataclass
class DartDocument:
    title: str
    rcp_no: str
    dcm_no: str
    ele_id: str
    offset: str
    length: str
    dtd: str
    url: str
    source_family: str = "dart_report_viewer"


@dataclass
class XbrlRole:
    title: str
    xbrl_ext_seq: str
    role_id: str
    lang: str
    role_code: str
    url: str
    source_family: str = "opendart_xbrl_viewer"


def _normalize(value: str, limit: int = 1000) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def _read_url(url: str, timeout: int = 12, data: dict[str, Any] | None = None) -> tuple[int, str, str]:
    encoded = None
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/json"}
    if data is not None:
        encoded = urlencode({key: str(value) for key, value in data.items() if value is not None}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["Referer"] = f"{DART_BASE}/dsab007/main.do"
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = Request(url, data=encoded, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public DART pages
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(5_000_000)
            return response.status, raw.decode(charset, errors="replace"), response.url
    except (HTTPError, URLError, OSError, TimeoutError):
        return _read_url_with_curl(url, timeout, encoded.decode("utf-8") if encoded else None)


def _read_url_with_curl(url: str, timeout: int, encoded_body: str | None = None) -> tuple[int, str, str]:
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
                "-H",
                f"Referer: {DART_BASE}/dsab007/main.do",
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


def _first_match(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else default


def parse_search_results(page: str, report_name: str | None = None) -> list[DartReport]:
    reports: list[DartReport] = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.DOTALL | re.IGNORECASE):
        if "rcpNo=" not in row:
            continue
        rcp_no = _first_match(r"rcpNo=(\d+)", row)
        if not rcp_no:
            continue
        corp_code = _first_match(r"openCorpInfoNew\('([^']+)'", row)
        links = re.findall(r"<a\b[^>]*>(.*?)</a>", row, flags=re.DOTALL | re.IGNORECASE)
        company = _normalize(links[0]) if links else ""
        title = _normalize(links[1]) if len(links) > 1 else _first_match(r'title="([^"]*?) 공시뷰어', row)
        if report_name and report_name not in title:
            continue
        td_values = [_normalize(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE)]
        filer = td_values[3] if len(td_values) > 3 else company
        filing_date = _first_match(r"<td>\s*(\d{4}\.\d{2}\.\d{2})\s*</td>", row)
        xbrl_available = "openXbrlViewerNew" in row and re.search(r"openXbrlViewerNew\([^)]*'Y'", row) is not None
        reports.append(
            DartReport(
                company=company,
                corp_code=corp_code,
                report_name=title,
                rcp_no=rcp_no,
                filing_date=filing_date,
                filer=filer,
                url=f"{DART_BASE}/dsaf001/main.do?rcpNo={rcp_no}",
                xbrl_available=xbrl_available,
                xbrl_url=f"{OPENDART_BASE}/xbrl/viewer/main.do?rcpNo={rcp_no}" if xbrl_available else "",
            )
        )
    return reports


def search_reports(
    company: str,
    start_date: str,
    end_date: str,
    report_name: str | None = "사업보고서",
    limit: int = 5,
    timeout: int = 12,
) -> dict[str, Any]:
    form = {
        "currentPage": 1,
        "maxResults": max(limit, 10),
        "maxLinks": 10,
        "sort": "date",
        "series": "desc",
        "textCrpNm": company,
        "startDate": start_date,
        "endDate": end_date,
        "finalReport": "recent",
        "publicType": ["A001", "A002", "A003"],
    }
    flat_form = {key: value for key, value in form.items() if not isinstance(value, list)}
    encoded = urlencode(flat_form) + "".join(f"&publicType={item}" for item in form["publicType"])
    url = f"{DART_BASE}/dsab007/detailSearch.ax"
    request = Request(
        url,
        data=encoded.encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{DART_BASE}/dsab007/main.do",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public DART search page
            page = response.read(5_000_000).decode("utf-8", errors="replace")
            status_code = response.status
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        try:
            status_code, page, _final_url = _read_url_with_curl(url, timeout, encoded)
        except (OSError, ValueError) as fallback_exc:
            return {
                "request": {
                    "company": company,
                    "start_date": start_date,
                    "end_date": end_date,
                    "report_name": report_name,
                    "limit": limit,
                    "method": "dart_detailSearch_public_web",
                },
                "access_status": "blocked",
                "reports": [],
                "error": f"{exc}; curl fallback failed: {fallback_exc}",
            }
    reports = parse_search_results(page, report_name)[:limit]
    return {
        "request": {
            "company": company,
            "start_date": start_date,
            "end_date": end_date,
            "report_name": report_name,
            "limit": limit,
            "method": "dart_detailSearch_public_web",
            "status_code": status_code,
        },
        "access_status": "ok" if reports else "partial",
        "reports": [asdict(report) for report in reports],
        "error": "" if reports else "No matching public DART reports found.",
    }


def parse_report_toc(page: str, rcp_no: str) -> list[DartDocument]:
    nodes: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in page.splitlines():
        if re.search(r"var\s+node\d+\s*=\s*\{\};", line):
            if current and current.get("text") and current.get("dcmNo"):
                nodes.append(current)
            current = {}
            continue
        if current is None:
            continue
        match = re.search(r"node\d+\['([^']+)'\]\s*=\s*\"([^\"]*)\";", line)
        if match:
            current[match.group(1)] = html.unescape(match.group(2)).strip()
    if current and current.get("text") and current.get("dcmNo"):
        nodes.append(current)

    documents = []
    seen: set[tuple[str, str, str]] = set()
    for node in nodes:
        title = _normalize(node.get("text", ""))
        if not title:
            continue
        key = (node.get("dcmNo", ""), node.get("eleId", ""), node.get("offset", ""))
        if key in seen:
            continue
        seen.add(key)
        if not node.get("rcpNo"):
            node["rcpNo"] = rcp_no
        if not all(node.get(field) for field in ["rcpNo", "dcmNo", "eleId", "offset", "length", "dtd"]):
            continue
        documents.append(
            DartDocument(
                title=title,
                rcp_no=node["rcpNo"],
                dcm_no=node["dcmNo"],
                ele_id=node["eleId"],
                offset=node["offset"],
                length=node["length"],
                dtd=node["dtd"],
                url=build_viewer_url(node),
            )
        )
    return documents


def build_viewer_url(node: dict[str, str]) -> str:
    params = urlencode(
        {
            "rcpNo": node["rcpNo"],
            "dcmNo": node["dcmNo"],
            "eleId": node["eleId"],
            "offset": node["offset"],
            "length": node["length"],
            "dtd": node["dtd"],
        }
    )
    return f"{DART_BASE}/report/viewer.do?{params}"


def financial_document_score(document: DartDocument) -> int:
    title = document.title.replace(" ", "")
    score = 0
    for term in FINANCIAL_TOC_TERMS:
        if term.replace(" ", "") in title:
            score += 10
    if "주석" in title:
        score -= 8
    if "연결" in title:
        score += 2
    if "요약" in title:
        score += 1
    return score


def select_financial_documents(documents: list[DartDocument], max_documents: int = 6) -> list[DartDocument]:
    candidates = [document for document in documents if financial_document_score(document) > 0]
    candidates.sort(key=_financial_document_sort_key)
    selected: list[DartDocument] = []
    seen_categories: set[str] = set()
    for document in candidates:
        category = financial_document_category(document.title)
        if category and category not in seen_categories:
            selected.append(document)
            seen_categories.add(category)
        if len(selected) >= max_documents:
            return selected
    for document in candidates:
        if document not in selected:
            selected.append(document)
        if len(selected) >= max_documents:
            return selected
    return selected


def _financial_document_sort_key(document: DartDocument) -> tuple[int, int, int, int]:
    return (
        financial_document_priority(document.title),
        0 if "연결" in document.title else 1,
        -financial_document_score(document),
        int(document.ele_id) if document.ele_id.isdigit() else 9999,
    )


def financial_document_priority(title: str) -> int:
    category = financial_document_category(title)
    order = ["balance_sheet", "income_statement", "comprehensive_income", "cash_flow", "equity_changes", "summary"]
    return order.index(category) if category in order else 99


def financial_document_category(title: str) -> str:
    compact = title.replace(" ", "")
    checks = [
        ("재무상태표", "balance_sheet"),
        ("포괄손익계산서", "comprehensive_income"),
        ("손익계산서", "income_statement"),
        ("현금흐름표", "cash_flow"),
        ("자본변동표", "equity_changes"),
        ("요약재무정보", "summary"),
    ]
    for term, category in checks:
        if term in compact:
            return category
    return ""


def fetch_report_documents(rcp_no: str, timeout: int = 12, max_documents: int = 6) -> dict[str, Any]:
    url = f"{DART_BASE}/dsaf001/main.do?rcpNo={rcp_no}"
    try:
        status, page, final_url = _read_url(url, timeout)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        return {
            "rcp_no": rcp_no,
            "access_status": "blocked",
            "status_code": None,
            "report_url": url,
            "documents": [],
            "selected_documents": [],
            "error": str(exc),
        }
    documents = parse_report_toc(page, rcp_no)
    selected = select_financial_documents(documents, max_documents=max_documents)
    return {
        "rcp_no": rcp_no,
        "access_status": "ok" if documents else "partial",
        "status_code": status,
        "report_url": final_url,
        "documents": [asdict(document) for document in documents],
        "selected_documents": [asdict(document) for document in selected],
        "error": "" if documents else "No DART report table of contents was detected.",
    }


def parse_xbrl_roles(page: str) -> list[XbrlRole]:
    roles: list[XbrlRole] = []
    for match in re.finditer(
        r"onclick=\"viewDoc\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)\"[^>]*>(.*?)</a>",
        page,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        xbrl_ext_seq, role_id, lang, role_code, body = match.groups()
        title = _normalize(body)
        if not role_id:
            continue
        params = urlencode({"xbrlExtSeq": xbrl_ext_seq, "roleId": role_id, "lang": lang or "ko"})
        roles.append(
            XbrlRole(
                title=title,
                xbrl_ext_seq=xbrl_ext_seq,
                role_id=role_id,
                lang=lang or "ko",
                role_code=role_code,
                url=f"{OPENDART_BASE}/xbrl/viewer/view.do?{params}",
            )
        )
    return roles


def xbrl_role_score(role: XbrlRole) -> int:
    title = role.title.replace(" ", "")
    score = 0
    for term in XBRL_ROLE_TERMS:
        if term.replace(" ", "") in title:
            score += 10
    if "연결" in title:
        score += 3
    if "주석" in title:
        score -= 8
    return score


def fetch_xbrl_roles(rcp_no: str, timeout: int = 12, max_roles: int = 5) -> dict[str, Any]:
    url = f"{OPENDART_BASE}/xbrl/viewer/main.do?rcpNo={rcp_no}"
    try:
        status, page, final_url = _read_url(url, timeout)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        return {
            "rcp_no": rcp_no,
            "access_status": "blocked",
            "status_code": None,
            "xbrl_url": url,
            "roles": [],
            "selected_roles": [],
            "error": str(exc),
        }
    roles = parse_xbrl_roles(page)
    selected = [role for role in roles if xbrl_role_score(role) > 0]
    selected.sort(key=lambda item: (xbrl_role_priority(item.role_code), -xbrl_role_score(item), item.role_code))
    selected = selected[:max_roles]
    return {
        "rcp_no": rcp_no,
        "access_status": "ok" if roles else "partial",
        "status_code": status,
        "xbrl_url": final_url,
        "roles": [asdict(role) for role in roles],
        "selected_roles": [asdict(role) for role in selected],
        "error": "" if roles else "No OpenDART XBRL roles were detected.",
    }


def xbrl_role_priority(role_code: str) -> int:
    order = [
        "D210000",
        "D310000",
        "D410000",
        "D520000",
        "D610000",
        "D210005",
        "D310005",
        "D410005",
        "D520005",
        "D610005",
    ]
    return order.index(role_code) if role_code in order else 99


def _source_from_parsed_result(result: dict[str, Any], source_type: str, name_prefix: str) -> dict[str, Any]:
    source = filing_to_source(result, source_type)
    source["name"] = f"{name_prefix}: {source.get('name', '')}".strip(": ")
    source["retrieval_method"] = result.get("retrieval_method", source.get("retrieval_method", "dart_public_web"))
    return source


def build_dart_public_bundle(config: dict[str, Any], timeout: int = 12) -> dict[str, Any]:
    search = search_reports(
        company=config["company"],
        start_date=str(config.get("start_date", config.get("startDate", "20250101"))),
        end_date=str(config.get("end_date", config.get("endDate", "20261231"))),
        report_name=config.get("report_name", config.get("reportName", "사업보고서")),
        limit=int(config.get("max_reports", config.get("limit", 1))),
        timeout=timeout,
    )
    sources: list[dict[str, Any]] = []
    reports_payload = []
    for report in search.get("reports", []):
        reports_payload.append(report)
        report_source = {
            "type": "disclosure",
            "name": f"DART {report.get('company')} {report.get('report_name')}",
            "url": report.get("url", ""),
            "access_status": "ok",
            "retrieval_method": "dart_public_search",
            "claims": [
                f"corp_code={report.get('corp_code')} rcp_no={report.get('rcp_no')} filing_date={report.get('filing_date')}",
                f"xbrl_available={report.get('xbrl_available')}",
            ],
            "numeric_facts": [],
            "caveats": ["DART public search result; no OpenDART API key used."],
            "dart": report,
        }
        sources.append(report_source)

        documents = fetch_report_documents(
            report["rcp_no"],
            timeout=timeout,
            max_documents=int(config.get("max_documents", 6)),
        )
        report_source["dart_documents"] = documents.get("selected_documents", [])
        for document in documents.get("selected_documents", []):
            parsed = parse_filing_target(
                document["url"],
                timeout=timeout,
                max_tables=int(config.get("max_tables", 8)),
                max_rows=int(config.get("max_rows", 30)),
            )
            parsed["retrieval_method"] = "dart_report_viewer"
            parsed["title"] = document["title"]
            source = _source_from_parsed_result(parsed, "financials", "DART report viewer")
            source.setdefault("caveats", []).append("Extracted from DART report viewer HTML.")
            source["dart_document"] = document
            sources.append(source)

        if report.get("xbrl_available", False) and config.get("include_xbrl", True):
            xbrl = fetch_xbrl_roles(
                report["rcp_no"],
                timeout=timeout,
                max_roles=int(config.get("max_xbrl_roles", 5)),
            )
            report_source["xbrl_roles"] = xbrl.get("selected_roles", [])
            for role in xbrl.get("selected_roles", []):
                parsed = parse_filing_target(
                    role["url"],
                    timeout=timeout,
                    max_tables=int(config.get("max_tables", 8)),
                    max_rows=int(config.get("max_rows", 30)),
                )
                parsed["retrieval_method"] = "opendart_xbrl_viewer"
                parsed["title"] = role["title"]
                source = _source_from_parsed_result(parsed, "financials", "OpenDART XBRL viewer")
                source.setdefault("caveats", []).append("Extracted from OpenDART XBRL viewer fact-table HTML; no API key used.")
                source["xbrl_role"] = role
                sources.append(source)

    return {
        "request": search.get("request", {}),
        "access_status": search.get("access_status", "blocked"),
        "reports": reports_payload,
        "sources": sources,
        "error": search.get("error", ""),
    }


def dump_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
