# Changelog

All notable changes to `tcf-accel` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once `v1.0.0` is reached (Phase 9).

Until `v1.0.0`, the project is in active build per the phase plan in
`00_MASTER_PROMPT.md §4`. Each phase's `phaseN_evaluate.md` records the
phase-level changes; this file rolls them up at release boundaries.

---

## [1.0.0] — 2026-05-28

### Phase 9 — Quality Audit, Security, Performance, Content Review & Launch

This release closes the build phase. Every functional surface
(plan, drills, mock exam, scoring, insights, readiness) is
audited end-to-end; the launch is gated by a twelve-item
checklist enforced by a signed `LAUNCH_READINESS_REPORT.md`.

Added — launch-audit harness + release pipeline:

- `tests/pedagogy/launch_audit.py` — twelve launch cohorts × 100
  stochastic trajectories. Three gates per cohort: planner-
  simulator calibration (±0.5 NCLC), projection-outcome
  consistency, kind-specific assertion. Headline result:
  calibration delta ≤ 0.05 NCLC across all twelve cohorts;
  honest-refusal cohorts (B1→C2; B1→NCLC9 in 84 d; short
  runway; low budget) verified to be refused by the planner
  AND fail in simulation.
- `tests/load/k6_sustained.js` — 100 VUs × 10 min mixed workload;
  p95 < 250 ms, failrate < 0.1%.
- `tests/load/k6_burst.js` — 500 VUs hitting `POST /v1/mock_exam/start`;
  > 14500 starts, < 50 scoring failures over 30 min.
- `tests/load/k6_cold_start.js` — `docker compose up` to healthy
  in < 60 s probe.
- `scripts/release/build_release.py` — driver for wheels, multi-
  arch Docker images, Helm chart, SBOM (`syft`), SHA-256
  manifest, optional `cosign` signature.
- `scripts/release/sign_audit_report.py` — walks
  `scripts/release/launch_checklist.yaml`, emits
  `LAUNCH_READINESS_REPORT.md`, exits non-zero in `--strict`
  mode when any required gate fails.
- `scripts/release/audit_docs.py` — automated documentation
  audit (presence check + grep for unfinished-work markers).
- `scripts/release/launch_checklist.yaml` — executable form of
  the launch checklist (twelve gates).

Added — launch documentation:

- `LIMITATIONS.md` — the load-bearing honest "we don't promise
  this" page. Twelve sections; tied to code + tests + ADRs.
- `LEARNER_GUIDE.md` — 12-week journey, week-by-week, with the
  CE/EE/EO-only path documented for Deaf / HoH candidates.
- `PEDAGOGY.md` — SLA evidence dossier; the eight principles
  rolled up against the code, the tests, and the ADRs.
- `ARCHITECTURE.md` — rolled-up architecture; eight surfaces,
  ADR index, deployment posture.
- `OPERATIONS.md` — operator runbooks: stand-up, env vars, JWT
  rotation, backups, security headers, queue health, schedule-
  cache alarms, real-learner trajectory capture, cost of
  operation, incident response.
- `docs/roadmap/v1.1.md` — the pre-empted "what's missing"
  roadmap, sequenced for v1.1 (or later).

Added — ADRs (`docs/adrs/`):

- **ADR-046** Launch criteria are blocking, not advisory.
- **ADR-047** External security review for v1.0 (or two-
  maintainer sign-off as a fallback).
- **ADR-048** Public publication of κ + cohort-success
  simulation results in the README.

Added — audit dossier (`data/audit/phase9/`):

- `pedagogy_audit.json` + `pedagogy_calibration.md`
- `security_audit.md` (two-maintainer fallback per ADR-047)
- `perf_summary.md`
- `content_audit.md`
- `a11y_conformance.md` (WCAG 2.2 AA + three-maintainer think-aloud)
- `docs_audit.md`
- `risk_register_check.md` (zero Open risks)
- `fei_source_check.md` (re-verified 2026-05-28)
- `kappa_publication.md`
- `release_artefacts.md`
- `demo_observation.md` (48 h, zero P0 alerts)

Added — top-level release artefacts:

- `LAUNCH_READINESS_REPORT.md` — signed by auditor; bundle SHA-256
  `9b064a2a3f73c74278a955e937955c9d93b2e35589c95f6213c04f0228a08bb1`.

Updated:

- `README.md` — full rewrite for v1.0.0 launch. Adds the
  `## Honesty receipts` section (ADR-048): κ table from
  `data/calibration/ee.v1.report.md` and synthetic-cohort
  P(success) table from `data/audit/phase9/pedagogy_audit.json`,
  with stable marker comments for the release-time regeneration.
  Links every load-bearing doc (`LIMITATIONS.md`,
  `LEARNER_GUIDE.md`, `PEDAGOGY.md`, `ARCHITECTURE.md`,
  `OPERATIONS.md`, `LAUNCH_READINESS_REPORT.md`).
- `RISK_REGISTER.md` — Phase 9 disposition pass: twelve risks
  Mitigated, seven Accepted with explicit two-maintainer
  rationales, zero Open at v1.0.0.

Hand-off (live, not deferred):

- `OPERATIONS.md §10` — real-learner trajectory capture: the
  post-launch operational discipline begins immediately on v1.0
  deployments.
- `docs/roadmap/v1.1.md` — the v1.1 commitments (third-party
  audit, κ_gold acquisition, multi-tenant mode, native mobile,
  TEF Canada track, B2 CO genre rebalance).

Phase docs: `phase9_think.md`, `phase9_design.md`,
`phase9_audit.md`, `phase9_evaluate.md`.

The build phase closes. `10_OPERATIONS.md` (the post-launch
operator's document, not authored in this build) picks up where
this changelog stops.

---

## [Unreleased]

### Phase 8 — Frontend UX, Study Planner, Dashboards, Accessibility, ADRs 0041–0045

Added — Next.js 15 App Router application (`apps/web/`):

- Route tree per `phase8_design.md §2`: `(app)/today`, `(app)/insights`
  (overview + per-skill + errors + readiness), `(app)/library`
  (grammar, vocab, writing, speaking, culture), `(app)/settings`
  (account, privacy, accessibility, notifications, api-keys),
  `onboarding/{goals,diagnostic,plan-preview}`, `mock-exam/{start,run/[id],report/[id]}`.
- Edge middleware (`middleware.ts`) — locale negotiation + auth gate
  + maintenance switch + onboarding-completion redirect.
- Root layout + providers — TanStack Query (60 s default staleTime,
  no refetch-on-focus) + next-intl client provider with theme/font
  mirroring to `<html data-theme data-dyslexic>`.

Added — design-system components (`apps/web/components/domain/`):

- `<CredibleInterval />` — sole NCLC-render surface (ADR-025 enforcement
  point); bar / inline / tuple formats; redundant `aria-label`.
- `<SkillTrajectory />` — pure-SVG posterior history + CI shading +
  target line; sparkline mode.
- `<ReadinessWidget />` — six states (INSUFFICIENT_DATA, NOT_READY,
  BORDERLINE, READY_ONE_MOCK, READY, REGRESSED); ADR-045 enforced
  via `lib/readiness.ts`; redundant glyphs alongside colour.
- `<MockReport />` — 7-section Phase 6 report; inflation-guard banner
  (ADR-040); EE span-annotation + EO audio playback.
- `<RubricCard />` — per-task rubric dimensions with clamp visibility
  + drill-link round-trip into Phase 5.
- `<DrillPlayer />` — universal FSM (IDLE → LOADING_ITEM → PRESENTED
  → ANSWERING → SUBMITTING → REVEALED) with per-drill renderers
  under `components/drills/`; keyboard shortcuts (Space play/pause,
  Enter submit, Esc end); `AudioPlayer` honours CO single-play
  (ADR-029); `Timer` is `aria-live="polite"` announcing at
  60/30/10/5/0s only.

Added — UI primitives (shadcn convention; copied not depended-on):
`Button`, `Card`/`CardHeader`/`CardTitle`, `Badge`.

Added — state & persistence:

- `lib/state/drill-store.ts` — Zustand store + pure `transition`
  function unit-tested in `tests/unit/drill-fsm.test.ts`.
- `lib/state/ui-store.ts` — persisted to localStorage + mirrored to
  IDB; theme / textSize / font / motion / captionsDefault / locale.
- `lib/persistence/idb.ts` — `idb-keyval` wrapper: drafts (per
  promptId), mock-answer queue, prefs snapshot.

Added — API client + hooks (`lib/api/`):

- `client.ts` — cookie-based auth, 401 → `/v1/auth/refresh` →
  retry-once interceptor, JSON envelope unwrapping.
- `keys.ts` — typed query-key factory.
- `hooks.ts` — `useToday`, `useReadiness`, `useSkill`,
  `useInsightsOverview`, `useMockReport`, `useAcceptPlan`,
  `useStartMock`, `useSubmitMockAnswer`.

Added — i18n (next-intl 3):

- Full EN + FR catalogs (`messages/{en,fr}.json`).
- ES + AR + ZH stubs (RTL wired for AR via `<html dir>`).
- `lib/i18n/{config,request}.ts` — cookie-based locale, English
  fallback for missing keys, `stubLocales` set drives
  `<StubLocaleBanner />`.
- `tests/unit/i18n-messages.test.ts` — FR catalog has every EN leaf
  key + ADR-043 banned-urgency-wording lint.

Added — tooling:

- Tailwind 4 config + design tokens in `globals.css`
  (light / dark / hc themes via `data-theme`; OpenDyslexic font
  via `data-dyslexic`).
- Storybook 8 (`@storybook/nextjs` + `addon-a11y`) — stories for
  CredibleInterval, SkillTrajectory, ReadinessWidget (every state).
- Playwright (`playwright.config.ts`) — Pixel 5 / iPhone 13 /
  iPad Mini / Desktop 1280 projects.
- E2E suites: `onboarding.spec.ts`, `drill.spec.ts`,
  `mock-exam.spec.ts` — each invokes `@axe-core/playwright`.
- Lighthouse CI (`lighthouserc.json`) — Slow 4G + Moto G4 profile;
  LCP ≤ 2.5 s, TBT ≤ 300 ms, CLS ≤ 0.05; perf/a11y/best/seo ≥ 90.
- `pa11y-ci` (`.pa11yci`) over 11 built routes against WCAG 2.2 AA.
- Custom ESLint rule `eslint/no-bare-nclc.js` enforcing ADR-025
  (NCLC values only via `<CredibleInterval />`).

Added — unit tests (Vitest + jsdom):

- `readiness.test.ts` — truth table covering INSUFFICIENT_DATA,
  NOT_READY, BORDERLINE, READY_ONE_MOCK (ADR-045 amber floor),
  READY (2 greens + p ≥ 0.85), REGRESSED, bottleneck selection.
- `drill-fsm.test.ts` — every legal transition + illegal-transition
  rejection.
- `format.test.ts` — `formatNclcMean`, `formatCi`, `formatNclcWithCi`,
  `formatProbability`, `formatMinutes`.

Added — ADRs (`docs/adrs/`):

- **ADR-0041** Next.js 15 App Router: RSC for static, CSC for
  interactive, edge middleware for locale + auth.
- **ADR-0042** No gamification — no streak flames, no leaderboards,
  no DAU-chasing UI patterns; copy lint enforces banned wording.
- **ADR-0043** Notifications opt-in, zero defaults; copy reviewed
  against the calm-principle lint rule.
- **ADR-0044** WCAG 2.2 AA across the app as a launch gate.
- **ADR-0045** Readiness widget never shows 🟢 without ≥ 2
  consecutive canonical-mode mocks at 🟢 AND `P(min ≥ target) ≥ 0.85`.

Phase docs: `phase8_think.md`, `phase8_design.md`, `phase8_audit.md`,
`phase8_evaluate.md`.

Hand-off to Phase 9: live API integration replacing the four screen-
level fixtures, staging deploy + Lighthouse CI against the staging
URL, three-maintainer think-aloud, the demo video, WCAG 2.2 AA
conformance statement bundled with the κ publication.

---

### Phase 7 — Auto-Scoring & Feedback: hybrid features + LLM + calibration, ADRs 0036–0040

Added — scoring pipeline (`packages/ml/src/tcf_accel_ml/scoring/`):

- `rubric_table.py` — published total_20 ↔ NCLC band lookup (ADR-036).
- `features/` — pure-Python feature extractors: `WritingFeatures`
  (MATTR-25, discourse-marker diversity, register, Canadian-lexicon
  density, conditional/subjunctive/passive counts, error density),
  `SpeakingFeatures` (writing + WPM, pause/filler rates, prosody,
  PER, self-corrections), heuristic regex error detector (frequent
  L2-French patterns: `si j'aurais`, wrong auxiliary, gender errors,
  anglicisms), connector registry (6 categories), familier↔soutenu
  register scorer.
- `llm/` — `LLMCritic` protocol, structured-prompt builders with
  refuse-to-inflate instruction + NCLC anchors (ADR-039),
  deterministic `LLMCriticStub` (CI / offline).
- `calibrate/` — `Ridge` (pure-Python Gaussian elimination),
  `RubricCalibrator` (per-dimension Ridge over features + LLM →
  expert; JSON-on-disk; training-set hash), `quadratic_weighted_kappa`,
  `mae`, `pearson_r`.
- `inflation_guard.py` — ADR-040 clamp: LLM > feature_floor + 3 ⇒
  clamp to floor + 2 and set `needs_human_review`.
- `feedback.py` — `FeedbackBlock` render (strengths / fixes /
  context / disclaimer); learner-text quotes carried in
  `learner_quote` field, never inlined into `detail` (ADR-040
  anti-criterion).
- `ee/score.py` — `EEScorer` orchestrator + `EEWorkerScorer` adapter.
- `eo/score.py` — `EOScorer` + pronunciation-signal glue + worker
  adapter (consumes Phase 5 `PronunciationSignal`).

Added — worker wiring:

- `apps/worker/src/tcf_accel_worker/tasks/__init__.py` —
  `_install_phase7_scorers()` registers `EEWorkerScorer` /
  `EOWorkerScorer` for `ee.v1` / `eo.v1` at import time; best-effort
  (Phase 5 stub remains when the ML package is absent).

Added — API surface (`apps/api/src/tcf_accel_api/`):

- `routes/submission.py` — Phase 7 implementations of
  `POST /v1/submission/ee` (multipart text), `POST /v1/submission/eo`
  (multipart audio), `GET /v1/submission/{id}` (poll); replaces the
  Phase 2 501-stubs.
- `submission_state.py` — in-process submission store
  (`create_submission` / `get_submission` / `update_submission`);
  Postgres + S3 swap-in deferred.

Added — scripts:

- `scripts/calibrate.py` — train a `RubricCalibrator` from a JSONL
  of rated submissions; emits the calibrator JSON + a markdown
  report.
- `scripts/eval_kappa.py` — release-time κ evaluator; exits non-zero
  when overall κ < 0.55 unless `--allow-experimental` is set
  (ADR-038).

Added — calibration data:

- `data/calibration/ee.v1.synthetic_silver.jsonl` — 12-row silver
  anchor (gold expert set pending acquisition per ADR-037).
- `data/calibration/ee.v1.json` — trained calibrator (silver).
- `data/calibration/ee.v1.report.md` — per-dimension fit report.

Added — tests (~80 new test cases across 6 ml/scoring test files +
the API submission route file):

- `packages/ml/tests/test_scoring_features.py`,
  `test_scoring_calibrate.py`, `test_scoring_inflation_guard.py`,
  `test_scoring_rubric_table.py`, `test_scoring_llm_stub.py`,
  `test_scoring_ee_eo.py`.
- `apps/api/tests/test_submission_routes.py` — multipart upload +
  graded round-trip.

Updated:

- `apps/worker/tests/test_score_ee.py` / `test_score_eo.py` —
  unregister Phase 7 scorers in the autouse fixture so the Phase 5
  stub tests remain stub-specific.
- `tests/capability/test_no_network_in_default.py` — accept both
  `phase7_status` values (`"stub"` or `"graded"`) since Phase 7's
  default LLM critic is the offline stub.
- `apps/api/tests/test_v1_stubs.py` — remove the `/v1/submission/{id}`
  501 entry (now real).
- `docs/api/openapi.v1.yaml` — regenerated to reflect the new
  submission handlers.

ADRs added:

- ADR-036 hybrid features + LLM + calibration architecture.
- ADR-037 expert-labelled set ≥ 200/skill is launch-blocking for
  "claimed κ" reporting.
- ADR-038 publish κ with every release; experimental badge below
  κ 0.55.
- ADR-039 LLM critic uses temperature ≤ 0.2 + structured-output
  enforcement.
- ADR-040 inflation guard clamps LLM scores against the feature
  floor.

Phase docs: `phase7_think.md`, `phase7_design.md`, `phase7_audit.md`,
`phase7_evaluate.md`.

Test suite: **779 passing, 0 failures**.

---

### Phase 6 — Mock Exam Engine: full 2h47 simulator, ADRs 0032–0035

Added — mock-exam engine (`packages/sla/src/tcf_accel_sla/mock_exam/`):

- `spec.py` — `EXAM_SHAPE = {CO: 39, CE: 39, EE: 3, EO: 3}`, `MODULE_DURATION_S` (35/60/60/12 min), `BREAK_DURATION_S` (5/5/15 min), `ACTIVE_DURATION_S = 10020 s = 2h47`, `FEI_SPREAD` (A1..C2), `CANONICAL_TAB_BLUR_GRACE_S = 5`.
- `state.py` — `MockState` enum + `transition()` pure state machine; SCHEDULED → CO_ACTIVE → … → SCORED, with FORFEITED branch (canonical only); `MockJournalEntry` audit record.
- `cadence.py` — ADR-0033 cap: 1/w (weeks 0..5), 2/w (6..9), 3/w (10+); training cap 1/day; `can_start_canonical/training`, `mocks_allowed_per_iso_week`, `week_index_since`.
- `selector.py` — ADR-0035 constraint-guided greedy with seeded RNG (rejection of OR-Tools); enforces FEI difficulty spread, ≥ 20% never-seen, task-number split for EE/EO, topic-cluster cap (0.08 per module), 30-day recency exclusion; sorts ascending by difficulty.
- `scorer.py` — fresh per-skill posterior per ADR-0034 (mock independent of drill); CO/CE via `update_with_mcq`, EE/EO via `update_with_rubric`; composite NCLC = floor(min) suppressed when any skill not confident; `divergence_alert` at |Δ| ≥ 2.0 NCLC.
- `report.py` — `MockExamReportFull` + `render_markdown` / `render_html`; seven sections (Headline / Module breakdown / EE / EO / Trajectory / Actionable plan / Booking advice); `booking_advice` never recommends without ≥ 2 consecutive canonical greens.
- `candidate.py` — `CandidateRunner` + `CandidateProfile` scripted candidate driving the full state machine; default profile times match the 2:47 active wall-clock (±1 s).

Added — API routes (`apps/api/src/tcf_accel_api/routes/mock_exam.py`):

- `POST /v1/mock-exam/start` (cadence-gated; `force=true` override logged) — replaces Phase 2 stub.
- `GET /v1/mock-exam/{id}/state` — never reveals answers.
- `POST /v1/mock-exam/{id}/advance` — state-machine driver (additive).
- `GET /v1/mock-exam/{id}/items/{module}` — items with `correct_option_id` / `explanation` recursively stripped (additive).
- `POST /v1/mock-exam/{id}/answer` — MCQ correctness derived server-side; rubric outcomes recorded as-is (additive).
- `POST /v1/mock-exam/{id}/co-play` — CO single-play enforcement (additive).
- `POST /v1/mock-exam/{id}/tab-blur` — canonical forfeit past 5 s grace (additive).
- `POST /v1/mock-exam/{id}/submit` — finalize + score inline (Celery wrapper deferred to Phase 9 production deploy).
- `GET /v1/mock-exam/{id}/report` — scored report with bottleneck identification.

Added — API plumbing:

- `apps/api/src/tcf_accel_api/mock_exam_pool.py` — deterministic 240 CO + 240 CE + 36 EE + 36 EO synthetic bank; `redact_item_dump` recursive answer-key stripper.
- `apps/api/src/tcf_accel_api/mock_exam_state.py` — in-process `MockExam` store + journal; `MockExamSummary` projection for cadence reasoning; canonical-streak-green bookkeeping on `UserState`.

Added — worker (`apps/worker/src/tcf_accel_worker/tasks/score_mock.py`):

- `tcf_accel.score_mock` Celery task — JSON-safe wrapper over the pure scorer; deterministic; idempotent.

Added — error taxonomy:

- `E_MOCK_001` `MockCadenceExceededError` (409), `E_MOCK_002` `MockForfeitedError` (409), `E_MOCK_003` `MockNotScoredError` (404), `E_MOCK_004` `MockInvalidTransitionError` (409), `E_MOCK_005` `MockCoSinglePlayViolation` (409), each with EN+FR copy.

Added — schemas (additive per ADR-016):

- `MockExamStart`, `MockExamAnswer`, `MockExamCoPlay`, `MockExamTabBlur` request bodies in `schemas/api/mock_exam.py`.

Added — ADRs:

- ADR-0032 — Canonical and training mock modes; canonical forfeits on abnormal exit; only canonical updates the readiness streak.
- ADR-0033 — Mock cadence cap 1/w → 2/w → 3/w ladder.
- ADR-0034 — Drill and mock posteriors tracked separately; alert at |Δ| ≥ 2 NCLC.
- ADR-0035 — Selector implementation is constraint-guided seeded greedy, *not* OR-Tools MIP (rejection rationale: deps weight, determinism risk, problem size, auditability).

Tests — added 73 across 8 files:

- `packages/sla/tests/test_mock_spec.py` (7), `test_mock_state.py` (14), `test_mock_cadence.py` (8), `test_mock_selector.py` (10), `test_mock_scorer.py` (9), `test_mock_report.py` (11).
- `apps/api/tests/test_mock_exam_routes.py` (11) — end-to-end via the scripted candidate, plus the no-leak, forfeit, cadence, and CO-single-play invariants.
- `apps/worker/tests/test_score_mock.py` (3) — eager-mode determinism + divergence alert.

Changed:

- `apps/api/src/tcf_accel_api/main.py::PHASE` bumped 2 → 6.
- `apps/api/tests/test_v1_stubs.py` — four `mock-exam/*` routes removed from the 501 expectations.
- `docs/api/openapi.v1.yaml` regenerated.

Hand-off:

- `docs/sample_mock_report.md` + `docs/sample_mock_report.html` — illustrative artifacts for the operator + Phase 8 UI.

Phase docs:

- `phase6_think.md`, `phase6_design.md`, `phase6_audit.md`, `phase6_evaluate.md`.

### Phase 5 — Practice & Drill Engines: 14 drills, pronunciation pipeline, ADRs 0028–0031

`SCHEMA_VERSION` bumped to `0.4.0` (purely additive — Phase 4 consumers parse Phase 5 rows by ignoring the new optional fields).

Added — schemas (`packages/shared/src/tcf_accel/schemas/`):

- `pronunciation.py` — `PronunciationSignal` (frozen, ADR-031 coarse-proxy contract with required `signal_kind="coarse_proxy"`, `disclaimer_version`, `display_label`) + `PronunciationProsody`.
- `Interaction` extended (additive): `drill_kind: DrillKind | None`, `pronunciation: PronunciationSignal | None`, `audio_path: str | None`.
- `DrillKind` literal (24 values); `DrillType` literal extended from 9 to 26 values (legacy names retained).
- `AccessibilityProfile` (CO/EE/EO alternatives) + `DismissalLogEntry`.
- Error codes: `E_SESSION_001..004`, `E_ASR_001`, `E_PRON_001`, `E_TTS_001`, `E_LLM_001`.

Added — drill engines (`packages/sla/src/tcf_accel_sla/drills/`):

- 14 drill implementations across all five modules. **CO**: `co_mcq` (single-play core), `co_dictation` (WER), `co_gapfill` (deterministic-cloze), `co_lexical_alt` (accessibility, `module="CE"`); **CE**: `ce_mcq`; **EE**: `ee_task`, `ee_rewrite`, `ee_register_adjust` (rubric-pending); **EO**: `eo_task`, `eo_picture`, `eo_spontaneous`, `eo_roleplay`, `eo_repair` (round-robin sub-criterion stub), `eo_text_alt` (accessibility, `module="EE"`).
- `base.py` — `DrillSpec`/`DrillStep`/`DrillResult`/`Drill` + `Drill.to_interaction` as the single funnel into `interactions` (writes `drill.spec.module`, not item's module — load-bearing for ADR-029).
- `_text.py`, `_ee_common.py` (FEI 80–110% band, −1 per 5%, cap −4), `_eo_common.py` (audio → PronunciationSignal), `_eo_followup.py` (12 per task, ≥ 8 audit floor).
- `registry.py` — singleton registry; `resolve_drill_kind(module, drill_type)`.

Added — audio + ML stack (`packages/ml/src/tcf_accel_ml/`):

- `asr/whisper_fr.py` — `LocalWhisperBackend` (lazy `faster-whisper`), `CloudLiteLLMASRBackend` (refuses construction unless `TCF_ACCEL_ASR_BACKEND=cloud:litellm`), `StubASRBackend`.
- `alignment/mfa.py` — `LocalMFAAligner` + `StubMFAAligner`.
- `prosody/{pause,pitch,analyze}.py` — pauses from alignments (200 ms threshold), pitch via lazy librosa (returns `0.0` if absent — "honest zero"), `PronunciationProsody` composition.
- `pronunciation/{per,insufficient_data,signal}.py` — Levenshtein PER, the gate (`< 2 s` ∨ `asr_conf < 0.50` ∨ `n_phon < 8` → `"insufficient_data"`), `build_signal` factory (the sanctioned construction site).
- `tts/xtts.py` — `LocalXTTSBackend` + `StubTTSBackend`. No cloud TTS opt-in in Phase 5.
- Env-var dispatch on `TCF_ACCEL_{ASR,MFA,TTS}_BACKEND`.
- `packages/sla/src/tcf_accel_sla/audio/pipeline.py::run_audio_pipeline` — lazy-imports `tcf_accel_ml`, composes the full pipeline end-to-end.

Added — session lifecycle + persistent dismissal log:

- `packages/sla/src/tcf_accel_sla/session/exam_shape_floor.py` — `floor_satisfied`, `rolling_7d_exam_shape_minutes`, `iso_week`. Effective floor clamped at `EXAM_SHAPE_FLOOR_LOWER = 20`.
- `apps/api/src/tcf_accel_api/session_state.py` — in-process `SessionStore` + **persistent dismissal log at `data/dismissal_log.jsonl`** (rehydrates across process restart; `TCF_ACCEL_DATA_DIR` overridable for tests).
- `apps/api/src/tcf_accel_api/routes/session.py` — implemented: `start` (with 409 floor gate), `next`, `answer` (registry dispatch, idempotent), `finish`, `pause`, `resume` (24h → 410), `exam-shape/dismiss`.
- `apps/api/src/tcf_accel_api/routes/me.py` — added `GET/PATCH /v1/me/accessibility`.
- `apps/api/src/tcf_accel_api/session_pool.py` — synthetic items CO/CE/EE/EO.

Added — worker tasks (`apps/worker/src/tcf_accel_worker/tasks/`):

- `score_ee.py` — Celery task + `RubricScorer` protocol + module-level scorer registry. Phase 5 stub computes word count, TTR, discourse-marker density. Phase 7 plugs in real scorer via `register_scorer("ee.v1", real)` without touching this module.
- `score_eo.py` — same pattern, independent registry; stub computes duration deviation + surfaces pronunciation `display_label`.

Added — planner integration (ADR-028, ADR-030):

- `generate_plan._reserve_shadowing` — 10 min/day reserved before the bottleneck allocator (ADR-030; clamped at 3-min floor).
- `generate_plan._enforce_exam_shape_cadence` — post-pass promotes first non-shadowing block when 7-day exam-shape minutes < floor.
- `select_drill_type` rotates across 4–5 distinct drill types per module so the drill-diversity audit clears.

Added — Alembic migrations:

- `0003_phase5_sessions_alter.py` — `paused_at` / `items_seen` / `items_correct` / `exam_shape` + rolling-window index.
- `0004_phase5_interactions_alter.py` — `drill_kind` / `pronunciation_signal` (JSONB) / `audio_path` + DB CHECK constraints (`drill_kind` enum, `co_lexical_alt → module='CE'`).

Added — ADRs (`docs/adrs/`):

- **ADR-0028**: Exam-shape floor — hard floor + soft cadence.
- **ADR-0029**: CO single-play default; lexical alternative emits `module=CE`.
- **ADR-0030**: Mandatory 10-min/day shadowing reservation in default plans.
- **ADR-0031**: `PronunciationSignal` is a structural coarse-proxy contract.

Added — tests (290+ new across the suite):

- Round-trip + downgrade safety (`packages/shared/tests/test_phase5_roundtrip.py`).
- Per-drill unit + perfect-agent + diversity (under `packages/sla/tests/drills/`, `tests/pedagogy/`).
- Planner ADR-028/ADR-030 (`packages/sla/tests/test_plan_shadowing_and_cadence.py`).
- ML stubs + pronunciation pipeline (`packages/ml/tests/`).
- Worker registries (`apps/worker/tests/test_score_{ee,eo}.py`).
- ADR-031 AST lint (`tests/lint/test_no_raw_pron_score_outside_allowlist.py`).
- Hypothesis contract (`tests/property/test_pron_signal_contract.py`) + ADR-017 filesystem (`test_audio_not_persisted_default.py`).
- **Capability tests** at the syscall layer (`tests/capability/`) — `block_network()` context manager catches `socket.connect`/`connect_ex`/`create_connection`/`getaddrinfo`.
- Exam-pace timer (`tests/perf/test_co_timer.py`), drill-spec a11y contract (`tests/a11y/test_drill_specs_a11y.py`).
- Persistent dismissal log E2E (`apps/api/tests/test_dismissal_log_persistence.py`).

Test totals at Phase 5 sign-off: **637 passed, 2 skipped** (Postgres integration only). Lint: clean across every Phase-5-touched file.

Deferred to later phases (documented in `phase5_evaluate.md` + `phase5_handoff.md`):

- `co_shadowing` / `co_accent` (bank-shape dependencies).
- `ee_connector` / `ee_error_correction` (cloze content / Phase 7 annotations).
- Postgres binding for `sessions` / `interactions` / `study_plans` (Phase 9 deploy — dismissal-log JSONL **is** shipped).
- axe-core + Playwright keyboard-walkthrough (Phase 8 frontend).
- WER ≤ 9% / PER ±0.05 quality gates (operator-side via `make install-models`).

### Phase 4 — Learner Model: FSRS + LECTOR, Bayesian NCLC estimator, CAT diagnostic, planner, readiness

Added:

- `packages/sla/src/tcf_accel_sla/` — full Phase 4 SLA surface, pure-stdlib (zero runtime deps):
  - `scheduler/fsrs.py` — FSRS-6 wrapper (`FSRSScheduler`, `Card`, `Rating`, `ReviewLog`) with the 21-parameter default weight vector inline; per-user `optimize` is a no-op in v1 per ADR-023.
  - `scheduler/lector.py` — `adjust_due_with_lector` with quadratic similarity penalty above 0.75, hard-capped at 2 days; idempotent.
  - `estimator/nclc.py` — `SkillPosterior` (mean, variance, n_obs, difficulty-band spread); `update_with_mcq` (Laplace approximation on 2PL IRT log-posterior, Newton-Raphson root); `update_with_rubric` (closed-form Gaussian); `to_nclc_estimate` projection.
  - `diagnostic/cat.py` — `DiagnosticSession` + `select_next_item` (Fisher-info max with same-difficulty-run cap).
  - `planner/allocator.py` — `allocate(total_minutes, posteriors, target)` with β-weighted gap-squared formula (β_EE=1.4, β_EO=1.5) and per-skill floor of 10 minutes.
  - `planner/generate_plan.py` — 12-week (or custom horizon) rolling daily blocks with rationale + conservative `simulate_learning` projection.
  - `planner/readiness.py` — `compute_readiness` with the ADR-025 launch-blocking "no green without confidence" gate; canonical-mock streak gate.
- `apps/api/src/tcf_accel_api/state.py` — in-process per-user state (`UserState`, `DiagnosticUmbrella`); Phase 5 swaps for Postgres/Redis.
- `apps/api/src/tcf_accel_api/diagnostic_pool.py` — synthetic deterministic CAT pool (36 items per skill across NCLC bands 3..11); Phase 5 swap to the real content bank.
- Wired Phase 4 routes: `/v1/plan`, `/v1/plan/regenerate`, `/v1/plan/today`, `/v1/diagnostic/start`, `/v1/diagnostic/{id}/answer`, `/v1/diagnostic/{id}/finish`, `/v1/insights/readiness`. The remaining `/v1/insights/*` routes stay Phase 8 stubs.
- 5 ADRs (`docs/adrs/0023..0027`): FSRS-6 default weights w/ deferred per-user optimization, LECTOR penalty bounded by FSRS, posterior CI mandatory + confidence flag launch-blocking, diagnostic = CAT for CO/CE & rubric for EE/EO, allocator over-weights production skills.
- 12 archetypal synthetic cohorts at `tests/pedagogy/synthetic_cohorts.py` + behavioral audit `test_synthetic_cohorts.py` (allocator floors, production-skill share, plan realism).
- Hypothesis-driven property tests at `tests/property/`: FSRS invariants, estimator CI coverage on 200 synthetic learners, readiness no-green-when-unconfident launch-blocker.
- Integration tests at `apps/api/tests/test_{plan,diagnostic,readiness}_routes.py` exercising the API contract end-to-end.
- Whitelisted mathematical/Greek confusables in `[tool.ruff.lint]` (`σ μ α β θ Φ ε × –`) — required for legible stats docstrings; no per-line `noqa`.
- `phase4_{think,design,audit,evaluate}.md` — phase-cycle artifacts; the audit table maps each spec §4 metric to its test (or to a deferred conformance check with the deferral named in ADR-023).

Updated:

- `apps/api/pyproject.toml`: added `tcf-accel-sla` dependency (workspace member).
- `apps/api/tests/test_v1_stubs.py`: dropped `/v1/plan/*`, `/v1/diagnostic/*`, `/v1/insights/readiness` from the 501-stub table; these routes now return real handlers.
- `apps/api/src/tcf_accel_api/main.py`: doctest example updated to reflect the new live routes.
- `docs/api/openapi.v1.yaml`: regenerated to capture the new request/response shapes (no breaking changes to the existing surface).

Deferred (named in ADR-023 + `phase4_audit.md`):

- FSRS-6 bit-identical conformance vs the reference `fsrs` package (10,000-sequence audit) — replaced by FSRS-shape invariants.
- Per-user FSRS optimization at ≥ 100 reviews — `FSRSScheduler.optimize` returns defaults until vendoring lands.
- Nightly IRT refit for `items.difficulty_irt` / `discrimination_irt` — Phase 5 worker.
- Plan persistence — currently in-process; Phase 5 Postgres.
- Confusable-pairs Postgres lookup feeding LECTOR — Phase 5 SQL.

### Phase 3 — Content Pipeline (foundation; in progress)

Added:

- `phase3_think.md` — three load-bearing decisions (hybrid authoring shape, CEFR-placement trust, repo/operator license boundary) with "what would change our mind" triggers per decision.
- `phase3_design.md` — full pipeline DAG, per-module synthesizer shapes, CEFR fine-tune + calibration recipe, 13-check quality gate, embedder/clusterer, manual-review UI, two-mode `seed_bank.py`, error taxonomy additions, ADR roadmap, 17-step CODE checklist.
- 5 ADRs (`docs/adrs/0018..0022`): hybrid scraped-passage + LLM-question authoring, adversarial-distractor threshold = 0.25 / 20 trials, no FEI test material in repo, synthetic-item cap = 40% per module, quota matrix as a hard release gate.
- `SCHEMA_VERSION` bumped `0.2.0` → `0.3.0` (strictly additive: 2 new `QualityFlag` values, documented `ItemMetadata` Phase 3 surfaces, 6 new error subclasses, new `confusable_pairs` table).
- New `QualityFlag` values: `CEFR_HUMAN_OVERRIDDEN`, `TOPIC_OVER_CAPPED` (existing values unchanged).
- Documented `ItemMetadata` optional fields used by the pipeline: `cefr_confidence`, `cefr_distribution`, `canadian_context`, `co_acoustic`, `calibration_anchors`, `synthesis_trace_uri`. Model remains `extra="allow"` so Phase 2 round-trip tests stay green.
- 6 new error subclasses under `E_CONTENT_*`: `IngestSourceUnavailableError` (503), `ContentLLMUnreliableError` (502), `CEFRClassifierUnavailableError` (503), `BankDistributionViolation` (422), `IngestLicenseMissingError` (422), `IngestLicenseIncompatibleError` (422); each with EN + FR message templates.
- Alembic migration `0002_confusable_pairs.py` — new `confusable_pairs` table with canonical-ordering CHECK and unique pair constraint; Phase 4 will consume it for LECTOR semantic scheduling.
- `packages/content` subpackage scaffolding: `sources/`, `cefr/`, `synthesize/`, `quality/`, `embedding/`, each with the protocol(s) and tunable thresholds the Phase 3 implementation will plug into. `types.py` carries the pipeline-internal `RawAsset`, `CandidateItem`, `SynthesisTrace`, `QualityReport` shapes.
- `REDISTRIBUTABLE_LICENSE_ALLOWLIST` (SPDX) + `license_compatible()` predicate, enforcing ADR-0010 at the source-module boundary.

Not yet landed (deferred to follow-up Phase 3 work):

- Concrete source modules (Common Voice, MLS, Voxpopuli, Wikisource, Gutenberg) and operator-tier ingest scripts (RFI, ICI Première, TV5MONDE).
- Whisper + MFA wiring in `synthesize/co.py`; CamemBERT fine-tune artifact in `cefr/`; LLM synthesizers for CE/EE/EO; the quality-gate checks (adversarial, length-balance, dup, PII, license); embedder + HDBSCAN; bank loader.
- Celery task graph in `apps/worker/.../tasks/`; `scripts/seed_bank.py`; `apps/review/` Streamlit UI.
- `make audit-content` target and its tests.
- `phase3_audit.md`, `phase3_evaluate.md`, `BANK_STATS.md`.

### Phase 2 — System Architecture, Data Model & API Contracts

Added:

- `phase2_think.md`, `phase2_design.md`, `phase2_audit.md`, `phase2_evaluate.md`.
- 7 ADRs (`docs/adrs/0011..0017`): JSONB item content, pre-computed schedule cache, online Bayesian per-skill + nightly IRT, error-code stability, pgvector → Qdrant swap criteria, URL `/v1/` versioning, privacy default `local_only`.
- `SCHEMA_VERSION` bumped `0.1.0` → `0.2.0` (additive: `ItemContent` narrowed to a discriminated union; new rubric + API schemas).
- Pydantic content variants under `tcf_accel.schemas.content.*`: `COContent`, `CEContent`, `EEContent`, `EOContent`, with supporting `Speaker`, `MCQ`, `MCQOption`, `ErrorAnnotation`, `ErrorType`.
- `WritingRubric` and `SpeakingRubric` with `total_20` component-sum invariant (±1).
- API request/response models under `tcf_accel.schemas.api.*` covering auth, profile, diagnostic, plan, session, submission, mock-exam, insights, plus the `ErrorEnvelope` wire shape.
- `Interaction` schema — the public projection of the `interactions` table row.
- Error taxonomy expanded from 8 → 19 stable codes across 7 domains; EN + FR message catalog at `tcf_accel.errors.messages`; `to_envelope()` serializer returning the documented `ErrorEnvelope` shape.
- Alembic configuration (`alembic.ini`, `infra/migrations/env.py`, `script.py.mako`) and migration `0001_initial.py` shipping 9 tables, all required indexes (including HNSW + GIN), and a complete `downgrade()` path.
- 27 `/v1/` FastAPI route stubs (auth, me, diagnostic, plan, session, submission, mock-exam, insights, data, health) — each returns the canonical `501 E_NOT_IMPLEMENTED_001` envelope with the owning phase number.
- `docs/api/openapi.v1.yaml` — frozen OpenAPI 3.1 spec (2802 lines), drift-checked in CI.
- `tcf_accel_api.scripts.export_openapi` CLI with `--output` and `--check` modes.
- `packages/client-py` (Python SDK; handwritten Phase 2 wrapper around `httpx`) and `packages/client-ts` (TS SDK; handwritten Phase 2 wrapper around `fetch`).
- `tests/pedagogy/golden_learner.jsonl` — a deterministic 200-interaction synthetic learner trajectory, regenerable via `scripts/generate_golden_learner.py`.
- New tests: `tests/contract/test_openapi_v1.py`, `tests/integration/test_alembic_round_trip.py`, `tests/pedagogy/test_golden_learner.py`, `apps/api/tests/test_v1_stubs.py`, plus expanded `packages/shared/tests/test_*.py` covering the discriminated union and the EN+FR error catalog.
- `Makefile` Phase 2 targets: `phase2-verify`, `phase2-verify-full`, `openapi-export`, `openapi-check`, `migrate-up`, `migrate-down`, `clients-generate`, `golden-learner-regenerate`.
- Risks R-011 (schedule-cache invalidation), R-012 (IRT-refit cost at scale), R-013 (OpenAPI spec determinism) added to `RISK_REGISTER.md`.

Changed:

- `Item.content` field narrowed from a permissive placeholder to the discriminated union (`COContent | CEContent | EEContent | EOContent`). The Phase 1 minimal placeholder `ItemContent(module="X")` no longer validates; full per-module content is now required.
- `tcf_accel.errors` restructured from a single file into a subpackage (`errors/__init__.py` + `errors/messages.py`). Public API unchanged for existing classes (`TCFAccelError`, `ContentNotAvailableError`, `SchedulerError`, `ScoringError`, `ASRConfidenceTooLowError`, `TextTooShortError`, `CalibrationError`, `InsufficientObservationsError` — all re-exported).
- `tcf_accel.errors.TCFAccelError` now exposes `to_envelope(locale=..., phase=...)` returning the `ErrorEnvelope` wire shape; `to_dict()` retained for structured logs.
- `apps/api`: `/healthz` now reports `phase=2`; the API title and description updated. Removed `ORJSONResponse` (FastAPI now serializes directly).
- `pnpm-workspace.yaml` enables `packages/client-ts`; root `pyproject.toml` enables `packages/client-py` as a uv workspace member.
- Root `pyproject.toml` dev group adds `alembic`, `sqlalchemy>=2`, `asyncpg`, `psycopg[binary]`, `schemathesis`, `pyyaml`. `filterwarnings` extended for pydantic field-name and third-party deprecation noise. `addopts` adds `--import-mode=importlib` so per-package `tests/` directories no longer collide.

Refused (per master prompt §11; logged in `RATIONALE.md`):

- *(no new refusals in Phase 2; the prior Phase 1 refusals remain in force.)*

### Phase 1 — Repository Bootstrap, Tooling, Contracts

Added:

- Monorepo layout (`apps/`, `packages/`, `infra/`, `docs/`, `tests/`, `scripts/`).
- Workspace configuration: `pyproject.toml` (uv workspace), `pnpm-workspace.yaml`.
- Canonical dev loop in `Makefile` (`setup`, `verify`, `audit-security`, `audit-deps`, etc.).
- `.pre-commit-config.yaml` with `ruff`, `mypy`, `gitleaks`, and custom data-commit + TODO-docstring hooks.
- `.gitignore`, `.gitattributes` (LF normalization), `.editorconfig`, `.env.example`.
- GitHub Actions workflows: `ci.yml` (lint + typecheck + test on Linux + macOS), `audit.yml` (weekly), `release.yml` (tag-triggered stub).
- Hello-world stubs: `apps/api` (FastAPI `/healthz`), `apps/web` (Next.js 15 page), `apps/worker` (Celery smoke task).
- Frozen Phase 1 contracts in `packages/shared/src/tcf_accel/schemas/`: `Item`, `ItemContent` (placeholder; Phase 2 narrows), `Provenance`, `QualityFlag`, `ItemMetadata`, `Score`, `NCLCEstimate`, error taxonomy base.
- Package stubs: `packages/sla`, `packages/ml`, `packages/content` (each with `pyproject.toml` + `__init__.py`).
- Infrastructure: `infra/docker-compose.yml` (Postgres 16 + pgvector, Redis 7, Qdrant 1.10), `infra/docker-compose.gpu.yml` (GPU override stub).
- Helper scripts: `scripts/license_check.py`, `scripts/abandoned_check.py`, `scripts/download_models.py` (stub).
- Governance docs: `LICENSE` (MIT), `CONTENT_LICENSE` (CC BY-SA 4.0), `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `RATIONALE.md`, `RISK_REGISTER.md`, `README.md`.
- 10 ADRs (`docs/adrs/0001..0010`) covering: monorepo with uv + pnpm, pgvector-first, FastAPI, Next.js 15 App Router, Celery + Redis, FSRS-6, `bofenghuang/whisper-large-v3-french`, CamemBERT CEFR classifier, litellm with `claude-sonnet-4-6` default, MIT + CC BY-SA dual licensing.
- Phase 1 artifacts: `phase1_think.md`, `phase1_design.md`, `phase1_audit.md`, `phase1_evaluate.md`.

Refused (per master prompt §11; logged in `RATIONALE.md`):

- C2 in 12 weeks from B1 (target re-set to NCLC 7–9; C2 offered as stretch).
- "Pass guaranteed" copy.
- Cloud telemetry of learner audio by default (default is `local_only`).
- Bundling FEI copyrighted test material (links only).
- Features contradicting the bottleneck heuristic.
- NCLC point estimates without credible intervals.
- Unbounded synthetic-item share (capped at 40%/module).
