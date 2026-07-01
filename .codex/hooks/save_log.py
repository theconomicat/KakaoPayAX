#!/usr/bin/env python3
"""Codex Stop hook: copy the original transcript into logs/codex/.

This hook intentionally copies the transcript verbatim. It does not trim,
summarize, redact, or reformat the conversation log.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:  # noqa: BLE001
        print(f"save_log: failed to parse stdin JSON: {exc}", file=sys.stderr)
        return 0

    transcript_path = payload.get("transcript_path")
    cwd = Path(payload.get("cwd") or os.getcwd())
    session_id = os.path.basename(str(payload.get("session_id") or "session"))
    if session_id in {"", ".", ".."}:
        session_id = "session"

    if not transcript_path or not Path(transcript_path).is_file():
        print(f"save_log: transcript_path missing: {transcript_path!r}", file=sys.stderr)
        return 0

    dest_dir = cwd / "logs" / "codex"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{session_id}.jsonl"
    try:
        shutil.copyfile(transcript_path, dest)
    except Exception as exc:  # noqa: BLE001
        print(f"save_log: copy failed: {exc}", file=sys.stderr)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

