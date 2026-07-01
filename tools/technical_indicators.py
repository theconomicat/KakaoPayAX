#!/usr/bin/env python3
"""Small no-dependency technical indicator helper for demo and tests."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window or window <= 0:
        return None
    return sum(values[-window:]) / window


def ema_series(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (span + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1 - alpha) * out[-1])
    return out


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values[-period - 1 : -1], values[-period:]):
        delta = current - previous
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values: list[float]) -> dict[str, float | None]:
    if len(values) < 26:
        return {"macd": None, "signal": None, "histogram": None}
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)
    macd_values = [a - b for a, b in zip(ema12[-len(ema26) :], ema26)]
    signal_values = ema_series(macd_values, 9)
    latest_macd = macd_values[-1]
    latest_signal = signal_values[-1]
    return {
        "macd": latest_macd,
        "signal": latest_signal,
        "histogram": latest_macd - latest_signal,
    }


def bollinger(values: list[float], window: int = 20, deviations: float = 2.0) -> dict[str, float | None]:
    if len(values) < window:
        return {"middle": None, "upper": None, "lower": None, "position": None}
    sample = values[-window:]
    middle = sum(sample) / window
    stdev = statistics.pstdev(sample)
    upper = middle + deviations * stdev
    lower = middle - deviations * stdev
    position = None if upper == lower else (values[-1] - lower) / (upper - lower)
    return {"middle": middle, "upper": upper, "lower": lower, "position": position}


def summarize_prices(prices: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [float(row["close"]) for row in prices if row.get("close") is not None]
    volumes = [float(row["volume"]) for row in prices if row.get("volume") is not None]
    summary: dict[str, Any] = {
        "observations": len(closes),
        "latest_close": closes[-1] if closes else None,
        "sma_5": sma(closes, 5),
        "sma_20": sma(closes, 20),
        "sma_60": sma(closes, 60),
        "rsi_14": rsi(closes, 14),
        "macd": macd(closes),
        "bollinger_20": bollinger(closes, 20),
        "volume_latest": volumes[-1] if volumes else None,
        "volume_sma_20": sma(volumes, 20) if volumes else None,
        "interpretation": [],
    }
    interpretation: list[str] = []
    latest = summary["latest_close"]
    sma20 = summary["sma_20"]
    if latest is not None and sma20 is not None:
        interpretation.append(
            "Latest close is above the 20-period average."
            if latest > sma20
            else "Latest close is below the 20-period average."
        )
    rsi14 = summary["rsi_14"]
    if rsi14 is not None:
        if rsi14 >= 70:
            interpretation.append("RSI is in an overbought context.")
        elif rsi14 <= 30:
            interpretation.append("RSI is in an oversold context.")
        else:
            interpretation.append("RSI is in a neutral context.")
    summary["interpretation"] = interpretation
    return summary


def read_prices_csv(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "date": row.get("date", ""),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]) if row.get("volume") else None,
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV with date,close,volume")
    args = parser.parse_args(argv)
    json.dump(summarize_prices(read_prices_csv(args.input)), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

