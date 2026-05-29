# ADR-0040: Inflation guard clamps LLM scores against the feature floor

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 7 (Auto-Scoring & Feedback)

## Context

The Phase 7 hybrid pipeline (ADR-036) combines an objective feature
floor with a structured LLM critic. The dominant failure mode the
literature documents for LLM graders is **inflation**: an LLM happily
gives 4/5 or 5/5 on coherence to a short, fluent-but-empty essay
whose feature-floor prediction is 1/5 or 2/5.

Even with temperature ≤ 0.2 (ADR-039), this happens. Calibration
helps — but the inflation creates training-time leakage too: the
calibrator can learn an "always-add-1" weight if every silver-rated
row has an inflated LLM score.

## Decision

For each rubric dimension, before the calibrator predicts, apply the
inflation guard:

```
if llm_score[dim] - feature_floor[dim] > 3.0:
    final_llm_score[dim] = feature_floor[dim] + 2.0
    needs_human_review = True
    clamped_dimensions.append(dim)
```

The threshold of 3.0 corresponds to "more than half the rubric
range" — a level of LLM-vs-feature disagreement that is almost
always the LLM being wrong. The clamp offset of 2.0 keeps the LLM's
qualitative judgement above the floor (so the rubric is not "just
the feature-floor"), but bounds the over-generation.

Every clamp is logged in `EEScoringResult.inflation_guard.clamped_dimensions`
and surfaces in the persisted graded_score dict. The audit asserts
that on a synthetic NCLC-5 cohort the inflation guard engages on a
test that forces an inflated LLM critique.

The guard is per-dimension; one inflated dimension does not clamp
the others. The `needs_human_review` flag is the global signal.

## Consequences

- Synthetic "fluent-but-empty" essays at NCLC 5 stay at NCLC 5 ± 1
  rather than drifting to NCLC 7+.
- The `needs_human_review` flag becomes the surface that an operator
  (or eventually a human reviewer queue) consumes to triage the
  most uncertain rubrics.
- The threshold + clamp offset are tunable per release but bumping
  either is an ADR-grade change.
- The guard runs before the calibrator, so even an uncalibrated
  scorer (fresh deployment) gets inflation protection.

## Related

- ADR-036, ADR-039
- `phase7_design.md §5.3`, `phase7_audit.md §4` (inflation guard test)
- `packages/ml/src/tcf_accel_ml/scoring/inflation_guard.py`
