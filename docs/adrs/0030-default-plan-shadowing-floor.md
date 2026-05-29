# ADR-0030: Mandatory 10-min/day shadowing reservation in default plans

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 5 (Practice & Drill Engines)

## Context

Master prompt §2.1.6: "Shadowing for prosody. Daily 10-min shadowing
block using Canadian and standard-European French audio."

The pedagogical evidence is consistent and strong: shadowing is the
single highest-ROI prosody intervention for solo learners. The
practical risk is that a learner faced with a daily-minute budget will
deprioritize shadowing for the more rubric-visible drills (writing,
mock sections). The system's job is to make the floor structural — a
learner can deprioritize *between* the production drills, but not skip
the shadowing reservation entirely.

## Decision

**The planner reserves 10 min/day of shadowing as the day's first
block, before the bottleneck allocator runs.**

Concrete shape:

1. `_reserve_shadowing(daily_minutes_budget)` carves
   `DEFAULT_SHADOWING_MINUTES = 10` out of the budget. The allocator
   then distributes the *remaining* minutes across CO/CE/EE/EO under
   the production-skill over-weighting (ADR-027).

2. `_shadowing_block(minutes)` constructs the canonical block:
   `skill="CO"`, `drill_type="shadowing"`. It's prepended to every
   daily block list so the UI shows it first.

3. The reservation is clamped at `SHADOWING_MIN_FLOOR = 3` minutes.
   An operator who configures `shadowing_minutes=1` gets 3 silently;
   the floor cannot be set to zero via configuration. The only path
   to a zero-shadowing day is editing the plan-template module
   directly — a deliberate three-step act, not a one-click toggle.

4. A daily budget too tight to fit 10 (shadowing) + 4×10 (allocator
   per-skill floor) = 50 minutes raises a clear `ValueError` at
   `generate_plan` time. The planner surfaces this rather than
   silently dropping the shadowing reservation.

## Consequences

- **Positive**:
  - Prosody-acquisition pressure is structural, not optional. A
    learner who never opens the shadowing block still has it logged
    against their daily allocation — the audit can spot
    chronic-skippers.
  - The reservation is carved out *before* the allocator, so the
    production-skill over-weighting from ADR-027 operates on the
    remainder and stays calibrated.
- **Negative**:
  - At very tight budgets (< 50 min/day), the planner refuses to
    generate a plan rather than fitting one in. This is the right
    error direction — the alternative is silently violating ADR-027
    or ADR-030.
- **Neutral**:
  - The 10-minute number is from the master prompt; the floor of 3
    is calibrated to "any prosody practice > none" while preserving
    the per-skill 10-minute floor for the four modules.

## Alternatives considered

- **No reservation — shadowing rotates like any other CO drill type**:
  rejected because the existing `select_drill_type` rotated
  shadowing in 1/3 of CO days. Master prompt §2.1.6 says *daily*.
- **Subtract shadowing from CO's allocator output after the fact**:
  rejected because it lets the allocator over-allocate CO and then
  retroactively "spend" some on shadowing, which double-counts.
  Reserving up-front keeps the math clean.
- **Operator config knob to disable shadowing entirely**: explicitly
  rejected. The pedagogical doctrine is structural; an operator who
  needs to disable it for a learner with a recorded voice disorder
  should edit the plan template (with comment and ADR amendment),
  not toggle a setting.

## What would change our mind

- A real cohort of learners with documented daily shadowing
  compliance shows no prosody improvement over a no-shadowing cohort.
  We'd revisit the master-prompt commitment (which itself cites the
  prosody literature) before tweaking the implementation.
- The default plan's per-day minute budget falls below 50 in
  production (e.g., a "10 minutes between meetings" mode the UX team
  adds). We'd revise the floor for shorter-session modes specifically,
  not the default 12-week intensive plan.

## References

- Master prompt §2.1.6.
- `phase5_design.md §17` step 10.
- `packages/sla/src/tcf_accel_sla/planner/generate_plan.py::_reserve_shadowing`,
  `_shadowing_block`.
- `tests/pedagogy/test_synthetic_cohorts.py` (cohort-level invariant).
- `tests/pedagogy/test_drill_diversity.py` (shadowing is in the
  diversity set on every CO day).
- `packages/sla/tests/test_plan_shadowing_and_cadence.py`.
- `phase5_audit.md §11`.
