# Phase 9 — THINK

> The launch gate. This document captures the *principles* against which
> Phase 9's design, code, and audit will be measured. It is the
> reviewer-facing definition of what "ready to ship" means for
> `tcf-accel`, and it sets the anti-criteria that Phase 9 will not be
> allowed to violate without an explicit Accepted-risk entry.

The user's framing: *"in the end all functions are in ready-to-launch
state."* Phase 9 is the place where that phrase gets a concrete
auditable meaning.

---

## 1. What "Launch-Ready" actually means

Six independent gates. Failing any one of them blocks the `v1.0.0`
tag. We refuse to ship behind a release-engineering veneer when the
underlying claim is shaky.

### 1.1 Pedagogically valid

A learner who follows the system as designed has a *realistic*
expectation of moving B1 → NCLC 7–9 in 12 weeks at ~2.5 h/day.

- "Realistic" means: the synthetic-cohort simulator from Phase 4
  (`tests/pedagogy/synthetic_cohorts.py`) plus the new Phase 9
  launch-cohort suite (`tests/pedagogy/launch_audit.py`) shows
  `P(min_skill ≥ target_NCLC at deadline) ≥ 0.65` for the realistic
  cohorts.
- "Realistic" excludes the over-reach cohort (B1 → C2 in 12 weeks):
  the system must *honestly refuse* to project success for that
  cohort, not produce optimistic numbers.
- The planner's projected trajectory must agree with the simulated
  reality within ±10 percentage points of P(success). Bigger
  divergence means the planner is lying — either over-promising or
  under-promising — and either is launch-blocking.

This is the load-bearing audit. Everything else can hold up while
this one slips, and the project would still be ethically broken.

### 1.2 Safe

No learner harm from:

- **Over-predicted NCLC.** Phase 4 + Phase 6 + Phase 8 already
  enforce the CI floor (ADR-025), the `confident=True` gate, the
  two-green-mocks readiness gate (ADR-045), and the
  no-bare-NCLC ESLint rule. Phase 9 verifies these still hold in
  the integrated build.
- **Copyright.** No third-party audio/text in the repo; the
  pre-commit hook that blocks `data/` commits is wired and the
  Phase 9 audit re-runs it against the release artefact.
- **Privacy leak.** `local_only` is the default (ADR-0017); no
  learner text or audio reaches logs/traces (ADR — see Phase 9
  §2.2); cloud LLM/ASR is opt-in.
- **Security.** OWASP Top 10 verified by manual + automated review;
  no high-severity findings in `pip-audit`, `npm audit`,
  `trivy fs`, `gitleaks`, `bandit`.

### 1.3 Operable

- A self-hoster can stand up the full stack on a clean machine via
  one command: `make dev` brings up Postgres / Redis / API / worker
  / web and they are healthy within 60 s.
- A non-technical learner can use the system without instruction.
  The Phase 8 think-aloud (deferred from Phase 8 §1 row 5) runs
  here, on the integrated build, against three maintainers acting
  as candidates.

### 1.4 Honest

Every claim made by marketing copy, documentation, and in-app
messaging is supported by the data the system collects.

- README, in-app onboarding, and `LIMITATIONS.md` say the same
  thing about what the system does and does not do.
- The published κ is real (Phase 7) and lives next to the README
  badge.
- No "pass guaranteed" language anywhere.
- The "What it isn't" section is at least as prominent as the
  "What it is" section.

### 1.5 Maintainable

A new contributor — without access to the maintainers — can
navigate the codebase using only the docs.

- `ARCHITECTURE.md` rolls up the 48 ADRs into one navigable
  document.
- `OPERATIONS.md` gives the operator the runbooks for every
  alert.
- `CONTRIBUTING.md` describes the phase discipline and the dev
  loop without ambiguity.

### 1.6 Documented

A learner can read the FAQ and understand what the system is, what
it isn't, and why.

- `LEARNER_GUIDE.md` describes the 12-week journey week-by-week.
- `LIMITATIONS.md` is honest about what the system can't do.
- Both are linked from the in-app onboarding and from the launch
  post.

---

## 2. The three audits hardest to pass

Three audits dominate the launch decision. If any of them slip, we
do not ship.

### 2.1 Pedagogy audit

*Question:* do the 12 synthetic-cohort trajectories under the
system's plan actually converge on the target NCLC distribution,
or is the system optimistic?

This is the *honest check* on pedagogy. The system's job is to
move learners; if the simulator says the planner over-promises,
the planner is broken — not the simulator. We re-tune the planner
or we don't ship.

Failure mode: an optimistic learning-rate constant
(`LEARNING_RATE_PER_MINUTE`) inflates projected gains; cohorts
look like they hit target on paper but the same cohorts in the
simulator come up short.

Recovery if it slips: re-calibrate the rate against FSRS retention
data + tighten the diminishing-returns curve; re-run; if still
short, narrow the marketed band from "NCLC 7–9 in 12 weeks" to
"NCLC 7 in 12 weeks" and re-launch the doc copy.

### 2.2 Calibration audit

*Question:* does the κ on the held-out expert set hold up over
time, across new prompts, across writing-vs-speaking?

Phase 7 measured κ once. Phase 9 verifies the published κ on the
release artefact's calibrator, not on a development snapshot. ADR-038
made the published κ a release gate; Phase 9 enforces it on the
release.

Failure mode: silent calibrator regression introduced after Phase
7 (e.g., a feature engineering tweak that nudges κ down).

Recovery: revert the regressing change; re-publish κ; re-issue
the release.

### 2.3 Content audit

*Question:* is the bank's CEFR-level labeling consistent with
current FEI sample materials? Or has drift accumulated?

Two checks: (a) bank composition matches the quota matrix; (b) a
100-item-per-module hand-review sample agrees with our CEFR
labels.

Failure mode: synthetic-item drift (Phase 3 ADR-019/021 trying to
contain this); FEI publishing a new sample that exposes a
mismatch.

Recovery: pull the offending items; rerun the distribution check;
re-publish.

---

## 3. What we don't promise

Be explicit. The system does NOT:

- **Guarantee a score.** The TCF Canada is administered by FEI;
  test-day variance, anxiety, illness, and the actual prompt set
  the learner draws are all out of our control.
- **Replace a human tutor for high-anxiety candidates or those
  with significant production gaps.** Our drills and our auto-
  scoring are calibrated to the median learner; learners with
  specific blocks (speaking anxiety, dyslexia, processing
  differences) will benefit from a human in the loop.
- **Score perfectly.** κ ≤ 0.75 means ~25% of subscale judgments
  still differ from expert raters by ≥ 1 point. The system
  surfaces this honestly via the κ badge and the `LIMITATIONS.md`
  page.
- **Provide CO accessibility for Deaf candidates beyond CE/EE/EO
  routing.** The CO section of the TCF Canada is audio-only by
  design (R-007); we can route a Deaf candidate through CE/EE/EO
  only, but we cannot make the CO section accessible. This is a
  *structural exam issue*, not a system gap, and we say so.
- **Substitute for booking actual practice with native speakers.**
  HelloTalk, Tandem, italki are all linked from the Library page
  and we recommend them in `LEARNER_GUIDE.md` for Week 4 onward.
- **Promise NCLC 11 (C2) in 12 weeks from B1.** The "aggressive
  cohort" in the pedagogy audit is allowed to fail; the system
  must honestly refuse to project success.

This honesty is documented in `LIMITATIONS.md`, surfaced in the
onboarding modal, and re-surfaced in the readiness widget when a
learner's posterior is far from target.

---

## 4. The risk register at launch

Every Open risk in `RISK_REGISTER.md` must be re-evaluated. The
options are: Mitigated, Accepted, or Retired. *No risk may remain
Open at launch.* If we cannot mitigate a risk, we Accept it with
an explicit one-paragraph rationale that names the residual
exposure and the trigger that would force us to re-open it.

The Phase 9 evaluate step lists every transition; the launch
checklist refers to the count of Open risks (must be zero).

---

## 5. Trade-offs Phase 9 will not litigate

The following are out of scope for `v1.0.0` — *not* because they're
unimportant, but because shipping a working v1 honestly is more
valuable than shipping a delayed v1.1 with these in it:

- Native mobile apps (the web PWA is the v1 mobile story).
- Tutor / multi-tenant deployment for language schools.
- TEF Canada parallel track.
- DELF/DALF support.
- Online-cohort feature (study groups).
- Improving κ from ≥ 0.65 (the Phase 7 gate) to ≥ 0.75 (a
  v1.1 stretch).
- A1 / pre-B1 onboarding.

These appear in the v1.1 roadmap (Phase 9 §2.8). The point of the
list is to pre-empt the reviewer asking "what's missing?" with a
written answer.

---

## 6. The reviewer's adversarial questions

The five questions a hostile reviewer would ask, and our answers:

1. **"How do I know your synthetic-cohort simulator isn't just
   producing the answer your planner wants?"**
   The simulator (`tcf_accel_sla.planner.generate_plan.simulate_learning`)
   uses a *single* documented learning-rate constant
   (`LEARNING_RATE_PER_MINUTE = 0.05 / 60`) and a documented
   diminishing-returns curve. The constant was calibrated *once*
   in Phase 4 against the cohort archetypes and is the same one
   we report at launch. The audit publishes both the rate and
   the per-cohort outcome; a future tweak that boosts P(success)
   without also boosting the constant is detectable.

2. **"Your κ is ≥ 0.65. The published auto-scoring research
   reports κ in the 0.70–0.80 range. Why should I trust you?"**
   Per ADR-038, every release publishes κ next to the badge.
   Per ADR-037, we distinguish κ_silver (against an LLM rater)
   from κ_gold (against a small expert set). The v1.0
   "experimental" badge stays until we accumulate the 200-row
   gold set (R-010, Open → still Open at v1.0); we say so in
   the release notes. We don't claim the research range
   anywhere.

3. **"Your system is on the web. What happens to learner audio?"**
   `local_only` is the default (ADR-0017). Audio never leaves
   the operator's machine in the default deployment. Cloud
   ASR/LLM is opt-in and the opt-in surface in
   `apps/web/.../settings` describes exactly what data leaves
   the machine when enabled. No learner text or audio is in
   logs or traces.

4. **"Show me a real-learner trajectory that matches the
   simulator."**
   v1.0 does not have this. We are pre-pilot. We say so. The
   pedagogy audit is the synthetic-cohort signal; the public
   pilot is post-v1.0, and `OPERATIONS.md` describes how the
   operator captures and reports the trajectories that do
   appear post-launch.

5. **"What if FEI changes the exam format the week after you
   launch?"**
   R-001 documents this. The exam format is abstracted into
   `packages/shared/src/tcf_accel/schemas/exam_format.py`
   (Phase 1 design + Phase 6 wiring); a format change is a
   versioned config rev, not a code rewrite. The release
   checklist's "FEI source-of-truth check" verifies the spec
   matches the live FEI page at the moment of the tag.

---

## 7. What Phase 9 actually delivers

This is the operational artifact list, kept here so the design
step (next) can reference it:

- `phase9_think.md` (this file).
- `phase9_design.md` — the audit suite, the release pipeline,
  the launch checklist, the ADRs.
- `phase9_audit.md` — the *evidence* for each gate.
- `phase9_evaluate.md` — the verdict (and any anti-criterion
  hits).
- Code: `tests/pedagogy/launch_audit.py`, `tests/load/k6_*.js`,
  `scripts/release/build_release.py`, `scripts/release/sign_audit_report.py`.
- Docs: `LIMITATIONS.md`, `LEARNER_GUIDE.md`, `PEDAGOGY.md`,
  `ARCHITECTURE.md`, `OPERATIONS.md`, rewritten `README.md`.
- ADRs 046–048 (launch criteria blocking, external security
  review or fallback, public κ + cohort report).
- Artefacts: `LAUNCH_READINESS_REPORT.md` (signed), `CHANGELOG.md`
  entry, `RISK_REGISTER.md` updated to zero Open.

---

## 8. The honest closing posture

The system is not perfect at v1.0. It is *honest about not being
perfect at v1.0*. That is the load-bearing distinction. A learner
who reads `LIMITATIONS.md` and our onboarding modal will know
exactly what they are getting; the readiness widget refuses to
promise readiness until two consecutive canonical mocks land
green and all four skills are confident; the published κ tells
them how much to trust the auto-scoring.

Phase 9's job is to verify that the honesty is end-to-end, that
the safety nets are wired, and that the launch artefacts make
both visible to the reviewer.
