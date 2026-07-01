#!/usr/bin/env python3
"""Run the API-key-free demo packet build."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    output = ROOT / "outputs" / "research_source_packet.md"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "build_source_packet.py"),
        "--input",
        str(ROOT / "examples" / "sample_raw_sources.json"),
        "--output",
        str(output),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

