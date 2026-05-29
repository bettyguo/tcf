# ADR-0034: Track drill and mock posteriors separately; alert on divergence

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 6 (Mock Exam Engine)

## Context

The system has two distinct evidence streams for per-skill ability:

- **The drill posterior** — accumulated across hundreds of short
  practice items over weeks. Phase 4 owns this. Its mean is the
  system's "how good is this learner at the underlying skill?"
  best-estimate.
- **The mock posterior** — built from the ~84 items of a single
  full-length mock under exam-day conditions.

Two failure modes can drive these apart by more than the noise floor:

1. **Drill overfitting**: drill posterior climbs because the learner
   has learned to pattern-match the drill format, but the underlying
   skill hasn't transferred to the 2h47 exam shape. The mock
   posterior stays low.
2. **Mock bank miscalibration**: the drill bank and the mock bank
   diverge in IRT difficulty calibration (the mock bank gets seen
   less often, so its calibration drifts). The mock posterior comes
   out high even though drill says the learner is weak.

Either is diagnostically important. Either degrades the headline NCLC
verdict if collapsed into a single number.

`06_MOCK_EXAM_ENGINE.md §2.4` and `phase6_think.md §1.2` mandate:

- Keep the two posteriors separate.
- Both shown in the report (trajectory section).
- Alert if `|drill.mean - mock.mean| ≥ threshold`.

Choices considered:

- (a) Collapse to a single posterior (mock evidence folds into the
  drill posterior immediately). Hides the diagnostic signal.
- (b) Track separately but never reconcile. Wastes the alert
  opportunity.
- (c) Track separately + threshold-based alert + the existing
  readiness gate (ADR-025) refuses 🟢 if any per-skill posterior is
  not confident.

## Decision

**(c) Track separately, alert at `|Δ| ≥ 2.0` NCLC, surface to both
the learner and the operator.**

1. **The mock scorer (`tcf_accel_sla.mock_exam.score_mock`) builds a
   fresh posterior** from the mock's items only (`bootstrap_posterior`
   + the per-item `update_with_*` calls). It does *not* see the
   user's drill posterior — that posterior is passed in only for
   divergence comparison.

2. **`DRILL_MOCK_DIVERGENCE_THRESHOLD = 2.0` NCLC**. The threshold
   matches the existing readiness CI-band width and the empirical
   "1 NCLC ≈ 1 σ" rule. A divergence of 2 σ is too large to be noise.

3. **The alert string** carries the skill, both means, the
   direction, and a hypothesis ("review for bank calibration" when
   mock > drill, "review for drill overfitting" when drill > mock).
   The string is shown in the learner-facing report (section 1,
   below the headline) and emitted as a structured field
   (`MockSkillScore.divergence_alert`) for the operator's audit log.

4. **The two posteriors remain separate inside `UserState`.** The
   long-running drill posterior continues to drive the planner; the
   mock posterior is local to the mock-exam record. The trajectory
   chart (report section 5) overlays the two.

5. **The Phase 4 readiness gate's `canonical_mock_streak_green` is
   updated from the mock posterior**, not the drill posterior —
   matching the "you are exam-day ready" semantics of the green
   light. Drill alone never earns 🟢.

## Consequences

- **Positive**:
  - Diagnostic signal is preserved. A learner who is drill-overfitting
    sees the alert immediately and can act.
  - Bank-calibration drift is detected, not absorbed silently into
    a tightening posterior.
  - The readiness gate's two-consecutive-canonical-greens rule
    (ADR-0033 + R-004) now operates on the *right* posterior.
- **Negative**:
  - Two state fields per user instead of one (drill posterior +
    canonical-mock-streak counter). The bookkeeping is small.
- **Neutral**:
  - The 2.0-NCLC threshold is a defensible heuristic; the right
    number is something we'll learn from operator usage. We log
    every divergence so the threshold is empirically tunable.

## Alternatives considered

- See Context (a)(b).
- **One posterior with a "test-day adjustment" factor**: rejected
  because the factor is unobservable and ends up being a fudge
  parameter that hides the underlying problem.
- **Alert only on operator-side, not learner-side**: rejected
  because the learner is the one who can act on "you're
  drill-overfitting"; hiding the signal is paternalistic.

## What would change our mind

- The 2.0 threshold trips on > 30% of mocks in operator review,
  drowning out genuine divergence. We'd widen to 2.5 or add a
  secondary "n_obs sanity gate" (drill posterior must have ≥ 80
  observations to compare).
- The alert turns out to be confusing to learners ("you've improved!
  but also you haven't"). We'd reword and possibly demote to
  operator-only.

## References

- `06_MOCK_EXAM_ENGINE.md §2.4`, `phase6_think.md §1.2`.
- `phase6_design.md §6.2`.
- `packages/sla/src/tcf_accel_sla/mock_exam/scorer.py:divergence_alert`.
- `packages/sla/tests/test_mock_scorer.py::test_divergence_alert_fires_at_threshold`.
- ADR-0025 — confidence gate is the upstream rule.
- ADR-0032 — canonical posterior is the only updater.
