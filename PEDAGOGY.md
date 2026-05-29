# PEDAGOGY

> The SLA (Second-Language Acquisition) evidence dossier for
> `tcf-accel`. Rolls up the eight SLA principles (master prompt
> §2.1), the planner's design (Phase 4), the mock/drill cadence
> (Phases 5–6), and the readiness gate (Phase 8), and ties each
> claim to the code, the test, and the ADR that makes it real.

This is the document a reviewer reads to decide whether to trust
our pedagogy claims. It is not marketing copy.

---

## 1. The eight evidence-aligned SLA principles

| # | Principle | Source | How we instantiate it |
|---|---|---|---|
| 1 | **Comprehensible input + 1** | Krashen (1985) | CEFR-classified item placement; the planner serves items at the learner's posterior level, occasionally pushing to level + 1 |
| 2 | **Pushed output** | Swain (1985) | Mandatory daily production minutes (EE + EO); the allocator's β_EE=1.4, β_EO=1.5 (ADR-027) prevents the learner from drifting into a reception-only routine |
| 3 | **Spaced retrieval** | Ebbinghaus / FSRS-6 | FSRS-6 SRS (ADR-0006); per-card scheduling using documented FSRS-6 default weights with per-user optimisation deferred (ADR-0023) |
| 4 | **Semantic-aware spacing for confusables** | LECTOR (arXiv 2508.03275) | The `amener/emmener` family of confusables gets LECTOR-style scheduling — bounded by FSRS (ADR-0024) so we don't override the SRS, only add a confusable-family-spacing constraint on top |
| 5 | **Deliberate practice on weakness** | Ericsson | The bottleneck allocator (`packages/sla/.../planner/allocator.py`) over-weights the weakest skill *and* the production skills |
| 6 | **Daily shadowing for prosody** | Murphey (2001) | ADR-030: every default daily plan reserves a 10-min `co_shadowing` block, configurable down to a `SHADOWING_MIN_FLOOR=3` min but never zero |
| 7 | **Interleaved retrieval in mocks** | Rohrer & Taylor (2007) | Canonical-mock structure mirrors the FEI exam shape; sections are interleaved across mock cadence (ADR-028 exam-shape floor) |
| 8 | **Testing-effect ramp** | Roediger & Karpicke (2006) | Mock cadence ramps biweekly → weekly → 3×/week in the final fortnight (ADR-033, ADR-034) |

Each principle has a code anchor + a test that verifies the
principle is operative in the running system, not just documented.

---

## 2. The optimisation target

We optimise the **minimum across skills**, not the average.

The reason: the IRCC NCLC immigration rule (master prompt §1.2)
caps the profile on the lowest skill, not the mean. A learner
with NCLC {CO:9, CE:9, EE:9, EO:5} maps to NCLC 5 for IRCC
purposes, *not* NCLC 8.

Implementation:

- `compute_readiness` (`packages/sla/.../planner/readiness.py`)
  bases its traffic light on the **minimum** skill posterior,
  not the mean.
- The allocator's α formula uses `(target - μ_s)²` so the
  weakest skill receives quadratic over-weighting in the daily
  allocation.
- The plan rationale (`generate_plan._render_plan_rationale`)
  names the bottleneck skill explicitly and reports the
  *projected weakest-skill NCLC at horizon*, never the mean.

This is the load-bearing pedagogy decision: an averaged-progress
plan would mis-time the learner's bookable date by weeks.

---

## 3. The honest learning-rate constant

`LEARNING_RATE_PER_MINUTE = 0.05 / 60` NCLC/minute is the single
constant the planner uses to project gain under practice. The
constant was calibrated *once* in Phase 4 against the synthetic-
cohort archetypes and verified at launch by the Phase 9 pedagogy
audit.

The diminishing-returns curve:

- Below target NCLC: full rate.
- Between target and NCLC 12: rate halves and then ramps to zero
  at the ceiling.

This is deliberately conservative. Under-promising and over-
delivering is the right error direction for the trust contract;
a learner who hits target ahead of schedule will book the exam
earlier, not later. A learner who is mis-projected ahead of
where they are will book the exam too early and lose the test
fee (master prompt §6.2 frames this as financial harm).

Audit: `tests/pedagogy/launch_audit.py` verifies the
constant is consistent with the simulated trajectories ±10pp on
P(success) for realistic cohorts.

---

## 4. The mock cadence

ADR-033 + ADR-034 set the cadence:

| Weeks | Cadence | Mode |
|---|---|---|
| 1–4 | 0 canonical / 1 training | Mid-arc training mock only |
| 5–6 | 1 canonical / week | First gating mock |
| 7–8 | 1 canonical / week | Ramp |
| 9 | 2 canonical / week | Calibration |
| 10–11 | 3 canonical / week | Pre-exam |
| 12 | 0 (the exam itself) | — |

Each canonical mock is a 2 h 47 min run that mirrors the
published FEI structure (`06_MOCK_EXAM_ENGINE.md`); training
mocks are shorter and serve as no-pressure shape-checks.

The drill-mock posterior-divergence alert (ADR-034) trips when
the learner's drill posterior and their mock posterior disagree
by > 1 NCLC; the planner then injects exam-shape blocks
(`writing_long`, `speaking_mono`, `mock_section`) to close the
gap.

---

## 5. The readiness gate

ADR-045 + Phase 8 implementation:

A 🟢 readiness signal — the only state that surfaces the
"book your exam" CTA — requires **all** of:

1. All four skills have `confident=True`
   (n_obs ≥ 40, variance ≤ 0.4, ≥ 3 difficulty bands seen).
2. **Two consecutive canonical-mock sessions** ended green
   (`MockSectionScore` clears the per-section gate for both).
3. The minimum skill posterior mean ≥ target NCLC.

If any of the three fails, the widget shows ⚪ / 🟡 / 🔴 / and
the CTA is "See your priority drills" — *not* "book now."

The ESLint rule `no-bare-nclc` (Phase 8 §2.2) enforces that no
component in the web app renders an NCLC number without its CI.
This is structural: a future contributor cannot accidentally
ship a confident-looking bare number.

---

## 6. Honest auto-scoring (κ + the experimental badge)

ADR-037 + ADR-038 + ADR-040 + ADR-048 set the auto-scoring
honesty contract:

- We measure κ on every release (ADR-038 makes it a release
  gate).
- We distinguish `κ_silver` (against an LLM critic, larger sample)
  from `κ_gold` (against a small expert set). v1.0 ships with a
  `κ_silver ≥ 0.65` claim and a sample-of-30 `κ_gold` spot-check.
- The inflation guard (ADR-040) clamps LLM-only scores that
  exceed the feature floor by > 3 dimensions, setting
  `needs_human_review = True`.
- v1.0 rubric scores carry an **"experimental"** badge until we
  accumulate the 200-row expert-rater dataset that R-010
  documents.
- The κ table is published in the README under
  `## Honesty receipts` (ADR-048).

Practical consequence: a learner reading the rubric score sees
the badge, sees the κ band, and treats the score as the system's
opinion — not an examiner's verdict.

---

## 7. The pedagogy audit (Phase 9)

Twelve cohorts, one hundred trajectories each, one report:
`tests/pedagogy/launch_audit.py` + `data/audit/phase9/pedagogy_audit.json`.

The audit verifies:

- For every realistic cohort, simulated `P(success) ≥ 0.65`.
- For every realistic cohort, the planner's projection agrees
  with the simulated reality within ±10pp.
- For the over-reach cohort (B1 → C2 in 12 weeks), the planner
  honestly refuses to project success.
- For the trivial cohort (already at target), the learner does
  not regress.
- For the edge cohorts (short runway, low budget), the planner
  honestly reflects the difficulty (projected_min < target +
  margin).

The cohort table + per-cohort P(success) is published in the
README under `## Honesty receipts` (ADR-048).

---

## 8. What we deliberately do not claim

A short list, made explicit so the reviewer can verify:

- **We do not claim** a published-research κ band (0.70–0.85)
  for our auto-scoring. We claim κ ≥ 0.65 with the experimental
  badge.
- **We do not claim** B1 → C2 in 12 weeks. The honest band is
  NCLC 7–9.
- **We do not claim** pronunciation scoring is a precise signal.
  It is a coarse proxy (ADR-031).
- **We do not claim** the system replaces a tutor for production-
  skill gaps. We say so in `LEARNER_GUIDE.md §5`.
- **We do not claim** real-learner outcome data at v1.0. We are
  pre-pilot. The Phase 9 pedagogy audit is the *synthetic*
  signal; real-learner data accumulates post-launch and is
  reported under `OPERATIONS.md §10`.

---

## 9. References

The peer-reviewed sources that anchor the eight principles:

- Krashen, S. (1985). *The Input Hypothesis.*
- Swain, M. (1985). "Communicative competence: Some roles of
  comprehensible input and comprehensible output."
- Ebbinghaus, H. (1885). *Über das Gedächtnis.*
- FSRS / Free Spaced Repetition Scheduler (Ye, 2022+).
- LECTOR: Wozniak et al. (arXiv 2508.03275, 2025).
- Ericsson, K. A., Krampe, R. T., & Tesch-Römer, C. (1993).
  "The role of deliberate practice in the acquisition of expert
  performance."
- Murphey, T. (2001). "Exploring conversational shadowing."
- Rohrer, D., & Taylor, K. (2007). "The shuffling of mathematics
  problems improves learning."
- Roediger, H. L., & Karpicke, J. D. (2006). "Test-enhanced
  learning."

The TCF Canada / NCLC alignment:

- France Éducation International (FEI) TCF Canada specification
  (re-verified at every release per the launch checklist).
- IRCC Canadian Language Benchmark (NCLC) descriptors.

---

## 10. The closing posture

We do not own pedagogy. We instantiate published evidence and
audit the instantiation against synthetic cohorts. When a claim
in this document is not backed by code + test + ADR, the claim
is false.

If you find a claim here that isn't anchored, file a bug — the
anchors are the source of truth.
