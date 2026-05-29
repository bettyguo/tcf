"""Allocator behavior tests.

Invariants:
- Allocations always sum to `total_minutes`.
- Every skill receives ≥ `SKILL_FLOOR_MINUTES`.
- The weakest skill receives the most minutes (given the β weighting).
- The production-skill floor: when bottleneck is EE or EO, EE+EO ≥ 50%.
- Re-allocation is deterministic for fixed inputs.
"""

from __future__ import annotations

import pytest
from tcf_accel_sla.estimator import SkillPosterior
from tcf_accel_sla.planner.allocator import (
    SKILL_FLOOR_MINUTES,
    SKILL_ORDER,
    allocate,
)


def _posteriors(co: float, ce: float, ee: float, eo: float) -> dict:
    return {
        "CO": SkillPosterior(skill="CO", mean=co, variance=0.3, n_obs=40),
        "CE": SkillPosterior(skill="CE", mean=ce, variance=0.3, n_obs=40),
        "EE": SkillPosterior(skill="EE", mean=ee, variance=0.3, n_obs=40),
        "EO": SkillPosterior(skill="EO", mean=eo, variance=0.3, n_obs=40),
    }


def test_sum_equals_total_minutes() -> None:
    posts = _posteriors(co=6, ce=6, ee=5, eo=5)
    alloc = allocate(60, posts, target_nclc=9)
    assert sum(alloc.values()) == 60


def test_floor_enforced() -> None:
    posts = _posteriors(co=9, ce=9, ee=9, eo=9)  # all at target, alphas tiny
    alloc = allocate(80, posts, target_nclc=9)
    for skill in SKILL_ORDER:
        assert alloc[skill] >= SKILL_FLOOR_MINUTES


def test_production_bottleneck_floor() -> None:
    """ADR-027 + Phase 4 anti-criterion: CO=CE=B2, EE=B1, EO=A2, target NCLC 9
    → EE+EO must take ≥ 50% of the daily minutes."""
    # B2 ≈ NCLC 7, B1 ≈ NCLC 5, A2 ≈ NCLC 3.
    posts = _posteriors(co=7, ce=7, ee=5, eo=3)
    alloc = allocate(120, posts, target_nclc=9)
    production_share = (alloc["EE"] + alloc["EO"]) / 120.0
    assert production_share >= 0.50, (
        f"production share {production_share:.2%} below 50%; alloc={alloc}"
    )


def test_weakest_skill_gets_most_minutes_when_below_target() -> None:
    posts = _posteriors(co=7, ce=7, ee=7, eo=3)
    alloc = allocate(120, posts, target_nclc=9)
    assert alloc["EO"] == max(alloc.values())


def test_deterministic_under_identical_inputs() -> None:
    posts = _posteriors(co=7, ce=6, ee=5, eo=4)
    a1 = allocate(100, posts, target_nclc=9)
    a2 = allocate(100, posts, target_nclc=9)
    assert a1 == a2


def test_total_below_floor_rejected() -> None:
    posts = _posteriors(co=7, ce=7, ee=7, eo=7)
    with pytest.raises(ValueError, match="below 4×floor"):
        allocate(30, posts, target_nclc=9)


def test_invalid_target_rejected() -> None:
    posts = _posteriors(co=7, ce=7, ee=7, eo=7)
    with pytest.raises(ValueError, match="target_nclc"):
        allocate(120, posts, target_nclc=0)
    with pytest.raises(ValueError, match="target_nclc"):
        allocate(120, posts, target_nclc=13)


def test_missing_skill_raises_keyerror() -> None:
    posts = _posteriors(co=7, ce=7, ee=7, eo=7)
    del posts["EE"]
    with pytest.raises(KeyError):
        allocate(120, posts, target_nclc=9)
