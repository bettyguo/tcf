# ADR-0018: Hybrid scraped-passage + LLM-question item authoring

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Content lead, ML lead
- **Phase**: 3

## Context

Phase 3 must produce ≥ 5000 CO items, ≥ 5000 CE items, ≥ 500 EE prompts,
≥ 800 EO prompts (`03_CONTENT_PIPELINE.md §4`). At our team size and
licensing posture (master prompt §6.3, ADR-0010), the bank cannot be
written by hand. Three authoring shapes are in play
(`phase3_think.md §1.1`):

1. **Pure scraping**: passages, audio, *and* the source's headlines or
   captions repurposed as questions. Format-mismatched (real prose was
   not written as a comprehension probe). Copyright-fragile (derivative
   use of headlines/captions is murkier than reuse of body text).
2. **Pure LLM authoring**: a single LLM call produces passage, question,
   correct answer, and distractors. Format-aligned but the *passage*
   is synthetic — the L2 input the learner reads/hears is not authentic
   French. Detectable-tells failure mode (R-003) is worst here: one
   model writes both passage and distractors and so knows the surface
   cues.
3. **Hybrid**: scrape passages from open-license sources (CC0, CC-BY,
   CC-BY-SA, PD; ADR-0010 §6.3), have an LLM author the
   question + correct answer + 3 distractors, validate with a
   different-family LLM in adversarial mode (ADR-0019).

Master prompt §6.1 (correctness over coverage) and §9 differentiator 5
(honesty / ethical content sourcing) compose: the unit being tested is
*comprehension of authentic French input*, not "ability to answer
LLM-styled probes."

## Decision

**Adopt the hybrid (option 3) for all four modules.** The *passage* (CE)
or *audio + transcript* (CO) is the authentic L2 evidence and is drawn
from a CC-compatible source. The *question + distractors* is
LLM-synthesized (Claude Sonnet 4.6 per ADR-0009) with documented
prompt provenance (`Provenance.llm_prompt_hash`) and rejected by the
adversarial gate (ADR-0019) if the distractors leak the answer.

For EE and EO (prompt-only items, no MCQ surface), the LLM authors the
*prompt text* directly; there is no adversarial check, but the prompt
itself is CEFR-classified, length-checked against FEI task specs, and
required to flag Canadian context for EE Tasks 2 & 3.

The CO module observes one additional invariant beyond ADR-0009: the
authoritative transcript is **never LLM-authored**. The transcript is
either the source's ground-truth or a Whisper-large-v3-french output
(`bofenghuang/whisper-large-v3-french`, ADR-0007) that has passed a
forced-alignment check (`phase3_design.md §3.2`).

## Consequences

- **Positive**:
  - Authentic L2 input is preserved across the bank; the system trains
    comprehension of real French, not LLM-French.
  - Question quality is mechanically verifiable via the adversarial
    pass (ADR-0019), converting "are these distractors good?" into a
    measurable predicate.
  - Two clean provenance chains compose: passage license
    (`Provenance.source`, `Provenance.license`) and synthesis metadata
    (`Provenance.llm_model`, `Provenance.llm_prompt_hash`,
    `Provenance.synthesizer_version`).
  - The synthetic-item cap (ADR-0021) applies cleanly: an item is
    "synthetic" iff `synthesizer_version` is non-null, regardless of
    passage source.
- **Negative**:
  - Two-model pipeline (synthesizer + adversarial validator) is more
    expensive per item than (a) or (b).
  - We must enforce that the synthesis LLM did not paraphrase the
    passage into the question (the adversarial check catches the
    extreme; subtler leakage is caught by the
    `distractors_supported_in_passage` check in
    `phase3_design.md §5.4`).
  - For EE/EO, the "passage" is the prompt itself; there is no
    authenticity anchor. We accept this because the EE/EO surface tests
    *production*, not comprehension, and the prompt is just the
    stimulus.
- **Neutral**:
  - The pipeline carries two distinct trace fields per item
    (passage-source provenance + synthesizer provenance); the
    `Provenance` schema in `packages/shared/src/tcf_accel/schemas/
    common.py` already accommodates both (Phase 1 baseline).

## Alternatives considered

- **Pure scraping (option 1)**: rejected because (i) the items would
  not match TCF MCQ format — real prose was not written as a
  comprehension probe; (ii) the licensable scope of derivative-use of
  headlines/captions is more restrictive than reuse of body text;
  (iii) we cannot produce the EE/EO surface at all this way. *Would
  reconsider*: only if the LLM synthesis quality collapses on a
  specific module and no prompt tuning recovers it — at which point
  we'd consider a tiny human-authoring residual for that module, not
  pure scraping.
- **Pure LLM authoring (option 2)**: rejected because the passage is
  the *evidence*, not the *probe*. A synthetic passage trains the
  learner to read LLM-styled French; transfer to authentic exam input
  is unmeasured. R-003 (synthetic tells) is worst when one model
  writes both passage and distractors. *Would reconsider*: only for
  CE specifically if a 100-item human-review sample finds that the
  *passage* (not the question) is the dominant failure mode —
  `phase3_think.md §2.1` triggers.

## What would change our mind

- **Adversarial gate rejects > 30%** of synthesized items for two
  consecutive batches — the synthesis prompt is unreliable; we'd
  revise it or swap the synthesis LLM before considering a fall-back
  authoring shape.
- **Human review on a 100-item sample finds the passage is the
  failure mode**, not the question — we'd reconsider option (b) for
  CE specifically, keeping (3) for CO (audio stays authentic).
- **The same-family adversarial check is gameable** (synthesis +
  adversarial LLM share blind spots and the gate passes items a
  human would trivially answer) — we'd swap the adversarial model
  family (Mistral / Llama vs Claude), and if discriminative power
  doesn't return, add a small human-review sample as a third filter.

## References

- `03_CONTENT_PIPELINE.md §1.4, §2.2, §2.3`
- `phase3_think.md §1.1`
- `phase3_design.md §3` (synthesizers), `§5.2` (adversarial gate),
  `§5.4` (distractor-in-passage check)
- Master prompt §6.1, §6.3, §9 differentiator 5
- ADR-0007 (Whisper primary ASR)
- ADR-0009 (Claude Sonnet 4.6 via litellm gateway)
- ADR-0010 (MIT code / CC-BY-SA content)
- ADR-0019 (adversarial-distractor threshold)
- ADR-0021 (synthetic cap)
- R-003 (synthetic-tells risk)
