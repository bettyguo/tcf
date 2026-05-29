# ADR-0033: Mock-exam cadence cap (1/w → 2/w → 3/w)

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 6 (Mock Exam Engine)

## Context

Mock exams are the most expensive evaluation unit in the system: each
canonical mock is 2h47 of active test time, consumes ~84 items the
learner should not see again for 30 days, and yields one posterior
update. The system would *like* learners to take many mocks (testing
effect; habituation to exam-day shape); the system *cannot afford* for
learners to take many mocks (bank exhaustion; the headline NCLC
becomes noise around the underlying signal as items recycle).

`06_MOCK_EXAM_ENGINE.md §1.3` proposes a ramp: 1/w early, 2/w
mid-program, 3/w in the final fortnight. The think doc
(`phase6_think.md §1.4`) endorses this and adds the engineering note
that the *first canonical mock* defines the week-0 epoch — not the
calendar week the learner joined.

The choices considered:

- (a) No cap. Bank exhausts; mock score variance dominates signal.
- (b) Hard 1/w cap throughout. Wastes the final-fortnight testing-
  effect peak; final-week learners specifically benefit from
  repeated exposure.
- (c) Three-stage ramp tied to since-first-mock week index.
- (d) Three-stage ramp tied to calendar week. Rejected because a
  learner who joins mid-week and immediately sits a mock would have
  the cap reset two days later.

## Decision

**(c) Three-stage ramp tied to since-first-mock week index.**

Implemented as:

```python
MOCK_CADENCE_TABLE = (
    (0, 5, 1),     # weeks 0..5 → 1/w
    (6, 9, 2),     # weeks 6..9 → 2/w
    (10, 999, 3), # weeks 10+  → 3/w
)
```

with:

- **Week-index counting starts at the first *canonical* mock**, not
  the first user action. A user who joins on day 1 but doesn't sit a
  mock until day 30 starts their cadence ladder on day 30.
- **The ISO-week** is the cap unit (a learner can sit one mock
  Mon–Sun, not "one mock in any 168-hour rolling window"). Matches
  how the rest of the system reasons about cadence.
- **Forfeited mocks do not count against the cap** (`MockExamSummary.forfeited=True` is excluded from the count).
- **Training mocks have a separate cap of `TRAINING_PER_DAY_CAP=1`**
  (per ADR-0032).
- **A `force=true` override is accepted** and logged at WARN; the
  `audit-mocks` runbook flags ≥ 3 overrides in any rolling week as
  a chronic pattern.

The route emits `E_MOCK_001` with `http_status=409` and a `reason`
field carrying the human-readable cap math; the wire envelope is
documented in `phase6_design.md §10.2`.

## Consequences

- **Positive**:
  - Bank exhaustion is bounded: a typical 12-week user sits at most
    `6×1 + 4×2 + 2×3 = 20` canonical mocks, consuming ~1680 items
    (well under the bank's working set).
  - Final-fortnight testing-effect peak is preserved.
  - The cap is *deterministic* — the same history always returns
    the same allowed/denied; audit can replay decisions.
- **Negative**:
  - A learner whose first mock was a forfeited canonical still
    starts the ladder from that timestamp. (Edge case; we accept it
    because the alternative — first-non-forfeited-canonical — is
    forensically harder.)
- **Neutral**:
  - The 1/2/3 numbers come from pedagogical intuition (testing-effect
    studies + the master prompt §2.1.8 reference), not from
    measurement on this specific cohort. We expect to re-fit once
    we have 100+ learner-weeks of data.

## Alternatives considered

- See Context (a)(b)(d).
- **Adaptive cadence based on score trajectory**: tempting (a
  learner converging at 🟢 might benefit from more frequent mocks);
  rejected for v1 because adaptive rules are hard to communicate to
  the learner and erode trust ("why can't I take it again?").

## What would change our mind

- Two consecutive cohorts hit bank-exhaustion warnings (the
  selector's `backoff_fill` warning) before week 10. We'd lower the
  weeks-7–9 cap from 2/w to 1/w + raise the bank's CO/CE size.
- A pedagogical study shows the testing-effect peak is at 5/w not
  3/w for the final fortnight. We'd raise the table.
- Operator audit shows ≥ 50% of users override the cap weekly. The
  cap has lost its meaning; we'd either tighten the override or
  remove the cap and rely on the bank-exhaustion gate alone.

## References

- `06_MOCK_EXAM_ENGINE.md §1.3`, master prompt §2.1.8.
- `phase6_think.md §1.4`, `phase6_design.md §4`.
- `packages/sla/src/tcf_accel_sla/mock_exam/cadence.py`.
- `packages/sla/tests/test_mock_cadence.py`.
- ADR-0032 — canonical vs training distinction.
