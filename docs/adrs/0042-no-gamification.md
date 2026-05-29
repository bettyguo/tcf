# ADR-0042: No gamification — calm over engagement

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, UX lead
- **Phase**: 8 (Frontend UX)

## Context

Adult-learner products in the language space have converged on a
gamification template — streak flames, daily-loss aversion,
leaderboards, push notifications — because those mechanics are well-
known to raise DAU, MAU, and retention.

Our target user is preparing for an immigration milestone. The
relevant outcome metric is *exam-day performance*, not session count.
The user's emotional baseline is already elevated anxiety. Streak
mechanics weaponise that anxiety against them; leaderboards introduce
social comparison among strangers competing for the same scarce
immigration slots; push spam degrades trust.

The temptation to introduce *one little streak counter* is enormous:
it would lift DAU at near-zero engineering cost. Pre-committing
against it in an ADR makes the temptation answerable.

## Decision

The tcf-accel product ships **none** of the following, ever:

- A streak counter or any visual streak indicator (no flames, no
  "X days in a row" badges, no calendar fill).
- A leaderboard of any kind, public or private, including class-
  cohort comparisons.
- A "your friends are ahead" or social-pressure surface.
- Daily-active-user-chasing copy ("Don't lose your progress!",
  "You're so close!", "Just 5 more minutes!").
- Celebratory animations on readiness-green (see ADR-045 for the
  specific consequence: green is the moment of *most* premature-
  booking risk, so it must render soberly).
- Sound effects, confetti, or any reward animation on drill
  completion.

The decision is enforced both by code review and by:

- A copy-style lint rule that fails on banned strings (matching
  `/lost!|behind!|don't.*miss|hurry/i`).
- Storybook story snapshots that exercise the readiness widget at
  green state and verify no celebratory animation is present.

## Consequences

- DAU is expected to be measurably lower than at a gamified peer.
  That is acceptable. The launch metric is exam-day NCLC ≥ target,
  not session count.
- The UI surface area is smaller. Less to maintain, less to A/B
  test, fewer copy strings to translate.
- Notifications are opt-in only (ADR-0043). Streak-loss notifications
  are explicitly prohibited.
- Reversing this decision requires not just engineering work but
  re-arguing the calm-vs-engagement trade-off at the ADR level. It
  is intentionally hard to undo.

## Related

- ADR-0043 (notifications), ADR-0045 (readiness widget)
- `phase8_think.md §2.1`, `phase8_design.md §6`
