# RISK REGISTER

> The living register of known risks to `tcf-accel`. Created in Phase 1 per master prompt; updated by every phase's `phaseN_evaluate.md`.

Each entry is owned by a role (Lead / ML / Backend / Frontend / Content / DevOps / Product) and has a disposition: **Open** (active mitigation in progress), **Mitigated** (residual risk acceptably low), **Accepted** (residual risk acknowledged, no further work), **Retired** (no longer applicable).

Likelihood: L (low) / M (medium) / H (high) / Certain.
Impact: L / M / H / Ethical (a risk that is not financial but is morally non-negotiable, e.g., misleading a learner).

---

## R-001 — TCF Canada format changes during build

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | H |
| Description | FEI publishes a format revision (e.g., the rumored adaptive-listening "29-question" variant; master prompt §1.3) mid-build, invalidating bank quotas, mock-exam structure, or scoring. |
| Mitigation | (a) FEI source page linked + re-verified every release (Phase 9 launch checklist). (b) Format abstracted into a versioned config (`packages/shared/src/tcf_accel/schemas/exam_format.py`). (c) Subscribe to FEI mailing announcements. (d) Build "adaptive listening" only as an optional drill mode, never as the live exam format (master prompt §1.3). |
| Owner | Lead |
| Status | Open |

## R-002 — Whisper-fr accuracy on Canadian/African accents inadequate for pronunciation scoring

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | H |
| Description | The pronunciation pipeline (Phase 5 §2.6) depends on Whisper transcripts + MFA alignment. If WER is materially higher on Canadian or West-African accents than on Hexagonal French, the pronunciation sub-score becomes biased; the system would penalize accent rather than intelligibility. |
| Mitigation | (a) Multi-accent eval set built in Phase 5 audit (≥ 50 utterances per major accent family). (b) ASR vendor swap design in ADR-0007. (c) Pronunciation feedback labeled as a "coarse proxy" everywhere (Phase 5 ADR-031, Phase 7 anti-criterion). (d) Refuse to gate readiness on pronunciation sub-score alone. |
| Owner | ML |
| Status | Open |

## R-003 — LLM-authored synthetic items contain detectable "tells"

| Field | Value |
|---|---|
| Likelihood | H |
| Impact | M |
| Description | Synthesized MCQ items (Phase 3) develop patterns that allow learners to answer without understanding (e.g., correct option is always the longest, or always the most syntactically complex). Trains the wrong skill; learner overestimates real-exam readiness. |
| Mitigation | (a) Adversarial-distractor rejection (Phase 3 §2.5: a second LLM tries to answer using only the question; rejected if > 25% accuracy). (b) Length-balance check (distractors within ±25% of correct-answer length). (c) Synthetic-item cap ≤ 40% per module (ADR-021). (d) Periodic human spot-review on a sample of synthetic items. |
| Owner | Content |
| Status | Open |

## R-004 — NCLC estimator overconfident → learner books exam prematurely

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | H |
| Description | The Bayesian NCLC estimator (Phase 4 §2.3) returns a point estimate that the UI surfaces before the credible interval has narrowed sufficiently. Learner books a $300+ exam they will fail. Master prompt §6.2 frames this as financial harm. |
| Mitigation | (a) Mandatory CI reporting on every estimate (Phase 4 ADR-025). (b) `confident=True` only when n_obs ≥ 40, variance ≤ 0.4, spread ≥ 3 difficulty bands. (c) Readiness widget refuses 🟢 without 2 consecutive canonical-mock 🟢 (Phase 6 + Phase 8 ADR-045). (d) Cohort-calibration audit at launch (Phase 9). |
| Owner | ML |
| Status | Open |

## R-005 — Compute budget for daily learner-tier hosting exceeds OSS sustainability

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | M |
| Description | Daily ASR + LLM calls per learner exceed what a maintainer can sustain at OSS scale; the project becomes pay-to-use de facto. |
| Mitigation | (a) Local Whisper inference as default (no per-call cost). (b) LLM gated by privacy default + opt-in (master prompt §6.4). (c) LLM cost profiling in Phase 7 audit; per-rubric calibration to minimize tokens; Phase 7 ADR-040 inflation guard also gates expensive re-calls. (d) Documented self-hosting cost in `OPERATIONS.md` (Phase 9). |
| Owner | DevOps |
| Status | Open |

## R-006 — Copyright complaint from a news source whose audio we redistribute

| Field | Value |
|---|---|
| Likelihood | L |
| Impact | H |
| Description | The repo accidentally ships news audio (RFI / TV5MONDE / Radio-Canada) cached during development; the rights-holder issues a takedown. |
| Mitigation | (a) Never redistribute; ingest-and-cache pipeline runs on operator's machine (Phase 3 §1.2). (b) `data/` is gitignored; pre-commit hook (`scripts/check_no_data_commit.py`) fails any commit that adds a file under `data/`. (c) `audit-content` distribution check verifies bank provenance is CC-compatible at every release (Phase 9). |
| Owner | Lead |
| Status | Open |

## R-007 — Deaf/HoH candidates have no path for CO

| Field | Value |
|---|---|
| Likelihood | Certain |
| Impact | Ethical |
| Description | The TCF Canada CO section is audio-only by design; no system can make it accessible to a Deaf or hard-of-hearing candidate. The exam itself is the source of the inaccessibility, not the system. |
| Mitigation | (a) Build a "CE/EE/EO only" mode for Deaf/HoH candidates (Phase 5 §2.7, Phase 9 §2.5). (b) `LIMITATIONS.md` documents the structural exam constraint clearly. (c) Library page links to IRCC's accommodations process and to deaf-advocacy organizations. (d) Be honest that this is a *structural exam issue*, not a system gap; do not over-claim our accessibility. |
| Owner | Product |
| Status | Open |

## R-008 — Windows-native dev loop drift (Phase 1 toolchain assumes POSIX)

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | M |
| Description | The Makefile and pre-commit hooks assume POSIX shell semantics. A Windows-native contributor (without WSL2) may hit silent failures, breaking I1 of Phase 1 (green `make verify`). |
| Mitigation | (a) `scripts/windows_dev.ps1` ships a PowerShell-friendly path. (b) README explicitly recommends WSL2 for Windows. (c) CI matrix does not include `windows-latest` for Phase 1 (we deliberately do not promise Windows-native; documented). (d) Re-evaluate if a Windows contributor reports friction. |
| Owner | DevOps |
| Status | Open |

## R-009 — Pedagogy audit fails: synthetic-cohort P(success) does not match planner projection

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | H |
| Description | Phase 9 §2.1 launch gate: simulated cohorts must achieve P(success) within ±10 pp of the planner's projection. If `simulate_learning` (Phase 4 §2.6) is over-optimistic, the system promises outcomes the learner won't get. |
| Mitigation | (a) `simulate_learning` uses conservative parameters (0.05 NCLC/hour weakest-skill, diminishing returns). (b) Phase 4 audit calibrates synthetic-cohort trajectories vs FSRS retention numbers. (c) Phase 9 launch gate is blocking; failure means re-calibrating before release. |
| Owner | ML / Pedagogy |
| Status | Open |

## R-010 — κ on EE/EO auto-scorer below 0.65 against expert raters

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | H |
| Description | Phase 7 audit requires Cohen's quadratic-weighted κ ≥ 0.65 on a held-out expert set. If we cannot source expert ratings (most likely outcome at v1) or if our calibration layer fails to lift the LLM critic into the published-research range, the rubric scores have no defensible accuracy claim. |
| Mitigation | (a) Phase 7 ADR-037: report κ_silver (vs LLM rater) + sample-of-30 κ_gold against actual experts; never claim κ_gold without the sample. (b) Phase 7 ADR-038: publish κ with every release. (c) Phase 7 ADR-040: inflation guard clamps LLM-only scores. (d) Partner outreach to Alliance Française / DELF examiners for the 200-rating gold set (Phase 7 §2.5). |
| Owner | ML |
| Status | Open |

## R-011 — Schedule-cache invalidation bug exposes the wrong queue

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | M |
| Description | ADR-0012 commits the API to read the next-item queue from a Redis cache that workers maintain. A bug in the invalidation protocol (missed version bump, race between answer-write and cache-rebuild) would show the learner a stale or out-of-order review queue. Master prompt §6.2 frames "show the user the right next item" as a load-bearing UX promise. |
| Mitigation | (a) Atomic version key + Lua-scripted read (ADR-0012). (b) TTL safety net at 24 h. (c) `SchedulerCacheMissError → E_SCHED_002` triggers a synchronous compute path with a published SLO. (d) Phase 4 ships an invariant test that the cached queue is byte-equal to a fresh in-process recompute from the FSRS state. (e) The cache-hit-rate is a Phase 9 SLO metric. |
| Owner | ML / Backend |
| Status | Open |

## R-012 — Nightly IRT refit cost grows unboundedly at scale

| Field | Value |
|---|---|
| Likelihood | L (now), M (post-Phase-5) |
| Impact | M |
| Description | ADR-0013 runs the 2PL IRT fit nightly over the previous 90 days of interactions. At > 10k users with growing item banks, the fit may exceed the nightly maintenance window. Stale item difficulties degrade the planner's quality without surfacing as a hard failure. |
| Mitigation | (a) Phase 4 ADR will pin the lookback window once we have data. (b) Streaming variational IRT (online-2PL) is the documented fallback if nightly > 4 hours. (c) CEFR-band sharding is the second fallback. (d) Phase 4 audit measures fit time on the synthetic-cohort; we set the alarm at 1 hour, well below the 4-hour ceiling. |
| Owner | ML |
| Status | Open |

## R-013 — OpenAPI spec generation is non-deterministic across machines

| Field | Value |
|---|---|
| Likelihood | L |
| Impact | M |
| Description | The drift gate (`make openapi-check`) treats the committed `docs/api/openapi.v1.yaml` as the contract. If FastAPI / Pydantic / pyyaml emit different bytes on different platforms or library versions, contributors see false drift, contracts churn cosmetically, and the gate loses credibility. |
| Mitigation | (a) `_dump` sorts keys + disables YAML default-flow style. (b) Library versions pinned in `pyproject.toml` (`fastapi[standard]>=0.115,<1.0`, `pydantic>=2.7,<3.0`, `pyyaml>=6.0,<7.0`). (c) CI runs the drift check on both Linux and macOS to catch platform-specific bytes. (d) If drift recurs, we'll switch to a YAML canonicalization library (e.g., ruamel.yaml with a fixed dumper) before relaxing the gate. |
| Owner | Backend |
| Status | Open |

---

## Update protocol

Every `phaseN_evaluate.md` must:

1. Re-evaluate every Open risk: still Open, now Mitigated, now Accepted, or Retired?
2. Add any new risk surfaced during the phase.
3. Append a "Changes this phase" subsection to this file with the deltas.

A Mitigated risk that re-fires becomes Open again — no quiet downgrade.

---

## Changes this phase (Phase 2)

- Added R-011 (schedule-cache invalidation), R-012 (IRT-refit cost),
  R-013 (OpenAPI spec determinism).
- Re-evaluated R-001 through R-010: all Open; R-004 (NCLC overconfidence)
  mitigation strengthened by typed `Readiness.canonical_mock_streak_green
  ≥ 2` gate; R-005 (compute budget) mitigation strengthened by ADR-0017
  making `local_only` the durable default at the DB layer.

---

## R-040 — LLM critic score inflation during EE/EO scoring

| Field | Value |
|---|---|
| Likelihood | H |
| Impact | H |
| Description | LLM graders systematically over-score short, fluent-but-empty responses. Without containment a calibrator trained on silver labels learns the inflation as a bias term, and live rubric scores drift up across releases — exactly the failure mode reviewers flag for auto-scoring papers. |
| Mitigation | ADR-040 inflation guard: per-dimension clamp at `feature_floor + 2` whenever `llm_score − feature_floor > 3`, with `needs_human_review` flag set. Engaged in code; tested by `test_inflation_guard_against_synthetic_nclc5_essay` and the orchestrator-level `test_ee_scorer_inflation_guard_engages_for_forced_inflated_llm`. Temperature ≤ 0.2 + structured-output enforcement (ADR-039) further reduces inflation variance. |
| Owner | ML |
| Status | Mitigated |

---

## R-041 — Rubric calibrator overfits on a small expert-labelled set

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | M |
| Description | The Ridge calibrator is fit on ~200 rows per dimension. Without regularization control or held-out validation, the calibrator can memorize the training set; live scores then track training labels closely but generalize poorly to new submissions. |
| Mitigation | (a) Ridge α ≥ 0.1 by default. (b) The calibrator JSON includes a `training_set_hash` field that the audit verifies matches the deployed dataset (`RubricCalibrator.training_set_hash`). (c) `scripts/eval_kappa.py` evaluates κ on a separate held-out set per release. (d) The calibrator is re-fit only when ≥ 50 new labels arrive (manual policy in `scripts/calibrate.py` docs). |
| Owner | ML |
| Status | Open |

---

## R-042 — Canadian-French lexicon drift breaks `canadian_context_integration` scoring

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | M |
| Description | The `fr-CA.v1` lexicon in `tcf_accel_ml.scoring.features.canadian` is ~100 entries. Adding or removing entries silently changes the `canadian_context_integration` distribution and invalidates the calibrator's learned coefficient on that feature. If we bump the lexicon without re-running the audit the rubric drifts. |
| Mitigation | (a) The lexicon is versioned (`lexicon_version()` returns `fr-CA.v1`). (b) The audit checks that the deployed calibrator's `training_set_hash` matches a dataset re-scored with the current lexicon version. (c) Any lexicon bump is an ADR-grade change and triggers calibrator re-fit. |
| Owner | ML |
| Status | Open |

---

## R-043 — Pronunciation pipeline silent-on-failure inside EO scorer

| Field | Value |
|---|---|
| Likelihood | L |
| Impact | M |
| Description | If `PronunciationSignal` arrives with `display_label="insufficient_data"` the EO rubric's `pronunciation_prosody` dimension lacks an objective floor. A naive implementation would silently default to mid-band and produce a confident-looking rubric anyway. |
| Mitigation | The EO orchestrator flags `needs_human_review=True` whenever `display_label == "insufficient_data"` and multiplies the confidence by 0.6 (`tcf_accel_ml.scoring.eo.score.EOScorer.score`). Verified by `test_eo_scorer_insufficient_data_flags_human_review`. ADR-031 (`signal_kind="coarse_proxy"`) provides the structural anchor. |
| Owner | ML |
| Status | Mitigated |

---

## R-044 — Confidently-wrong qualitative feedback (fix suggestions don't apply)

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | M |
| Description | The feedback renderer picks the top-3 most-confident error annotations and emits them as actionable fixes. A high-confidence false positive (e.g., the bare-"ne" rule firing on legitimate negative-construction prose) becomes a confidently-wrong correction in the learner's feedback panel. |
| Mitigation | (a) Each rule in `tcf_accel_ml.scoring.features.errors` carries a calibrated `confidence` value derived from its known precision (e.g., the `si j'aurais` rule at 0.95, the bare-"ne" rule at 0.45). (b) The UI is expected to filter under a confidence threshold per `WritingRubric.error_list` (Phase 8 responsibility). (c) The disclaimer block ("Auto-feedback is approximate. A trained examiner could see more.") is always rendered. |
| Owner | ML / Frontend |
| Status | Open |

---

## R-046 — Published κ drift across releases (introduced by ADR-038)

| Field | Value |
|---|---|
| Likelihood | M |
| Impact | M |
| Description | ADR-038 makes the published κ a hard release gate. A future release that re-tunes the calibrator on a different training set, or that bumps the rubric prompt template, can drift the published κ without anyone noticing if the audit script silently accepts a re-generated dataset. |
| Mitigation | `RubricCalibrator.training_set_hash` is included in the calibrator JSON. `scripts/eval_kappa.py` records the hash in the κ-table output. CI runs the audit on every PR that touches `packages/ml/src/tcf_accel_ml/scoring/`; a κ regression of > 0.05 against the previous main fails the build. |
| Owner | ML |
| Status | Open |

---

## Changes this phase (Phase 7)

- Added R-040 (LLM score inflation, Mitigated via ADR-040), R-041
  (calibrator overfit), R-042 (Canadian lexicon drift), R-043
  (pronunciation silent-on-failure, Mitigated via Phase 5 ADR-031 +
  Phase 7 review-flag), R-044 (confidently-wrong feedback), R-046
  (published κ drift, introduced by ADR-038).
- Re-evaluated R-010 (κ < 0.65 on EE/EO): still Open, but now
  partially Mitigated by (a) the hybrid features + LLM + calibration
  architecture (ADR-036), (b) the inflation guard (ADR-040), and (c)
  the structural "experimental" badge for releases below the gate
  (ADR-038). The "claimed κ" path remains gated on the ≥ 200-row
  gold expert set (ADR-037), which is the load-bearing acquisition
  step.
- Re-evaluated R-002 (Whisper-fr accuracy): still Open; Phase 7
  carries forward Phase 5's `display_label="insufficient_data"` gate,
  so the silent-failure mode is contained downstream regardless of
  the underlying ASR.

---

## Changes this phase (Phase 9)

Per ADR-046 (launch criteria are blocking) the Phase 9 walk must
end with zero Open risks. Twelve risks transitioned to Mitigated;
seven Accepted with explicit two-maintainer-signed rationales +
v1.1 follow-ups. The full per-risk disposition lives in
`data/audit/phase9/risk_register_check.md`.

**Mitigated this phase:**

- **R-001** (FEI format changes) — Mitigated by `exam_format.py`
  format abstraction + FEI source re-verification at launch
  (`data/audit/phase9/fei_source_check.md`).
- **R-003** (LLM synthetic-item tells) — Mitigated by adversarial-
  distractor rejection + length-balance check + synthetic-ratio
  ≤ 40% per module verified in `content_audit.md`.
- **R-004** (NCLC estimator overconfident) — Mitigated by the
  Phase 9 calibration audit: planner-simulator agreement within
  ±0.05 NCLC across 12 cohorts.
- **R-005** (compute budget) — Mitigated by `local_only` default
  + LLM opt-in + cost documented in `OPERATIONS.md §11` and
  `LIMITATIONS.md §9`. (The Accepted portion is the residual
  exposure under cloud opt-in, capped by the inflation guard.)
- **R-006** (copyright complaint) — Mitigated by `data/` gitignore
  + pre-commit hook + content audit grep clean for watermark
  phrases.
- **R-009** (pedagogy audit failure) — Mitigated by the Phase 9
  audit pass (12/12 cohorts; `pedagogy_audit.json`).
- **R-011** (schedule-cache invalidation) — Mitigated by the
  atomic version key + Lua-scripted read + Phase 4 invariant
  test + the `OPERATIONS.md §9` alarm on cache hit rate.
- **R-012** (IRT-refit cost) — Mitigated by the Phase 4 1-hour
  margin + the documented streaming-variational fallback.
- **R-013** (OpenAPI spec determinism) — Mitigated by pinned deps
  + sorted keys + cross-platform CI.
- **R-040** (LLM critic inflation) — re-confirmed Mitigated via
  ADR-040 inflation guard.
- **R-042** (Canadian lexicon drift) — Mitigated by lexicon
  versioning + calibrator `training_set_hash` gate.
- **R-043** (pronunciation pipeline silent-on-failure) — re-
  confirmed Mitigated via the `display_label="insufficient_data"`
  flag.
- **R-046** (published κ drift) — Mitigated by the CI κ regression
  check + per-release table in the README.

**Accepted this phase** (each with two-maintainer-signed rationale
+ v1.1 follow-up; full text in
`data/audit/phase9/risk_register_check.md`):

- **R-002** (Whisper-fr accent accuracy) — Accepted: pronunciation
  is flagged as coarse proxy (ADR-031); never gates readiness.
  v1.1: multi-accent eval set expansion.
- **R-007** (Deaf/HoH CO accessibility) — Accepted: CE/EE/EO-only
  mode shipped + verified; structural exam constraint surfaced
  in `LIMITATIONS.md §3`. v1.1: continue dialogue with IRCC
  accommodations.
- **R-008** (Windows-native dev loop) — Accepted: PowerShell path
  ships; WSL2 recommended. Re-evaluate on contributor report.
- **R-010** (κ_gold gap) — Accepted: v1.0 ships κ_silver ≥ 0.65
  with the "experimental" badge per ADR-037 + ADR-038. v1.1
  commits to acquiring the 200-row expert set.
- **R-041** (calibrator overfit) — Accepted: Ridge α ≥ 0.1 +
  `training_set_hash` + held-out eval per release; v1.1 expands
  the held-out set.
- **R-044** (confidently-wrong feedback) — Accepted: per-rule
  confidence threshold + UI disclaimer at v1.0. v1.1 will tune
  per-rule precision based on real-learner reports.

**Open count entering Phase 9**: 18. **Open count exiting Phase 9**: 0.

ADR-046 conformance verified: every Accepted item carries the
two-maintainer-signed rationale required by the launch criteria.
