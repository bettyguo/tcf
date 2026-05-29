# ADR-0036: Auto-scoring uses a hybrid features + LLM + calibration architecture

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 7 (Auto-Scoring & Feedback)

## Context

Phase 7 produces per-rubric scores for EE writing and EO speaking.
The scoring surface is the most reviewer-skeptical part of the system:
commercial L2 auto-scorers (ETS e-rater, Pearson IntelliMetric) sit
in the κ 0.65–0.75 band against expert raters even after decades of
calibration data. We will not exceed that band in v1.

`07_AUTO_SCORING_AND_FEEDBACK.md §1.4` and `phase7_think.md §4`
enumerate four candidate architectures:

- (a) Pure regex / hand-crafted feature scoring. Plateaus around
  κ 0.45; brittle across topics.
- (b) Fine-tuned classifier (BERT-fr on rubric scores). Needs
  thousands of labelled rows we will not have for v1.
- (c) LLM-only with chain-of-thought. Documented score inflation
  and high prompt-to-prompt variance.
- (d) Hybrid feature pipeline + LLM critic + a small Ridge
  calibrator. ← chosen.

## Decision

Phase 7's EE and EO scorers fuse three sources:

1. `WritingFeatures` / `SpeakingFeatures` — linear-time, pure-Python,
   bounded. Provide the objective floor: TTR, MATTR-25, discourse-
   marker diversity, error density, register, Canadian-lexicon
   density, prosody.
2. A `LLMCritic` (the cloud Claude Sonnet 4.6 critic in production,
   the deterministic `LLMCriticStub` in CI and offline mode) returns
   structured per-rubric scores, justifications, error annotations,
   and rewrite suggestions.
3. A `RubricCalibrator` (per-dimension Ridge regression over
   `(features, llm_score) → expert_score`) trained on the expert-
   labelled set. Pure-Python implementation; persists as JSON for
   audit.

The Ridge calibrator is small enough (~6 inputs × ~200 rows per
dimension) that it does not overfit even when expert labels are
scarce. The feature pipeline anchors the floor; the LLM provides the
qualitative judgement; the calibrator fuses them.

## Consequences

- The scoring package (`packages/ml/src/tcf_accel_ml/scoring/`) ships
  in pure Python; no spaCy / numpy / sklearn at import time. The
  pipeline runs in a clean venv.
- Calibrators are versioned by `(rubric_version, training_set_hash)`
  and stored as JSON next to the audit reports.
- A deployment without an expert-labelled set runs uncalibrated — the
  LLM scores pass through and the rubric carries the
  "experimental" badge (see ADR-038).
- Inflation is contained by the per-dimension guard (ADR-040); we do
  not rely on the LLM's self-restraint alone.
- Replacing the architecture with (b) — a fine-tuned classifier —
  remains a Phase 10+ option if ≥ 1 000 labels per dimension arrive.

## Related

- `phase7_think.md §3, §4`
- `phase7_design.md §1, §4, §5`
- ADR-038 (publish κ with every release)
- ADR-040 (inflation guard)
