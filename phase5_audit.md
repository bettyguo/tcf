# Phase 5 — Audit

> Companion to `05_PRACTICE_AND_DRILLS.md §4`. Each spec audit metric
> maps to a test path, a gate threshold, and a status. Status is
> `Pending` for items whose implementation step (per
> `phase5_design.md §17`) has not landed; status flips to ✅ / ❌ as
> implementation does. The intent: this doc is the acceptance contract
> the implementer signs off against, not a post-hoc report.

Date opened: 2026-05-28.

---

## 0. How to read this doc

Each section maps to one spec §4 bullet. The columns:

- **Spec metric** — quoted from the spec, verbatim.
- **Gate** — the precise numeric/boolean threshold; what the test
  asserts.
- **Test path** — the file Phase 5 implementation will land + the
  function name.
- **Status** — `Pending` / ✅ / ❌ / `Deferred` (with reason).
- **Notes** — anything load-bearing about the metric or threshold.

The status column flips during implementation. The doc is the source
of truth for "what counts as Phase 5 done."

---

## 1. Per-drill correctness — perfect-agent suite

**Spec metric**: "for each drill type, write a scripted 'perfect agent'
that always answers correctly; the agent's final session report must
show 100% accuracy, expected FSRS state updates, correct posterior
shift."

**Gate**: for each of the 21 `drill_kind` values
(`phase5_design.md §4.5`), a perfect-agent session of N=10 items emits:

- `SessionSummary.items_correct == items_seen` (100% accuracy).
- For each item: the FSRS `Card.stability` post-review is ≥ pre-review.
- The aggregate posterior shift on the relevant skill: `Δmean ≥
  EXPECTED_DELTA[drill_kind]` (per-drill table below) within 0.05 NCLC.

| `drill_kind` | EXPECTED_DELTA per 10-item session | Notes |
|---|---|---|
| `co_mcq` | +0.20 NCLC | baseline reception drill |
| `co_dictation` | +0.18 NCLC | dictation correctness ≈ MCQ but partial-credit smooths |
| `co_shadowing` | +0.15 NCLC (CO) + pronunciation `strong` | dual signal |
| `co_accent` | +0.15 NCLC | narrow sub-skill |
| `co_gapfill` | +0.18 NCLC | per-gap aggregated |
| `co_lexical_alt` | 0.0 NCLC on CO, **+0.20 on CE** | proves the §7 routing |
| `ce_mcq` | +0.20 NCLC | baseline |
| `ce_skim_scan` | +0.15 NCLC | three-Q aggregate |
| `ce_vocab_context` | +0.18 NCLC | per-lexeme aggregate |
| `ce_register_id` | +0.10 NCLC | narrow |
| `ce_summary` | +0.05 NCLC | rubric-stubbed in Phase 5 |
| `ee_task` (Task 2) | rubric-pending; `graded_score.pending=True` | Phase 5 emits, Phase 7 scores |
| `ee_rewrite` | rubric-pending | same |
| `ee_connector` | +0.15 NCLC | per-slot MCQ aggregate |
| `ee_error_correction` | annotations-pending | Phase 5 stub |
| `ee_register_adjust` | rubric-pending | same |
| `eo_task` (Task 1) | rubric-pending; pronunciation signal present | dual hand-off to Phase 7 |
| `eo_picture` | rubric-pending | |
| `eo_spontaneous` | rubric-pending | |
| `eo_roleplay` | rubric-pending | |
| `eo_repair` | rubric-pending + microdrill round-robin | |

For the rubric-pending drills, the perfect-agent gate is reduced: the
`Interaction` is well-typed, `graded_score.pending=True`, the Phase 7
hook is dispatchable (worker task succeeds), and the pronunciation
signal (if applicable) carries `display_label != "insufficient_data"`
on a clean reference recording.

**Test path**: `tests/pedagogy/test_perfect_agent_per_drill.py`
(parametric on `drill_kind`).

**Status**: `Pending` — gated on §17 steps 2, 5, 8, 9.

**Notes**: The EXPECTED_DELTA numbers are calibrated against Phase 4's
synthetic-cohort baseline (`tests/pedagogy/synthetic_cohorts.py`). If
the delta lands ≥ 50% off, the underlying allocator's β weights or the
estimator's variance is doing something we don't expect — investigate
the calibration before relaxing the test.

---

## 2. Pacing — exam-pace timer within ±1 s

**Spec metric**: "the timer in exam-pace mode matches the official
module duration to within ±1 s over a 35-min stretch."

**Gate**: a mocked-clock CO session driven through 39 items at
`audio_length + 20 s` per item produces a cumulative elapsed time
within ±1 s of 35 min × 60 = 2100 s.

**Test path**: `tests/perf/test_co_timer.py::test_exam_pace_35min_within_1s`.

**Status**: `Pending` — gated on §17 step 12.

**Notes**: The test mocks `time.monotonic` to a deterministic clock;
the assertion is on the timer's *logical* progression, not on
wall-clock latency. A wall-clock latency test is out of scope for
Phase 5's audit (that's a deployment concern; Phase 9). Repeats with
CE (60 min / 39 items) and EE (60 min for 3 tasks) included in the
same module; per-module assertions parametric on the spec timings.

---

## 3. Pronunciation pipeline end-to-end — PER within ±0.05

**Spec metric**: "on a 50-utterance held-out test set with
hand-labeled phoneme transcriptions, MFA + our pipeline produces a
PER within ±0.05 of expert annotations."

**Gate**: for each utterance in
`packages/ml/data/eval/aligned_50/*.wav`,
`abs(per_pipeline - per_expert) <= 0.05`. Aggregate: at least 47/50
utterances within bound (one outlier per 17 allowed by Wilson
binomial at α=0.05 around the 0.94 floor).

**Test path**: `tests/quality/test_mfa_per.py::test_pipeline_per_within_005_of_expert`.

**Status**: `Pending` — gated on §17 step 6 + the eval set's
hand-annotation pass (operator task).

**Deferred sub-metric**: per-phoneme accuracy breakdown. The Phase 5
audit gates the aggregate PER only; per-phoneme tables are produced
as informational output (`per_phoneme_accuracy.csv`) but not gated.
Phase 7's rubric calibration may tighten this in a follow-up.

**Notes**: The 50-utterance set lives in `packages/ml/data/eval/` and
is sourced from Common Voice fr (CC0). Hand annotation produces
`<sha256>.lab` files with phoneme sequences in IPA. The test is
skipped with a warning if the eval set is absent (it requires the
operator to have run `make install-eval-data` once).

---

## 4. ASR quality — WER ≤ 9% on Common Voice fr

**Spec metric**: "WER on Common Voice fr test set ≤ 9% (matches
published whisper-large-v3-french benchmarks)."

**Gate**: Whisper-large-v3-french against a 500-utterance Common Voice
fr test slice produces WER ≤ 0.09.

**Test path**: `tests/quality/test_whisper_wer.py::test_cv_fr_wer_under_9pct`.

**Status**: `Pending` — gated on §17 step 6.

**Deferred sub-metric**: WER on the operator's local Canadian-accent
slice (RFI / ICI Première). This is an operator-tier dataset (Phase 3
ADR-020-adjacent); the Phase 5 audit does not gate it. Operators who
care should compare the local WER against the published baseline as
part of their own acceptance.

**Notes**: The test loads the model from the local cache. CI runs it
only after `make install-models` has populated
`~/.cache/huggingface/`. The test is marked `slow` (it processes 500
utterances at ~3× real-time on CPU; ≈ 20 min in CI) and gated by a
`--run-slow` pytest flag.

---

## 5. Accessibility — axe-core clean + keyboard walkthrough

**Spec metric**: "axe-core scan returns zero violations on every drill
UI; keyboard-only walkthrough succeeds for every drill."

**Gate**:

- **axe-core**: every drill UI stub (one per `drill_kind`, served by
  the Phase 8 placeholder shell at `apps/web/app/drill/[kind]`) is
  loaded in Playwright; `axe.run()` returns `violations.length === 0`
  at WCAG 2.2 AA.
- **Keyboard walkthrough**: a scripted Playwright keyboard journey
  per drill reaches every interactive element via Tab/Shift+Tab/Enter/
  Space; no element-trap; the drill is completable end-to-end.

**Test path**:
- `tests/a11y/test_axe_per_drill.py`
- `tests/a11y/test_keyboard_walkthrough.py`

**Status**: `Pending` — gated on §17 step 12. Phase 8 ships the
production UI; Phase 5 ships the drill *shells* sufficient for the
audit (a `<DrillFrame>` component per kind with the prescribed ARIA
roles and the audio-element contract from §4.1).

**Notes**: The axe configuration excludes the Phase-8-owned
chrome/layout (`#site-header`, `#site-footer`) so the audit measures
the drill surface specifically. The keyboard walkthrough explicitly
asserts that **CO drills do not expose audio scrubbing keys** — the
arrow keys, Home/End, and digit keys do not seek the audio element.

---

## 6. Drill diversity — ≥ 4 drill kinds per module per 100 sessions

**Spec metric**: "in a 100-session synthetic run, the planner selects
from ≥ 4 drill types per module (no monoculture)."

**Gate**: for each `module ∈ {CO, CE, EE, EO}`,
`len(distinct(drill_kind for session in 100_session_run if
session.module == module)) >= 4`.

**Test path**: `tests/pedagogy/test_drill_diversity.py::test_diversity_per_module_100_sessions`.

**Status**: `Pending` — gated on §17 step 10.

**Notes**: The 100-session run uses a deterministic seed and the
synthetic cohort fixture from Phase 4. The diversity selector
(`select_drill_kind(module, posteriors, history)`) is the Phase 5
boundary; the spec leaves it implicit. The selector is implemented in
`packages/sla/src/tcf_accel_sla/planner/select_drill_kind.py` and
maintains a per-user recency window (≤ 30 days) so the same drill
doesn't repeat back-to-back. Test asserts both the diversity floor and
that no single drill kind exceeds 50% of the module's sessions.

---

## 7. Single-play UX contract — replay never available pre-answer

**Not in spec §4**, but added per `phase5_think.md §1.1` and ADR-029.

**Gate**: across all CO default-mode drills, no audio element
re-binds `currentTime` between PRESENT and AWAIT_RESPONSE; the React
component tree's `<AudioPlayer>` exposes no seek API outside review
mode; a Playwright DOM-introspection test asserts the
`<audio>` element has `controls={false}` and `preload="none"`
before submission.

**Test path**: `tests/a11y/test_single_play_contract.py::test_co_no_replay_pre_answer`.

**Status**: `Pending` — gated on §17 step 5.

**Notes**: This is the structural complement to the keyboard-walkthrough
test in §5. The two together close the spec §5 anti-criterion "any
drill that allows replay of CO audio during the question."

---

## 8. Pronunciation contract — every signal carries `signal_kind` + `disclaimer_version`

**Not in spec §4** but per `phase5_think.md §1.2` and ADR-031.

**Gate**: a property test asserts that every `PronunciationSignal`
constructed from any pipeline path has:

- `signal_kind == "coarse_proxy"`,
- `disclaimer_version` is a non-empty string,
- `display_label` is one of `{"weak","fair","strong","insufficient_data"}`.

A second property test asserts the lint rule against `.score` access
outside the two allowed modules: a grep across `apps/`, `packages/`
excluding `packages/sla/src/tcf_accel_sla/scoring/`,
`apps/worker/src/tcf_accel_worker/tasks/score_*.py`, and the test
suite, finds zero `.score` accesses on `PronunciationSignal`.

**Test path**:
- `tests/property/test_pron_signal_contract.py::test_every_signal_is_coarse_proxy`
- `tests/lint/test_no_raw_pron_score_outside_allowlist.py`

**Status**: `Pending` — gated on §17 step 7.

**Notes**: The lint test is a static grep, not a runtime check. The
runtime serializer guard (`@model_validator` in
`PronunciationSignal`) is exercised by the unit tests in
`packages/ml/tests/pronunciation/test_signal.py`. The pairing of
runtime + static is deliberate (defense in depth).

---

## 9. Privacy posture — no audio/text crosses the network in default mode

**Not in spec §4** but per `phase5_think.md §1.3` and ADR-017.

**Gate**: the `tests/capability/` suite asserts:

- A default-mode EO session (`TCF_ACCEL_ASR_BACKEND` unset, no cloud
  LLM env vars set) makes zero outbound socket connections during the
  ASR / MFA / prosody pipeline.
- A default-mode EE session likewise makes zero outbound socket
  connections during scoring (the Phase 5 EE scorer stub runs
  locally).
- After a default-mode session completes, `data/` directory size
  delta is 0 bytes (no audio persistence).
- Constructing a cloud backend without the corresponding env var
  raises at construction time.

**Test path**:
- `tests/capability/test_no_network_in_default.py`
- `tests/capability/test_cloud_backend_requires_env.py`
- `tests/property/test_audio_not_persisted_default.py`

**Status**: `Pending` — gated on §17 step 13.

**Notes**: The capability tests use a `blocknet` fixture that
monkeypatches `socket.socket.connect` to raise `BlockedNetworkError`.
The fixture's coverage was originally written for the Phase 3 content
audit (`tests/capability/test_no_data_commits.py`); Phase 5 extends it
to the ASR/LLM paths.

---

## 10. Exam-shape floor — 409 on under-floor `POST /v1/session/start`

**Not in spec §4** but per `phase5_think.md §1.4` and ADR-028.

**Gate**:

- A user with `rolling_7d_exam_shape_minutes < EXAM_SHAPE_FLOOR_MIN`
  (default 30) and no dismissal this week receives `409 Conflict` with
  `error="E_SESSION_001"` on `POST /v1/session/start` for any
  non-exam-shape drill kind.
- The 409 response body matches the §9.4 schema with `dismissable=true`
  and `next_action="exam_shape"`.
- After `POST /v1/session/exam-shape/dismiss`, the same user can start
  a drill session; the dismissal is recorded in
  `data/dismissal_log.jsonl`.

**Test path**:
- `apps/api/tests/test_session_routes.py::test_under_floor_returns_409`
- `tests/property/test_exam_shape_floor.py::test_dismissal_unblocks_session_start`

**Status**: `Pending` — gated on §17 step 4.

**Notes**: The audit also asserts that mock-section sessions (Phase 6)
*do* count toward `rolling_7d_exam_shape_minutes`, even though Phase 6
ships the implementation. The Phase 5 boundary is the sessions
table's `exam_shape BOOLEAN` column; Phase 6 sets it.

---

## 11. Shadowing floor — every default plan reserves ≥ 10 min/day shadowing

**Not in spec §4** but per ADR-030.

**Gate**: across 100 synthetic-cohort plans generated by
`generate_plan` with the default plan-template, every day's
`co_shadowing` minutes ≥ 10. The floor is enforceable down to 3
minutes only via an operator plan-template override
(`packages/sla/templates/`).

**Test path**: `tests/pedagogy/test_default_plan_shadowing_floor.py::test_default_plan_satisfies_shadowing_floor`.

**Status**: `Pending` — gated on §17 step 10.

**Notes**: The shadowing minutes count against the CO allocation
(they update the CO posterior); the planner subtracts them before
distributing the remainder. A plan that hits the budget ceiling
(`target_minutes_per_day < 10 + sum(other_floors)`) is rejected at
generation; the planner surfaces a "budget too tight" rationale
rather than silently violating the floor.

---

## 12. Interaction-row completeness — every session writes its rows

**Not in spec §4** but per `phase5_think.md §5` invariant 7.

**Gate**: a fuzzed session-completion test asserts that for every
(drill_kind, response) pair where `submit_answer` returns 200, a row
exists in the `interactions` table with `session_id`, `item_id`,
`module`, `drill_kind` populated; `created_at` non-null.

**Test path**: `tests/property/test_interaction_completeness.py::test_every_session_writes_its_rows`.

**Status**: `Pending` — gated on §17 step 3.

**Notes**: The test fuzzes via Hypothesis on `(drill_kind,
mock_response_strategy)`; the strategy is keyed on `drill_kind` to
produce shape-valid responses.

---

## 13. Schema additivity — `0.4.0` is forward-compatible

**Not in spec §4** but per `phase5_think.md §5` invariant 8.

**Gate**:

- The Phase 2/3/4 round-trip tests pass unchanged.
- A new round-trip suite asserts that a Phase 5 `Interaction` (with
  `drill_kind`, `pronunciation`, `audio_path` set) round-trips
  cleanly.
- A "downgrade" property: a Phase 5 `Interaction` *without* the new
  fields (or with `null` values) parses against the *Phase 4*
  schema definition.

**Test path**:
- `packages/shared/tests/test_roundtrip.py` (existing, must continue
  to pass)
- `packages/shared/tests/test_phase5_roundtrip.py::test_phase5_interaction_roundtrips`
- `packages/shared/tests/test_schema_additivity.py::test_phase5_downgrade_safe`

**Status**: `Pending` — gated on §17 step 1.

**Notes**: The downgrade test pins a snapshot of the Phase 4 schema
JSON (`schemas/phase4.schema.json`) and uses `jsonschema.validate`
against it. SCHEMA_VERSION="0.4.0" but additive-only means a Phase 4
consumer can still parse a Phase 5 row (ignoring the new fields).

---

## 14. EO LLM follow-up — local-stub diversity ≥ 8 per task

**Not in spec §4** but per `phase5_design.md §12.2`.

**Gate**: the local-stub LLM-follow-up pool exposes ≥ 8 distinct
follow-up prompts per `(task_number, topic)` pair, sampled
deterministically by `hash(transcript_hash + task_number) % len(pool)`.

**Test path**: `tests/eo/test_followup_diversity.py::test_local_stub_diversity_per_task`.

**Status**: `Pending` — gated on §17 step 9.

**Notes**: The local stub is a deterministic pool, not a generator.
The cloud opt-in path (LiteLLM gateway) is *not* audit-gated here —
the cloud LLM produces more variety by construction; the audit
threshold is on the *local* stub because that's the default.

---

## 15. Summary

| # | Audit metric | Gate | Test path | Status |
|---|---|---|---|---|
| 1 | Per-drill perfect-agent | 21 drills × 100% accuracy | `tests/pedagogy/test_perfect_agent_per_drill.py` | Pending |
| 2 | Exam-pace timer | ±1 s over 35 min | `tests/perf/test_co_timer.py` | Pending |
| 3 | Pronunciation PER | ±0.05 of expert on 50 utts | `tests/quality/test_mfa_per.py` | Pending |
| 4 | ASR WER | ≤ 9% on Common Voice fr | `tests/quality/test_whisper_wer.py` | Pending |
| 5 | Accessibility | axe 0 violations + keyboard pass | `tests/a11y/*` | Pending |
| 6 | Drill diversity | ≥ 4 kinds / module / 100 sessions | `tests/pedagogy/test_drill_diversity.py` | Pending |
| 7 | Single-play UX | No replay pre-answer | `tests/a11y/test_single_play_contract.py` | Pending |
| 8 | Pronunciation contract | Every signal coarse-proxy + lint | `tests/property/test_pron_signal_contract.py` + `tests/lint/` | Pending |
| 9 | Privacy posture | 0 sockets, 0 audio bytes in default | `tests/capability/*` | Pending |
| 10 | Exam-shape floor 409 | Under-floor → 409, dismiss unblocks | `apps/api/tests/test_session_routes.py` | Pending |
| 11 | Shadowing floor | Default plan ≥ 10 min/day shadow | `tests/pedagogy/test_default_plan_shadowing_floor.py` | Pending |
| 12 | Interaction completeness | Every session writes its rows | `tests/property/test_interaction_completeness.py` | Pending |
| 13 | Schema additivity | Phase 4 still parses Phase 5 rows | `packages/shared/tests/test_schema_additivity.py` | Pending |
| 14 | EO follow-up diversity | Local stub ≥ 8/task | `tests/eo/test_followup_diversity.py` | Pending |

**Deferred** (with reason):

- **Per-phoneme accuracy breakdown** (sub-metric of §3): the
  aggregate PER is gated; the per-phoneme table is produced as
  informational output. Phase 7 may tighten this when calibrating
  the rubric scorer.
- **Wall-clock latency tests**: out of scope for Phase 5; Phase 9
  deploy-shape concerns.
- **WER on operator's Canadian-accent slice** (sub-metric of §4):
  operator-tier; not in repo CI.
- **EO LLM follow-up diversity for the *cloud* backend** (§14):
  not gated; cloud LLM is by definition more diverse than the
  stub.

The 14 numbered gates are the Phase 5 acceptance contract. The audit
doc transitions from `Pending` to a final status when implementation
lands; the evaluate doc (`phase5_evaluate.md`) reads this table at
close-out.
