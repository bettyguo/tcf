# ADR-0019: Adversarial-distractor rejection threshold = 0.25 over 20 trials

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Content lead, ML lead
- **Phase**: 3

## Context

Under ADR-0018 (hybrid authoring), the LLM-synthesized question +
distractors are validated by an adversarial pass: a *different-family*
LLM tries to answer with no passage visible, and the item is rejected
if the blind LLM beats chance.

For a 4-option MCQ, **chance is 0.25**. An adversarial accuracy strictly
above 0.25 means the question itself (or the distractor surface) leaks
the answer — the distractors are too telegraphic, the correct option
has a length / syntax / register tell, or the question is reasoning-
solvable without comprehension. Below 0.25, the blind LLM is doing no
better than guessing; the question really does require the passage.

The two free parameters are:

1. **The accuracy threshold** above which we reject.
2. **The number of trials** over which we estimate the accuracy.

R-003 names "detectable tells" as the most likely synthetic-content
failure mode. The gate is the primary defense.

## Decision

**Reject any item whose adversarial accuracy exceeds 0.25 over 20
independent trials with temperature 0.7 and varied seeds.**

Operationally:

- Adversarial model: `claude-haiku-4-5` (different family from the
  synthesizer's `claude-sonnet-4-6`; per `phase3_design.md §5.2`).
- Trials: 20.
- Per-trial temperature: 0.7 (gives the model some variance so a single
  lucky guess doesn't dominate).
- Per-trial seed: `(item_hash, trial_index)` so the audit is
  reproducible.
- Reject condition: `correct_count / 20 > 0.25`, i.e. > 5/20.

The threshold is **strict** (`>`, not `≥`): exactly 5/20 = 0.25 is the
chance line and passes. 6/20 = 0.30 fails.

## Consequences

- **Positive**:
  - Converts "are these distractors good?" into a measurable predicate
    with a documented threshold.
  - Different-family validator (Haiku vs Sonnet) reduces shared-blind-
    spot risk.
  - 20 trials gives ~0.10 standard error on the accuracy estimate at
    p=0.25 — tight enough to discriminate, cheap enough to run on
    every item.
  - Reproducible (seeded) so audits can replay the exact rejection
    decision later.
- **Negative**:
  - Each item carries 20 extra LLM calls (Haiku is cheap, but at 10k
    items it is real money). Operator cost is documented in
    `docs/audit/llm_cost_per_bank.json` (`phase3_design.md §12.8`).
  - The threshold is statistical: an item with adversarial accuracy
    of exactly chance still has a ~50% chance of fluctuating above
    0.25 in a 20-trial run. We accept this false-reject rate (≈ 12%
    at the boundary) because the cost of accepting a leaky item is
    higher than the cost of regenerating one.
  - Same-family fallback: if Haiku is unavailable, the validator
    falls back to a non-Anthropic model (Mistral Large via litellm
    gateway). The threshold stays 0.25 across model families.
- **Neutral**:
  - The reject reason (`quality_flag = HIGH_ADVERSARIAL`) is logged
    to the rejections cache; the synthesizer can be re-prompted
    with the offending item as a negative exemplar in a future
    prompt revision.

## Alternatives considered

- **Threshold = 0.30 over 10 trials** (looser): rejected because the
  false-pass rate at the boundary rises to ~30% with only 10 trials,
  and 30% leaky-item accept rate would dominate R-003.
- **Threshold = 0.20 over 50 trials** (tighter): rejected because the
  cost climbs proportionally (2.5× LLM calls per item) and the
  signal-to-noise improvement at 0.20 is marginal — most genuinely-
  leaky items score 0.40+ over 20 trials, well above 0.25.
- **Adaptive thresholds per CEFR level** (e.g., higher threshold for
  A1 where questions naturally allow more guessing): rejected for
  v1 simplicity. *Would reconsider*: if Phase 3 audit shows the gate
  is systematically rejecting A1/A2 items at a much higher rate than
  B1/B2.
- **Same-model adversarial check** (Sonnet validating its own output):
  rejected because shared blind spots make the gate optimistic.

## What would change our mind

- **The gate rejects > 30% of synthesized items for two consecutive
  batches.** This means the synthesis prompt is the problem (not the
  threshold). We'd revise the synthesis prompt or the synthesis LLM
  before relaxing the threshold.
- **Phase 4's IRT calibration shows that "passed" items have
  systematically too-high observed accuracy** — i.e., real learners
  also find the items easy — suggesting the threshold is letting
  leaky items through. We'd tighten to 0.20.
- **Cost audit shows the 20-trial gate exceeds 30% of total
  pipeline LLM cost.** We'd consider dropping to 10 trials with a
  bootstrap CI gate (reject if the lower CI bound > 0.25) instead
  of raising the threshold.
- **A different-family adversarial model becomes materially cheaper
  or better.** We swap and re-validate; the threshold stays.

## References

- `03_CONTENT_PIPELINE.md §1.4, §2.5`
- `phase3_think.md §1.1, §2.1`
- `phase3_design.md §5.2`
- ADR-0009 (LLM gateway)
- ADR-0018 (hybrid authoring)
- R-003 (synthetic-tells risk)
