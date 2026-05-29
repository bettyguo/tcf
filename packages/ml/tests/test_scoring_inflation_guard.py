"""Inflation guard tests (ADR-040, Phase 7)."""

from __future__ import annotations

from tcf_accel_ml.scoring.inflation_guard import apply_inflation_guard


def test_clamps_when_llm_inflates() -> None:
    r = apply_inflation_guard(
        llm_scores={"task_completion": 5.0, "coherence_cohesion": 4.0},
        feature_predicted_scores={"task_completion": 1.0, "coherence_cohesion": 4.0},
    )
    assert r.clamped_scores["task_completion"] == 3.0  # floor + clamp_offset
    assert r.clamped_scores["coherence_cohesion"] == 4.0  # untouched
    assert r.needs_human_review is True
    assert r.clamped_dimensions == ["task_completion"]


def test_no_clamp_when_below_threshold() -> None:
    r = apply_inflation_guard(
        llm_scores={"a": 3.0, "b": 3.5},
        feature_predicted_scores={"a": 2.5, "b": 3.0},
    )
    assert r.needs_human_review is False
    assert r.clamped_dimensions == []


def test_clamp_handles_multiple_inflated_dimensions() -> None:
    r = apply_inflation_guard(
        llm_scores={"a": 5.0, "b": 5.0, "c": 2.0},
        feature_predicted_scores={"a": 1.0, "b": 1.0, "c": 1.0},
    )
    assert sorted(r.clamped_dimensions) == ["a", "b"]
    assert r.needs_human_review is True


def test_clamped_scores_stay_in_zero_five() -> None:
    r = apply_inflation_guard(
        llm_scores={"a": 5.0},
        feature_predicted_scores={"a": 5.0},  # llm − floor = 0, no clamp
    )
    assert 0.0 <= r.clamped_scores["a"] <= 5.0


def test_floor_plus_clamp_offset_bounded_at_five() -> None:
    r = apply_inflation_guard(
        llm_scores={"a": 5.0},
        feature_predicted_scores={"a": 0.0},
        threshold=3.0, clamp_offset=2.0,
    )
    # 0 + 2 = 2, well under 5.
    assert r.clamped_scores["a"] == 2.0


def test_inflation_guard_against_synthetic_nclc5_essay() -> None:
    """Anchor test for the audit's NCLC-5 cohort assertion.

    A synthetic essay at NCLC 5 should not drift to NCLC 7+ when the
    LLM critic gives an inflated score. The guard clamps each dim;
    the resulting total ≤ feature_floor + 2 per dim.
    """
    llm = {
        "task_completion": 5.0,
        "coherence_cohesion": 5.0,
        "lexical_range": 5.0,
        "grammatical_accuracy": 5.0,
        "register_appropriateness": 5.0,
    }
    floor = {dim: 1.0 for dim in llm}  # consistent with NCLC 5
    r = apply_inflation_guard(
        llm_scores=llm, feature_predicted_scores=floor,
    )
    # Each dim clamped at floor + 2 = 3.
    assert all(v == 3.0 for v in r.clamped_scores.values())
    assert r.needs_human_review is True
