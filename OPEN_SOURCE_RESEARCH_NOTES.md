# Open-Source Financial Agent Research Notes

Date: 2026-07-01

This document records public open-source references reviewed while strengthening KPS Analyst Workbench. No source code was copied or forked from these projects.

## Reviewed References

- FinRobot: https://github.com/AI4Finance-Foundation/FinRobot
  - Pattern considered: financial analyst workflows as reusable agent tasks.
  - Adopted idea: separate data gathering, analysis, and report generation.

- Dexter: https://github.com/virattt/dexter
  - Pattern considered: autonomous financial research with task planning, tool execution, self-validation, loop limits, and scratchpad logging.
  - Adopted idea: keep collection steps explicit, preserve tool outputs, and verify source completeness before drafting.

- Anthropic financial-services reference agents: https://github.com/anthropics/financial-services
  - Pattern considered: financial-services skills and workflow decomposition for equity research, banking, and wealth workflows.
  - Adopted idea: keep focused skills rather than one monolithic prompt.

- TradingAgents: https://github.com/TauricResearch/TradingAgents
  - Pattern considered: role-based analyst/risk/research agents.
  - Adopted idea: keep role-focused skills and separate evidence from final memo.

- OpenBB: https://github.com/OpenBB-finance/OpenBB
  - Pattern considered: broad public investment research terminal with many data providers.
  - Adopted idea: treat data adapters as replaceable source families.

- SEC-API Python: https://github.com/SEC-API-io/sec-api-python
  - Pattern considered: normalized SEC/EDGAR filings and financial statements as structured API data.
  - Adopted idea: optional API path should return structured rows and status metadata.

- sec-edgar-agentkit: https://github.com/stefanoamorelli/sec-edgar-agentkit
  - Pattern considered: agent-oriented SEC filing access.
  - Adopted idea: filing access should be a dedicated tool, not hidden inside LLM prompt text.

- AlphaAnalyst: https://github.com/kbhujbal/AlphaAnalyst-open-source-autonomous-equity-research-agent
  - Pattern considered: analyst memo pipelines with financials, comps, news, and earnings.
  - Adopted idea: include earnings-watch and news context, but keep recommendation language out.

- stock-brief: https://github.com/SahilBacchus/stock-brief
  - Pattern considered: specialized agents synthesizing market data, SEC filings, and financial news.
  - Adopted idea: source families are gathered separately and joined in a final packet.

- financial-research-agent: https://github.com/smadinen7/financial-research-agent
  - Pattern considered: multi-step RAG pipeline for SEC filings and news.
  - Adopted idea: preserve retrieved evidence and make gaps explicit before thesis writing.

- EdgarTools: https://github.com/dgunning/edgartools
  - Pattern considered: structured access to filings, financial statements, and filing metadata.
  - Adopted idea: financial-statement extraction should return rows, periods, source URLs, and caveats instead of a prose-only summary.

- Reddit/community examples of financial research agents:
  - https://www.reddit.com/r/algotrading/comments/1l82has/ive_built_an_automated_research_agent_for_stock/
  - https://www.reddit.com/r/ValueInvesting/comments/1m7pyim/built_a_focused_ai_agent_for_sec_filings_not/
  - Pattern considered: users value multi-source pull, cross-checking, official filings, and citations more than shallow generic answers.
  - Adopted idea: the primary product should be a source packet and verification trail, not only a final narrative.

- insane-search: https://github.com/fivetaku/insane-search
  - Pattern considered: Phase 0 to Phase 3 public-source access escalation, including official/public endpoints, feed/mobile/JSON variants, browser-shaped requests, TLS impersonation when available, Playwright rendering, and clear stop conditions for login/paywall/CAPTCHA.
  - Adopted idea: public retrieval should keep trying lawful public routes before giving up, and every attempt should be visible in a trace.

## Implemented Changes Inspired By The Review

- Added `tools/collectors/dart_public.py` and `tools/dart_public_client.py` for no-key DART public search, report viewer section discovery, and OpenDART XBRL viewer fact-table extraction.
- Added `tools/collectors/kind_public.py` and `tools/kind_public_client.py` for no-key KIND company resolution, disclosure search, viewer routing, original external HTML retrieval, and table extraction.
- Added `tools/filing_parser.py` for DART/KIND/company filing text, table, and financial-row extraction.
- Added `tools/byul_client.py` for Byul public news, economic calendar, earnings-watch, and sentiment/volatility indices.
- Added `tools/source_catalog.py` to search The Econmicat public finance-tool directory and route Codex to sources such as Yahoo Finance, Unusual Whales, SEC EDGAR, FRED, Finviz, OpenInsider, Macrotrends, and Stock Analysis only when needed.
- Upgraded `tools/market_data_reader.py` so Yahoo Finance public chart data works without `yfinance` or API keys where the endpoint is publicly accessible.
- Upgraded `tools/public_page_reader.py` from a single direct `urllib` read into an adaptive public reader: desktop/mobile browser headers, mobile/RSS/feed/JSON/Jina Reader URL variants, optional `curl_cffi` TLS impersonation if locally installed, optional Playwright rendering, and per-attempt trace metadata.
- Upgraded `tools/playwright_probe.mjs` to use a realistic browser context and record public JSON/RSS/API network candidates for later selective reading.
- Split collector/parsing organization into `tools/collectors/` and `tools/parsers/` while keeping stable root CLI entrypoints.
- Added `Evidence Quality Checklist` before memo drafting.
- Added `Filing Table Extraction` and `Byul Market Intelligence` sections to the packet.
- Kept investment recommendations, target prices, and personalized advice out of the workflow.

## Access Strategy

The access strategy follows a public-source-first pattern similar in spirit to `insane-search`, without copying its code:

1. Try official public webpages or public endpoints where available.
2. Read direct public URLs with normal browser-shaped headers.
3. Try no-auth public variants such as mobile URLs, RSS/feed URLs, `.json` suffixes, and Jina Reader when appropriate.
4. Use optional `curl_cffi` only for normal browser TLS impersonation if the package is locally available.
5. Extract visible text, filing tables, XBRL viewer fact tables, OGP/JSON-LD-style page text, and public network candidates.
6. Use optional Playwright only to render public pages or identify public JSON/RSS/API responses loaded by that page.
7. Stop at login, paywall, CAPTCHA, or authentication boundary and record the failure status.

This makes the tool useful for difficult public financial data without turning it into an access-control bypasser.
