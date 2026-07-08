#!/usr/bin/env python3
"""Offline smoke test for Doc Helper AI Agent.

Boots the FastAPI app in-process (no server, no network, no API key) and exercises
the key endpoints so an agent/maintainer can quickly confirm the system still
works after a change.

Usage:
    uv run python .github/tools/smoke_test.py
    # or, without uv:
    python .github/tools/smoke_test.py

Exits non-zero if any check fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the src/ layout importable when run as a plain script.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    try:
        from fastapi.testclient import TestClient

        from doc_helper_ai_agent.main import app
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"[SETUP FAILED] Could not import the app: {exc}")
        print("Hint: run `uv sync` first so dependencies are installed.")
        return 2

    client = TestClient(app)
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {name}{f' — {detail}' if detail else ''}")
        if not condition:
            failures.append(name)

    # 1) Health
    resp = client.get("/health")
    check("health status", resp.status_code == 200, f"HTTP {resp.status_code}")
    check("health payload", resp.json().get("status") == "ok")

    # 2) Pricing question -> RAG with sources
    resp = client.post("/api/chat", json={"message": "How much does teeth whitening cost?"})
    data = resp.json()
    check("pricing classification", data.get("classification") == "pricing_question")
    check("pricing has sources", bool(data.get("sources")))
    check("pricing not escalated", data.get("requires_human") is False)

    # 3) Appointment request -> availability + intake
    resp = client.post(
        "/api/chat",
        json={"message": "I need to book an appointment for whitening next Friday"},
    )
    data = resp.json()
    tools_used = [a["tool"] for a in data.get("actions", [])]
    check("appointment classification", data.get("classification") == "appointment_request")
    check("appointment checked availability", "check_availability" in tools_used)
    check("appointment created request", "create_appointment_request" in tools_used)

    # 4) Emergency -> escalate, requires human, no diagnosis
    resp = client.post(
        "/api/chat",
        json={"message": "I have severe pain and my gum is bleeding"},
    )
    data = resp.json()
    tools_used = [a["tool"] for a in data.get("actions", [])]
    check("emergency classification", data.get("classification") == "emergency_or_pain")
    check("emergency requires human", data.get("requires_human") is True)
    check("emergency escalated", "escalate_to_human" in tools_used)

    # 5) Documents listing
    resp = client.get("/api/documents")
    data = resp.json()
    check("documents listed", data.get("total_documents", 0) >= 4)

    print()
    if failures:
        print(f"SMOKE TEST FAILED: {len(failures)} check(s) failed -> {failures}")
        return 1
    print("SMOKE TEST PASSED: all checks green (offline, mock mode).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
