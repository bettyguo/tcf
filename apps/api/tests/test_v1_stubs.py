"""Phase 2 stub-surface tests.

Every `/v1/` route registered in Phase 2 returns `501` with the
canonical `ErrorEnvelope` shape and a `phase` field identifying the
owning build phase. These tests catch:

- A route that returns 500 because the stub helper broke.
- A route that returns 200/204 because someone landed a real handler
  without bumping the contract (and so should also have been in `/v2/`).
- A renamed or removed route (drift from `phase2_design.md §4.4`).

Phase 4 has landed real handlers for the planner + diagnostic + readiness
surface (`04_LEARNER_MODEL.md §3`), so those routes are excluded from
this 501 table and covered separately under
`tests/test_plan_routes.py`, `test_diagnostic_routes.py`,
`test_readiness_route.py`.

Phase 5 has landed the practice-session surface (`/v1/session/*`,
`05_PRACTICE_AND_DRILLS.md §2`), so those routes are likewise excluded
and covered under `tests/test_session_routes.py`.

Phase 6 has landed the mock-exam surface (`/v1/mock-exam/*`,
`06_MOCK_EXAM_ENGINE.md §2`), so those routes are likewise excluded
and covered under `tests/test_mock_exam_routes.py`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from tcf_accel_api.main import app

client = TestClient(app)


# (method, path, owner-phase, expected status, body-required)
# Phase 4 implementations have been excluded from this table:
#   - /v1/plan/*           (Phase 4 §2.5–2.6)
#   - /v1/diagnostic/*     (Phase 4 §1.3 + §2.4)
#   - /v1/insights/readiness (Phase 4 §2.7)
_STUB_TABLE = [
    ("POST", "/v1/auth/signup", 3, 501, True),
    ("POST", "/v1/auth/login", 3, 501, True),
    ("POST", "/v1/auth/refresh", 3, 501, True),
    ("GET", "/v1/me", 3, 501, False),
    ("PATCH", "/v1/me", 3, 501, True),
    # /v1/submission/* implemented in Phase 7 — see tests/test_submission_routes.py
    ("GET", "/v1/insights/nclc-trajectory", 8, 501, False),
    ("GET", "/v1/insights/weak-points", 8, 501, False),
    ("GET", "/v1/data/export", 9, 501, False),
    ("DELETE", "/v1/data", 9, 501, False),
]


def _minimal_body(path: str) -> dict[str, object]:
    """Return a minimal valid body for routes that require one (so we hit the handler, not 422)."""
    if "/auth/signup" in path:
        return {"email": "ada@example.com", "password": "a-strong-password-1234"}
    if "/auth/login" in path:
        return {"email": "ada@example.com", "password": "x" * 12}
    if "/auth/refresh" in path:
        return {"refresh_token": "x"}
    if "/me" in path:
        return {}
    if "/diagnostic/" in path and path.endswith("/answer"):
        return {
            "item_id": "00000000-0000-0000-0000-000000000000",
            "response": {},
            "rt_ms": 100,
        }
    if "/session/start" in path:
        return {"module": "CO", "drill_type": "flashcard", "target_minutes": 10}
    if "/session/" in path and path.endswith("/answer"):
        return {
            "item_id": "00000000-0000-0000-0000-000000000000",
            "response": {},
            "rt_ms": 100,
        }
    return {}


def test_every_stub_returns_501_envelope() -> None:
    for method, path, phase, status, needs_body in _STUB_TABLE:
        body = _minimal_body(path) if needs_body else None
        response = client.request(method, path, json=body)
        assert response.status_code == status, (
            f"{method} {path}: got {response.status_code}, expected {status}"
        )
        envelope = response.json()["detail"]
        assert envelope["code"] == "E_NOT_IMPLEMENTED_001", f"{method} {path}: {envelope}"
        assert envelope["http_status"] == 501
        assert envelope["phase"] == phase, f"{method} {path}: phase mismatch"
        assert "en" in envelope["message_localized"]
        assert "fr" in envelope["message_localized"]


def test_openapi_includes_all_v1_routes() -> None:
    """The OpenAPI spec must include every Phase 2 route."""
    spec = client.get("/openapi.json").json()
    paths = set(spec["paths"].keys())
    # Subset of routes we test for in _STUB_TABLE — paths use {param} not literal UUIDs.
    expected_subset = {
        "/v1/health",
        "/v1/auth/signup",
        "/v1/auth/login",
        "/v1/auth/refresh",
        "/v1/me",
        "/v1/diagnostic/start",
        "/v1/plan",
        "/v1/plan/today",
        "/v1/plan/regenerate",
        "/v1/session/start",
        "/v1/mock-exam/start",
        "/v1/insights/nclc-trajectory",
        "/v1/insights/weak-points",
        "/v1/insights/readiness",
        "/v1/data/export",
        "/v1/data",
    }
    missing = expected_subset - paths
    assert not missing, f"Missing routes in OpenAPI: {missing}"
