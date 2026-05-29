"""Celery task: `tcf_accel.score_mock` — eager-mode determinism."""

from __future__ import annotations

from uuid import UUID

import pytest

from tcf_accel_worker.celery_app import celery_app
from tcf_accel_worker.tasks.score_mock import score_mock


@pytest.fixture(autouse=True)
def _eager_mode() -> None:
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False


def _payload() -> dict:
    co = [
        {
            "item_id": str(UUID(int=i)),
            "module": "CO",
            "difficulty": 6.0,
            "discrimination": 1.0,
            "correct": (i % 2 == 0),
            "rt_ms": 5000,
        }
        for i in range(1, 40)
    ]
    ce = [
        {
            "item_id": str(UUID(int=i + 1000)),
            "module": "CE",
            "difficulty": 7.0,
            "discrimination": 1.0,
            "correct": True,
            "rt_ms": 8000,
        }
        for i in range(1, 40)
    ]
    ee = [
        {
            "item_id": str(UUID(int=2000 + t)),
            "module": "EE",
            "task_number": t,
            "prompt_target_nclc": 7.0,
            "rubric_total_20": 14.0,
        }
        for t in (1, 2, 3)
    ]
    eo = [
        {
            "item_id": str(UUID(int=3000 + t)),
            "module": "EO",
            "task_number": t,
            "prompt_target_nclc": 7.0,
            "rubric_total_20": 13.0,
        }
        for t in (1, 2, 3)
    ]
    return {
        "mock_id": str(UUID(int=42)),
        "co_outcomes": co,
        "ce_outcomes": ce,
        "ee_outcomes": ee,
        "eo_outcomes": eo,
    }


def test_score_mock_returns_per_skill_block() -> None:
    result = score_mock.delay(_payload()).get(timeout=5)
    assert set(result["per_skill"].keys()) == {"CO", "CE", "EE", "EO"}
    assert "overall_confident" in result
    assert "bottleneck_skill" in result


def test_score_mock_is_deterministic() -> None:
    payload = _payload()
    r1 = score_mock.delay(payload).get(timeout=5)
    r2 = score_mock.delay(payload).get(timeout=5)
    # The mock_id round-trips and the per-skill posterior means are equal.
    for skill in ("CO", "CE", "EE", "EO"):
        assert (
            r1["per_skill"][skill]["posterior"]["mean"]
            == r2["per_skill"][skill]["posterior"]["mean"]
        )


def test_score_mock_attaches_divergence_alert_when_drill_diverges() -> None:
    payload = _payload()
    payload["drill_posteriors"] = {
        "CO": {
            "skill": "CO",
            "mean": 11.0,
            "variance": 0.2,
            "n_obs": 200,
            "difficulty_bands_seen": [7, 8, 9],
        },
    }
    result = score_mock.delay(payload).get(timeout=5)
    assert any("CO" in alert for alert in result["divergence_alerts"])
