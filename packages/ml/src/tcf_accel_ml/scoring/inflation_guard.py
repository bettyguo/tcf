"""ADR-040 inflation guard.

If the LLM critic returns a rubric-dimension score more than `threshold`
points above the feature-floor prediction, clamp it to
`feature_floor + clamp_offset` and flag the rubric as
`needs_human_review`.

The clamp is per-dimension; one inflated dimension does not clamp the
others. The function is pure and decisionable in tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InflationGuardResult:
    """Post-guard scores + clamp metadata."""

    clamped_scores: dict[str, float]
    needs_human_review: bool
    clamped_dimensions: list[str]


def apply_inflation_guard(
    *,
    llm_scores: dict[str, float],
    feature_predicted_scores: dict[str, float],
    threshold: float = 3.0,
    clamp_offset: float = 2.0,
) -> InflationGuardResult:
    """Clamp inflated LLM scores against the feature floor.

    Args:
        llm_scores: Per-rubric LLM-critic scores in 0–5.
        feature_predicted_scores: Per-rubric feature-only prediction
            in 0–5 (e.g., from a baseline regressor or the calibrator
            run with `w_llm = 0`).
        threshold: Allowed LLM−feature gap before clamping.
        clamp_offset: How far above the feature floor the clamped score
            sits.

    Returns:
        `InflationGuardResult` with the post-clamp scores and a
        `needs_human_review` flag set when any dimension was clamped.

    Example:
        >>> r = apply_inflation_guard(
        ...     llm_scores={"task_completion": 5.0, "coherence_cohesion": 4.0},
        ...     feature_predicted_scores={"task_completion": 1.0, "coherence_cohesion": 4.0},
        ... )
        >>> r.clamped_scores["task_completion"]
        3.0
        >>> r.needs_human_review
        True
        >>> r.clamped_dimensions
        ['task_completion']

        >>> r = apply_inflation_guard(
        ...     llm_scores={"a": 3.0}, feature_predicted_scores={"a": 2.5},
        ... )
        >>> r.needs_human_review
        False
    """
    clamped: dict[str, float] = {}
    inflated: list[str] = []
    for dim, llm in llm_scores.items():
        floor = feature_predicted_scores.get(dim, llm)
        if llm - floor > threshold:
            new = floor + clamp_offset
            clamped[dim] = max(0.0, min(5.0, new))
            inflated.append(dim)
        else:
            clamped[dim] = max(0.0, min(5.0, llm))
    return InflationGuardResult(
        clamped_scores=clamped,
        needs_human_review=bool(inflated),
        clamped_dimensions=inflated,
    )


__all__ = ["InflationGuardResult", "apply_inflation_guard"]
