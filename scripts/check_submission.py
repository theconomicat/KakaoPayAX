#!/usr/bin/env python3
"""Check hackathon submission structure in a directory."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED = [
    "src/.codex-plugin/plugin.json",
    "src/skills",
    "src/.mcp.json",
    "README.md",
    "logs",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("submission_dir")
    args = parser.parse_args(argv)
    root = Path(args.submission_dir)
    missing = [item for item in REQUIRED if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"missing: {item}")
        return 1
    log_files = [
        path
        for path in (root / "logs").rglob("*")
        if path.is_file() and path.suffix.lower() in {".jsonl", ".json", ".md", ".txt"}
    ]
    if not any(path.suffix.lower() == ".jsonl" for path in log_files):
        print("missing: logs/*.jsonl")
        return 1
    print("submission structure ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
