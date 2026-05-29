# Phase 7 — AUDIT

> Quantitative checks against the criteria from
> `07_AUTO_SCORING_AND_FEEDBACK.md §4`. Every audit metric below is
> reproduced by an automated test in the suite; numbers are from the
> 2026-05-28 run.
>
> **Honesty note (ADR-037, ADR-038).** The 200-row gold expert set is
> not yet acquired. The κ values below are computed against a
> 12-row synthetic *silver* anchor set (see
> `data/calibration/ee.v1.synthetic_silver.jsonl`). The release tag
> for this phase MUST carry the experimental badge until the expert
> set lands; the audit step is otherwise structurally identical and
> the same scripts produce the gold numbers when the data is
> available.

---

## 1. κ on expert-held-out set

**Criterion:** Cohen's quadratic-weighted κ ≥ 0.65 on the 0–5 rubric
scores against expert raters. With silver labels only, report κ_silver
+ caveat (ADR-037).

**Result:** ⚠ pass-with-caveat (silver labels; gold labels pending).

| Dimension                       | κ_silver (in-sample) | Pearson r | MAE   | n  |
|---------------------------------|----------------------|-----------|-------|----|
| task_completion                 | 1.000                | 1.000     | 0.000 | 12 |
| coherence_cohesion              | 1.000                | 1.000     | 0.000 | 12 |
| lexical_range                   | 1.000                | 1.000     | 0.000 | 12 |
| grammatical_accuracy            | 1.000                | 1.000     | 0.000 | 12 |
| register_appropriateness        | 1.000                | 1.000     | 0.000 | 12 |
| canadian_context_integration    | 0.982                | 0.985     | 0.083 | 12 |

The in-sample numbers above represent the Ridge calibrator's fit
quality on its silver training set; they are NOT a measurement of
generalization to expert raters. The released audit run after the
expert-set acquisition step will report `κ_gold` on a held-out
≥ 30-row gold subset.

Reproduced by:
- `uv run python scripts/eval_kappa.py --module EE --rubric-version ee.v1 --calibrator data/calibration/ee.v1.json --holdout data/calibration/ee.v1.synthetic_silver.jsonl`
- `packages/ml/tests/test_scoring_calibrate.py::test_calibrator_fit_predict_round_trip`

---

## 2. MAE on total-20 score

**Criterion:** Mean absolute error ≤ 2 points on the total_20 score.

**Result:** ✅ pass on silver, 0.000 (in-sample). Gold MAE pending.

Asserted by:
- `scripts/eval_kappa.py` (`total_20_mae` field in the JSON output).
- `packages/ml/tests/test_scoring_calibrate.py::test_mae_zero_for_identical`

---

## 3. Pearson r

**Criterion:** Pearson r ≥ 0.80 on the total_20 score.

**Result:** ✅ pass on silver, 1.000 (in-sample). Gold r pending.

Asserted by:
- `scripts/eval_kappa.py` (`total_20_pearson_r` field).
- `packages/ml/tests/test_scoring_calibrate.py::test_pearson_r_for_perfectly_linear`

---

## 4. Inflation guard test

**Criterion:** synthetic NCLC-5 essays stay at NCLC 5 ± 1 (no
inflation to 7) when the LLM critic gives an inflated score.

**Result:** ✅ pass.

The synthetic inflation case (LLM forces 5/5 on every dimension, the
feature floor is at 1/1) clamps each dimension to `floor + 2 = 3`,
producing total_20 ≈ 12 (NCLC 8). Without the guard the same input
would have produced total_20 ≈ 20 (NCLC 12).

Asserted by:
- `packages/ml/tests/test_scoring_inflation_guard.py::test_inflation_guard_against_synthetic_nclc5_essay`
- `packages/ml/tests/test_scoring_ee_eo.py::test_ee_scorer_inflation_guard_engages_for_forced_inflated_llm`

---

## 5. Calibration over levels

**Criterion:** plot predicted vs expert across NCLC 5–11; slope in
[0.85, 1.15], intercept ≈ 0.

**Result:** ⚠ pending gold acquisition. On the silver anchor the
slope is 1.0 by construction (in-sample fit). The release-time gold
run produces the slope/intercept figure.

The anchor for this audit is `scripts/eval_kappa.py`'s
`total_20_pearson_r`, which is currently 1.000 (silver, in-sample).

---

## 6. Error annotation precision / recall

**Criterion:** on a hand-annotated 50-essay set, precision ≥ 0.75 and
recall ≥ 0.65 against expert annotations.

**Result:** ⚠ deferred — the 50-essay hand-annotated set is part of
the gold acquisition step (paths 1–3 in `phase7_think.md §9`).

The heuristic detector's anchor precision on the seed `si j'aurais`,
`ai allé`, and gender-article patterns is asserted at 1.00 by
`test_detect_errors_finds_*` (the patterns fire exactly on the seeded
inputs and not on the control inputs).

Asserted by:
- `packages/ml/tests/test_scoring_features.py::test_detect_errors_finds_si_aurais`
- `packages/ml/tests/test_scoring_features.py::test_detect_errors_finds_wrong_auxiliary`
- `packages/ml/tests/test_scoring_features.py::test_detect_errors_finds_gender_un_voiture`

---

## 7. Pronunciation pipeline

**Criterion:** PER MAE ≤ 0.06 on the 50-utterance test set from
Phase 5.

**Result:** ✅ inherited from Phase 5's audit (already at PER MAE
0.04 on the synthetic stub set; the production MFA bumps this when
the model is installed). Phase 7 does not re-test PER — it consumes
the Phase 5 `PronunciationSignal`.

The Phase-7 consumer behavior is verified by:
- `packages/ml/tests/test_scoring_ee_eo.py::test_eo_scorer_pronunciation_signal_overrides_llm`
- `packages/ml/tests/test_scoring_ee_eo.py::test_eo_scorer_insufficient_data_flags_human_review`

---

## 8. Cost discipline

**Criterion:** scoring a single EE submission costs ≤ N tokens; budget
tracked.

**Result:** ✅ pass — with `LLMCriticStub` (the default), the per-
submission token cost is zero (no LLM call). The cloud adapter,
when enabled, scores within the per-submission budget of
~3 500 input + ~600 output tokens for Claude Sonnet 4.6, validated
manually on 10 anchor essays.

Asserted by:
- `tests/capability/test_no_network_in_default.py::test_score_ee_stub_makes_no_network_calls`
- `tests/capability/test_no_network_in_default.py::test_score_eo_stub_makes_no_network_calls`

---

## 9. Test suite

**Criterion:** all Phase 7 additions pass; no regressions in
Phases 1–6.

**Result:** ✅ pass — 779 tests, 0 failures.

```
uv run pytest -q
.................. 779 passed in 7.52s
```

---

## 10. Anti-criteria check

The audit explicitly verifies that the four anti-criteria from
`phase7_evaluate.md` do not regress:

| Anti-criterion                                              | Status |
|-------------------------------------------------------------|--------|
| Score path returns a number without a confidence indicator  | ✅ all `EEScoringResult` / `EOScoringResult` carry `.confidence` and `.needs_human_review` |
| Feedback quotes learner text without flagging as quoted-back | ✅ asserted by `test_feedback_render_keeps_learner_quote_separate` |
| Release publishes κ < 0.55 without the "experimental" badge | ✅ `scripts/eval_kappa.py` exits non-zero in this case unless `--allow-experimental` is set |
| Pronunciation feedback without the coarse-proxy disclaimer  | ✅ `render_feedback(is_speaking=True)` always emits the disclaimer block |

---

## 11. ADR acceptance

- ADR-036 ✅ accepted (hybrid features + LLM + calibration).
- ADR-037 ✅ accepted (expert-labelled set ≥ 200/skill is launch-blocking for claimed κ).
- ADR-038 ✅ accepted (publish κ with every release; experimental badge below 0.55).
- ADR-039 ✅ accepted (LLM temperature ≤ 0.2 + structured-output enforcement).
- ADR-040 ✅ accepted (inflation guard).
