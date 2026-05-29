"""Phase 5 /v1/session/* route tests.

Covers the drill loop (start → next → answer → finish), the exam-shape
floor 409 + dismissal (ADR-028), idempotent answers, and pause/resume.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tcf_accel_api.main import create_app
from tcf_accel_api.session_state import reset_all as reset_sessions
from tcf_accel_api.state import reset_all as reset_state


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect the persistent dismissal log to a per-test temp dir (ADR-017)."""
    monkeypatch.setenv("TCF_ACCEL_DATA_DIR", str(tmp_path))


def _client() -> TestClient:
    reset_state()
    reset_sessions()
    return TestClient(create_app())


def _dismiss(client: TestClient) -> None:
    r = client.post("/v1/session/exam-shape/dismiss")
    assert r.status_code == 200, r.text


def _start_co(client: TestClient) -> dict:
    r = client.post(
        "/v1/session/start",
        json={"module": "CO", "drill_type": "mcq", "target_minutes": 10},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ─── exam-shape floor (ADR-028) ────────────────────────────────


def test_fresh_user_drill_blocked_by_floor() -> None:
    client = _client()
    r = client.post(
        "/v1/session/start",
        json={"module": "CO", "drill_type": "mcq", "target_minutes": 10},
    )
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "E_SESSION_001"
    assert detail["next_action"] == "exam_shape"
    assert detail["dismissable"] is True


def test_dismiss_then_start_succeeds() -> None:
    client = _client()
    _dismiss(client)
    body = _start_co(client)
    assert body["module"] == "CO"
    assert body["drill_type"] == "mcq"
    assert body["items_seen"] == 0
    assert body["finished_at"] is None


# ─── drill loop ────────────────────────────────────────────────


def test_next_returns_item_then_answer_advances() -> None:
    client = _client()
    _dismiss(client)
    session = _start_co(client)
    sid = session["id"]

    nxt = client.get(f"/v1/session/{sid}/next")
    assert nxt.status_code == 200, nxt.text
    item = nxt.json()["item"]
    assert item["module"] == "CO"
    item_id = item["id"]

    # The fixture's correct option is always "a".
    ans = client.post(
        f"/v1/session/{sid}/answer",
        json={"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 5000},
    )
    assert ans.status_code == 200, ans.text
    state = ans.json()
    assert state["items_seen"] == 1
    assert state["items_correct"] == 1


def test_answer_is_idempotent() -> None:
    client = _client()
    _dismiss(client)
    sid = _start_co(client)["id"]
    item_id = client.get(f"/v1/session/{sid}/next").json()["item"]["id"]
    payload = {"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 5000}
    first = client.post(f"/v1/session/{sid}/answer", json=payload).json()
    second = client.post(f"/v1/session/{sid}/answer", json=payload).json()
    assert first["items_seen"] == second["items_seen"] == 1


def test_perfect_agent_session_100pct_accuracy_and_positive_delta() -> None:
    client = _client()
    _dismiss(client)
    sid = _start_co(client)["id"]

    answered = 0
    for _ in range(5):
        nxt = client.get(f"/v1/session/{sid}/next")
        if nxt.status_code == 409:
            break  # queue exhausted
        item_id = nxt.json()["item"]["id"]
        client.post(
            f"/v1/session/{sid}/answer",
            json={"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 4000},
        )
        answered += 1

    summary = client.post(f"/v1/session/{sid}/finish").json()
    assert summary["items_seen"] == answered
    assert summary["items_correct"] == answered
    assert summary["accuracy"] == 1.0
    # An all-correct session should not lower the CO posterior.
    co_delta = next(d for d in summary["deltas"] if d["skill"] == "CO")
    assert co_delta["delta"] >= 0.0


# ─── pause / resume ────────────────────────────────────────────


def test_pause_blocks_answer_until_resume() -> None:
    client = _client()
    _dismiss(client)
    sid = _start_co(client)["id"]
    item_id = client.get(f"/v1/session/{sid}/next").json()["item"]["id"]

    assert client.post(f"/v1/session/{sid}/pause").status_code == 200
    blocked = client.post(
        f"/v1/session/{sid}/answer",
        json={"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 1000},
    )
    assert blocked.status_code == 409

    assert client.post(f"/v1/session/{sid}/resume").status_code == 200
    ok = client.post(
        f"/v1/session/{sid}/answer",
        json={"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 1000},
    )
    assert ok.status_code == 200


# ─── not-found / lifecycle guards ──────────────────────────────


def test_unknown_session_is_404() -> None:
    client = _client()
    r = client.get("/v1/session/00000000-0000-0000-0000-000000000000/next")
    assert r.status_code == 404


def test_finish_then_answer_is_409() -> None:
    client = _client()
    _dismiss(client)
    sid = _start_co(client)["id"]
    item_id = client.get(f"/v1/session/{sid}/next").json()["item"]["id"]
    client.post(f"/v1/session/{sid}/finish")
    r = client.post(
        f"/v1/session/{sid}/answer",
        json={"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 1000},
    )
    assert r.status_code == 409
