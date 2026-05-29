"""Mock-exam API routes — end-to-end via the scripted candidate.

Phase 6 §3 (CODE deliverable): "A scripted candidate agent that takes
a full mock end-to-end with realistic timing distributions — used as
an integration test." This file is that test.

Covers the happy path plus the load-bearing invariants:

- Wire-shape: every response validates against the documented schema.
- No leak: items and state never carry `correct_option_id` etc.
- Cadence cap: a second canonical start in the same week returns 409.
- Forfeit: a tab-blur > 5 s in canonical forfeits the session.
- CO single play: a second co-play call returns 409.
- Report shape: 4 per-module scores; bottleneck identified.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tcf_accel_api.main import app
from tcf_accel_api.mock_exam_state import reset_all as reset_mocks
from tcf_accel_api.session_state import reset_all as reset_sessions
from tcf_accel_api.state import reset_all as reset_state

from tcf_accel_sla.mock_exam.candidate import CandidateProfile, CandidateRunner


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    reset_mocks()
    reset_sessions()
    reset_state()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _runner(client: TestClient) -> CandidateRunner:
    return CandidateRunner(
        start_mock=lambda body: _ok(client.post("/v1/mock-exam/start", json=body)),
        fetch_items=lambda mid, module: _ok(
            client.get(f"/v1/mock-exam/{mid}/items/{module}"),
        ),
        submit_answer=lambda mid, body: _ok(
            client.post(f"/v1/mock-exam/{mid}/answer", json=body),
        ),
        advance=lambda mid: _ok(client.post(f"/v1/mock-exam/{mid}/advance")),
        submit_final=lambda mid: _ok(client.post(f"/v1/mock-exam/{mid}/submit")),
        fetch_report=lambda mid: client.get(f"/v1/mock-exam/{mid}/report").json(),
        fetch_state=lambda mid: client.get(f"/v1/mock-exam/{mid}/state").json(),
    )


def _ok(response):  # type: ignore[no-untyped-def]
    response.raise_for_status()
    return response.json()


def test_full_canonical_mock_run_end_to_end(client: TestClient) -> None:
    runner = _runner(client)
    result = runner.run(CandidateProfile(), mode="canonical", rng_seed=42)
    assert result.report is not None
    assert result.leak_audit_passed, "answer key leaked into the wire payload"
    assert len(result.selected_item_ids) == 39 + 39 + 3 + 3
    assert result.report["bottleneck_skill"] in ("CO", "CE", "EE", "EO")
    assert 1 <= result.report["overall_nclc"] <= 12


def test_state_response_never_includes_answer_key(client: TestClient) -> None:
    start = client.post("/v1/mock-exam/start", json={"mode": "canonical"}).json()
    state = client.get(f"/v1/mock-exam/{start['id']}/state").json()
    blob = str(state)
    for forbidden in ("correct_option_id", "explanation", "answer_key"):
        assert forbidden not in blob


def test_items_response_strips_correct_option_id(client: TestClient) -> None:
    start = client.post("/v1/mock-exam/start", json={"mode": "canonical"}).json()
    mid = start["id"]
    client.post(f"/v1/mock-exam/{mid}/advance")
    items = client.get(f"/v1/mock-exam/{mid}/items/CO").json()
    blob = str(items)
    assert "correct_option_id" not in blob
    assert "explanation" not in blob


def test_second_canonical_in_same_week_returns_409(client: TestClient) -> None:
    r1 = client.post("/v1/mock-exam/start", json={"mode": "canonical"})
    assert r1.status_code == 201
    r2 = client.post("/v1/mock-exam/start", json={"mode": "canonical"})
    assert r2.status_code == 409
    envelope = r2.json()["detail"]
    assert envelope["code"] == "E_MOCK_001"


def test_force_overrides_cadence(client: TestClient) -> None:
    r1 = client.post("/v1/mock-exam/start", json={"mode": "canonical"})
    assert r1.status_code == 201
    r2 = client.post("/v1/mock-exam/start", json={"mode": "canonical", "force": True})
    assert r2.status_code == 201


def test_tab_blur_above_grace_forfeits_canonical(client: TestClient) -> None:
    start = client.post("/v1/mock-exam/start", json={"mode": "canonical"}).json()
    mid = start["id"]
    client.post(f"/v1/mock-exam/{mid}/advance")  # → CO_ACTIVE
    r = client.post(f"/v1/mock-exam/{mid}/tab-blur", json={"duration_ms": 6000})
    assert r.status_code == 200
    state = client.get(f"/v1/mock-exam/{mid}/state").json()
    # Wire status is `in_progress` for FORFEITED too (it's terminal but not scored).
    # Verify forfeit by attempting another advance, which must 409.
    r2 = client.post(f"/v1/mock-exam/{mid}/advance")
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "E_MOCK_002"


def test_tab_blur_short_blur_does_not_forfeit(client: TestClient) -> None:
    start = client.post("/v1/mock-exam/start", json={"mode": "canonical"}).json()
    mid = start["id"]
    client.post(f"/v1/mock-exam/{mid}/advance")
    r = client.post(f"/v1/mock-exam/{mid}/tab-blur", json={"duration_ms": 2000})
    assert r.status_code == 200
    # Should still be advanceable.
    r2 = client.post(f"/v1/mock-exam/{mid}/advance")
    assert r2.status_code == 200


def test_tab_blur_training_does_not_forfeit(client: TestClient) -> None:
    start = client.post("/v1/mock-exam/start", json={"mode": "training"}).json()
    mid = start["id"]
    client.post(f"/v1/mock-exam/{mid}/advance")
    r = client.post(f"/v1/mock-exam/{mid}/tab-blur", json={"duration_ms": 60_000})
    assert r.status_code == 200
    r2 = client.post(f"/v1/mock-exam/{mid}/advance")
    assert r2.status_code == 200  # not forfeited


def test_co_single_play_second_request_409(client: TestClient) -> None:
    start = client.post("/v1/mock-exam/start", json={"mode": "canonical"}).json()
    mid = start["id"]
    client.post(f"/v1/mock-exam/{mid}/advance")
    items = client.get(f"/v1/mock-exam/{mid}/items/CO").json()
    item_id = items[0]["id"]
    r1 = client.post(f"/v1/mock-exam/{mid}/co-play", json={"item_id": item_id})
    assert r1.status_code == 200
    r2 = client.post(f"/v1/mock-exam/{mid}/co-play", json={"item_id": item_id})
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "E_MOCK_005"


def test_report_404_before_submit(client: TestClient) -> None:
    start = client.post("/v1/mock-exam/start", json={"mode": "canonical"}).json()
    mid = start["id"]
    r = client.get(f"/v1/mock-exam/{mid}/report")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "E_MOCK_003"


def test_report_contains_four_per_module_scores(client: TestClient) -> None:
    runner = _runner(client)
    result = runner.run(CandidateProfile(), mode="canonical", rng_seed=123)
    assert result.report is not None
    modules = [pm["module"] for pm in result.report["per_module"]]
    assert sorted(modules) == ["CE", "CO", "EE", "EO"]
