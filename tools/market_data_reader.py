#!/usr/bin/env python3
"""No-key public market data adapter.

This tool first tries Yahoo Finance's public chart endpoint. If that fails and
``yfinance`` is installed, it falls back to yfinance. It is not required for demo
mode and it does not require API keys.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def read_yahoo_chart(ticker: str, period: str = "6mo", interval: str = "1d", timeout: int = 12) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}?range={quote(period)}&interval={quote(interval)}"
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 KPSAnalystWorkbench/0.3 "
                "(public Yahoo Finance chart reader)"
            )
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - public market data endpoint
            payload = json.loads(response.read(3_000_000).decode("utf-8", errors="replace"))
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "status": "blocked",
            "provider": "yahoo_chart_public",
            "ticker": ticker,
            "url": url,
            "error": str(exc),
            "prices": [],
        }

    chart = payload.get("chart", {}) if isinstance(payload, dict) else {}
    if chart.get("error"):
        return {
            "status": "blocked",
            "provider": "yahoo_chart_public",
            "ticker": ticker,
            "url": url,
            "error": json.dumps(chart["error"], ensure_ascii=False),
            "prices": [],
        }
    results = chart.get("result") or []
    if not results:
        return {
            "status": "partial",
            "provider": "yahoo_chart_public",
            "ticker": ticker,
            "url": url,
            "error": "Yahoo chart returned no result.",
            "prices": [],
        }
    result = results[0]
    meta = result.get("meta", {})
    timestamps = result.get("timestamp") or []
    quote_data = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    prices = []
    for index, ts in enumerate(timestamps[-180:]):
        close = _list_get(quote_data.get("close"), index)
        if close is None:
            continue
        prices.append(
            {
                "date": datetime.fromtimestamp(int(ts), timezone.utc).date().isoformat(),
                "open": _list_get(quote_data.get("open"), index),
                "high": _list_get(quote_data.get("high"), index),
                "low": _list_get(quote_data.get("low"), index),
                "close": close,
                "volume": _list_get(quote_data.get("volume"), index),
            }
        )
    return {
        "status": "ok" if prices else "partial",
        "provider": "yahoo_chart_public",
        "ticker": ticker,
        "url": url,
        "meta": {
            "symbol": meta.get("symbol"),
            "shortName": meta.get("shortName"),
            "longName": meta.get("longName"),
            "currency": meta.get("currency"),
            "exchangeName": meta.get("exchangeName"),
            "regularMarketPrice": meta.get("regularMarketPrice"),
            "regularMarketVolume": meta.get("regularMarketVolume"),
            "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
        },
        "prices": prices,
        "error": "" if prices else "No close prices were returned.",
    }


def _list_get(values: Any, index: int) -> float | int | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_yfinance(ticker: str, period: str = "6mo") -> dict[str, Any]:
    try:
        import yfinance as yf  # type: ignore
    except Exception as exc:  # noqa: BLE001 - optional dependency
        return {
            "status": "auth_required",
            "provider": "yfinance",
            "ticker": ticker,
            "error": f"optional dependency unavailable: {exc}",
            "prices": [],
        }
    frame = yf.Ticker(ticker).history(period=period)
    prices = []
    for index, row in frame.tail(120).iterrows():
        prices.append(
            {
                "date": str(index.date() if hasattr(index, "date") else index),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            }
        )
    return {"status": "ok", "provider": "yfinance", "ticker": ticker, "prices": prices}


def read_market_data(ticker: str, period: str = "6mo", interval: str = "1d", provider: str = "auto") -> dict[str, Any]:
    if provider in {"auto", "yahoo"}:
        yahoo = read_yahoo_chart(ticker, period=period, interval=interval)
        if provider == "yahoo" or yahoo.get("status") == "ok":
            return yahoo
    if provider in {"auto", "yfinance"}:
        fallback = read_yfinance(ticker, period=period)
        if provider == "auto":
            fallback["fallback_after"] = "yahoo_chart_public"
        return fallback
    return {
        "status": "blocked",
        "provider": provider,
        "ticker": ticker,
        "error": f"unknown provider: {provider}",
        "prices": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--period", default="6mo")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--provider", choices=["auto", "yahoo", "yfinance"], default="auto")
    args = parser.parse_args(argv)
    json.dump(read_market_data(args.ticker, args.period, args.interval, args.provider), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
