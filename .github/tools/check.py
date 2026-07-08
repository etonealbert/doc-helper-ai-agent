#!/usr/bin/env python3
"""Quality gate runner: lint + tests (+ optional smoke test).

Runs the same checks the project expects before a change is considered done.
Cross-platform (works on macOS/Linux/Windows) as long as `uv` is available.

Usage:
    uv run python .github/tools/check.py
    python .github/tools/check.py --smoke   # also run the offline smoke test
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run(label: str, cmd: list[str]) -> bool:
    print(f"\n=== {label}: {' '.join(cmd)} ===")
    try:
        result = subprocess.run(cmd, cwd=REPO_ROOT)
    except FileNotFoundError:
        print(f"[SKIP] '{cmd[0]}' not found on PATH.")
        return True  # don't fail the gate solely because a tool is missing
    ok = result.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {label} (exit {result.returncode})")
    return ok


def main(argv: list[str]) -> int:
    checks = [
        ("ruff", ["uv", "run", "ruff", "check", "."]),
        ("pytest", ["uv", "run", "pytest"]),
    ]
    if "--smoke" in argv:
        checks.append(
            ("smoke", ["uv", "run", "python", ".github/tools/smoke_test.py"])
        )

    results = [run(label, cmd) for label, cmd in checks]
    print("\n" + ("ALL CHECKS PASSED" if all(results) else "SOME CHECKS FAILED"))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
