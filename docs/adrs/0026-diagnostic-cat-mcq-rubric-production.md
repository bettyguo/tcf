# ADR-0026: Diagnostic is computer-adaptive (CAT) for CO/CE; rubric-scored prompts for EE/EO

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 4 (Learner Model)

## Context

A learner needs an initial NCLC estimate per skill so the planner can
allocate time. The diagnostic must:

- Take ≤ 60 minutes total (master prompt §6.2 + Phase 4 evaluation
  acceptance criterion).
- Produce a calibrated posterior, not a single-number summary.
- Refuse to over-predict (R-004 + ADR-025).

The four skills (CO, CE, EE, EO) differ structurally:

- **CO** and **CE** are MCQ-style. Each item is a binary correct/
  incorrect outcome. Item-response theory (IRT) gives us a principled
  way to pick the next item: maximize Fisher information at the current
  posterior mean. This is exactly computer-adaptive testing (CAT).
- **EE** and **EO** are production tasks: short writing / speaking
  prompts. There is no "next-item-info" notion; each prompt is a
  substantial chunk of work scored on a rubric (Phase 7's auto-scorer).

## Decision

- **CO and CE**: CAT routine in
  `packages/sla/src/tcf_accel_sla/diagnostic/cat.py`. The session
  starts at the learner's self-reported level (default B1 = NCLC 5),
  updates the posterior after each item via the 2PL IRT Laplace update
  (ADR-013 / ADR-025), and selects the next item to maximize Fisher
  information at the posterior mean. Stops when variance ≤ 0.3 or
  15 items administered.
- **EE and EO**: a single calibrated prompt per skill at each of three
  target NCLC levels (B1 / B2 / C1, mapping to NCLC 5 / 7 / 9). The
  Phase 7 auto-scorer produces the rubric total; the posterior is
  updated with the Gaussian likelihood from
  `update_with_rubric`.

Total wall-clock estimate (based on the scripted test agent in
`tests/pedagogy/`): ~15 min CO + ~15 min CE + ~15 min EE + ~12 min EO
≈ **57 min total** including transitions and breaks — within the
60-min envelope.

Diagnostic *also* applies a same-difficulty-run cap
(`SAME_DIFFICULTY_RUN_CAP = 3`): if the last 3 items are all at the
same band, the next item is forced to a different band. This is the
"avoid frustration" rule from `04_LEARNER_MODEL.md §1.3 step 3`.

## Consequences

- **Positive**:
  - CO/CE diagnostic is short (typically 5–10 items per skill before
    the variance threshold) and pedagogically defensible (IRT is the
    gold standard for adaptive testing).
  - EE/EO posteriors are still updated, just with a smaller sample —
    the production-task bottleneck is *how many prompts a learner can
    write in 30 min*, not *how many we'd ideally want*.
  - The hand-off to Phase 7 is clean: the diagnostic delegates rubric
    scoring entirely.
- **Negative**:
  - EE/EO posteriors have higher variance than CO/CE coming out of the
    diagnostic — they will not satisfy `confident=True` after one
    session. The user must complete additional production work in the
    plan before the readiness traffic light can go green. This is
    fine — it's exactly the right behavior per ADR-025.
  - The CO/CE pool needs IRT-calibrated items (Phase 3 + the nightly
    IRT refit ADR-0013). At v1 the pool is the
    Phase-4-fixture pool in `apps/api/src/tcf_accel_api/diagnostic_pool.py`
    with `discrimination = 1.0` defaults.
- **Neutral**:
  - The stopping criterion (variance ≤ 0.3) is tighter than the
    confidence threshold (≤ 0.4). This is intentional: the diagnostic
    aims to *exceed* the confidence gate so the user has some buffer
    against decay between sessions.

## Alternatives considered

- **Fixed-length test (e.g., 10 MCQ per skill, no adaptivity)**:
  rejected because non-adaptive tests waste a learner's time at the
  wrong difficulty level and produce noisier posteriors per minute.
- **Self-rating only**: rejected because R-004 — self-ratings are
  notoriously poorly calibrated, particularly for production skills.
- **A single all-skills CAT** (one big pool with cross-skill item
  selection): rejected because the four skills measure largely
  independent latent abilities; pooling adds complexity for no
  posterior-precision gain.

## What would change our mind

- The 57-min total measured against the test agent stretches past
  60 min for ≥ 10% of users (e.g., because the stopping criterion
  takes longer than expected) → we'd tighten the item cap from 15 to
  12 per CO/CE skill.
- The EE/EO single-prompt-per-band approach proves too noisy in the
  calibration audit (posterior variance after 3 prompts is still > 1.0)
  → switch to 2 prompts per band, accepting longer wall-clock time.

## References

- ADR-013 (online posterior / batch IRT split).
- ADR-025 (posterior CI mandatory).
- `04_LEARNER_MODEL.md §1.3`, `§2.4`.
- `packages/sla/src/tcf_accel_sla/diagnostic/cat.py`.
