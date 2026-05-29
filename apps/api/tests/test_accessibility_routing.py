"""ADR-029: the CO accessibility alternative reroutes session start.

When `AccessibilityProfile.co_alternative == "lexical_alt"`, starting a
CO drill must (a) succeed without auditioning the CO posterior and
(b) report the finish delta on the CE skill, not CO.
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


def _dismiss(c: TestClient) -> None:
    assert c.post("/v1/session/exam-shape/dismiss").status_code == 200


def test_get_accessibility_defaults_to_none() -> None:
    c = _client()
    r = c.get("/v1/me/accessibility")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["co_alternative"] == "none"
    assert body["ee_alternative"] == "none"
    assert body["eo_alternative"] == "none"


def test_patch_accessibility_persists() -> None:
    c = _client()
    r = c.patch(
        "/v1/me/accessibility",
        json={
            "co_alternative": "lexical_alt",
            "ee_alternative": "none",
            "eo_alternative": "none",
            "dyslexia_font": True,
            "high_contrast": False,
        },
    )
    assert r.status_code == 200, r.text
    again = c.get("/v1/me/accessibility").json()
    assert again["co_alternative"] == "lexical_alt"
    assert again["dyslexia_font"] is True


def test_co_drill_with_lexical_alt_profile_updates_ce_not_co() -> None:
    c = _client()
    # Opt into the CO lexical alternative.
    c.patch("/v1/me/accessibility", json={"co_alternative": "lexical_alt"})
    _dismiss(c)

    # The user asks for a CO MCQ session — the router must swap it to co_lexical_alt.
    start = c.post(
        "/v1/session/start",
        json={"module": "CO", "drill_type": "mcq", "target_minutes": 10},
    )
    assert start.status_code == 201, start.text
    sid = start.json()["id"]

    # Run the perfect agent through the queue.
    answered = 0
    for _ in range(5):
        nxt = c.get(f"/v1/session/{sid}/next")
        if nxt.status_code == 409:
            break
        item_id = nxt.json()["item"]["id"]
        c.post(
            f"/v1/session/{sid}/answer",
            json={"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 4000},
        )
        answered += 1
    assert answered >= 1

    summary = c.post(f"/v1/session/{sid}/finish").json()
    # The load-bearing assertion: the delta is on CE, not CO.
    # If a bug ever routes a co_lexical_alt session's posterior update
    # back to CO, this test catches it.
    assert {d["skill"] for d in summary["deltas"]} == {"CE"}
    ce_delta = summary["deltas"][0]
    assert ce_delta["delta"] >= 0.0  # all-correct should not lower CE


def test_co_drill_without_alt_profile_updates_co() -> None:
    # Sanity: with no accessibility opt-in, the normal CO MCQ flow
    # still reports a CO delta (the default behavior is unchanged).
    c = _client()
    _dismiss(c)
    sid = c.post(
        "/v1/session/start",
        json={"module": "CO", "drill_type": "mcq", "target_minutes": 10},
    ).json()["id"]
    item_id = c.get(f"/v1/session/{sid}/next").json()["item"]["id"]
    c.post(
        f"/v1/session/{sid}/answer",
        json={"item_id": item_id, "response": {"option_id": "a"}, "rt_ms": 4000},
    )
    summary = c.post(f"/v1/session/{sid}/finish").json()
    assert {d["skill"] for d in summary["deltas"]} == {"CO"}


# ─── EO accessibility (text_input → eo_text_alt, module=EE) ────


def test_eo_drill_with_text_input_alt_routes_to_eo_text_alt() -> None:
    """Symmetric to ADR-029 (`phase5_design.md §7.2`): when the learner
    has opted into the EO text alternative, a requested EO session
    silently swaps to `eo_text_alt`, whose interactions update the EE
    posterior, **not** EO."""
    c = _client()
    c.patch("/v1/me/accessibility", json={"eo_alternative": "text_input"})
    _dismiss(c)

    # The DrillType the planner emits for EO Task 1 is `speaking_mono`
    # → resolves to `eo_task`, but the accessibility swap overrides it
    # to `eo_text_alt`. The session route accepts the DrillType and
    # makes the swap server-side.
    start = c.post(
        "/v1/session/start",
        json={"module": "EO", "drill_type": "speaking_mono", "target_minutes": 10},
    )
    assert start.status_code == 201, start.text
    sid = start.json()["id"]

    item_id = c.get(f"/v1/session/{sid}/next").json()["item"]["id"]
    c.post(
        f"/v1/session/{sid}/answer",
        json={"item_id": item_id, "response": {"text": "Une réponse écrite."}, "rt_ms": 30_000},
    )
    summary = c.post(f"/v1/session/{sid}/finish").json()
    # The load-bearing assertion: the delta is on EE, not EO.
    assert {d["skill"] for d in summary["deltas"]} == {"EE"}
