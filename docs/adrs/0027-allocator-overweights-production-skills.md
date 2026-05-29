# ADR-0027: The bottleneck-driven time allocator over-weights production skills (β_EE=1.4, β_EO=1.5)

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 4 (Learner Model)

## Context

The planner needs to allocate a daily minute budget across the four
skills (CO, CE, EE, EO). Naive "spend more time on the weakest skill"
(`minutes_s ∝ (target - μ_s)²`) under-allocates production skills (EE,
EO) because:

- Production-skill posteriors converge more slowly per minute (writing
  and speaking ability are harder to move than receptive vocab).
- A production-skill weakness is dispositive for the TCF Canada exam
  outcome: the headline score is `min(CO, CE, EE, EO)` for immigration
  thresholds, but production scores have higher variance and are more
  often the bottleneck per `02_ARCHITECTURE.md` benchmarks.

Master prompt §2.3: "production-skill floor when the bottleneck is EE
or EO."

The Phase 4 audit anti-criterion explicitly names this:

> ❌ Any allocator output that violates the production-skill floor when
> the bottleneck is EE or EO.

## Decision

The allocator multiplies each skill's "gap-squared" weight by a
per-skill `β`:

| Skill | β    |
|-------|------|
| CO    | 1.0  |
| CE    | 0.9  |
| EE    | 1.4  |
| EO    | 1.5  |

Reception skills (CO, CE) are roughly co-equal; production skills get
40–50% over-weighting. The exact values are calibrated against the
12 synthetic cohorts in `tests/pedagogy/synthetic_cohorts.py` — the
audit metric "a learner with CO=B2/CE=B2/EE=B1/EO=A2 targeting NCLC 9
spends ≥ 50% of their daily minutes on EE+EO" is the load-bearing
test (`tests/pedagogy/test_synthetic_cohorts.py::test_production_bottleneck_floor`).

A `SKILL_FLOOR_MINUTES = 10` floor per skill prevents the allocator
from dropping any skill to zero — even a fully-on-target skill needs
review-time minutes to defend against decay.

## Consequences

- **Positive**:
  - Production-skill bottlenecks get the time they need to move.
  - The allocator is one function, one formula — easy to audit and to
    explain in the plan rationale.
  - The β values are tunable; updating them is a one-line ADR-0027
    amendment, not a refactor.
- **Negative**:
  - When a learner is unusually strong on production and weak on
    reception (cohort #11 in the synthetic set), the allocator still
    over-weights production a bit. This is the correct error direction
    (production is harder to recover late) but worth naming.
- **Neutral**:
  - The β values combine with the (target - μ)² term; the *interaction*
    matters more than either factor alone. A change to β alone won't
    affect cohorts already at-target.

## Alternatives considered

- **Equal weights (β = 1 for all)**: rejected because the synthetic-
  cohort audit shows the all-equal allocator under-allocates production
  by 18% on average vs the β-weighted version, missing the production
  bottleneck on cohorts 3, 5, 8.
- **Steeper production weighting (β_EE=2.0, β_EO=2.5)**: rejected
  because cohort 11 (production-strong) ends up with reception below
  10 min floor and a degraded retention picture.
- **Dynamic β derived from learning rate**: rejected for v1 — adds a
  per-user state we don't have data to fit. *Would reconsider*: at
  > 10k users, we can fit per-cohort β values.

## What would change our mind

- The synthetic-cohort audit shows the current β values miss a real
  bottleneck on a new cohort archetype (e.g., the "diaspora speaker
  with strong EO but weak EE" cohort that the current 12 do not cover).
- Real users show systematic over-allocation to production (e.g.,
  median user spends > 60% on EE+EO when their actual bottleneck is CO)
  → re-tune.

## References

- Master prompt §2.3.
- `04_LEARNER_MODEL.md §2.5` + `§4` (anti-criterion).
- `packages/sla/src/tcf_accel_sla/planner/allocator.py`.
- `tests/pedagogy/synthetic_cohorts.py`.
