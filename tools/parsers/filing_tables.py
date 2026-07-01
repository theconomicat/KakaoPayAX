"""Filing table parser wrapper.

The root-level ``tools/filing_parser.py`` remains the stable CLI entrypoint.
This module gives collectors a clearer import path for table extraction.
"""
from __future__ import annotations

try:
    from ..filing_parser import parse_filing_target, to_source
except ImportError:  # pragma: no cover - direct script fallback
    from filing_parser import parse_filing_target, to_source  # type: ignore

__all__ = ["parse_filing_target", "to_source"]

