---
name: public-source-researcher
description: Gather and classify public web, news, filing, IR, and market sources for analyst research packets while recording access status and source quality.
---

# Public Source Researcher

Use this skill to gather or organize source material before analysis.

## Source Priority

1. Official company IR, exchange, regulator, DART, KIND, SEC, and press releases.
2. Reputable news and industry publications.
3. Market data pages such as Yahoo Finance, exchange pages, or Investing.com when public.
4. Community or unsourced pages only as weak context, never as primary evidence.

## Retrieval Policy

- Start with provided URLs and sample fixtures.
- Use public fetch methods first: direct browser-shaped requests, official public endpoints, mobile/RSS/feed/JSON variants, and public reader conversions where appropriate.
- For broad financial websites, use `tools/source_catalog.py` to find relevant candidates from The Econmicat, then fetch only the needed URLs.
- Use `tools/openbb_public_sources.py` to find no-key provider candidates such as SEC EDGAR, FRED, Yahoo, Ken French, Finviz, FINRA, Deribit, and IMF. This follows OpenBB's provider-routing idea without copying OpenBB code.
- When a selected catalog source needs a second step, use `tools/source_deep_probe.py` for a bounded loop: page probe, public network candidate discovery, and public JSON/RSS/API follow-up.
- For DART, prefer public disclosure search, report viewer sections, and OpenDART XBRL viewer fact tables before general web scraping.
- For KIND, prefer public company autocomplete, company disclosure search, viewer routing, and original external HTML before general web scraping.
- For US companies, use SEC public ticker lookup and companyfacts. For macro context, use FRED public graph CSV where possible.
- Use Playwright only for public rendering or network reconnaissance, and only after lighter public routes are insufficient.
- Stop at login, paywall, CAPTCHA, access denial, or terms ambiguity.
- Record access status instead of pretending a failed source was read.

## Classification

Classify each source as:

- `news`
- `disclosure`
- `financials`
- `market_data`
- `technical_signal`
- `ir`
- `analyst_reference`
- `company_background`
- `unknown`

For each source, capture:

- source name
- URL
- publication or filing date if available
- access status
- retrieval method
- extracted claims
- numeric facts
- caveats
