# RATIONALE — Refusal & Pushback Log

> This document records every directive (from the master prompt or from a user) that this project refused or substituted, with the load-bearing reason. Required by master prompt §11.

Each entry includes:
- **What was requested**
- **What we did instead**
- **Why** (evidence + reasoning)
- **Date / Phase**

When in doubt, future maintainers: bias toward honesty over engagement, evidence over convenience, learner welfare over feature breadth.

---

## R-001 — C2 in 12 weeks from B1

- **Requested**: the user's stated goal was "B2/C1/C2 in 3 months from B1" (master prompt §0).
- **Did instead**: target re-set to **NCLC 7 floor / NCLC 9 ceiling** over a 12-week, 210-hour budget (master prompt §2.2). C2-stretch modules are offered but the system never promises C2 attainment. The readiness widget (Phase 4 §2.7) refuses 🟢 unless `confident=True` on all four skills and ≥ 2 consecutive canonical mocks at 🟢 (Phase 8 ADR-045).
- **Why**: Every credible CEFR guided-learning-hour estimate places C2 at ~1,000–1,200 cumulative hours from a B1 start; 210 hours covers the B1 → low-C1 transition with high credibility but is implausibly short for B1 → C2. The harm of a false promise is concrete: a $300+ exam fee plus visa-window cost if the candidate books prematurely on inflated readiness signals.
- **Date / Phase**: 2026-05-27 / Phase 1 (re-affirmed every release).

---

## R-002 — "Pass-guaranteed" copy

- **Requested**: none yet; pre-emptively refused per master prompt §11.
- **Will do instead**: documentation, marketing copy, and in-app messaging carry no guarantee language. The honest framing — "the system targets a realistic NCLC 7 floor / 9 ceiling at the budgeted hours; outcomes vary with prior knowledge, time-on-task, and exam-day conditions" — is published in `LIMITATIONS.md` (Phase 9) and surfaced at onboarding (Phase 8).
- **Why**: A guarantee badge induces booking decisions the model is not confident enough to support. Outcome-on-exam is the metric we optimize; daily-active-users / engagement metrics are *not*.
- **Date / Phase**: 2026-05-27 / Phase 1 (standing).

---

## R-003 — Cloud telemetry of learner audio by default

- **Requested**: none; pre-emptively refused.
- **Will do instead**: `PRIVACY_DEFAULT_MODE=local_only`. ASR runs on-device via the local Whisper model; cloud ASR is opt-in via `cloud_optin` and is gated by an explicit consent screen (Phase 8 settings). The privacy notice + data-export endpoint + delete endpoint are launch-blocking (Phase 9 §2.2).
- **Why**: Master prompt §6.4. Learner audio is sensitive; off-device defaults invert the consent model. Cohort calibration (which would benefit from cloud sampling) is opt-in only.
- **Date / Phase**: 2026-05-27 / Phase 1 (standing).

---

## R-004 — Redistribution of copyrighted FEI test material

- **Requested**: implicit (a fully-stocked CO/CE bank would be easier if we just copied FEI samples).
- **Did instead**: FEI sample materials are *referenced*, never bundled. The repo ships a thin proxy in the UI (Phase 8 Library) that fetches FEI's public sample pages at runtime. Phase 3 ADR-020 codifies this rule.
- **Why**: FEI owns the copyright; bundling exposes the project and any operator to takedown and liability. The cost is a slightly less convenient sample experience for the learner; the benefit is project survival and respect for the rights-holder.
- **Date / Phase**: 2026-05-27 / Phase 1.

---

## R-005 — Features that contradict the bottleneck heuristic

- **Requested**: none; pre-emptively refused.
- **Will do instead**: no "polish your best skill" gamified module, no leaderboard on the strongest-skill axis, no streak that rewards drilling a skill already at target. The planner allocator (Phase 4 §2.5) over-weights the weakest production skill (β=1.4 EE, β=1.5 EO) and the system refuses to let a learner train on a skill that has crossed target until the floor catches up.
- **Why**: The immigration rule (master prompt §1.2) caps the profile on the *minimum* of the four scores. Optimizing the mean inflates the dashboard but does not change the outcome. Master prompt §2.1.5.
- **Date / Phase**: 2026-05-27 / Phase 1 (standing).

---

## R-006 — Showing a point estimate without a credible interval

- **Requested**: none; pre-emptively refused.
- **Will do instead**: every NCLC display includes a CI bar. The `confident` flag (Phase 4 §2.3) is `False` until n_obs ≥ 40 AND posterior variance ≤ 0.4 AND difficulty-band spread ≥ 3. When `confident=False`, the UI shows "still learning your level — complete N more items" instead of a number. Master prompt §6.2 + Phase 4 ADR-025.
- **Why**: Over-prediction → premature booking → real financial harm. The CI is the antidote to false precision.
- **Date / Phase**: 2026-05-27 / Phase 1 (standing).

---

## R-007 — Synthetic-item share without an explicit cap

- **Requested**: none; pre-emptively bounded.
- **Will do instead**: synthetic items (LLM-authored) capped at ≤ 40% of any module's bank, tagged `synthetic=true`, subjected to adversarial-distractor rejection (Phase 3 §2.5 quality gate). Phase 3 ADR-021.
- **Why**: Synthetic items risk detectable "tells" that learners exploit, training the wrong skill. The cap + adversarial-pass mitigates without removing the speed benefit synthesis provides.
- **Date / Phase**: 2026-05-27 / Phase 1 (standing).

---

## Process

Every release re-audits this file. Any new refusal in the lifetime of the project gets an entry. Removing an entry requires a written reversal in `CHANGELOG.md` with the reason that the underlying risk no longer applies.
