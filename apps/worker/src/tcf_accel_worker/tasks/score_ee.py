"""Asynchronous EE scoring task (`phase5_design.md §11`).

The task ships in Phase 5 as a **pipeline shell**: the Celery task is
registered, the rubric-scorer registry is in place, and a Phase 5 stub
scorer returns a structured "not-yet-calibrated" payload. Phase 7 plugs
the real rubric scorer in by calling `register_scorer()` at import time
*without touching this module* — the hand-off contract is the
`RubricScorer` protocol below.

In Phase 5 the API doesn't yet persist `Interaction` rows to Postgres
(deferred to step 11), so this task accepts a *typed payload* dict
rather than an interaction id. When the persistence swap lands the
signature will shift to `(interaction_id: int)` without changing the
registry / scorer protocol.

Idempotency contract: a scorer must be deterministic given the same
payload. Phase 5's stub trivially satisfies this; Phase 7's calibrated
scorer is responsible for honoring the contract.
"""

from __future__ import annotations

from typing import Any, Protocol

from tcf_accel_worker.celery_app import celery_app

#: Module-level scorer registry. Keys are `rubric_version` strings
#: (e.g. `"ee.v1"`); values implement `RubricScorer`. Phase 7 registers
#: the real scorer at import time via `register_scorer()`.
_SCORER_REGISTRY: dict[str, RubricScorer] = {}


class RubricScorer(Protocol):
    """Phase 7 hand-off contract for the EE rubric scorer.

    A scorer accepts the structured payload Phase 5's drill produced
    (text, drill_kind, rubric_version, word-count metadata) and
    returns the graded-score dict the worker writes back to the
    `Interaction.graded_score` JSONB column. The dict is *open* —
    Phase 7 can include `WritingRubric.model_dump()` plus any
    auxiliary signals — but it MUST carry the keys this task asserts
    on (`phase7_status`, `rubric_version`).
    """

    def score_ee(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Score an EE payload; return the graded_score dict the worker persists."""
        ...


class _StubEEScorer:
    """Phase 5 stub: emits a 'not-yet-calibrated' marker.

    Returns a graded_score dict that:
    - keeps the rubric_version + drill_kind for traceability,
    - sets `phase7_status="stub"` so the audit can detect Phase-5-era
      rows that never received a real grade,
    - computes a few cheap metrics (word count, type-token ratio,
      connector density) that the Phase 7 scorer will likely consume
      regardless of its final rubric implementation. The audit
      (`phase5_audit.md §1` rubric-pending entries) consumes these.
    """

    def score_ee(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a deterministic pending payload."""
        text = str(payload.get("text", ""))
        words = text.split()
        n_words = len(words)
        ttr = (len({w.casefold() for w in words}) / n_words) if n_words else 0.0
        connectors = _count_connector_markers(words)
        density = (connectors / n_words * 100.0) if n_words else 0.0
        return {
            "pending": True,
            "phase7_status": "stub",
            "rubric_version": payload.get("rubric_version", "ee.v1"),
            "drill_kind": payload.get("drill_kind"),
            "metrics": {
                "word_count": n_words,
                "type_token_ratio": ttr,
                "discourse_marker_count": connectors,
                "discourse_marker_density_per_100w": density,
            },
        }


# A minimal connector seed used by the stub's discourse-marker count.
# The full list lives in `packages/content/data/connectors.fr.yaml`
# (deferred to the §17 step 14 quality gates); these are the high-
# frequency markers Phase 7 calibrates against per master prompt §1.4.
_CONNECTOR_SEED: frozenset[str] = frozenset(
    {
        # addition
        "et", "aussi", "également", "puis", "ensuite",
        # contrast
        "mais", "cependant", "néanmoins", "toutefois",
        # cause
        "car", "parce", "puisque",
        # consequence
        "donc", "ainsi", "alors",
        # conclusion
        "enfin", "finalement",
    },
)


def _count_connector_markers(words: list[str]) -> int:
    return sum(1 for w in words if w.strip(".,;:!?").casefold() in _CONNECTOR_SEED)


def register_scorer(rubric_version: str, scorer: RubricScorer) -> None:
    """Register a rubric scorer for `rubric_version` (Phase 7 hand-off).

    Calling this at Phase 7 import time replaces the Phase 5 stub
    without touching any Phase 5 code. The registry is module-level
    state; tests can swap a fake scorer in/out via `register_scorer`
    + the inverse `unregister_scorer`.

    Example:
        >>> class _Fake:
        ...     def score_ee(self, payload):
        ...         return {"phase7_status": "fake", "rubric_version": "x"}
        >>> register_scorer("x", _Fake())
        >>> get_scorer("x").score_ee({})["phase7_status"]
        'fake'
        >>> unregister_scorer("x")
    """
    _SCORER_REGISTRY[rubric_version] = scorer


def unregister_scorer(rubric_version: str) -> None:
    """Remove a scorer (test helper)."""
    _SCORER_REGISTRY.pop(rubric_version, None)


def get_scorer(rubric_version: str) -> RubricScorer:
    """Return the registered scorer for `rubric_version`, falling back to the stub."""
    return _SCORER_REGISTRY.get(rubric_version, _StubEEScorer())


@celery_app.task(name="tcf_accel.score_ee")
def score_ee(payload: dict[str, Any]) -> dict[str, Any]:
    """Score an EE interaction's payload.

    Dispatches to the registered scorer for `payload['rubric_version']`,
    falling back to the Phase 5 stub. The returned dict is what the
    worker writes back to `Interaction.graded_score` once the
    persistence swap (step 11) lands.

    Example (eager mode):
        >>> from tcf_accel_worker.celery_app import celery_app
        >>> celery_app.conf.task_always_eager = True
        >>> result = score_ee.delay({
        ...     "text": "Bonjour donc voilà",
        ...     "rubric_version": "ee.v1",
        ...     "drill_kind": "ee_task",
        ... }).get(timeout=1)
        >>> result["phase7_status"]
        'stub'
    """
    rubric_version = str(payload.get("rubric_version", "ee.v1"))
    scorer = get_scorer(rubric_version)
    return scorer.score_ee(payload)


__all__ = [
    "RubricScorer",
    "get_scorer",
    "register_scorer",
    "score_ee",
    "unregister_scorer",
]
