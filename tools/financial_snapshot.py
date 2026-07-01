#!/usr/bin/env python3
"""Financial snapshot helper for research packets."""
from __future__ import annotations

from typing import Any


def percent_change(current: float | int | None, prior: float | int | None) -> float | None:
    if current is None or prior in (None, 0):
        return None
    return (float(current) - float(prior)) / abs(float(prior)) * 100


def ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def summarize_financials(financials: dict[str, Any]) -> dict[str, Any]:
    current = financials.get("current", {})
    prior = financials.get("prior", {})
    revenue = current.get("revenue")
    operating_profit = current.get("operating_profit")
    net_income = current.get("net_income")
    equity = current.get("equity")
    liabilities = current.get("liabilities")
    summary = {
        "currency": financials.get("currency", ""),
        "period": current.get("period", ""),
        "source": financials.get("source", "unknown"),
        "revenue_change_pct": percent_change(revenue, prior.get("revenue")),
        "operating_profit_change_pct": percent_change(
            operating_profit, prior.get("operating_profit")
        ),
        "net_income_change_pct": percent_change(net_income, prior.get("net_income")),
        "operating_margin": ratio(operating_profit, revenue),
        "net_margin": ratio(net_income, revenue),
        "debt_to_equity": ratio(liabilities, equity),
        "notes": [],
    }
    notes: list[str] = []
    if summary["revenue_change_pct"] is not None and summary["operating_profit_change_pct"] is not None:
        if summary["revenue_change_pct"] > 0 and summary["operating_profit_change_pct"] < 0:
            notes.append("Revenue grew while operating profit declined; check margin pressure.")
    if summary["debt_to_equity"] is not None and summary["debt_to_equity"] > 1.0:
        notes.append("Liabilities exceed equity; review balance sheet risk and industry norms.")
    if not notes:
        notes.append("No automatic red-flag combination found in the supplied snapshot.")
    summary["notes"] = notes
    return summary

