"""Phase 4 /v1/insights/readiness route tests.

Critical invariant from ADR-025: fresh user (no diagnostic) → readiness
returns ⚪/red with `Insufficient data` reason, no green.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from tcf_accel_api.main import create_app
from tcf_accel_api.state import reset_all


def _client() -> TestClient:
    reset_all()
    return TestClient(create_app())


def test_fresh_user_returns_red_insufficient_data() -> None:
    client = _client()
    r = client.get("/v1/insights/readiness")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["light"] == "red"
    assert "Insufficient data" in body["reason"]
    assert len(body["per_skill"]) == 4
    for s in body["per_skill"]:
        assert s["confident"] is False


def test_other_insights_routes_still_stub_501() -> None:
    client = _client()
    for path in ("/v1/insights/nclc-trajectory", "/v1/insights/weak-points"):
        r = client.get(path)
        assert r.status_code == 501, f"{path} should still be Phase 8 stub"
