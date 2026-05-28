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

---

## Update protocol

Every `phaseN_evaluate.md` must:

1. Re-evaluate every Open risk: still Open, now Mitigated, now Accepted, or Retired?
2. Add any new risk surfaced during the phase.
3. Append a "Changes this phase" subsection to this file with the deltas.

A Mitigated risk that re-fires becomes Open again — no quiet downgrade.
