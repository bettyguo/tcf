# ADR-0045: Readiness widget never shows 🟢 without ≥ 2 consecutive canonical mocks at 🟢

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, Psychometrics consultant
- **Phase**: 8 (Frontend UX)

## Context

The Insights screen's Readiness widget signals, in effect, *should
you book the exam?* Two empirical realities frame the design:

1. **A single mock-exam result is noisier than learners expect.**
   Variance from item-pool sampling, daily mood, sleep, and
   distraction is large enough that one green mock has materially
   higher probability of being followed by a non-green mock than
   most learners assume.
2. **Premature booking is the dominant cost.** A user who books on
   a single green and underperforms loses CAD ~340 + travel + 6–8
   weeks of demoralised re-prep, and (most consequentially) misses
   their Express Entry invitation window.

The Phase 7 mock scoring is honest but it does not produce a
binary "ready" verdict. The UI does, and the UI must therefore
encode a conservative threshold.

The candidate-volume cap on canonical mocks (ADR-0033) means the
"two consecutive" requirement is bounded — a user cannot game it by
cramming canonical mocks.

## Decision

The `<ReadinessWidget />` shows the green light (`light: "green"`,
`state: "READY"`) **only if all of the following hold**:

1. ≥ 2 canonical-mode mock exams completed (training-mode mocks do
   not count toward this threshold).
2. The two most recent canonical mocks are at green (per-skill min
   posterior mean ≥ target).
3. The posterior `P(min skill ≥ target) ≥ 0.85`.

Otherwise the widget displays one of: `INSUFFICIENT_DATA` (⚪) when
no canonical mocks; `READY_ONE_MOCK` (🟡) when one green canonical
mock; `BORDERLINE` (🟡); `NOT_READY` (🔴); `REGRESSED` (🔴) when a
previously-green stage has been followed by a non-green canonical
mock.

The mapping is enforced in `lib/readiness.ts` (pure function), the
single source of truth that the widget reads. Every state has a
unit test in `tests/unit/readiness.test.ts` and a Storybook entry
in `stories/ReadinessWidget.stories.tsx`.

Additional design constraints (enforced in component code, not just
this ADR):

- No celebratory animation, sound, or confetti on green — green is
  the moment of *most* premature-booking risk and must render
  soberly (linked to ADR-0042).
- The "Book your exam" CTA is rendered **only** in `READY`. In any
  other state, the CTA is replaced by "See your priority drills"
  so the user always has a forward action.
- The bottleneck skill is named prominently in every non-empty
  state. Express Entry awards points against the *minimum* skill,
  so a user reading the average without the minimum has been failed
  by the UI.

## Consequences

- Some learners who are *actually* ready will see 🟡 because they
  have completed only one canonical mock. The mitigation is the
  explicit recommendation copy: "Run a second canonical mock in
  7–10 days to confirm." Conservative.
- The single source of truth (`lib/readiness.ts`) is the only place
  to express any future relaxation; a workaround in the widget
  would be a code-review failure.
- Reversing this trade-off would require a new ADR with a
  documented review of the consequences — specifically, of the
  premature-booking failure mode.

## Related

- ADR-0025 (posterior CI mandatory — paired with this gate)
- ADR-0032 (canonical-vs-training mock modes)
- ADR-0033 (mock cadence cap)
- ADR-0042 (no gamification — pairs with no-celebration-on-green)
- `phase8_think.md §6`, `phase8_design.md §3.2, §12.3`,
  `tests/unit/readiness.test.ts`, `stories/ReadinessWidget.stories.tsx`
