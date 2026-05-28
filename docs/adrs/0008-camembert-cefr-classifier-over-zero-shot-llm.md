# ADR-0008: CamemBERT-derived CEFR classifier over zero-shot LLM classification

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, ML lead, Pedagogical architect
- **Phase**: 1

## Context

CEFR classification of texts and transcripts is on the critical path: it determines item difficulty placement on the scheduler ladder (Phase 4), gates content-pipeline acceptance (Phase 3), and feeds the auto-scorer (Phase 7). It runs on tens of thousands of items at ingestion and re-runs on every per-user recommendation.

Master prompt §2.1.1 and §8 name `JonathanStefanov/CEFR_Classifier_French` (CamemBERT-based, MIT) as the starting point, fine-tuned on a TCF-style augmented set.

The honest alternative is a zero-shot LLM call ("classify this text as A1/A2/B1/B2/C1/C2"). It is cheaper to set up but worse on every axis that matters.

## Decision

A dedicated CEFR classifier derived from CamemBERT (`JonathanStefanov/CEFR_Classifier_French`), fine-tuned in Phase 3 on:

- Cambridge ESOL French texts (where licensable)
- HuggingFace `CEFR-Levels-French` dataset
- FLELex lexicon-augmented data
- A 500-item hand-labeled TCF-style validation set

Hosted as a small (~110 MB) classifier loaded on the worker. Inference runs in `packages/ml/src/tcf_accel_ml/cefr/classifier.py` behind a typed interface.

LLM-zero-shot may be used as a *secondary cross-check* on items with low classifier confidence (Phase 3 ADR-019-adjacent), never as the primary signal.

## Consequences

- **Positive**:
  - Deterministic, low-latency (~10 ms/text), reproducible (no LLM temperature variance).
  - Calibrated confidence outputs; we can threshold for "needs human review" (Phase 3 quality gate).
  - Free at inference; no per-call cost.
  - Phase 3 audit target macro-F1 ≥ 0.72 + adjacent-level accuracy ≥ 0.93 is empirically achievable.
- **Negative**:
  - Training set is finite; the classifier will mis-label novel registers or jargon. Mitigated by the quality gate routing low-confidence items to human review (Phase 3 §2.7 manual-review UI).
  - Maintenance burden: re-train on schema/distribution drift.
- **Neutral**:
  - Weights versioned in `packages/ml/data/cefr/<sha>/`; not committed to git; built by `make setup-models`.

## Alternatives considered

- **Zero-shot LLM (Claude Sonnet 4.6, GPT-4o)**: rejected as primary because (a) per-call cost on millions of inferences is prohibitive, (b) reproducibility is degraded by model versioning and temperature, (c) measured inflation: LLMs systematically over-assign CEFR levels by ~0.5 bands on French L2 texts (literature signal; we'll re-verify in Phase 3). *Would reconsider*: never as the primary; remains the cross-check.
- **A trained model from scratch**: rejected on data scarcity; CamemBERT's pre-trained French representations are the right starting point.
- **A regex/lexicon-based classifier (FLELex only)**: brittle on novel vocabulary, ignores syntactic complexity. *Would reconsider*: as a fast fallback when the classifier is unavailable (degraded mode).

## What would change our mind

- A published CEFR classifier with materially better numbers (macro-F1 > 0.85 on a comparable held-out set) under a permissive license.
- Phase 3 audit reveals the CamemBERT-derived classifier cannot reach the F1 / adjacency targets even with our fine-tuning budget.

## References

- [JonathanStefanov/CEFR_Classifier_French](https://huggingface.co/JonathanStefanov/CEFR_Classifier_French)
- Stefanov, 2024.
- Master prompt §2.1.1, §8.
- Phase 3 §1.3.
