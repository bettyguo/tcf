# Phase 6 — EVALUATE

> Acceptance check against `06_MOCK_EXAM_ENGINE.md §5`.

---

## Acceptance criteria

- ✅ **All audit metrics pass.** See `phase6_audit.md` §1–14; 14/14
  pass, 2 items rely on the in-process journal (Postgres swap
  deferred to Phase 9 — same pattern as Phase 4 + Phase 5).
- ✅ **Scripted candidate produces a valid mock report end-to-end.**
  `apps/api/tests/test_mock_exam_routes.py::test_full_canonical_mock_run_end_to_end`
  drives 39 + 39 + 3 + 3 = 84 items through the API and produces
  a populated `MockExamReport`.
- ✅ **Mock report contains all 7 sections from §2.5.**
  `packages/sla/tests/test_mock_report.py::test_markdown_contains_all_seven_sections`
  and `::test_html_contains_all_seven_sections` enumerate every
  required heading. The sample artifacts live at
  `docs/sample_mock_report.md` and `docs/sample_mock_report.html`.
- ✅ **Booking advice never escalates to "ready" without ≥ 2
  consecutive 🟢 canonical mocks.** Multiple parametrized tests:
  - `test_single_green_mock_never_recommends_booking[0]`
  - `test_single_green_mock_never_recommends_booking[1]`
  - `test_yellow_never_recommends_booking`
  - `test_red_never_recommends_booking`
  - `test_training_mode_never_recommends_booking`
  - `test_two_consecutive_canonical_greens_unlocks_booking`
- ✅ **ADRs ADR-0032 through ADR-0035 accepted.**
  - `docs/adrs/0032-canonical-vs-training-mock-modes.md`
  - `docs/adrs/0033-mock-cadence-cap.md`
  - `docs/adrs/0034-drill-mock-posterior-divergence-alert.md`
  - `docs/adrs/0035-seeded-greedy-selector-not-ortools.md`

---

## Anti-criteria

- ✅ **No way for the client to extract the correct answer before
  submitting.** The `redact_item_dump` recursive stripper removes
  every `correct_option_id` / `explanation` / `answer_key` from the
  wire payload; the scripted candidate's leak walker confirms.
  `apps/api/tests/test_mock_exam_routes.py::test_items_response_strips_correct_option_id`
  asserts this directly.
- ✅ **No mock completes without writing to the journal + outcomes.**
  The state machine routes every `start → … → SCORED` path through
  `journal()` and the answer route writes the outcome record. (The
  `mock_exams` / `interactions` Postgres tables are Phase 9 deploy;
  the in-process equivalents are the journal + outcomes dicts on
  `MockExam`.)
- ✅ **Booking-advice path that says "ready" with one 🟢 mock does
  not exist.** Asserted by the above parametrized tests.
- ✅ **A mock in canonical mode that allows pausing does not exist.**
  - No `/pause` route on `/v1/mock-exam/*` (we have one on
    `/v1/session/*` but not here).
  - The `tab-blur` route forfeits canonical past the grace window.
  - Asserted by
    `apps/api/tests/test_mock_exam_routes.py::test_tab_blur_above_grace_forfeits_canonical`.

---

## Hand-off

- ✅ **Sample mock report.** `docs/sample_mock_report.md` (Markdown)
  and `docs/sample_mock_report.html` (standalone HTML) illustrate
  each report section for a synthetic candidate (NCLC ≈ 8, EE
  bottleneck).

---

## Phase 6 deltas at a glance

| Surface                                | Status                                              |
|----------------------------------------|-----------------------------------------------------|
| `tcf_accel_sla.mock_exam.*`            | new package: spec, state, cadence, selector, scorer, report, candidate |
| `apps/api/.../routes/mock_exam.py`     | live (was Phase 2 stub)                             |
| `apps/api/.../mock_exam_pool.py`       | new — 240/240/36/36 fixture bank                    |
| `apps/api/.../mock_exam_state.py`      | new — in-process store + journal                    |
| `apps/worker/.../tasks/score_mock.py`  | new — Celery wrapper over the pure scorer           |
| ADR-0032 … ADR-0035                    | accepted                                            |
| `errors/{__init__,messages}.py`        | +5 error codes (E_MOCK_001..005) with EN+FR copy   |
| Tests added                            | 73 (across 8 files)                                 |
| OpenAPI spec                           | regenerated; contract test green                    |

Phase 7 picks up the EE/EO rubric-scorer registration (the
`register_scorer()` contract from Phase 5 is untouched); Phase 8
builds the player UI to the server invariants pinned here. Neither
blocks; both can land in parallel.
