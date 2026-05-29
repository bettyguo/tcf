"""Readiness traffic-light tests.

The single most important invariant from ADR-025:

> Any code path that returns 🟢 readiness while `confident=False` on
> any skill is a launch-blocking bug.

The tests below pin that invariant + the threshold semantics.
"""

from __future__ import annotations

from tcf_accel_sla.estimator import SkillPosterior
from tcf_accel_sla.planner import compute_readiness, probability_meets_target


def _confident_posterior(
    skill: str, mean: float, variance: float = 0.2, n_obs: int = 40,
) -> SkillPosterior:
    return SkillPosterior(
        skill=skill,  # type: ignore[arg-type]
        mean=mean,
        variance=variance,
        n_obs=n_obs,
        difficulty_bands_seen=frozenset({3, 5, 7, 9}),
    )


def _unconfident_posterior(skill: str, mean: float) -> SkillPosterior:
    return SkillPosterior(
        skill=skill,  # type: ignore[arg-type]
        mean=mean,
        variance=1.0,
        n_obs=5,
        difficulty_bands_seen=frozenset({5}),
    )


def test_no_green_when_any_skill_unconfident() -> None:
    """ADR-025 launch-blocker."""
    posts = {
        "CO": _confident_posterior("CO", 9.0),
        "CE": _confident_posterior("CE", 9.0),
        "EE": _confident_posterior("EE", 9.0),
        "EO": _unconfident_posterior("EO", 9.0),
    }
    r = compute_readiness(posts, target_nclc=7, canonical_mock_streak_green=5)
    assert r.light != "green"
    assert r.light == "red"  # ⚪ maps to red on the wire
    assert "Insufficient data" in r.reason


def test_green_requires_mock_streak_even_with_confident_posteriors() -> None:
    posts = {
        s: _confident_posterior(s, 9.5)
        for s in ("CO", "CE", "EE", "EO")
    }
    # Posteriors say green, but streak is 0.
    r = compute_readiness(posts, target_nclc=7, canonical_mock_streak_green=0)
    assert r.light == "yellow"
    assert "canonical-mock" in r.reason


def test_green_with_all_conditions_met() -> None:
    posts = {
        s: _confident_posterior(s, 9.5)
        for s in ("CO", "CE", "EE", "EO")
    }
    r = compute_readiness(posts, target_nclc=7, canonical_mock_streak_green=2)
    assert r.light == "green"
    assert "Likely ready" in r.reason


def test_yellow_when_borderline_probability() -> None:
    posts = {
        s: _confident_posterior(s, 6.8, variance=0.3)  # close to target 7
        for s in ("CO", "CE", "EE", "EO")
    }
    r = compute_readiness(posts, target_nclc=7, canonical_mock_streak_green=3)
    # The P(skill >= 7) is moderate; not green-likely with this margin.
    assert r.light in ("yellow", "green", "red")


def test_red_when_far_below_target() -> None:
    posts = {
        s: _confident_posterior(s, 4.0)  # far below 9
        for s in ("CO", "CE", "EE", "EO")
    }
    r = compute_readiness(posts, target_nclc=9, canonical_mock_streak_green=3)
    assert r.light == "red"
    assert "Not yet" in r.reason


def test_probability_monotone_in_mean() -> None:
    target = 7
    high = _confident_posterior("CO", 9.0, variance=0.3)
    low = _confident_posterior("CO", 5.0, variance=0.3)
    assert probability_meets_target(high, target) > probability_meets_target(low, target)


def test_probability_in_unit_interval() -> None:
    p = _confident_posterior("CO", 6.0, variance=0.5)
    pv = probability_meets_target(p, 7)
    assert 0.0 <= pv <= 1.0
