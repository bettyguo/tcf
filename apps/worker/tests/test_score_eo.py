"""`tcf_accel.score_eo` worker task tests (Phase 5 step 9).

Mirrors `test_score_ee`. The EO worker accepts a payload carrying the
pre-computed pronunciation signal's display_label + the recording
duration; the Phase 5 stub returns a typed pending dict, Phase 7
plugs in the real `SpeakingRubric` scorer via the registry.
"""

from __future__ import annotations

from typing import Any

import pytest
from tcf_accel_worker.celery_app import celery_app
from tcf_accel_worker.tasks.score_eo import (
    EORubricScorer,
    get_scorer,
    register_scorer,
    score_eo,
    unregister_scorer,
)


@pytest.fixture(autouse=True)
def _eager_celery() -> None:
    """Eager Celery + isolate Phase 5 stub behaviour from Phase 7 install."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    unregister_scorer("eo.v1")
    yield
    try:
        from tcf_accel_ml.scoring import install_default_scorers
        install_default_scorers()
    except ImportError:
        pass


# ─── Phase 5 stub scorer ───────────────────────────────────────


def test_stub_scorer_emits_pending_with_phase7_status() -> None:
    result = score_eo.delay(
        {
            "transcript": "bonjour le monde",
            "duration_s": 10.0,
            "target_duration_s": 15.0,
            "rubric_version": "eo.v1",
            "drill_kind": "eo_task",
            "task_number": 1,
        }
    ).get(timeout=1)
    assert result["pending"] is True
    assert result["phase7_status"] == "stub"
    assert result["rubric_version"] == "eo.v1"
    assert result["drill_kind"] == "eo_task"


def test_stub_scorer_computes_duration_deviation() -> None:
    # 12 s recording against a 15 s target → -20% deviation.
    result = score_eo.delay(
        {
            "duration_s": 12.0,
            "target_duration_s": 15.0,
            "rubric_version": "eo.v1",
            "drill_kind": "eo_task",
        }
    ).get(timeout=1)
    metrics = result["metrics"]
    assert metrics["duration_s"] == 12.0
    assert metrics["target_duration_s"] == 15.0
    assert abs(metrics["duration_deviation_ratio"] - (-0.20)) < 1e-9


def test_stub_scorer_handles_missing_target() -> None:
    # A drill that doesn't carry target_duration_s should not crash;
    # the deviation just comes back as None.
    result = score_eo.delay(
        {
            "duration_s": 10.0,
            "rubric_version": "eo.v1",
            "drill_kind": "eo_spontaneous",
        }
    ).get(timeout=1)
    assert result["metrics"]["duration_deviation_ratio"] is None


def test_stub_scorer_surfaces_pronunciation_display_label() -> None:
    result = score_eo.delay(
        {
            "transcript": "x",
            "duration_s": 8.0,
            "target_duration_s": 10.0,
            "rubric_version": "eo.v1",
            "drill_kind": "eo_task",
            "pronunciation_display_label": "fair",
        }
    ).get(timeout=1)
    assert result["metrics"]["pronunciation_display_label"] == "fair"


def test_stub_scorer_is_deterministic() -> None:
    payload = {
        "transcript": "bonjour",
        "duration_s": 8.0,
        "target_duration_s": 10.0,
        "rubric_version": "eo.v1",
        "drill_kind": "eo_task",
    }
    a = score_eo.delay(payload).get(timeout=1)
    b = score_eo.delay(payload).get(timeout=1)
    assert a == b


# ─── Phase 7 hand-off registry ─────────────────────────────────


class _FakePhase7EOScorer:
    """Test double for the eventual Phase 7 EO rubric scorer."""

    def score_eo(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "pending": False,
            "phase7_status": "scored",
            "rubric_version": payload.get("rubric_version", "fake.v1"),
            "total_20": 16,
            "pronunciation_prosody": 4,
        }


def test_register_scorer_replaces_stub_for_named_version() -> None:
    try:
        register_scorer("fake.v1", _FakePhase7EOScorer())
        scorer: EORubricScorer = get_scorer("fake.v1")
        result = scorer.score_eo({"rubric_version": "fake.v1"})
        assert result["phase7_status"] == "scored"
        assert result["total_20"] == 16
    finally:
        unregister_scorer("fake.v1")


def test_unregister_scorer_restores_stub_fallback() -> None:
    register_scorer("temp.v1", _FakePhase7EOScorer())
    unregister_scorer("temp.v1")
    scorer = get_scorer("temp.v1")
    result = scorer.score_eo({"rubric_version": "temp.v1"})
    assert result["phase7_status"] == "stub"


def test_task_dispatches_through_registry() -> None:
    try:
        register_scorer("fake.v1", _FakePhase7EOScorer())
        result = score_eo.delay(
            {
                "rubric_version": "fake.v1",
                "drill_kind": "eo_task",
            }
        ).get(timeout=1)
        assert result["phase7_status"] == "scored"
    finally:
        unregister_scorer("fake.v1")


def test_task_is_registered_with_celery_app() -> None:
    # The task name pins the wire identity — renaming it would
    # invalidate any queued tasks during a Phase-7 deploy.
    assert "tcf_accel.score_eo" in celery_app.tasks


# ─── EE + EO registries are independent ───────────────────────


def test_ee_and_eo_registries_are_separate() -> None:
    # Registering an EO scorer must NOT shadow EE's registry, and
    # vice versa. The two tasks use distinct module-level dicts.
    from tcf_accel_worker.tasks.score_ee import (  # noqa: PLC0415
        get_scorer as get_ee_scorer,
    )
    from tcf_accel_worker.tasks.score_ee import (  # noqa: PLC0415
        register_scorer as register_ee_scorer,
    )
    from tcf_accel_worker.tasks.score_ee import (  # noqa: PLC0415
        unregister_scorer as unregister_ee_scorer,
    )

    class _FakeEE:
        def score_ee(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {"phase7_status": "ee_scored"}

    try:
        register_ee_scorer("shared.v1", _FakeEE())
        register_scorer("shared.v1", _FakePhase7EOScorer())
        # EE registry returns the EE scorer; EO returns the EO scorer.
        assert get_ee_scorer("shared.v1").score_ee({})["phase7_status"] == "ee_scored"
        assert get_scorer("shared.v1").score_eo({})["phase7_status"] == "scored"
    finally:
        unregister_ee_scorer("shared.v1")
        unregister_scorer("shared.v1")
