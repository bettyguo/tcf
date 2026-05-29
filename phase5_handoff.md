# Phase 5 — Hand-off to Phase 6

> What Phase 6 (Mock Exam Engine) inherits, what's frozen, what's
> deferred. Date: 2026-05-28.

Phase 6 composes mock exams from the same item bank Phase 5 drills
consume, and feeds canonical-mock results into the Phase 4 readiness
traffic light. This document records the surfaces Phase 6 must NOT
break and the deferrals Phase 5 acknowledged but didn't ship.

---

## 1. Frozen surfaces Phase 6 must compose against

### 1.1 `Interaction` shape — additive only

`SCHEMA_VERSION = "0.4.0"` (`packages/shared/src/tcf_accel/schemas/`).
Phase 6 may *add* optional fields (additive); it must not remove,
rename, or change the type of any existing field. Required Phase 6
respect:

- `Interaction.module ∈ {CO, CE, EE, EO}` — mock-section interactions
  carry the module of the section they belong to.
- `Interaction.drill_kind` — Phase 6 emits `"mock_section"` (already
  reserved in `DrillKind`, registry pre-allocated as the entry point
  for Phase 6's implementation).
- `Interaction.pronunciation` — `None` unless the interaction
  recorded audio; the same Phase 5 contract applies.
- `Interaction.audio_path` — `None` by default (ADR-017). Phase 6's
  mock exam **must not** persist audio bytes; the privacy posture is
  uniform across phases.
- `Interaction.graded_score` — the JSONB payload Phase 7 reads. For
  EE/EO mock sections, Phase 6 emits `{"pending": True, ...}` and
  the worker registry (Phase 5 step 8) handles the rest.

The audit gate `phase5_audit.md §13` (schema additivity) pins this:
a Phase 4 consumer can still parse a Phase 5/6 row, ignoring the new
fields.

### 1.2 Exam-shape floor + cadence (ADR-028)

`EXAM_SHAPE_DRILL_TYPES = {mock_section, writing_short, writing_long,
speaking_mono, speaking_role}` is the canonical set. Phase 6's
`mock_section` is already in it; the runtime floor at `POST
/v1/session/start` and the planner's cadence post-pass both consult
it.

**Phase 6 must** emit `mock_section` as the `DrillType` for every
canonical mock interaction so the rolling-7-day floor sums correctly.
The `Sessions.exam_shape` boolean column (migration 0003) is the
storage-side counterpart — Phase 6 sets it `True` for any mock
session.

### 1.3 `PronunciationSignal` contract (ADR-031)

Mock exam EO sections record audio. The pipeline is the same as the
Phase 5 EO drills: `run_audio_pipeline()` from
`tcf_accel_sla.audio.pipeline` produces a typed `PronunciationSignal`,
which Phase 6 attaches to the EO interactions via
`Drill.to_interaction()`. The **structural contract** (signal_kind
literal, disclaimer_version required, display_label separated from
score) is enforced at the schema + lint layers — Phase 6 inherits
this for free as long as it goes through `build_signal()`.

### 1.4 Accessibility routing (ADR-029)

Phase 6's mock exam must honor the same accessibility profile the
practice drills do:

- `accessibility_profile.co_alternative == "lexical_alt"` → the mock
  exam's CO section is rendered as text; interactions emit `module =
  "CE"`, not CO. The CO posterior is *never* updated from a
  lexical-alt mock.
- `accessibility_profile.eo_alternative == "text_input"` → EO section
  is a typed response; interactions emit `module = "EE"`.

The DB CHECK constraint `interactions_lexical_alt_module_ck`
(migration 0004) enforces this at the storage layer.

### 1.5 Worker scoring registries

Phase 6 reuses the `score_ee` and `score_eo` Celery tasks +
`RubricScorer` / `EORubricScorer` registries from
`apps/worker/src/tcf_accel_worker/tasks/`. **Phase 6 does NOT** add
a third worker for mock scoring — the per-section rubric is the
same; the mock just composes multiple sections.

---

## 2. Reserved names Phase 6 owns

- `DrillKind = "mock_section"` — registered in
  `packages/shared/src/tcf_accel/schemas/api/plan.py`; **NOT**
  registered in `tcf_accel_sla.drills.REGISTRY` (Phase 6 lands the
  implementation).
- `Module = "..."` — Phase 6 may emit interactions for any of CO, CE,
  EE, EO depending on the section.
- Worker task `tcf_accel.score_mock` — namespace reserved per
  `apps/worker/src/tcf_accel_worker/tasks/__init__.py:7` ("Phase 6:
  `score_mock`"); Phase 6 adds the module + includes it in
  `celery_app.py`.

---

## 3. Deferred items (Phase 5 acknowledged but did not ship)

These are documented openly so Phase 6 doesn't trip over them.

### 3.1 Within Phase 5 step 5 (drills)

- **`co_shadowing`**: depends on ASR + PronunciationSignal (steps 6/7
  shipped the pipeline; the drill itself is deferred). Phase 6 does
  not depend on this drill. If Phase 6 wants to score a CO section's
  shadowing-style sub-task, it can call `run_audio_pipeline()`
  directly.
- **`co_accent`**: needs 2-clip item content (`COContent` is
  single-clip). The bank work to support 2-clip items is the gating
  factor; Phase 6 also operates on single-clip items today.

### 3.2 Within Phase 5 step 8 (EE drills)

- **`ee_connector`**: cloze-shaped item content not in
  `EEContent`. Defer to the bank-shape extension.
- **`ee_error_correction`**: needs Phase 7's per-sentence error
  annotations as input. Defer to Phase 7.

### 3.3 Within Phase 5 step 11 (persistence)

- **`sessions` / `interactions` / `study_plans` Postgres binding**:
  Alembic migrations are in place (steps 1 + 10); the actual DB
  session wiring is deferred to Phase 9 (deploy). Phase 6 should
  consume the in-process stores (`get_session`, `put_session`,
  `session_records`) — when Phase 9 swaps them for DB-backed
  implementations, Phase 6's call sites don't change.
- The **dismissal log JSONL** at `data/dismissal_log.jsonl` IS shipped
  (ADR-017). Phase 6 doesn't need to extend it.

### 3.4 Within Phase 5 step 12/14

- **axe-core + Playwright a11y suite**: requires Phase 8 frontend;
  Phase 5 ships the *contract-level* a11y assertions
  (`tests/a11y/test_drill_specs_a11y.py`). Phase 6 inherits these for
  any new drill_kind it adds.
- **WER ≤ 9% on Common Voice fr**, **PER ±0.05 on hand-aligned eval
  set**: these are model-weight-dependent gates that run only after
  `make install-models`. The test scaffolding is in place; the
  gating runs in the operator's environment, not in CI.

---

## 4. Tests Phase 6 inherits (must not regress)

A few load-bearing test files Phase 6 will encounter:

| File | What it pins |
|---|---|
| `packages/shared/tests/test_phase5_roundtrip.py` | SCHEMA_VERSION = 0.4.0, additive-only `Interaction`, downgrade safety |
| `tests/lint/test_no_raw_pron_score_outside_allowlist.py` | ADR-031 AST lint |
| `tests/property/test_pron_signal_contract.py` | Hypothesis: every signal is coarse-proxy |
| `tests/property/test_audio_not_persisted_default.py` | ADR-017: data/ delta = 0 after a default-mode session |
| `tests/capability/test_no_network_in_default.py` | Sockets blocked under default mode |
| `tests/capability/test_cloud_backend_requires_env.py` | Cloud backends refuse construction without env var |
| `tests/pedagogy/test_perfect_agent_per_drill.py` | Every implemented drill emits well-typed Interactions |
| `tests/pedagogy/test_drill_diversity.py` | ≥ 4 distinct drill types per module over 100 sessions |
| `packages/sla/tests/test_plan_shadowing_and_cadence.py` | ADR-028 cadence post-pass + ADR-030 shadowing floor |
| `apps/api/tests/test_dismissal_log_persistence.py` | Persistent JSONL + cross-process restart survival |
| `apps/api/tests/test_accessibility_routing.py` | ADR-029 routing E2E (both CO and EO) |
| `apps/worker/tests/test_score_ee.py`, `test_score_eo.py` | RubricScorer registry; Phase 6 must not shadow either |

A Phase 6 PR that breaks any of these is a regression in a Phase 5
gate, not a Phase 6 limitation.

---

## 5. Phase 5 ADRs Phase 6 inherits

| ADR | Subject | Phase 6 impact |
|---|---|---|
| 0028 | Exam-shape floor (hard + soft cadence) | Phase 6 *is* the canonical exam-shape producer; `mock_section` is in `EXAM_SHAPE_DRILL_TYPES` |
| 0029 | CO single-play + lexical alt (module=CE) | Phase 6 honors accessibility profile in mock composition |
| 0030 | Default plan shadowing floor (10 min/day) | Phase 6 doesn't crowd this out — mock-day plans still include the reservation |
| 0031 | `PronunciationSignal` structural coarse-proxy | Phase 6 EO sections reuse `build_signal()` and inherit the contract |

---

## 6. Phase 5 sign-off

- **Test suite**: 637 passed, 2 skipped (Postgres integration only).
- **Lint**: every Phase-5-touched file passes `ruff check` + `ruff format --check`.
- **Drills implemented**: 14 of 19 design-time kinds; 2 deferred to
  bank-shape work, 2 deferred to Phase 7 annotations, 1 deferred
  with the ML stack.
- **ADRs**: 0028, 0029, 0030, 0031 — all four accepted, all
  structurally enforced (runtime + static).
- **Privacy posture (ADR-017)**: enforced at four layers — schema
  (audio_path None), runtime (no audio in raw_response), filesystem
  (data/ delta = 0 in default mode), syscall (sockets blocked under
  the capability fixture).
- **Phase 6 hand-off**: this document.

Phase 5 is complete to the bounds of what's testable without model
weights + a frontend. Phase 6 starts now.
