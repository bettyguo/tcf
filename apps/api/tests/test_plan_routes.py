"""Phase 4 /v1/plan/* route tests.

The planner-as-API contract:
- GET /v1/plan auto-generates a plan on first access (no 404 limp).
- POST /v1/plan/regenerate writes a fresh plan and supersedes the old one.
- GET /v1/plan/today returns only today's blocks.
- StudyPlanView shape matches the contract.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from tcf_accel_api.main import create_app
from tcf_accel_api.state import reset_all


def _client() -> TestClient:
    reset_all()
    return TestClient(create_app())


def test_get_plan_auto_generates_first_time() -> None:
    client = _client()
    r = client.get("/v1/plan")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["horizon_days"] >= 1
    assert len(body["daily_blocks"]) == body["horizon_days"]
    # Each daily block has 4 skill blocks summing to daily budget.
    first = body["daily_blocks"][0]
    assert first["total_minutes"] == sum(b["minutes"] for b in first["blocks"])
    assert {b["skill"] for b in first["blocks"]} == {"CO", "CE", "EE", "EO"}


def test_regenerate_changes_plan_id() -> None:
    client = _client()
    a = client.get("/v1/plan").json()
    b = client.post("/v1/plan/regenerate").json()
    assert a["id"] != b["id"]


def test_today_returns_subset() -> None:
    client = _client()
    r = client.get("/v1/plan/today")
    assert r.status_code == 200, r.text
    blocks = r.json()
    today = datetime.now(UTC).date().isoformat()
    assert all(b["date"] == today for b in blocks)


def test_plan_rationale_is_non_empty() -> None:
    client = _client()
    body = client.get("/v1/plan").json()
    assert body["rationale"]
    assert "target NCLC" in body["rationale"]
