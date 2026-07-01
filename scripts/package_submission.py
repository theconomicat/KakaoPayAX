#!/usr/bin/env python3
"""Create dist/submission.zip with the hackathon-required structure."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build" / "submission"


EXCLUDE_NAMES = {
    ".env",
    ".git",
    "__pycache__",
    "build",
    "dist",
    "logs",
    "node_modules",
    "outputs",
}


def ignore_filter(_dir: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDE_NAMES or name.endswith(".pyc")}


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    src = BUILD / "src"
    shutil.copytree(ROOT, src, ignore=ignore_filter)
    shutil.copy2(ROOT / "README.md", BUILD / "README.md")
    logs = BUILD / "logs"
    if (ROOT / "logs").exists():
        shutil.copytree(ROOT / "logs", logs, ignore=ignore_filter)
    else:
        logs.mkdir()
        (logs / "README.md").write_text(
            "Replace this file with official unedited AI conversation logs before final upload.\n",
            encoding="utf-8",
        )
    subprocess.run([sys.executable, str(ROOT / "scripts" / "check_submission.py"), str(BUILD)], check=True)
    DIST.mkdir(exist_ok=True)
    zip_base = DIST / "submission"
    archive = shutil.make_archive(str(zip_base), "zip", BUILD)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
