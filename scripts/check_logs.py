#!/usr/bin/env python3
"""Validate unedited JSONL logs before packaging a submission."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


def inspect_jsonl(path: Path) -> dict[str, Any]:
    lines = 0
    bad_lines = []
    roles: dict[str, int] = {}
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                bad_lines.append({"line": index, "error": str(exc)})
                continue
            lines += 1
            role = payload.get("role") or payload.get("type") or payload.get("event") or "unknown"
            roles[role] = roles.get(role, 0) + 1
    return {
        "path": str(path),
        "format": "jsonl",
        "bytes": path.stat().st_size,
        "json_lines": lines,
        "bad_lines": bad_lines,
        "roles": roles,
    }


def inspect_logs(logs_dir: Path) -> dict[str, Any]:
    files = sorted(
        path
        for path in logs_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jsonl", ".json", ".md", ".txt"}
    )
    jsonl = [inspect_jsonl(path) for path in files if path.suffix.lower() == ".jsonl"]
    bad_jsonl = sum(len(item["bad_lines"]) for item in jsonl)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "logs_dir": str(logs_dir),
        "file_count": len(files),
        "jsonl_count": len(jsonl),
        "total_bytes": sum(path.stat().st_size for path in files),
        "jsonl": jsonl,
        "status": "ok" if files and jsonl and bad_jsonl == 0 else "blocked",
        "caveat": "This manifest validates log files without editing, trimming, summarizing, or redacting them.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs_dir", nargs="?", default="logs")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    summary = inspect_logs(Path(args.logs_dir))
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if summary["status"] != "ok":
        print("log validation failed: logs must include parseable JSONL files", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
