# Phase 6 — THINK

> The mock exam is the **single non-drill signal** that tells a learner
> "you are ready (or not)." Drill posteriors say "you can answer items
> like these well"; the mock posterior says "you can sit the actual
> 2h47 exam well." Those are different claims, and the system must
> not collapse them.

This document is the load-bearing reasoning for Phase 6. It precedes
the design and pins the constraints we will not relax later.

---

## 1. What "realistic" means here

### 1.1 The exam-day psychology

A mock that matches FEI's **content** but not its **psychology** is
worse than no mock at all: it certifies confidence the learner has not
actually earned. Concretely the system must:

- **Hold strict timing** per module (35 min CO, 60 min CE, 60 min EE,
  12 min EO) and the published 5/5/15 inter-module breaks. There is
  no "pause"; abnormal exits forfeit.
- **Withhold all feedback** until the very end. Mid-test feedback
  trains the wrong response (it teaches the learner to read for
  correctness signals instead of comprehension).
- **Forbid replay** in CO. The audio plays exactly once, server-side
  enforced. CE passages are scrollable but a flagged item can only be
  revisited within the same module's clock.
- **Sequence difficulty ascending** within a module (FEI's "progressive
  difficulty" principle).
- **Optional proctor mode** simulates centre conditions: fullscreen,
  focus tracking, no second-monitor escape hatch. We do not actually
  proctor — we simulate the constraint.

This is non-negotiable: any departure trains a habit the real exam
will punish.

### 1.2 Why the mock posterior is *separate* from the drill posterior

The drill posterior (Phase 4 `SkillPosterior`) absorbs hundreds of
short-form interactions across weeks. Its mean is the system's best
"how good are you at the underlying skill?" estimate. The mock
posterior is the system's "how do you perform under exam-day
conditions?" estimate.

These two numbers should agree to within ~1 NCLC. When they diverge by
≥ 2 NCLC the system raises an alert — both outcomes are diagnostic:

- *Drill > mock by 2*: drill overfitting (the learner has learned to
  pattern-match the drill format, not the underlying skill).
- *Mock > drill by 2*: the mock item bank is mis-calibrated against
  the drill bank, **or** the learner only performs under pressure (rare
  but real). Operator gets the alert and decides.

ADR-034 records this separation.

### 1.3 Item sampling for a single mock

The bank has thousands of items per module. A *good* mock must:

- **Match the official shape exactly**: 39 CO + 39 CE + 3 EE + 3 EO.
- **Cover the full A1..C2 difficulty distribution per FEI** — *not*
  the learner's current level. That is what drills are for. A mock
  that only tests at the learner's level cannot diagnose ceiling
  effects.
- **Avoid recent recall**: no item the learner has seen in the past
  30 days. If we re-use an item the learner has already drilled,
  we are measuring recall, not comprehension.
- **Span genre / accent / register** per the existing quota matrix.
- **Pull ≥ 20% of CO/CE items the learner has *never* seen**, so the
  mock has genuine novelty even for power users.
- **For EE/EO**: exactly one each of Task 1, 2, 3. This is the
  official shape and FEI enforces it; the mock must too.

Within-module ordering follows ascending difficulty (FEI doctrine).

### 1.4 The multiple-mock tradeoff

Frequent mocks → testing-effect benefit, plus the learner habituates
to the exam-day shape. Too frequent → bank exhaustion + result
variability obscures trend; the headline NCLC becomes noise around the
underlying signal.

We cap mocks at:

- **Week 0–6**: 1 mock per ISO week.
- **Week 7–10**: 2 mocks per ISO week.
- **Week 11–12 (final fortnight)**: 3 mocks per ISO week.

ADR-033 records this. The cap is *enforced* — `POST /v1/mock-exam/start`
returns 409 with `next_action="cooldown"` if the rate is exceeded.

A cooldown override exists for the operator (logged for audit) so a
learner who is sitting the real exam tomorrow can still take one more
diagnostic mock.

### 1.5 What the mock reports — and to whom

Three audiences:

1. **The learner** — per-skill score with credible interval, NCLC
   band, traffic-light readiness, top-3 weak patterns per skill, and
   an *actionable* next-week recommendation that follows from the
   weak patterns (not platitudes).
2. **The planner** — a refreshed posterior for each skill. The planner
   re-allocates the next 7 days of minutes off of this, with the
   constraint that drill-posterior and mock-posterior differ by ≤ 1
   NCLC.
3. **The audit log** — full item-by-item record (item id, response,
   time taken, correctness, IRT difficulty) for later review and for
   the nightly IRT recalibration job to consume.

The booking advice is the most consequential output. The rule:

- 🟢 sustained for **2 consecutive canonical** mocks
  → "booking your exam is reasonable in 2–4 weeks."
- 🟡 → "schedule another canonical mock in 7 days; do not book."
- 🔴 → "do not book; complete the bottleneck plan first."

A single 🟢 mock is *never* booking advice. This is the hardest
discipline of the whole system and the most tempting to relax — the
guardrail is encoded in the report renderer and reinforced by Phase 4's
readiness gate (R-004, already implemented and tested).

---

## 2. The hardest engineering sub-problem

### 2.1 Cross-module timing with persistence

A learner mid-mock can lose internet, close the browser, or have the
laptop sleep. There are two principled answers:

- **Forfeit on abnormal exit.** Brutal but matches the real exam.
- **Allow resumption.** Forgiving but easy to game ("I had a glitch,
  let me reset the timer and re-read CE 17").

We split the choice:

- **Canonical mode** (default): forfeits on any abnormal exit
  (browser close, tab visibility loss > 5 s, process crash on the
  server). Forfeited mocks **do not update the NCLC posterior** but
  *are* journaled, so audit can detect "this learner forfeits 40% of
  starts" — that pattern itself signals exam anxiety, which is
  prep-worthy.

- **Training mode** (opt-in): pause/resume within 24 h. The resulting
  score is flagged `mode=training` and **does not update the NCLC
  posterior**, but it *is* shown in the trajectory chart (with a
  visual marker so the learner sees the distinction).

The planner *forces* a canonical mock at least once every 14 days
during weeks 4+. Two consecutive training-only mocks during that
window block the readiness 🟢.

ADR-032 records the canonical-vs-training distinction.

### 2.2 Where state lives

- Live state (current module, timer, current item) lives in **Redis**
  in production; in-process dict in the Phase 6 stub (same as the
  practice-session pattern from Phase 5).
- Every state transition writes a **Postgres journal row** so a
  forensics replay can reconstruct exactly when the learner advanced.
  Phase 9 wires the real Postgres; Phase 6 ships an in-process
  audit-list with the same shape.

Resumption (training mode) reads the last journaled state, replays
the deterministic "where am I" computation, and restores. There is
no "let me move the cursor back" affordance.

### 2.3 The leak-prevention discipline

Two failure modes are catastrophic:

1. **Correct answer leaks via the API.** If `GET /v1/mock-exam/{id}/state`
   ever includes a field that lets the client deduce the correct
   answer before the learner submits, the entire exercise is void.
   This is enforced both by a redaction layer (the response model
   does not include item content's correct-answer fields) and by an
   audit test that walks the response body and asserts no
   `correct_option_id` substring appears anywhere.

2. **Re-trigger of CO audio.** The audio plays exactly once per item
   per session. The server tracks the play; the client cannot ask for
   a second play.

The pattern: anything that *can* be checked server-side *must* be
checked server-side. The client is an untrusted renderer.

---

## 3. Scoring discipline

### 3.1 CO / CE

Deterministic. Count correct → raw → IRT-derived NCLC posterior with
CI via the same Bayesian Laplace machinery the drill estimator uses
(`tcf_accel_sla.estimator.nclc`). The IRT difficulty per item is the
calibrated `difficulty_irt` from the bank.

### 3.2 EE / EO

Phase 7 owns the actual rubric scorer; Phase 6 delegates. For the
hand-off contract: the mock submission triggers
`tcf_accel.score_ee` / `tcf_accel.score_eo` celery tasks, which
produce `WritingRubric` / `SpeakingRubric` (Phase 7 contract).
Aggregation across the 3 tasks of each module is the **mean** of the
three task totals, mapped through `_rubric_score_to_nclc`.

The mock-posterior update folds in one observation per item (39 + 39
MCQs + 3 + 3 rubrics → 84 evidence points per canonical mock).

### 3.3 Confidence gate

A mock NCLC point estimate is never shown when the underlying
posterior has `confident=False`. The headline degrades to "insufficient
evidence; finish another mock to unlock a band". This applies even when
all CO/CE evidence is in — if EE/EO has too few rubric points, the
overall NCLC is suppressed and the per-skill bands are shown
individually.

### 3.4 Drill ↔ mock divergence alert

Compute `Δ = |drill_posterior.mean - mock_posterior.mean|` per skill.
If `Δ ≥ 2.0` for any skill, the mock report shows a banner:

> "Your mock CO score (NCLC 5) is more than 2 bands below your drill
> CO score (NCLC 8). This usually means drill overfitting or test
> anxiety. Talk to your tutor or schedule a training-mode mock."

The alert is also emitted to the audit log so the operator can spot
systemic divergence (often the bank is the problem, not the learner).

ADR-034 records the alert threshold.

---

## 4. What the player UI must enforce (specified here, built in Phase 8)

- Fullscreen mode (CSS + JS).
- Tab-visibility tracking → > 5 s blur = forfeit in canonical mode.
- Per-module countdown only (no overall countdown — too anxiety-
  producing per the empirical UX research the master prompt cites).
- Flag-and-revisit scoped to the current module only.
- Single CO audio play, server-tracked.
- "Submit" is irreversible.
- "Exit" must require a typed confirmation in canonical mode.

Phase 6 ships these as documented **server-side invariants** so Phase
8's UI implementation simply respects them.

---

## 5. Selector: constraint satisfaction, not optimization

### 5.1 The constraints recap

For a canonical mock per module:

| Module | Count | Difficulty mix | Genre/accent quotas | Task split |
|--------|-------|----------------|---------------------|------------|
| CO     | 39    | A1..C2 spread  | accent matrix       | n/a        |
| CE     | 39    | A1..C2 spread  | genre matrix        | n/a        |
| EE     | 3     | one per CEFR band | n/a              | tasks 1/2/3 |
| EO     | 3     | one per CEFR band | n/a              | tasks 1/2/3 |

Plus across all modules:

- No item seen by user in past 30 days.
- ≥ 20% never seen by user.
- Topic-cluster cap (no cluster > 8% of any module's items).

### 5.2 Why not OR-Tools after all

The design originally specified OR-Tools MIP. We considered it and
chose against:

- **Deps weight**: OR-Tools is ~80 MB of native binaries; pulling it
  in for a single solver call is disproportionate.
- **Determinism risk**: OR-Tools' MIP solver has non-deterministic
  tie-breaking under default settings; pinning seeds works but is
  fragile across versions.
- **Problem size**: ~84 items out of low-thousands. A constraint-
  guided randomized greedy converges in < 50 ms in practice and is
  easy to audit by reading the code.

ADR-035 records the OR-Tools rejection and the greedy alternative.

### 5.3 The greedy algorithm

For each module:

1. Filter the bank to items satisfying the recency + retired + quality
   filters.
2. Bucket the remaining items by (CEFR, genre/accent, task-number-for-
   EE/EO).
3. Draw the required count per bucket. The buckets' target counts are
   computed from the FEI difficulty spread (`mock_exam.spec.FEI_SPREAD`).
4. If a bucket cannot be filled (rare for a fresh bank, common after
   many mocks), back off to "filled by adjacent bucket" with a logged
   warning. The audit catches systemic backoff.
5. After all buckets are filled, sort within-module by ascending
   difficulty.

The randomization seed is the user_id + the ISO-week-of-start, so
running the same selector twice in the same week for the same user
returns the same items — which is correct because a duplicate-start
inside the cooldown returns the existing mock id, not a new one.

### 5.4 Selector diversity (the audit-criteria)

Over 100 mocks for the same user (simulated, the user never sees the
results) the union of selected items must cover ≥ 60% of the bank.
This guards against the failure mode where the selector concentrates
on a small "favorite" subset — typical for poorly-randomized greedy
algorithms.

The audit step runs this metric and fails the build if it dips.

---

## 6. The scripted candidate

We need a way to take a full 2h47 mock end-to-end *without a human*.
This is the load-bearing integration test of the whole phase. The
scripted candidate:

- Accepts a *reliability profile* (probability of answering CO/CE
  correctly per CEFR band, target rubric distribution for EE/EO).
- Walks the state machine: start → CO items → break → CE → break →
  EE → break → EO → submit.
- Samples timing per item from a configured distribution so the total
  is `2h47:00 ± 30s`.
- Asserts at each step that the API response is well-formed and that
  no correct-answer field leaks.

Used both as a phase test and as the audit-step driver.

---

## 7. ADR slate

- **ADR-032** Canonical vs training mode for mocks; canonical forfeits
  on abnormal exit and is the only mode that updates the posterior.
- **ADR-033** Mock cadence cap (1/w → 2/w → 3/w over weeks 0..12+).
- **ADR-034** Drill posterior and mock posterior are tracked
  separately; divergence > 2 NCLC triggers an alert.
- **ADR-035** Selector implementation is constraint-guided greedy with
  seeded RNG, *not* OR-Tools MIP.

---

## 8. Risks we are accepting

- **R-1**: Forfeit-on-tab-loss may anger a learner whose laptop lost
  focus to a system notification. Mitigated by training mode and by
  the visible 5-second grace window the player will display.
- **R-2**: The mock bank's IRT calibration drifts away from the drill
  bank because the mock items are seen far less often. ADR-034's
  divergence alert flags this; the nightly IRT job can re-fit a
  combined corpus.
- **R-3**: Operator-side audit log grows fast (one row per item per
  mock; an active user could generate ~250 rows/week). Mitigated by
  the 90-day retention rule that the housekeeper already enforces for
  the dismissal log (Phase 5).

---

## 9. What changes for Phase 7 and Phase 8

- **Phase 7** wires the real EE/EO rubric scorers in via the existing
  Phase 5 `register_scorer` hand-off contract. Phase 6 simply consumes
  whatever Phase 7 registers; the Phase 5 stub continues to work for
  Phase 6 CI.
- **Phase 8** builds the player UI to the server invariants listed in
  §4. Phase 6 emits the necessary timing/state fields on
  `GET /v1/mock-exam/{id}/state` so the UI has nothing to invent.

The hand-off is clean. Phase 6 does not block on either.
