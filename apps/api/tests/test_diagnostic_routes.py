"""Phase 4 /v1/diagnostic/* route tests.

- POST /v1/diagnostic/start returns a fresh `DiagnosticState` with a
  `next_item_id` pre-fetched.
- POST /v1/diagnostic/{id}/answer advances the session and updates the
  per-skill posterior.
- POST /v1/diagnostic/{id}/finish returns a `DiagnosticReport` whose
  per-skill list has 4 entries and `bottleneck_skill` is the lowest-mean
  skill.
- A `confident_summary` of "exploratory" is produced for a single-answer
  session (low n_obs).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from tcf_accel_api.diagnostic_pool import candidates_for
from tcf_accel_api.main import create_app
from tcf_accel_api.state import reset_all


def _client() -> TestClient:
    reset_all()
    return TestClient(create_app())


def test_start_returns_pre_fetched_next_item() -> None:
    client = _client()
    r = client.post("/v1/diagnostic/start")
    assert r.status_code == 201, r.text
    state = r.json()
    assert state["next_item_id"] is not None
    assert state["items_seen"] == 0
    assert state["current_module"] == "CO"


def test_answer_advances_state_and_updates_posterior() -> None:
    client = _client()
    state = client.post("/v1/diagnostic/start").json()
    session_id = state["id"]
    # Pick a known CO item and answer correct.
    pool = candidates_for("CO")
    item_id = str(pool[0].item_id)
    r = client.post(
        f"/v1/diagnostic/{session_id}/answer",
        json={"item_id": item_id, "response": {"answer": "__correct__"}, "rt_ms": 12345},
    )
    assert r.status_code == 200, r.text
    state2 = r.json()
    assert state2["items_seen"] == 1
    assert "CO" in state2["estimates_in_progress"]


def test_finish_returns_full_report() -> None:
    client = _client()
    state = client.post("/v1/diagnostic/start").json()
    session_id = state["id"]
    # Answer one CO item to get the session past the empty check.
    pool = candidates_for("CO")
    client.post(
        f"/v1/diagnostic/{session_id}/answer",
        json={"item_id": str(pool[0].item_id),
              "response": {"answer": "__correct__"}, "rt_ms": 100},
    )
    r = client.post(f"/v1/diagnostic/{session_id}/finish")
    assert r.status_code == 200, r.text
    report = r.json()
    assert len(report["per_skill"]) == 4
    assert report["bottleneck_skill"] in {"CO", "CE", "EE", "EO"}
    # Single-answer session → not enough obs to be confident anywhere.
    assert report["confidence_summary"] == "exploratory"


def test_unknown_session_returns_404() -> None:
    client = _client()
    r = client.post(
        "/v1/diagnostic/00000000-0000-0000-0000-000000000000/answer",
        json={
            "item_id": "00000000-0000-0000-0000-000000000000",
            "response": {"answer": "x"},
            "rt_ms": 100,
        },
    )
    assert r.status_code == 404
