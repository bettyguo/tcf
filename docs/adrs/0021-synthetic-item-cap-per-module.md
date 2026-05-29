# ADR-0021: Synthetic-item cap = 40% per module

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Content lead, ML lead
- **Phase**: 3

## Context

Under ADR-0018 (hybrid authoring), items entering the bank fall into two
categories with respect to the LLM:

- **Non-synthetic**: the passage / transcript is scraped from a CC-
  compatible source, the question + distractors are LLM-authored, but
  the underlying L2 evidence is authentic. By convention, items in
  this category have `synthesizer_version` set (the question was
  synthesized) but the passage is real. They are *not flagged*
  `synthetic=True`.
- **Synthetic**: the passage *itself* is LLM-generated (for example,
  a CE passage modeled on a register the open corpus does not cover
  well — formal letters, administrative notices), or an EE / EO
  prompt where the entire stimulus is authored from scratch. These
  items have both `synthesizer_version` *and* `synthetic=True`.

The motivation for synthetic passages: open-license French content is
strong on news (Voxpopuli), narrative (Wikisource, Gutenberg), and
spoken vernacular (Common Voice). It is weak on the *administrative*
and *formal-letter* registers that TCF CE genres require. Synthetic
passages backfill those cells.

The risk: a bank that is mostly synthetic trains comprehension of
LLM-French, not French. R-003 escalates as synthetic share grows.

The question is **where to draw the line** and **at what denominator**.

`phase3_think.md §3` defers the numerical value to design; this ADR
locks it in.

## Decision

**Synthetic items are capped at ≤ 40% of each module's bank.** The
denominator is *per module* (CO / CE / EE / EO), not per cell in the
quota matrix and not bank-wide.

- For CO: synthetic share ≤ 40% — but in practice CO is near 0%
  synthetic because authentic audio is the central evidence and the
  master prompt §6.3 invariant ("never used for the authoritative
  transcript of CO audio") rules out fully-synthetic audio items.
  The cap is permissive; the policy is restrictive.
- For CE: synthetic share ≤ 40% — backfills administrative and
  formal-letter cells.
- For EE: synthetic share ≤ 40% — but in practice EE is near 100%
  synthetic, because EE *prompts* are stimuli we author from scratch.
  The EE module is exempt from this cap by construction; the
  `synthetic` flag for EE is informational, not gating.
- For EO: same as EE.

Operational consequence: the **cap applies meaningfully to CO and CE
only**. For EE and EO, the `synthetic` flag is tracked for provenance
but the cap is documented as not-applicable (the items are inherently
prompts, not derived from authentic source material).

## Consequences

- **Positive**:
  - The CO and CE banks remain majority-authentic, preserving the
    Krashen-style comprehensible-input claim (master prompt §2.1).
  - The synthesis pipeline has explicit headroom to fill genre
    cells the open corpus cannot cover, without unbounded growth.
  - The cap is enforced at audit time
    (`tests/content/test_synthetic_cap.py`,
    `phase3_design.md §12.6`) and visible in `BANK_STATS.md`.
- **Negative**:
  - 40% is a judgment call. The literature on synthetic-vs-authentic
    L2 input efficacy is thin enough that we cannot defend a tighter
    bound without a Phase 4 calibration study.
  - Under-filling the cap (e.g., reaching only 15% synthetic in CE
    because the open corpus covers most genres adequately) is
    *also* fine and produces a better bank; the cap is a ceiling,
    not a target.
  - For EE and EO, the cap is effectively disabled. This is documented
    but a reader who scans only the ADR title may misinterpret. The
    audit report makes the module-by-module status explicit.
- **Neutral**:
  - The `synthetic` boolean column on `items` (Phase 2 schema, §2.2
    of `phase2_design.md`) is already in place; no schema change is
    required for this ADR.

## Alternatives considered

- **Cap at 20%**: would force more reliance on authentic
  administrative/formal-letter content, which is sparse in CC-
  licensed corpora; would fail to meet CE quota cells. *Would
  reconsider*: if a calibration study shows 20% achieves materially
  better learner outcomes.
- **Cap at 60%**: lets synthesis dominate; weakens the authenticity
  claim and increases R-003 surface area. Not aligned with master
  prompt §2.1 (comprehensible *authentic* input as the doctrine).
- **Cap per CEFR cell** (e.g., "≤ 40% synthetic in each CEFR × genre
  cell"): rejected because (i) it forces synthesis to backfill rare
  cells regardless of quality, defeating the cap's intent; (ii)
  measurement noise at small cell sizes (< 50 items) makes the cap
  trigger spuriously. *Would reconsider*: at bank sizes > 50k where
  cell sizes are large enough for stable measurement.
- **Bank-wide cap** (≤ 40% across the union of all four modules):
  rejected because EE and EO are ~100% synthetic by construction;
  a bank-wide cap would force underproduction of EE/EO or
  overcompensation in CO/CE.

## What would change our mind

- **Phase 4 calibration study**: if the IRT-calibrated difficulty of
  synthetic items diverges systematically from authentic items (e.g.,
  synthetic items are 0.5 logits easier than authentic at the same
  CEFR), the cap should tighten and synthetic items should be
  re-CEFR-classified.
- **Learner outcome audit (Phase 9)**: if simulated cohorts whose
  diet is synthetic-heavy show systematically worse exam-readiness
  trajectories than authentic-heavy cohorts, tighten the cap to
  25%.
- **R-003 incident**: a learner-detectable "synthetic tell" is
  identified in production (e.g., distractor length always matches
  correct option) — we audit *all* synthetic items, re-run the
  adversarial gate (ADR-0019) at a tighter threshold, and may
  retire the affected synthesizer version.

## References

- `03_CONTENT_PIPELINE.md §1.2, §2.4`
- `phase3_think.md §1.2, §3`
- `phase3_design.md §3, §12.6, §15`
- Master prompt §2.1 (comprehensible input), §6.3
- ADR-0018 (hybrid authoring)
- ADR-0019 (adversarial threshold)
- R-003 (synthetic-tells risk)
