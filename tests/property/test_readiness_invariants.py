"""Hypothesis-driven readiness invariants (ADR-025 launch-blocker).

The single most important invariant: any `compute_readiness` call where
at least one skill is `confident=False` MUST return a non-green light.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from tcf_accel_sla.estimator import SkillPosterior
from tcf_accel_sla.planner import compute_readiness


@st.composite
def _posterior_strategy(draw, force_confident: bool | None = None):
    if force_confident is True:
        n_obs = draw(st.integers(min_value=40, max_value=200))
        variance = draw(st.floats(min_value=0.05, max_value=0.39, allow_nan=False))
        spread = draw(st.integers(min_value=3, max_value=8))
    elif force_confident is False:
        # At least one of the three predicates fails.
        n_obs = draw(st.integers(min_value=0, max_value=200))
        variance = draw(st.floats(min_value=0.05, max_value=3.0, allow_nan=False))
        spread = draw(st.integers(min_value=0, max_value=8))
    else:
        n_obs = draw(st.integers(min_value=0, max_value=200))
        variance = draw(st.floats(min_value=0.05, max_value=3.0, allow_nan=False))
        spread = draw(st.integers(min_value=0, max_value=8))
    bands = frozenset(range(spread)) if spread > 0 else frozenset()
    mean = draw(st.floats(min_value=1.0, max_value=12.0, allow_nan=False))
    return SkillPosterior(
        skill="CO",  # we vary skill at construction site
        mean=mean,
        variance=variance,
        n_obs=n_obs,
        difficulty_bands_seen=bands,
    )


@given(
    posts=st.lists(_posterior_strategy(), min_size=4, max_size=4),
    target=st.integers(min_value=1, max_value=12),
    streak=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=200, deadline=None)
def test_no_green_when_any_skill_unconfident(
    posts: list[SkillPosterior], target: int, streak: int,
) -> None:
    """ADR-025: 🟢 is forbidden if any skill is not confident."""
    posteriors = {
        skill: SkillPosterior(
            skill=skill,  # type: ignore[arg-type]
            mean=p.mean,
            variance=p.variance,
            n_obs=p.n_obs,
            difficulty_bands_seen=p.difficulty_bands_seen,
        )
        for skill, p in zip(("CO", "CE", "EE", "EO"), posts, strict=True)
    }
    any_not_confident = any(not p.confident for p in posteriors.values())
    r = compute_readiness(
        posteriors, target_nclc=target, canonical_mock_streak_green=streak,
    )
    if any_not_confident:
        assert r.light != "green", (
            f"green returned with not-confident posteriors: "
            f"{[(s, p.confident) for s, p in posteriors.items()]}"
        )
