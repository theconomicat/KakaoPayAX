---
name: financial-snapshot-analyst
description: Analyze revenue, profitability, balance sheet, cash flow, and source-backed financial facts for research packets without issuing investment advice.
---

# Financial Snapshot Analyst

Use this skill when a research packet includes revenue, operating profit, net income, margins, debt, equity, cash flow, or segment facts.

## Work

1. Identify reporting period and data source.
2. Extract key metrics.
3. Compute simple deltas and margins only when the denominator is present.
4. Flag unusual combinations such as revenue growth with margin compression, profit growth with cash flow deterioration, or leverage expansion.
5. Record unknowns explicitly.

## Output

Use concise bullets:

- Metric
- Current value
- Prior value if available
- Direction
- Why it matters
- Source

## Guardrails

- Do not overfit one quarter.
- Do not call a stock cheap or expensive without a clearly sourced valuation basis.
- Do not invent missing numbers.
- If data is fixture data, label it as demo/sample.

