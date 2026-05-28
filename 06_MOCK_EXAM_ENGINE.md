# PHASE 6 — Mock Exam Engine (Full 2h47 Simulator)

> Goal: a high-fidelity simulator that reproduces the TCF Canada exam day. The single most important non-drill output of the system: this is what tells a learner "you are ready" (or not).

---

## 1. THINK (produce `phase6_think.md`)

### 1.1 What "Realistic" Means Here

The mock must reproduce the *psychological* exam day, not just the content. That means:

- **Strict timing.** 35 min CO, 60 min CE, 60 min EE, 12 min EO, with the published inter-module break structure. No pausing without forfeiting the result.
- **No mid-test feedback.** Learner gets no scores until the end. The temptation to show "you got that right!" during the test must be resisted; doing so trains the wrong response.
- **No replay.** CO audio plays once. CE passages are scrollable but cannot be flagged-and-returned in adaptive mode (only in non-adaptive). Mirror the official UI behavior.
- **Sequenced difficulty.** Per FEI's "progressive difficulty" principle, items are sequenced from easier to harder within each module.
- **Proctor mode.** Optional webcam-on, focus-locked, full-screen mode that approximates an in-centre test feel. We don't actually proctor; we simulate the constraint.

### 1.2 Item Sampling for a Single Mock

The bank has thousands of items per module. A mock must:

- Match the official **39 CO + 39 CE + 3 EE + 3 EO** shape exactly.
- Cover the full A1–C2 difficulty distribution per FEI, *not* the learner's current level (that's what drills do).
- Avoid items the learner has seen in the past 30 days (prevents recall confounding the test).
- Span genres, accents, registers per the quota matrix.
- Pull at least 20% of CO/CE items the learner has *never* seen, to ensure novelty.

### 1.3 The Multiple-Mock Tradeoff

Frequent mocks → testing-effect benefit. Too frequent → bank exhaustion + result variability obscures trends. Compromise: cap at 1 mock/week up to week 6, then 2/week weeks 7–10, then 3/week final fortnight (per the master prompt §2.1.8). The system enforces this by refusing to start a mock if the cooldown is active (override available but logged).

### 1.4 What the Mock Reports

Three audiences for the report:

1. **Learner**: per-skill score with CI, NCLC band, traffic-light readiness, top 3 weak patterns per skill, actionable next-week recommendation.
2. **Planner**: refreshed posterior for each skill, drives re-allocation.
3. **Audit log**: full item-by-item record for later review and for IRT recalibration.

### 1.5 The Hardest Engineering Sub-Problem

Cross-module timing with persistence. A learner mid-mock could lose internet, close the browser, or have the laptop sleep. Either we (a) forfeit the session, which is brutal, or (b) allow resumption, which can be gamed. Compromise:

- Default: session must complete in one sitting; closing the browser = forfeit. Like the real exam.
- Opt-in "training mode": pause-and-resume within 24h is allowed, but the resulting score is flagged "non-canonical" and does not update the NCLC posterior.

Both modes exist; the planner forces a "canonical" mock at least monthly.

---

## 2. DESIGN (produce `phase6_design.md`)

### 2.1 Session State Machine

```
SCHEDULED ─▶ STARTED
              │
              ├─▶ CO_ACTIVE (35:00 countdown) ─▶ CO_DONE
              │                                     │
              │                                     ▼
              │                              BREAK_1 (5:00)
              │                                     │
              │                                     ▼
              │                              CE_ACTIVE (60:00)
              │                                     │
              │                                     ▼
              │                              BREAK_2 (5:00)
              │                                     │
              │                                     ▼
              │                              EE_ACTIVE (60:00)
              │                                     │
              │                                     ▼
              │                              BREAK_3 (15:00)
              │                                     │
              │                                     ▼
              │                              EO_ACTIVE (12:00) ─▶ FINISHED ─▶ SCORED
              │
              └─▶ FORFEITED (any abnormal exit in canonical mode)
```

Every transition is timestamped and audited. State lives in Redis with a Postgres journal.

### 2.2 Item Selector

```python
# packages/sla/src/mock_exam/selector.py
def select_mock_items(user: User, module: Module, bank: ItemBank) -> list[Item]:
    """
    Selects N items for a mock of `module`.
    Constraints:
      - Quantity matches FEI: CO=39, CE=39, EE=3, EO=3
      - Difficulty distribution matches FEI: rough mix from A1 to C2
      - No item seen by user in past 30 days
      - ≥20% never seen by user
      - Genre/accent/register quotas respected
      - Topic-cluster cap (no cluster > 8% of mock; tighter than the bank-level cap)
      - For EE: exactly one each of Task 1, 2, 3
      - For EO: exactly one each of Task 1, 2, 3
    Implementation: constraint satisfaction via mixed-integer programming
    (small problem, OR-Tools handles it in <1s).
    """
    ...
```

### 2.3 The Player

The player UI (Phase 8 implements fully) enforces:

- Full-screen mode (CSS).
- Browser-tab visibility tracking → if the tab loses focus for >5 s in canonical mode, the session is FORFEITED (matching the real centre's strict no-distraction policy).
- A visible per-module countdown; no overall countdown (too anxiety-producing).
- A flag-and-revisit feature, scoped to the current module only.
- Single CO audio play tracked server-side; client cannot re-trigger.

### 2.4 The Scorer (delegates to Phase 7 for EE/EO)

- CO/CE: deterministic; count correct → raw → IRT-derived NCLC score with CI.
- EE: each of 3 tasks → SpeakingRubric/WritingRubric from Phase 7 → aggregate to 0–20.
- EO: same.
- Per-skill posterior update (Phase 4 estimator) using the mock's items.

The mock's NCLC estimate is a *separate* posterior from the long-running drill posterior. Both are reported. They should agree within ~1 NCLC band; if they diverge by ≥ 2 NCLC, the system flags this for review (likely either: drill-overfitting, or a mock item bank that doesn't match the drill bank's difficulty).

### 2.5 The Mock Report

Markdown + interactive HTML. Sections:

1. **Headline**: per-skill NCLC ± CI; minimum skill (bottleneck); traffic light.
2. **Module breakdown**: question-by-question with timing, correctness, item difficulty, weak patterns.
3. **EE report**: per-task rubric scores + annotated text + 3 model improvements per task.
4. **EO report**: per-task rubric + transcript + spectrogram + a "next-step" pronunciation drill recommendation.
5. **Trajectory**: how this mock compares to the user's history; trend line with the long-running posterior overlay.
6. **Actionable plan**: top 3 things to do this week (the planner's output, filtered to what mock revealed).
7. **Booking advice**: if 🟢 sustained for 2 mocks → "booking your exam is reasonable in 2–4 weeks." If 🟡 → "schedule another mock in 7 days; book the exam only after 2 consecutive 🟢."

### 2.6 Anti-Cheat / Honesty Features

- Recordings of EO sit only on the user's device unless `cloud_optin=true`.
- No "improve my score" toggle that would inflate results.
- The system *never* shows a score the estimator marked `confident=False`.

### 2.7 ADRs

- ADR-032: Canonical vs training mode for mocks; canonical forfeits on abnormal exit.
- ADR-033: Mock cadence cap (1/w → 2/w → 3/w over 12 weeks).
- ADR-034: Drill posterior and mock posterior are tracked separately; divergence > 2 NCLC triggers an alert.
- ADR-035: OR-Tools for item selection.

---

## 3. CODE

- `packages/sla/src/mock_exam/selector.py` (OR-Tools-based).
- `packages/sla/src/mock_exam/state.py` (state machine).
- `apps/api/routes/mock_exam.py`.
- `apps/worker/tasks/score_mock.py`.
- `packages/sla/src/mock_exam/report.py` (Markdown+HTML renderer).
- A "scripted candidate" agent that takes a full mock end-to-end with realistic timing distributions — used as an integration test.

---

## 4. AUDIT (produce `phase6_audit.md`)

- **Shape conformance:** generated mocks match FEI's structure exactly (39/39/3/3, durations, breaks).
- **Selector diversity:** over 100 generated mocks for the same user, the union of items covers ≥ 60% of the bank (no over-concentration on a few "favorite" items).
- **Timing fidelity:** the scripted candidate completes a full mock in 2:47:00 ± 30 s with realistic timing variability.
- **State persistence:** killing the API mid-mock + restarting + resuming returns the session to the correct module/timer state.
- **Score consistency:** a candidate that answers correctly with reliability p produces a posterior mean within ±0.5 NCLC of `expected_nclc(p)` over 50 runs.
- **No-leak audit:** the response body of `/v1/mock-exam/{id}/state` while the mock is ACTIVE never contains correct-answer fields.
- **Forfeit behavior:** simulated browser-tab loss → session FORFEITED, no scoring, learner sees a clear message.

---

## 5. EVALUATE (produce `phase6_evaluate.md`)

Acceptance criteria:

- ✅ All audit metrics pass.
- ✅ Scripted candidate produces a valid mock report end-to-end.
- ✅ Mock report contains all 7 sections from §2.5.
- ✅ Booking advice never escalates to "ready" without ≥ 2 consecutive 🟢 canonical mocks.
- ✅ ADRs ADR-032 through ADR-035 accepted.

Anti-criteria:

- ❌ Any way for the client to extract the correct answer before submitting.
- ❌ Any mock that completes without writing to `mock_exams` + `interactions`.
- ❌ A booking-advice path that says "ready" with one 🟢 mock.
- ❌ A mock in canonical mode that allows pausing.

Hand-off: a sample mock report (PDF or HTML) for a synthetic candidate, illustrating each report section.
