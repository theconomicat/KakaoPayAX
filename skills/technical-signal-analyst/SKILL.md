---
name: technical-signal-analyst
description: Summarize OHLCV-derived trend, momentum, volatility, and volume signals as research inputs, not trading recommendations.
---

# Technical Signal Analyst

Use this skill when price history or OHLCV data is available.

## Signals

Default signals:

- close price
- SMA 5, 20, 60 where enough data exists
- RSI 14
- MACD line, signal, histogram
- Bollinger band position
- volume trend if volume is provided

## Output

Frame signals as "market context":

- trend
- momentum
- volatility
- unusual volume
- caveats

Never say "buy", "sell", "entry", "exit", "target", or "stop loss" unless quoting a source, and mark quotes as third-party claims.

