# ADR-0025: Every NCLC point estimate ships with a credible interval; the `confident` flag is launch-blocking

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, ML lead
- **Phase**: 4 (Learner Model)

## Context

R-004 in `RISK_REGISTER.md`: the single biggest financial harm this
product can cause is **over-prediction** of a learner's NCLC level. A
learner who books the TCF Canada exam on the strength of an over-
confident estimate and fails loses ~$340 in exam fees and ~12 weeks of
preparation time.

Master prompt §6.2 names "credible interval mandatory; refusal-to-
predict below threshold; calibration audit" as non-negotiable honesty
primitives.

The Bayesian estimator (`packages/sla/src/tcf_accel_sla/estimator/nclc.py`)
naturally produces a posterior with a mean and a variance. The question
is what gate, exactly, decides when we're allowed to show a final
estimate.

## Decision

Three predicates, all required, before the UI may show a final NCLC
number for a skill:

1. **`n_obs ≥ 40`** — the IRT 1PL fit minimum from the IRT literature.
   Below this, the posterior is dominated by the prior.
2. **`variance ≤ 0.4`** — equivalently, posterior σ ≤ ~0.63 NCLC units,
   or a 95% CI roughly ±1 NCLC band. Below this we cannot meaningfully
   distinguish NCLC bands.
3. **`difficulty_bands_seen ≥ 3`** — the learner has been tested at
   three distinct difficulty bands. Without spread, the estimate is
   extrapolated from a narrow evidence base.

The `SkillPosterior.confident` property in
`packages/sla/src/tcf_accel_sla/estimator/nclc.py` returns the
conjunction. Every API response that carries an NCLC estimate
(`NCLCEstimate`, `Score`, `Readiness`, `DiagnosticReport`) also carries
the `confident` flag.

The `/v1/insights/readiness` route is **forbidden** from returning a
green light when any skill's `confident` is False (the rule is
implemented in `packages/sla/src/tcf_accel_sla/planner/readiness.py`
and tested in `tests/property/test_readiness_invariants.py`).

This rule is **launch-blocking**: the Phase 9 audit gate refuses to
ship if the test for "fresh user → readiness ⚪" fails.

## Consequences

- **Positive**:
  - The harm modeled in R-004 cannot happen via the readiness traffic
    light — the only path to green is the all-confident path.
  - The UI's "still learning your level" copy is grounded in a real
    statistical predicate, not a wave-of-the-hand UX choice.
  - The calibration audit (Phase 4 §4) directly tests the three
    predicates against a holdout, not against a vibes-based heuristic.
- **Negative**:
  - Users may be frustrated by "we don't know yet" early. Mitigated by
    showing the *continuous* posterior mean with a wide CI (a visual
    band, not a number) and a count of items completed.
  - The 40-obs threshold rules out a "quick check NCLC level in 5 min"
    flow that some prospective users will want. We treat this as a
    feature, not a bug — see R-004.
- **Neutral**:
  - The three thresholds are tunable; ADR-0013 reserves the right to
    re-tune them once the synthetic-cohort calibration shipped data.

## Alternatives considered

- **Two-predicate gate (n_obs + variance only)**: rejected because
  difficulty-band spread is what catches "tested only at NCLC 5; we
  have no evidence about NCLC 9 performance." The 40-obs predicate
  alone doesn't catch this.
- **Soft gate (show estimate with a "low confidence" badge)**: rejected
  because users do not read badges. The R-004 harm requires a hard gate.
- **One-predicate gate (variance only)**: rejected because variance can
  dip below threshold with very few observations if the prior was lucky
  — the n_obs floor protects against that.

## What would change our mind

- The calibration audit shows the three-predicate gate is over-
  conservative — e.g., the 95% CI contains the truth at >99% (not the
  target ≥92%) — we'd loosen one of the thresholds.
- A real over-prediction incident occurs despite all three predicates
  → tighten one of the thresholds.

## References

- R-004 in `RISK_REGISTER.md`.
- Master prompt §6.2.
- ADR-0013 (online streaming Bayesian update; the algorithm this ADR
  gates the *output* of).
- `04_LEARNER_MODEL.md §1.2`, `§2.7`.
