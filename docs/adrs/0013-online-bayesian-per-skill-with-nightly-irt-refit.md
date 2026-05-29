# ADR-0013: Online streaming Bayesian update for per-skill posterior; nightly batch IRT refit for item difficulty

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, ML lead, Pedagogical architect
- **Phase**: 2 (per-skill scaffolding); Phase 4 (estimator implementation)

## Context

The NCLC estimator decomposes into two layers with very different
computational shapes (`phase2_think.md §1.3`):

1. **Per-skill posterior** (one row per user × module): a closed-form
   Bayesian update against a conjugate prior. The math is O(1) per
   interaction (Beta-Binomial-like; Phase 4 ADR-024 will make the
   precise distributional choice).
2. **Per-item IRT difficulty** (`items.difficulty_irt`,
   `items.discrimination_irt`): a 2PL parameter fit across the
   interaction matrix. The math is O(items × users) and is iterative
   (gradient descent or EM); it is not closed-form.

Three update cadences were considered:

1. Recompute everything on every interaction (online for both).
2. Recompute everything on session-end + nightly batch.
3. Online for the per-skill posterior; nightly batch for IRT.

Master prompt §6.2 names "credible interval mandatory, refusal-to-
predict below threshold, calibration audit" — all of which depend on
the *frequency* of the posterior update.

## Decision

Two code paths, each using the correct algorithm for its shape:

- **Per-skill posterior**: online streaming update after every interaction
  for `CO/CE` (binary correct/incorrect) and after every async grade for
  `EE/EO` (continuous rubric score). Each `(user_id, skill)` row in
  `skill_estimates` is written once per update; no append-only history.
- **Per-item IRT (`difficulty_irt`, `discrimination_irt`)**: nightly
  batch fit via a 2PL MLE solver (Phase 4 wraps `py-irt` or a custom
  jax-based solver) over the previous 90 days of interactions. The job
  runs on the worker pool; failure is logged but non-fatal (yesterday's
  values remain valid).

The two paths share zero code by design; the per-skill update lives in
`packages/sla/src/tcf_accel_sla/posterior.py` and the IRT refit lives in
`packages/sla/src/tcf_accel_sla/calibration.py`. Both write to Postgres;
the posterior cache (ADR-0012) is invalidated when either path writes.

Phase 2 reserves the columns and scaffolding; Phase 4 ships the
implementations.

## Consequences

- **Positive**:
  - The "is the user improving?" question is answerable mid-session;
    no learner sees a posterior that's > 24 h stale.
  - The expensive IRT fit runs once a day, off the critical path.
  - Each path uses the correct math; we don't compromise either.
  - The two paths are independently swappable (e.g., replace the per-
    skill posterior with a particle filter in Phase 4 without
    touching IRT).
- **Negative**:
  - Two ML code paths to test and maintain. Mitigated by:
    - The Phase 4 audit ships a synthetic-cohort calibration check
      for both paths.
    - Property-based invariants (monotonicity, boundedness, CI
      coverage) hold for both.
  - The per-skill posterior is computed *online* in the worker; a bug
    in the update rule corrupts the cached posterior. Mitigated by
    a Phase 4 invariant test that the posterior is recoverable from
    the `interactions` history (idempotent re-derivation).
- **Neutral**:
  - The 90-day IRT lookback window is a tunable; Phase 4 ADR will pin
    the value once we have calibration data.

## Alternatives considered

- **Option 1: online for both** — rejected because IRT 2PL fit is
  O(items × users) per update and not closed-form. We'd need a streaming
  variational approximation, which adds complexity for no v1 benefit.
  *Would reconsider*: if at > 10k users the nightly job stretches
  beyond 4 hours, a streaming variational IRT (online-2PL) would let
  difficulty stay fresher.
- **Option 2: batch for both** — rejected because session-end batch
  posterior update means a long session shows the user yesterday's
  number. Master prompt §6.2 implicitly requires honest, current
  estimates. *Would reconsider*: if the per-skill closed-form update
  proves numerically unstable in the synthetic-cohort audit (a Phase 4
  failure mode); we'd switch to session-end batch as a quick fix.

## What would change our mind

- **Posterior oscillation** on the Phase 4 synthetic-cohort trajectory.
  The closed-form update should be monotone in evidence; oscillation
  indicates a bug or a prior misspecification. We'd switch to session-
  end batch updates until fixed.
- **Nightly IRT refit > 4 hours** at production scale. We'd move to
  weekly with a streaming approximation, or shard the fit per CEFR band.
- **Calibration audit failure**: the posterior is mis-calibrated by
  > 1 NCLC band on average against a holdout. This is the R-004 harm
  signal; we'd halt online updates and re-derive from history.

## References

- `02_ARCHITECTURE.md §1.1.3`, `§2.4`.
- `phase2_think.md §1.3`.
- `04_LEARNER_MODEL.md §2.3` (the Phase 4 elaboration this ADR is the
  contract for).
- ADR-0006 (FSRS-6; the scheduler that consumes the posterior).
- Master prompt §6.2 (honesty primitives).
- R-004 (NCLC overconfidence risk).
