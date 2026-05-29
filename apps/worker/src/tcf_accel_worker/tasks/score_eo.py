"""Asynchronous EO scoring task (`phase5_design.md §11`).

Mirrors `score_ee`: pipeline shell + Phase 7 hand-off registry. The
drill itself has already run ASR → MFA → prosody → `PronunciationSignal`
at grade time (`tcf_accel_sla.drills._eo_common`), so the worker
inherits the pre-computed signal in the payload and routes to the
registered scorer.

The Phase 5 stub returns a `SpeakingRubric`-shaped pending dict, with
the pronunciation signal's `display_label` re-surfaced for traceability.
Phase 7 plugs in the real rubric scorer via `register_scorer()` —
identical pattern to `score_ee`, distinct registry.
"""

from __future__ import annotations

from typing import Any, Protocol

from tcf_accel_worker.celery_app import celery_app

_SCORER_REGISTRY: dict[str, EORubricScorer] = {}


class EORubricScorer(Protocol):
    """Phase 7 hand-off contract for the EO rubric scorer.

    The payload carries `transcript`, `duration_s`, `task_number`,
    `rubric_version`, and the `pronunciation_display_label` from the
    `PronunciationSignal` (the planner reads the raw score elsewhere;
    the scorer consumes whatever fields it needs, with the same
    privacy posture as `score_ee`).
    """

    def score_eo(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Score an EO payload; return the graded_score dict the worker persists."""
        ...


class _StubEOScorer:
    """Phase 5 stub: emits a 'not-yet-calibrated' marker for EO.

    Computes a few cheap signals the Phase 7 scorer will likely consume
    (target-duration deviation, speech-rate WPM, pronunciation
    display_label) and packages them under `phase7_status="stub"`.
    """

    def score_eo(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a deterministic pending payload for EO."""
        duration_s = float(payload.get("duration_s", 0.0) or 0.0)
        target_duration_s = float(payload.get("target_duration_s", 0.0) or 0.0)
        deviation = (
            (duration_s - target_duration_s) / target_duration_s if target_duration_s > 0 else None
        )
        return {
            "pending": True,
            "phase7_status": "stub",
            "rubric_version": payload.get("rubric_version", "eo.v1"),
            "drill_kind": payload.get("drill_kind"),
            "task_number": payload.get("task_number"),
            "metrics": {
                "duration_s": duration_s,
                "target_duration_s": target_duration_s,
                "duration_deviation_ratio": deviation,
                "speech_rate_wpm": payload.get("speech_rate_wpm"),
                "pause_count": payload.get("pause_count"),
                "pronunciation_display_label": payload.get(
                    "pronunciation_display_label",
                ),
            },
        }


def register_scorer(rubric_version: str, scorer: EORubricScorer) -> None:
    """Register an EO rubric scorer for `rubric_version` (Phase 7 hand-off).

    Calling this at Phase 7 import time replaces the Phase 5 stub
    without touching any Phase 5 code. Symmetric to the `score_ee`
    registry; distinct namespace so the two scorers can't be confused.
    """
    _SCORER_REGISTRY[rubric_version] = scorer


def unregister_scorer(rubric_version: str) -> None:
    """Remove a scorer (test helper)."""
    _SCORER_REGISTRY.pop(rubric_version, None)


def get_scorer(rubric_version: str) -> EORubricScorer:
    """Return the registered scorer for `rubric_version`, else the Phase 5 stub."""
    return _SCORER_REGISTRY.get(rubric_version, _StubEOScorer())


@celery_app.task(name="tcf_accel.score_eo")
def score_eo(payload: dict[str, Any]) -> dict[str, Any]:
    """Score an EO interaction's payload.

    Dispatches to the registered scorer for `payload['rubric_version']`,
    falling back to the Phase 5 stub. The returned dict is what the
    worker writes back to `Interaction.graded_score` once the
    persistence swap (step 11) lands.

    Example (eager mode):
        >>> from tcf_accel_worker.celery_app import celery_app
        >>> celery_app.conf.task_always_eager = True
        >>> result = score_eo.delay(
        ...     {
        ...         "transcript": "bonjour le monde",
        ...         "duration_s": 10.0,
        ...         "target_duration_s": 15.0,
        ...         "rubric_version": "eo.v1",
        ...         "drill_kind": "eo_task",
        ...         "task_number": 1,
        ...     }
        ... ).get(timeout=1)
        >>> result["phase7_status"]
        'stub'
    """
    rubric_version = str(payload.get("rubric_version", "eo.v1"))
    scorer = get_scorer(rubric_version)
    return scorer.score_eo(payload)


__all__ = [
    "EORubricScorer",
    "get_scorer",
    "register_scorer",
    "score_eo",
    "unregister_scorer",
]
