"""Phase 4 synthetic-cohort audit.

Each cohort is run through `allocate()` + `generate_plan()`; the
following audit-anti-criteria are checked (`04_LEARNER_MODEL.md §4`):

- Allocator over-weights production skills when bottleneck is EE or EO.
- Generated plans don't promise the impossible (no plan that claims
  > 5-NCLC improvement in 12 weeks).
- A fresh-posterior cohort (no diagnostic) → readiness ⚪/red.
- For each cohort, the plan output is deterministic w.r.t inputs.
"""

from __future__ import annotations

import re
from datetime import date
from uuid import UUID

from tcf_accel.ids import UserId
from tcf_accel_sla.estimator import bootstrap_posterior
from tcf_accel_sla.planner import PlannerInputs, allocate, compute_readiness, generate_plan
from tcf_accel_sla.planner.allocator import SKILL_FLOOR_MINUTES
from tcf_accel_sla.planner.generate_plan import DEFAULT_HORIZON_DAYS

from tests.pedagogy.synthetic_cohorts import COHORTS, Cohort


def _user_id() -> UserId:
    return UserId(UUID(int=42))


def _max_plan_gain(cohort: Cohort) -> float:
    """Max simulated NCLC delta across all skills in the cohort's plan."""
    posteriors = cohort.confident_posteriors()
    plan = generate_plan(
        PlannerInputs(
            user_id=_user_id(),
            posteriors=posteriors,
            target_nclc=cohort.target_nclc,
            daily_minutes_budget=60,
            start_date=date(2026, 6, 1),
            horizon_days=DEFAULT_HORIZON_DAYS,
        ),
    )
    # Read the plan's rationale-projected min vs starting min as the proxy.
    starting_min = min(p.mean for p in posteriors.values())
    # Parse the rationale's projected number (it's the last float in the str).
    text = plan.rationale
    m = re.findall(r"-?\d+\.\d+", text)
    projected_min = float(m[-1]) if m else starting_min
    return projected_min - starting_min


def test_every_cohort_alloc_sums_to_budget() -> None:
    for cohort in COHORTS:
        alloc = allocate(
            total_minutes=120,
            posteriors=cohort.confident_posteriors(),
            target_nclc=cohort.target_nclc,
        )
        assert sum(alloc.values()) == 120, f"cohort {cohort.id} alloc sum != 120"
        for skill, mins in alloc.items():
            assert mins >= SKILL_FLOOR_MINUTES, (
                f"cohort {cohort.id} skill {skill}: {mins} < floor"
            )


def test_production_bottleneck_cohorts_get_50pct_production() -> None:
    """Cohort 6 (EE bottleneck) + 7 (EO bottleneck): EE+EO ≥ 50% of budget."""
    for cohort_id in (6, 7):
        cohort = next(c for c in COHORTS if c.id == cohort_id)
        alloc = allocate(
            total_minutes=120,
            posteriors=cohort.confident_posteriors(),
            target_nclc=cohort.target_nclc,
        )
        share = (alloc["EE"] + alloc["EO"]) / 120.0
        assert share >= 0.50, (
            f"cohort {cohort.id} ({cohort.label}): EE+EO share {share:.2%} < 50%"
        )


def test_plan_does_not_promise_the_impossible() -> None:
    """Anti-criterion: no plan claims NCLC 11 in 12 weeks from NCLC 4 — i.e.
    no projected delta > 5 NCLC."""
    for cohort in COHORTS:
        delta = _max_plan_gain(cohort)
        assert delta <= 5.0, (
            f"cohort {cohort.id}: plan projects +{delta:.1f} NCLC in 12 weeks"
        )


def test_plan_generation_deterministic_modulo_timestamp() -> None:
    """Same inputs → same daily blocks (`generated_at` and `id` may differ)."""
    cohort = COHORTS[0]
    inputs = PlannerInputs(
        user_id=_user_id(),
        posteriors=cohort.confident_posteriors(),
        target_nclc=cohort.target_nclc,
        daily_minutes_budget=60,
        start_date=date(2026, 6, 1),
        horizon_days=14,
    )
    p1 = generate_plan(inputs)
    p2 = generate_plan(inputs)
    assert p1.horizon_days == p2.horizon_days
    # Daily blocks structure must be identical.
    assert [(d.date, d.total_minutes) for d in p1.daily_blocks] == [
        (d.date, d.total_minutes) for d in p2.daily_blocks
    ]
    # Allocations per block must match.
    for d1, d2 in zip(p1.daily_blocks, p2.daily_blocks, strict=True):
        assert [(b.skill, b.minutes) for b in d1.blocks] == [
            (b.skill, b.minutes) for b in d2.blocks
        ]


def test_fresh_posteriors_yield_insufficient_data_readiness() -> None:
    """`04_LEARNER_MODEL.md §4` anti-criterion + ADR-025."""
    fresh = {
        skill: bootstrap_posterior(skill=skill, self_report_nclc=5.0)
        for skill in ("CO", "CE", "EE", "EO")
    }
    r = compute_readiness(fresh, target_nclc=7, canonical_mock_streak_green=10)
    assert r.light == "red"
    assert "Insufficient data" in r.reason


def test_at_target_cohort_still_respects_floors() -> None:
    """Cohort 12 (already at target): allocator still gives every skill ≥ floor."""
    cohort = next(c for c in COHORTS if c.id == 12)
    alloc = allocate(
        total_minutes=60,
        posteriors=cohort.confident_posteriors(),
        target_nclc=cohort.target_nclc,
    )
    for skill in ("CO", "CE", "EE", "EO"):
        assert alloc[skill] >= SKILL_FLOOR_MINUTES
