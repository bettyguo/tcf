"""Asynchronous mock-exam scoring task (Phase 6).

The route handler enqueues `score_mock` on `POST /v1/mock-exam/{id}/submit`.
In tests we run with `task_always_eager=True` so the result is
immediate. Phase 9 plumbs the real Celery + Redis broker.

The task is a thin wrapper over `tcf_accel_sla.mock_exam.score_mock`:
it accepts a JSON-serializable payload (Celery's JSON-only contract
means no SkillPosterior objects on the wire) and returns the scored
payload as JSON.

Idempotent: the same payload deterministically produces the same
result (the underlying scorer is deterministic given fixed inputs).
"""

from __future__ import annotations

from typing import Any

from tcf_accel.ids import ItemId
from tcf_accel_sla.estimator.nclc import SkillPosterior
from tcf_accel_sla.mock_exam import (
    ItemOutcome,
    RubricOutcome,
    score_mock as score_mock_pure,
)
from tcf_accel_worker.celery_app import celery_app


def _to_item_outcome(payload: dict[str, Any]) -> ItemOutcome:
    return ItemOutcome(
        item_id=ItemId(_uuid(payload["item_id"])),
        module=payload["module"],
        difficulty=float(payload["difficulty"]),
        discrimination=float(payload.get("discrimination", 1.0)),
        correct=bool(payload["correct"]),
        rt_ms=int(payload.get("rt_ms", 0)),
    )


def _to_rubric_outcome(payload: dict[str, Any]) -> RubricOutcome:
    return RubricOutcome(
        item_id=ItemId(_uuid(payload["item_id"])),
        module=payload["module"],
        task_number=int(payload["task_number"]),
        prompt_target_nclc=float(payload["prompt_target_nclc"]),
        rubric_total_20=float(payload["rubric_total_20"]),
    )


def _uuid(raw: str | object) -> Any:
    from uuid import UUID

    return UUID(str(raw))


def _to_posterior(payload: dict[str, Any]) -> SkillPosterior:
    return SkillPosterior(
        skill=payload["skill"],
        mean=float(payload["mean"]),
        variance=float(payload["variance"]),
        n_obs=int(payload.get("n_obs", 0)),
        difficulty_bands_seen=frozenset(payload.get("difficulty_bands_seen", [])),
    )


def _from_posterior(p: SkillPosterior) -> dict[str, Any]:
    return {
        "skill": p.skill,
        "mean": p.mean,
        "variance": p.variance,
        "n_obs": p.n_obs,
        "difficulty_bands_seen": sorted(p.difficulty_bands_seen),
        "ci_low": p.ci_low,
        "ci_high": p.ci_high,
        "confident": p.confident,
    }


@celery_app.task(name="tcf_accel.score_mock")
def score_mock(payload: dict[str, Any]) -> dict[str, Any]:
    """Score a submitted mock and return the JSON-safe result.

    Expected payload shape:

        {
            "mock_id": "uuid",
            "co_outcomes": [{"item_id": ..., "module": "CO", "difficulty": .., "correct": .., "rt_ms": ..}, ...],
            "ce_outcomes": [...],
            "ee_outcomes": [{"item_id": ..., "module": "EE", "task_number": .., "prompt_target_nclc": .., "rubric_total_20": ..}, ...],
            "eo_outcomes": [...],
            "drill_posteriors": {"CO": {"skill": "CO", "mean": .., "variance": .., "n_obs": .., "difficulty_bands_seen": [..]}, ...}
        }

    Returns a JSON dict carrying:

        {
            "mock_id": "uuid",
            "per_skill": {"CO": {"raw": .., "max_raw": .., "posterior": {...}, "n_items": ..}, ...},
            "overall_nclc": int | null,
            "overall_confident": bool,
            "bottleneck_skill": "CO|CE|EE|EO",
            "divergence_alerts": [...],
        }
    """
    co = [_to_item_outcome(o) for o in payload.get("co_outcomes", [])]
    ce = [_to_item_outcome(o) for o in payload.get("ce_outcomes", [])]
    ee = [_to_rubric_outcome(o) for o in payload.get("ee_outcomes", [])]
    eo = [_to_rubric_outcome(o) for o in payload.get("eo_outcomes", [])]

    drill_in = payload.get("drill_posteriors") or {}
    drill_posteriors = {s: _to_posterior(p) for s, p in drill_in.items()} or None

    result = score_mock_pure(
        co=co,
        ce=ce,
        ee=ee,
        eo=eo,
        drill_posteriors=drill_posteriors,
    )

    return {
        "mock_id": str(payload.get("mock_id", "")),
        "per_skill": {
            s: {
                "skill": score.skill,
                "raw": score.raw,
                "max_raw": score.max_raw,
                "n_items": score.n_items,
                "posterior": _from_posterior(score.posterior),
                "divergence_alert": score.divergence_alert,
            }
            for s, score in result.per_skill.items()
        },
        "overall_nclc": result.overall_nclc,
        "overall_confident": result.overall_confident,
        "bottleneck_skill": result.bottleneck_skill,
        "divergence_alerts": result.divergence_alerts,
    }


__all__ = ["score_mock"]
