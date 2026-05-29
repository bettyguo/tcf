# ADR-0028: Exam-shape floor — hard floor + soft cadence

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 5 (Practice & Drill Engines)

## Context

The 80/20 doctrine in `05_PRACTICE_AND_DRILLS.md §1.3`: roughly 80% of
practice time on drills with rich feedback, 20% on exam-shape sessions
where feedback is withheld until the end. The think doc
(`phase5_think.md §1.4`) frames the design space as soft-nudge vs
hard-gate vs hybrid; the catastrophic failure mode is the *long tail
of zero*, not the 75/25 vs 80/20 drift.

A learner doing 100/0 has built no exam-day skill at all. A learner
doing 75/25 still gets meaningful exam-shape practice. The hard
component should target the catastrophic-mode boundary, not the soft
ratio.

## Decision

**Hard floor + soft cadence.** Two distinct enforcement mechanisms,
operating at two layers:

1. **Runtime hard floor** at `POST /v1/session/start`: a non-exam-shape
   drill is refused with `409 E_SESSION_001` if the learner's rolling
   7-day exam-shape minutes are below `EXAM_SHAPE_FLOOR_MIN = 30`
   (clamped at a hard lower bound of 20 minutes — one CE half-section
   under exam pace). The 409 envelope carries
   `next_action="exam_shape"` and `dismissable=true`.

2. **Per-week dismissal** via `POST /v1/session/exam-shape/dismiss`:
   the learner can override the floor for the current ISO week. The
   dismissal is recorded as a typed `DismissalLogEntry` in
   `data/dismissal_log.jsonl` (local-only per ADR-017; never
   replicated). Chronic dismissals (≥ 4 in 8 weeks) are flagged by
   `audit-exam-shape` — doctrine remains, audit flags the divergence.

3. **Planner-side cadence post-pass**: `_enforce_exam_shape_cadence`
   walks the generated plan; on any day where the trailing 7-day
   exam-shape minutes fall below the floor, the first non-shadowing,
   non-exam-shape block is promoted to its skill's canonical
   exam-shape sibling (CO/CE → `mock_section`, EE → `writing_long`,
   EO → `speaking_mono`). Rationale text gets ` | + exam-shape
   cadence` appended.

The `EXAM_SHAPE_DRILL_TYPES` set is the canonical source of truth:
`{mock_section, writing_short, writing_long, speaking_mono,
speaking_role}`. The planner and the runtime floor both consult it.

## Consequences

- **Positive**:
  - The catastrophic-mode (zero exam-shape weeks) is structurally
    prevented at two layers — the runtime gate and the plan cadence.
  - Dismissal is a real escape hatch — the system isn't adversarial,
    but the dismissal is logged so the operator can spot abuse.
  - The default plan trivially clears the cadence (EE/EO use
    writing_*/speaking_* drill types, both exam-shape), so the
    cadence pass is a no-op in the happy path — it's the *structural
    floor* for plan-template variants that drift.
- **Negative**:
  - A brand-new learner hits the floor on their first non-exam-shape
    drill. The escape hatch (dismiss) handles this, but onboarding
    UX must make the dismiss path obvious. Tracked in the Phase 8
    UI work.
  - Chronic dismissers learn nothing structural about the doctrine —
    the audit catches them post-hoc rather than preventing it.
- **Neutral**:
  - The 30-min floor is tunable per release; the clamp at 20 min
    keeps an operator from accidentally disabling the doctrine.

## Alternatives considered

- **Soft nudge only (dashboard hint)**: rejected because the doctrine
  becomes a toolbar tip; at scale the long-tail-of-zero failure mode
  returns.
- **Hard gate (no dismissal)**: rejected because one bad UX moment
  (learner has 20 min, exam-shape needs 60) collapses trust. The
  dismissal-with-confirmation is calibrated friction.
- **Soft cadence only (no runtime gate)**: rejected because a plan
  can satisfy cadence while a learner who ignores the plan still
  drills with feedback only.

## What would change our mind

- The floor is silently dismissed > 50% of weeks across the user
  base. The "calibrated friction" hypothesis is wrong; raise the
  friction (e.g., a typed-phrase confirmation) or move closer to
  the hard gate.
- Chronic dismissers' exam-day outcomes match non-dismissers'. The
  doctrine is wrong, or exam-shape practice is doing less than we
  believed. Re-examine Phase 6's mock-exam composition before
  relaxing the floor.

## References

- `phase5_think.md §1.4`, `phase5_design.md §8`.
- `packages/sla/src/tcf_accel_sla/session/exam_shape_floor.py`.
- `packages/sla/src/tcf_accel_sla/planner/generate_plan.py::_enforce_exam_shape_cadence`.
- `apps/api/src/tcf_accel_api/routes/session.py::start` (the 409 path).
- `apps/api/src/tcf_accel_api/session_state.py::record_dismissal` (the JSONL log).
- `phase5_audit.md §10`.
