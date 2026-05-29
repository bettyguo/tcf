# ADR-0023: FSRS-6 default weights initially; per-user optimization deferred to ≥ 100 reviews

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 4 (Learner Model)

## Context

ADR-0006 picks FSRS-6 as the scheduler. The reference package ships a
21-parameter default weight vector and a per-user optimizer that re-fits
those weights against the user's own review history.

The optimizer needs N ≥ ~100 reviews to produce a parameter vector that
demonstrably beats the defaults (per the FSRS literature). At N < 100,
the fit is dominated by noise and the per-user weights can be *worse*
than the defaults.

Master prompt §6.2: "honesty primitives — refuse to over-predict."
Using a poorly-fit per-user vector early would amount to over-predicting
the scheduler's accuracy.

A secondary constraint: Phase 1's audit gate is "make verify passes in
an empty venv." We do not want the SLA package to take a runtime
dependency on `fsrs` until we have a vendoring story for CI.

## Decision

- Phase 4 ships **default FSRS-6 weights**, re-implemented inline in
  `packages/sla/src/tcf_accel_sla/scheduler/fsrs.py` (pure stdlib).
- Per-user optimization is **a no-op in Phase 4**; the public
  `FSRSScheduler.optimize(history)` returns the defaults unchanged.
- A future PR (post-Phase-5) replaces the inline weights with the
  `fsrs` package and wires a nightly batch job to call `optimize` once
  the user has ≥ 100 reviews.

## Consequences

- **Positive**:
  - Honest defaults — no claim of personalization we haven't earned.
  - Zero runtime dependency for the SLA package; tests run in any venv.
  - The swap to the reference package is a *module*-level substitution
    (the `FSRSScheduler` API surface is unchanged).
- **Negative**:
  - Two FSRS-6 implementations to maintain (briefly): the inline one
    until the swap, the reference one after. Mitigated by the audit
    invariants in `tests/property/test_scheduler_invariants.py` which
    test FSRS-shape properties (again decreases stability, easy grows
    faster than good, retention at due ≈ target) rather than bit-
    identical numerical output.
- **Neutral**:
  - The bit-identical conformance audit named in
    `04_LEARNER_MODEL.md §4` ("10,000 random sequences through both")
    is deferred to the post-Phase-5 PR; the audit doc names this
    deferral explicitly.

## Alternatives considered

- **Ship per-user optimization from day one**: rejected because the
  optimizer is statistically unsound below 100 reviews and would
  produce worse scheduling than the defaults. *Would reconsider*: at
  > 1k users / month, we could pre-cluster learners and use a cohort-
  weights bootstrap before the per-user threshold.
- **Wrap the `fsrs` package right now**: rejected because the package
  is not yet vendored in CI; a soft dep + skip-on-missing would mean
  the audit metric is silently skipped on PRs, which violates
  master-prompt §6 (rigor).

## What would change our mind

- The bit-identical conformance audit ships in CI and stays green for
  4 consecutive weeks → swap the implementation to the reference
  package, retire the inline version.
- The synthetic-cohort audit shows per-user optimization beats the
  defaults at N < 100 in cross-validation → lower the threshold.

## References

- ADR-0006 (FSRS-6 as the scheduler).
- `04_LEARNER_MODEL.md §2.1`, `§4`.
- [open-spaced-repetition/free-spaced-repetition-scheduler](https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler)
