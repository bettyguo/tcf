# ADR-0039: LLM critic uses temperature ≤ 0.2 + structured-output enforcement

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 7 (Auto-Scoring & Feedback)

## Context

The Phase 7 LLM critic returns per-rubric scores, justifications,
error annotations, and rewrite suggestions. Two failure modes
documented in the L2 auto-scoring literature drive this ADR:

- **Chain-of-thought leakage / inconsistency.** A free-form LLM
  graded twice on the same submission can produce two different
  rubric scores, sometimes by 2+ bands. Temperature 0.7 amplifies
  this; temperature 0 mitigates but does not eliminate it.
- **Response-shape drift.** If the LLM occasionally emits prose
  instead of JSON, the scorer falls back to silent default scores —
  a "silently wrong" path the system must refuse.

## Decision

The cloud LLM critic adapter (the production implementation of
`LLMCritic`) MUST be configured with:

1. Temperature ≤ 0.2 (provider-specific equivalent: Claude
   `temperature` ≤ 0.2; OpenAI `temperature` ≤ 0.2).
2. Structured-output enforcement (`response_format` JSON schema, or
   the provider's equivalent strict structured-output mode).
3. The grading prompt MUST include the "refuse-to-inflate"
   instruction: a 5/5 on any dimension requires a quoted text span
   as evidence. This is encoded in `EE_STRICT_INSTRUCTION` /
   `EO_STRICT_INSTRUCTION` in `tcf_accel_ml.scoring.llm.prompts`.
4. Few-shot anchors at NCLC 7 / 9 / 11 ceilings (paraphrased; no
   reproduction of FEI test material — ADR-020).

If the LLM returns malformed output, the adapter MUST return
`LLMCritique(refused=True)` and the scorer MUST flag the rubric
`needs_human_review`. Silent fallbacks are forbidden.

## Consequences

- Variance is bounded. Two grading runs on the same submission agree
  on the rubric scores within ≤ 1 band per dimension; the audit
  asserts this on a synthetic test set of 30 fixed inputs.
- The `LLMCriticStub` honors the same protocol — refusal is
  reachable in tests without a cloud call.
- The structured-output requirement is provider-specific; the
  adapter abstracts it. A provider that drops structured-output
  support is unfit for this slot until support returns.

## Related

- ADR-036, ADR-040
- `phase7_design.md §4`
- `packages/ml/src/tcf_accel_ml/scoring/llm/prompts.py`
