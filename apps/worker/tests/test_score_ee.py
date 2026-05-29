"""`tcf_accel.score_ee` worker task tests (Phase 5 step 8).

Covers:
- The Celery task is registered and round-trips in eager mode.
- The Phase 5 stub scorer emits a well-shaped pending payload with the
  cheap pre-computed metrics (word count, TTR, connector density).
- The `register_scorer` / `get_scorer` registry pattern lets Phase 7
  plug in a real scorer without touching this module.
- Idempotency: identical payloads produce identical outputs.
"""

from __future__ import annotations

from typing import Any

import pytest
from tcf_accel_worker.celery_app import celery_app
from tcf_accel_worker.tasks.score_ee import (
    RubricScorer,
    get_scorer,
    register_scorer,
    score_ee,
    unregister_scorer,
)


@pytest.fixture(autouse=True)
def _eager_celery() -> None:
    """Run Celery tasks inline so tests don't need a broker.

    Phase 7 installs a calibrated scorer for `ee.v1` at worker-import
    time. The Phase 5 stub tests below assert the *stub's* behaviour,
    so we unregister the Phase 7 scorer for the duration of these
    tests and re-install it afterwards.
    """
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    unregister_scorer("ee.v1")
    yield
    try:
        from tcf_accel_ml.scoring import install_default_scorers
        install_default_scorers()
    except ImportError:
        pass


# ─── Phase 5 stub scorer ───────────────────────────────────────


def test_stub_scorer_emits_pending_with_phase7_status() -> None:
    result = score_ee.delay(
        {
            "text": "Bonjour le monde",
            "rubric_version": "ee.v1",
            "drill_kind": "ee_task",
        }
    ).get(timeout=1)
    assert result["pending"] is True
    assert result["phase7_status"] == "stub"
    assert result["rubric_version"] == "ee.v1"
    assert result["drill_kind"] == "ee_task"


def test_stub_scorer_computes_metrics() -> None:
    text = (
        "Le télétravail est avantageux car il économise du temps. "
        "Cependant, il isole les employés. Donc, un équilibre est nécessaire."
    )
    result = score_ee.delay(
        {
            "text": text,
            "rubric_version": "ee.v1",
            "drill_kind": "ee_task",
        }
    ).get(timeout=1)
    metrics = result["metrics"]
    assert metrics["word_count"] == len(text.split())
    # TTR should be in (0, 1] for any non-empty response.
    assert 0.0 < metrics["type_token_ratio"] <= 1.0
    # Three connectors ("car", "Cependant", "Donc") in the seed list.
    assert metrics["discourse_marker_count"] == 3
    assert metrics["discourse_marker_density_per_100w"] > 0.0


def test_stub_scorer_handles_empty_text() -> None:
    result = score_ee.delay(
        {
            "text": "",
            "rubric_version": "ee.v1",
            "drill_kind": "ee_task",
        }
    ).get(timeout=1)
    assert result["metrics"]["word_count"] == 0
    assert result["metrics"]["type_token_ratio"] == 0.0


def test_stub_scorer_is_deterministic() -> None:
    payload = {
        "text": "Bonjour donc voilà",
        "rubric_version": "ee.v1",
        "drill_kind": "ee_task",
    }
    a = score_ee.delay(payload).get(timeout=1)
    b = score_ee.delay(payload).get(timeout=1)
    assert a == b


def test_stub_scorer_uses_default_rubric_version_when_missing() -> None:
    # A payload without a rubric_version still scores (the stub is the default).
    result = score_ee.delay({"text": "salut"}).get(timeout=1)
    assert result["phase7_status"] == "stub"
    assert result["rubric_version"] == "ee.v1"


# ─── Phase 7 hand-off registry ─────────────────────────────────


class _FakePhase7Scorer:
    """Test double standing in for the eventual Phase 7 rubric scorer."""

    def score_ee(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "pending": False,
            "phase7_status": "scored",
            "rubric_version": payload.get("rubric_version", "fake.v1"),
            "total_20": 17,
        }


def test_register_scorer_replaces_stub_for_named_version() -> None:
    try:
        register_scorer("fake.v1", _FakePhase7Scorer())
        scorer: RubricScorer = get_scorer("fake.v1")
        result = scorer.score_ee({"rubric_version": "fake.v1", "text": "x"})
        assert result["phase7_status"] == "scored"
        assert result["total_20"] == 17
    finally:
        unregister_scorer("fake.v1")


def test_unregister_scorer_restores_stub_fallback() -> None:
    register_scorer("temp.v1", _FakePhase7Scorer())
    unregister_scorer("temp.v1")
    # After unregister, get_scorer falls back to the Phase 5 stub.
    scorer = get_scorer("temp.v1")
    result = scorer.score_ee({"text": "x", "rubric_version": "temp.v1"})
    assert result["phase7_status"] == "stub"


def test_task_dispatches_through_registry() -> None:
    """End-to-end via the Celery task: a registered scorer is honored."""
    try:
        register_scorer("fake.v1", _FakePhase7Scorer())
        result = score_ee.delay(
            {
                "text": "x",
                "rubric_version": "fake.v1",
                "drill_kind": "ee_task",
            }
        ).get(timeout=1)
        assert result["phase7_status"] == "scored"
    finally:
        unregister_scorer("fake.v1")


def test_task_is_registered_with_celery_app() -> None:
    # The task name pins the wire identity — renaming it would
    # invalidate any queued tasks during a Phase-7 deploy.
    assert "tcf_accel.score_ee" in celery_app.tasks
