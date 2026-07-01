#!/usr/bin/env python3
"""OpenBB-inspired no-key public source catalog for Codex routing."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import sys


@dataclass(frozen=True)
class PublicProvider:
    name: str
    domain: str
    category: str
    url: str
    access: str
    use_case: str
    local_tool: str
    caveat: str


PROVIDERS = [
    PublicProvider(
        "SEC EDGAR companyfacts",
        "US filings and fundamentals",
        "financials",
        "https://data.sec.gov/api/xbrl/companyfacts/",
        "no_api_key",
        "US-listed company standardized XBRL facts such as revenue, income, assets, liabilities.",
        "tools/sec_edgar_client.py",
        "Requires a respectful User-Agent and public SEC rate limits still apply.",
    ),
    PublicProvider(
        "FRED graph CSV",
        "Macro economy",
        "macro",
        "https://fred.stlouisfed.org/graph/fredgraph.csv",
        "no_api_key",
        "Rates, inflation, unemployment, oil, and other macro time series by public series id.",
        "tools/fred_public_client.py",
        "FRED API needs a key, but graph CSV route is public for common series.",
    ),
    PublicProvider(
        "Yahoo Finance chart",
        "Equity prices",
        "market_data",
        "https://query1.finance.yahoo.com/v8/finance/chart/",
        "no_api_key",
        "Daily OHLCV for Korean and global tickers when Yahoo symbols are known.",
        "tools/market_data_reader.py",
        "Unofficial public endpoint; can change or block traffic.",
    ),
    PublicProvider(
        "Ken French Data Library",
        "Factor research",
        "factor_data",
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
        "no_api_key",
        "Academic factor returns and benchmark portfolios for valuation/risk context.",
        "tools/public_page_reader.py",
        "Dataset files require source-specific parsing if used beyond page discovery.",
    ),
    PublicProvider(
        "Finviz",
        "US screener and market map",
        "market_data",
        "https://finviz.com/",
        "no_api_key",
        "US equity screener, sector heatmap, and quick market snapshot.",
        "tools/public_page_reader.py",
        "Use only public visible content; do not bypass login or premium gates.",
    ),
    PublicProvider(
        "FINRA public data",
        "US market regulation",
        "regulatory",
        "https://www.finra.org/finra-data",
        "no_api_key_or_free_registration",
        "Short interest, OTC, margin, and regulatory datasets depending on endpoint.",
        "tools/public_page_reader.py",
        "Some datasets may require portal flow or registered access.",
    ),
    PublicProvider(
        "Deribit public market data",
        "Crypto derivatives",
        "derivatives",
        "https://docs.deribit.com/",
        "no_api_key_for_public_market_data",
        "Crypto options/futures market data where public endpoints are enough.",
        "tools/public_page_reader.py",
        "Trading/account endpoints are not used.",
    ),
    PublicProvider(
        "IMF Data",
        "Global macro",
        "macro",
        "https://www.imf.org/en/Data",
        "no_api_key",
        "Country-level macro datasets for global economy context.",
        "tools/public_page_reader.py",
        "Endpoint formats vary by dataset.",
    ),
]


def search_providers(query: str = "", category: str = "", limit: int = 20) -> list[dict[str, str]]:
    terms = [term.lower() for term in query.split() if term.strip()]
    category_term = category.lower().strip()
    results = []
    for provider in PROVIDERS:
        haystack = " ".join(
            [
                provider.name,
                provider.domain,
                provider.category,
                provider.url,
                provider.use_case,
                provider.local_tool,
            ]
        ).lower()
        if category_term and category_term not in provider.category.lower():
            continue
        if terms and not any(term in haystack for term in terms):
            continue
        results.append(asdict(provider))
    return results[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="")
    parser.add_argument("--category", default="")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    payload = {
        "source_model": "OpenBB-inspired provider routing; no OpenBB code copied.",
        "access_policy": "Prefer no-key public endpoints and stop at login, paywall, CAPTCHA, or registered/private access.",
        "providers": search_providers(args.query, args.category, args.limit),
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
