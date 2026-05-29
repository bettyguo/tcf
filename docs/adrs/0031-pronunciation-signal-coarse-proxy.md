# ADR-0031: `PronunciationSignal` is a structural coarse-proxy contract

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 5 (Practice & Drill Engines)

## Context

The pronunciation pipeline (`phase5_design.md §5`) produces a number —
PER, per-phoneme accuracy, prosody score. The think doc
(`phase5_think.md §1.2`) names the harm: pronunciation scoring is
genuinely hard to do well; over-claiming reproduces the R-004-shape
(over-prediction of ability) that ADR-025 commits us to refusing for
the NCLC posterior.

The think doc considered three options:

- (a) Decorative caveat: tooltip next to a numeric score. Rejected
  because one A/B test removes the tooltip and the harm shape
  returns.
- (b) Bucketed-only signal (no number). Rejected because the planner
  needs a continuous value for the rubric integration; over-coarse
  loses diagnostic capacity.
- (c) `PronunciationSignal` is a typed model with `score: float` AND
  `display_label: Literal[...]`; UI consumes `display_label`, planner
  consumes `score`; static + runtime checks enforce the separation.

## Decision

**(c) Structural separation: `score` for the planner, `display_label`
for the UI, both required.**

1. **Frozen Pydantic contract** in
   `packages/shared/src/tcf_accel/schemas/pronunciation.py`. Every
   `PronunciationSignal` carries:

   - `score: float ∈ [0, 1]` — the planner / rubric scorer reads this.
   - `signal_kind: Literal["coarse_proxy"]` — fixed literal; any
     other value fails validation. A future contributor cannot
     "simplify" the contract without deleting an explicit field.
   - `disclaimer_version: str` (min_length=1) — required; the UI
     renders the matching disclaimer copy alongside any surfaced
     label.
   - `display_label: Literal["weak","fair","strong","insufficient_data"]`
     — the UI reads this.
   - Nested `prosody: PronunciationProsody` with `pitch_range_hz`,
     `speech_rate_wpm`, `pause_count`, `mean_pause_ms`.

   `model_config = frozen=True, extra="forbid"`.

2. **Insufficient-data gate** (`display_label_from`): when
   `duration_s < 2.0` OR `asr_mean_confidence < 0.50` OR
   `n_phonemes_aligned < 8`, the label is `"insufficient_data"`
   regardless of PER. The planner ignores any row with
   `display_label == "insufficient_data"` (audited by
   `phase5_audit.md §8`).

3. **Static AST lint rule**
   (`tests/lint/test_no_raw_pron_score_outside_allowlist.py`): an
   AST walker scans every `.py` file under `packages/` and `apps/`
   for attribute accesses `<NAME>.score` where `NAME` matches the
   pronunciation-signal variable convention
   (`pronunciation`/`pronunciation_signal`/`pron_signal`/`pron_sig`).
   Any such access outside the allowlist
   (`packages/ml/.../pronunciation/`, future
   `packages/sla/.../scoring/`, future
   `apps/worker/.../tasks/score_*`) fails the test with the offending
   file + line.

4. **`PronunciationSignal` is the only sanctioned construction path**
   outside tests: `tcf_accel_ml.pronunciation.signal.build_signal`.
   Phase 7's rubric scorer reads `score`; the UI reads
   `display_label`. The two layers are statically separated.

5. **Hypothesis property tests** (`tests/property/test_pron_signal_contract.py`)
   verify: every factory output is `signal_kind="coarse_proxy"`,
   every display_label is in the documented set, the gate routes to
   insufficient_data when any predicate fails, `score = max(0, 1 -
   PER)` saturating, and the gate is monotone in PER over the
   sufficient regime.

## Consequences

- **Positive**:
  - The harm shape is structurally prevented. A future engineer who
    wants the "raw number" hits the lint rule first, the
    type-system second, and the documented contract third — three
    layers of friction, deliberately.
  - The disclaimer is required, not optional. A model dump that
    misses the disclaimer fails at validation, not at code review.
  - The refuse-to-predict path (insufficient_data) mirrors the
    Phase 4 confidence gate from ADR-025; consistent harm-shape
    handling across the system.
- **Negative**:
  - Two surfaces (planner / UI) for one number; the discipline is
    the *separation*. New code reading `PronunciationSignal` has to
    pick the right field.
- **Neutral**:
  - The thresholds (2 s, 0.50 confidence, 8 phonemes, 10%/20% PER
    bands) are tunable; the *shape* of the gate (existence of
    insufficient_data + signal_kind literal + required disclaimer)
    is not.

## Alternatives considered

- See Context (a) and (b).
- **Compute the label client-side from `score`**: rejected because
  it lets a UI engineer bypass the gate ("our threshold is
  different"); centralizing the mapping in the factory keeps it
  uniform.
- **Drop `score` from the schema entirely**: would block legitimate
  Phase 7 rubric integration that combines pronunciation with other
  components on a numeric axis.

## What would change our mind

- A UI engineer surfaces `PronunciationSignal.score` as a number in
  a card despite the `display_label` separation. The contract held;
  the discipline did not. We'd add a runtime serializer guard and
  raise the lint rule's CI severity.
- Phoneme-level signal turns out to be much *less* reliable than
  assumed (correlation < 0.4 with expert ratings). We'd downgrade
  the surfaced signal to two buckets and remove pronunciation from
  the rubric until Phase 7 recalibrates.
- Phoneme-level signal turns out to be *more* reliable than the
  bucketing suggests (correlation > 0.8). We'd revisit bucketing
  granularity but **not** surface the raw float; the structural
  guarantee is the floor.

## References

- `phase5_think.md §1.2`, `phase5_design.md §5.2`.
- `packages/shared/src/tcf_accel/schemas/pronunciation.py` — the model.
- `packages/ml/src/tcf_accel_ml/pronunciation/{signal,per,insufficient_data}.py`
  — the factory + gate.
- `tests/lint/test_no_raw_pron_score_outside_allowlist.py` — AST static check.
- `tests/property/test_pron_signal_contract.py` — Hypothesis invariants.
- `phase5_audit.md §8`.
