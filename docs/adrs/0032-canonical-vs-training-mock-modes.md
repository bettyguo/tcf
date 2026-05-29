# ADR-0032: Canonical and training mock modes

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 6 (Mock Exam Engine)

## Context

`06_MOCK_EXAM_ENGINE.md §1.1` and `phase6_think.md §1.1` make a
load-bearing claim: a mock exam that matches FEI content but not
exam-day **psychology** is worse than no mock — it certifies confidence
the learner has not earned. The simulator must reproduce the timing
discipline (strict module timers, no replays, no mid-test feedback)
and the "abnormal-exit-forfeits" discipline.

But real laptops crash, browsers misbehave, kids walk into rooms. A
fully-strict mode is the right *default* — and the right thing for the
"am I ready?" verdict — but a learner who genuinely had a system glitch
shouldn't be forced to wait a week for the next slot. There needs to be
a relaxed mode for diagnostic practice.

The think doc considered three options:

- (a) Single strict mode, forfeit-or-nothing.
  Brutal; learner trust erodes after the first false forfeit.
- (b) Single forgiving mode with full pause/resume.
  The headline NCLC becomes meaningless because the learner can game
  the test (re-read a CE passage after consulting notes mid-pause).
- (c) Two modes, both supported, with the planner forcing canonical
  cadence.

## Decision

**(c) Two modes — `canonical` and `training` — with strict separation
of effect.**

1. **`canonical`** (default):
   - Strict timing per module per `MODULE_DURATION_S`.
   - Tab-blur > `CANONICAL_TAB_BLUR_GRACE_S` (5 s) → forfeit.
   - Process abort → forfeit.
   - **Forfeited mocks do not update the NCLC posterior.**
   - **Forfeited mocks DO count for the journal**, so audit can detect
     "this learner forfeits 40% of starts" — itself a prep signal.
   - Only canonical mocks contribute to the
     `canonical_mock_streak_green` counter that Phase 4's readiness
     gate (ADR-025 + R-004) requires for a 🟢 verdict.

2. **`training`**:
   - Same item shape and timing as canonical.
   - Tab-blur and process-abort are **no-ops** (the route returns 200
     and does nothing — the player UI may surface a pause/resume
     control here).
   - Submitted training mocks **are** scored and shown in the
     trajectory chart with a visual marker, but they **do not** update
     the long-running drill posterior and **do not** count toward the
     canonical-streak.
   - Looser cadence: 1/day instead of 1/w → 2/w → 3/w.

3. **The planner forces a canonical mock at least once every 14 days
   in week 4+.** A two-week training-only streak blocks the readiness
   🟢 even if every other gate is green.

4. The wire shape (`MockExamState.mode`) is the frozen Phase 2 enum
   `Literal["canonical", "training"]`; the state machine
   (`tcf_accel_sla.mock_exam.transition`) gates the `tab_blur_exceeded`
   and `process_abort` events on `mode == "canonical"`.

## Consequences

- **Positive**:
  - The "am I ready?" verdict remains trustworthy. A green streak
    can only be earned under canonical conditions.
  - Learners get an escape hatch for genuine glitches without
    inflating the headline NCLC.
  - The mode separation is *visible* in the report (training mocks
    show a distinct badge), so a learner cannot accidentally treat a
    training result as canonical.
- **Negative**:
  - Two code paths for everything (scoring, state machine, report).
    The state-machine implementation factors this with `mode` as an
    argument; the report renderer factors it with a `mode` field on
    the data record. Cost: ~20 lines of branching across the
    codebase.
- **Neutral**:
  - The 5-second grace window is tunable but the floor is documented;
    operators can lengthen but not eliminate it without an ADR.

## Alternatives considered

- See Context (a) and (b).
- **Mode chosen at submit time, not start time**: rejected because
  it lets a learner who's doing well in a mock retroactively claim
  "canonical"; mode must be locked at start.
- **Allow a single pause in canonical (up to N seconds)**: rejected
  because every pause is a potential exfiltration point (consult
  notes, listen again), and 5 seconds is already enough to dismiss
  a system notification.

## What would change our mind

- A statistically meaningful share of canonical forfeits turn out to
  be benign (clear pattern of "tab-blur for 6–10 s, learner returns
  immediately"). We'd extend the grace window and emit a soft
  warning instead of an immediate forfeit, gated by a new ADR.
- Training-mode mocks turn out to drive over-confidence (learners
  treat training scores as canonical despite the badging). We'd
  remove the trajectory-chart marker for training mocks entirely.

## References

- `06_MOCK_EXAM_ENGINE.md §1.5`.
- `phase6_think.md §2.1`, `phase6_design.md §3` (state machine), §10.3
  (forfeit route).
- `packages/sla/src/tcf_accel_sla/mock_exam/state.py` — transition() in canonical mode forfeits.
- `apps/api/src/tcf_accel_api/routes/mock_exam.py` — `/tab-blur` enforcement.
- ADR-0025 — posterior confidence gate is the upstream rule.
- ADR-0033 — cadence cap.
