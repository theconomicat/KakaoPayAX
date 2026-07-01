"""Byul.ai public API collector wrapper.

The root-level ``tools/byul_client.py`` remains the stable CLI entrypoint.
This module exists so orchestration code can import public collectors from a
single package without changing the CLI contract.
"""
from __future__ import annotations

try:
    from ..byul_client import fetch_byul_bundle
except ImportError:  # pragma: no cover - direct script fallback
    from byul_client import fetch_byul_bundle  # type: ignore

__all__ = ["fetch_byul_bundle"]

