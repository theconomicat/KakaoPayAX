# Third-Party Notices

## insane-search

Reference:

- https://github.com/fivetaku/insane-search
- License: MIT

This submission does not copy or fork `insane-search` code. It only takes architectural inspiration from the public-source-first retrieval idea: try lightweight public access first, use metadata, public endpoints, feed/mobile/JSON variants, browser-shaped requests, optional TLS/browser rendering where locally available, and stop at login/paywall/CAPTCHA/authentication boundaries.

If any code is copied from `insane-search` in a future version, the MIT license notice must be included.

## Optional Python Libraries

The current demo path has no required third-party Python dependencies.

Optional future live adapters may use:

- `yfinance`: https://github.com/ranaroussi/yfinance
- `FinanceDataReader`: https://github.com/FinanceData/FinanceDataReader
- `ta`: https://github.com/bukosabino/ta

These must remain optional unless their licenses and data-source terms are reviewed for the exact submission use case.

## Open-Source Financial Agent References

The current submission does not copy code from the following projects. They were reviewed as public design references for workflow shape, source separation, role-based analysis, and evidence tracking:

- FinRobot: https://github.com/AI4Finance-Foundation/FinRobot
- Dexter: https://github.com/virattt/dexter
- Anthropic financial-services: https://github.com/anthropics/financial-services
- TradingAgents: https://github.com/TauricResearch/TradingAgents
- OpenBB: https://github.com/OpenBB-finance/OpenBB
- SEC-API Python: https://github.com/SEC-API-io/sec-api-python
- sec-edgar-agentkit: https://github.com/stefanoamorelli/sec-edgar-agentkit
- AlphaAnalyst: https://github.com/kbhujbal/AlphaAnalyst-open-source-autonomous-equity-research-agent
- EdgarTools: https://github.com/dgunning/edgartools

Patterns adopted without copying code:

- keep news, filings, financial statements, indices, and technical signals as separate source families;
- preserve source URLs, retrieval method, access status, and caveats;
- use role-focused workflows instead of one monolithic answer;
- keep tool execution outputs inspectable before memo drafting;
- add an evidence-quality checklist before memo drafting;
- treat source packet generation as the primary artifact and memo generation as secondary.

## Byul.ai Public API

This plugin can read public Byul.ai endpoints for market news, economic calendar, earnings-watch context, and market sentiment/volatility indices.

Base URL used by the deployed service:

- https://api.byul.ai/api/v1

No Byul API key is included in this submission.

## The Econmicat

- Website: https://www.theconomicat.com/
- Use: public finance-source directory used as a live catalog for finding candidate public sources.
- Notes: no website code is copied. The plugin reads public links and records access status for selected sources only.

## Optional Playwright

`tools/playwright_probe.mjs` can use Playwright if it is installed. It is optional and must not be used to bypass login, paywalls, CAPTCHA, or access controls.
