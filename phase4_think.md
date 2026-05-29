# Phase 4 — Think

> Companion to `04_LEARNER_MODEL.md`. Captures the load-bearing design
> decisions and the alternatives we explicitly rejected.

## 1. The three sub-models, restated

| Sub-model | Role | Phase 4 module |
|---|---|---|
| FSRS-6 | When to re-show every learnable item | `tcf_accel_sla.scheduler.fsrs` |
| LECTOR | Push confusable items apart in the same day's queue | `tcf_accel_sla.scheduler.lector` |
| Bayesian per-skill NCLC posterior | Planning signal — what NCLC would the learner get today? | `tcf_accel_sla.estimator.nclc` |

These are **complementary**, not substitutes. Picking one and discarding
the others reproduces a known failure mode of every prior SLA system
we've audited.

## 2. The honesty primitives

The whole estimator + planner stack is gated by ADR-025: **every NCLC
point estimate ships with a credible interval, and the `confident` flag
is launch-blocking.** This is non-negotiable; the harm modeled in R-004
is the single largest risk we ship.

We chose to make this enforcement a *structural* property of the API,
not a UX convention:

- The `SkillPosterior.confident` property in
  `packages/sla/src/tcf_accel_sla/estimator/nclc.py` returns the
  conjunction of three predicates.
- `compute_readiness` in
  `packages/sla/src/tcf_accel_sla/planner/readiness.py` is **incapable**
  of returning 🟢 when any predicate fails — the unconfident path is
  the first branch.
- `tests/property/test_readiness_invariants.py` proves this property
  under Hypothesis-generated inputs.

A future contributor cannot "fix" the unconfident-→-red gate without
deleting an explicit assertion. That is the right level of friction.

## 3. The Bayesian formulation

We use a 2-parameter IRT likelihood (`P(correct | θ) = σ(a · (θ - b))`)
combined with a Gaussian prior, updated via Laplace approximation:

1. Find the posterior mode by Newton-Raphson.
2. Take `-1/H` at the mode as the posterior variance.

We considered three alternatives and rejected them:

- **HMC / NUTS** — overkill for a per-interaction online update; the
  Laplace approximation is conservative (variance shrinks more slowly
  than HMC), which is the right error direction for refuse-to-predict.
- **Particle filter** — variance-conservative in the wrong way (variance
  *grows* with weak observations), drifting the posterior under noise.
- **Closed-form Beta-Binomial** — only works if we collapse to a single
  "correct rate"; loses item-difficulty information that's the whole
  point of IRT.

For EE/EO (rubric-scored), the likelihood is Gaussian, so the update
is closed-form (no Newton needed).

## 4. The CAT diagnostic

`04_LEARNER_MODEL.md §1.3` specifies the diagnostic flow. We implement
it in `packages/sla/src/tcf_accel_sla/diagnostic/cat.py`. The
load-bearing design decisions:

- Maximum 15 items per skill before forced stop.
- Variance threshold ≤ 0.3 (tighter than the confidence-gate threshold
  of ≤ 0.4 — gives buffer against between-session decay).
- Same-difficulty-run cap of 3: after three items at the same band,
  the next item must be at a different band. Without this, a "hot
  streak" of correct answers at band 7 would keep the CAT spinning
  at band 7 indefinitely; the rule forces it to test band 8 or 6.

For EE/EO the CAT is degenerate: a single calibrated prompt at each
of B1 / B2 / C1. We do not adaptively select prompts at the writing/
speaking level because:

1. A single prompt is a substantial chunk of work; spending it on a
   "wrong difficulty" prompt is acceptable.
2. We rely on the Phase 7 rubric calibration to make the *scoring*
   sensitive to ability level; the *prompt* is fixed.

## 5. The bottleneck-driven allocator

The headline formula (ADR-027):

```
α_s = max(ε, (target - μ_s))² · β_s
minutes_s = total_minutes · α_s / Σ α
```

with `β_CO = 1.0, β_CE = 0.9, β_EE = 1.4, β_EO = 1.5`.

Why squared, not linear? Linear under-weights the gap when the learner
is two-or-more bands below target — exactly the situation where
intervention matters most. Squared compounds the urgency.

Why over-weight production? Two reasons:

1. Production skills converge more slowly per minute of practice.
2. A production-skill bottleneck is dispositive for TCF Canada
   immigration thresholds (the `min` over skills).

We rejected three alternatives:

- **Equal β across skills**: the synthetic-cohort audit shows this
  misses the production bottleneck on cohorts 3, 5, 8.
- **Steeper β (EE=2.0, EO=2.5)**: cohort 11 (production-strong)
  ends up with reception below the 10-minute floor; bad for retention.
- **Dynamic β derived from learning rate**: needs per-user data we
  don't have at v1; reconsider at >10k users.

## 6. What we deferred to later phases

- **FSRS bit-identical conformance** vs the reference `fsrs` package.
  Phase 4 ships an inline re-implementation; vendoring the reference
  package + the 10,000-sequence conformance test lands post-Phase-5
  (ADR-023).
- **Nightly IRT refit** for `items.difficulty_irt` / `discrimination_irt`.
  Phase 2 reserved the columns (ADR-0013); Phase 4 leaves the column
  unpopulated and uses `discrimination=1.0` defaults. Phase 5 ships
  the worker.
- **Confusable-pairs Postgres lookup** for LECTOR. The library accepts
  embedding vectors directly; the API layer doesn't yet query the
  Phase 3 `confusable_pairs` table.
- **Per-user FSRS optimization** at ≥ 100 reviews. Deferred per ADR-023.
- **Plan persistence**. v1 uses an in-process dict; Phase 5 swaps to
  Postgres (`StudyPlan` table reserved in Phase 2 schema).

## 7. The acceptance posture

The Phase 4 evaluate doc enumerates the acceptance + anti-criteria. We
hit:

- ✅ All audit metrics pass (`phase4_audit.md`).
- ✅ All ADRs 023..027 accepted.
- ✅ Diagnostic completes in ≤ 60 min (scripted-agent estimate).
- ✅ Allocator + planner integrate with `/v1/plan/*`, `/v1/diagnostic/*`,
  `/v1/insights/readiness`.

We honor the anti-criteria via the property/Hypothesis tests in
`tests/property/`.
