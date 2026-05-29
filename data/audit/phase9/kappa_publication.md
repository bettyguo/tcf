# κ publication check — Phase 9

STATUS: pass

> ADR-038 makes the published κ a hard release gate. This file
> verifies the κ table embedded in the README's "Honesty receipts"
> section matches `data/calibration/ee.v1.report.md` (the source
> of truth) and that the per-dimension κ clears the Phase 7 ≥ 0.65
> floor on the EE rubric. The EO calibrator at v1.0 ships the
> same architecture; the κ_silver numbers will replace the EE
> placeholder when the EO calibrator artefact lands (v1.0.1).

## Source of truth

- `data/calibration/ee.v1.report.md` — EE κ table
- Training-set hash recorded in `RubricCalibrator.training_set_hash`
  (`packages/ml/src/tcf_accel_ml/scoring/calibrator.py`)
- κ regression check: `scripts/eval_kappa.py --release v1.0.0`

## EE κ_silver (v1.0)

| Dimension | κ (silver) | n | ≥ 0.65 gate |
|---|---|---|---|
| `task_completion` | 1.000 | 12 | ✅ |
| `coherence_cohesion` | 1.000 | 12 | ✅ |
| `lexical_range` | 1.000 | 12 | ✅ |
| `grammatical_accuracy` | 1.000 | 12 | ✅ |
| `register_appropriateness` | 1.000 | 12 | ✅ |
| `canadian_context_integration` | 0.982 | 12 | ✅ |

All six dimensions clear the gate. The κ ≈ 1.0 reflects the
small-sample synthetic-silver setup; the *real* κ test is against
the (yet-to-acquire) 200-row κ_gold set (R-010 + ADR-037).

The README embeds these numbers between the `<!-- HONESTY-RECEIPTS:START -->`
and `<!-- HONESTY-RECEIPTS:END -->` markers per ADR-048. Verified
on 2026-05-28.

## Experimental badge

v1.0 ships with the "experimental" badge on rubric scores per
ADR-037 + ADR-038. The badge drops only when κ_gold ≥ 0.75 on a
200-row expert-rater set (R-010); v1.1 commits to this.

The badge is rendered in:

- `apps/web/components/domain/RubricScore.tsx` (Phase 8).
- The README "Honesty receipts" section (ADR-048).
- `LIMITATIONS.md §4`.

## Training-set hash

`7591d824b2101399…` — recorded in `data/calibration/ee.v1.json`
and in the README receipts section. The hash gates calibrator
regressions per ADR-038 + R-046.

## Conclusion

EE κ_silver clears the ≥ 0.65 gate on all six dimensions.
Experimental badge active until v1.1 κ_gold acquisition.
STATUS: pass.
