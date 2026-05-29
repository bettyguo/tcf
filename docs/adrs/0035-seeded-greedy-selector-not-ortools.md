# ADR-0035: Mock-exam item selector — seeded greedy, not OR-Tools MIP

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 6 (Mock Exam Engine)

## Context

The mock-exam item selector must pick exactly **39 CO + 39 CE + 3 EE
+ 3 EO** items from a bank of low-thousands, subject to a constraint
set documented in `06_MOCK_EXAM_ENGINE.md §1.2`,
`phase6_think.md §5.1`, and `phase6_design.md §5.1`:

- Quantity per module.
- FEI difficulty distribution per CEFR band.
- No item the learner has seen in the past 30 days.
- ≥ 20% never seen by the learner.
- Genre / accent / register / topic-cluster caps.
- For EE/EO: exactly one each of task numbers 1, 2, 3.

`06_MOCK_EXAM_ENGINE.md §2.2` proposed implementing this as a
constraint-satisfaction problem via OR-Tools' CP-SAT solver.

Choices reconsidered during the design pass:

- (a) OR-Tools CP-SAT (the spec's default).
- (b) Pulp-style ILP via a pure-Python solver.
- (c) Constraint-guided greedy with a seeded RNG, plus a backoff
  warning when buckets cannot be filled.

## Decision

**(c) Constraint-guided greedy with a seeded RNG.**

Algorithm shape (full code in
`packages/sla/src/tcf_accel_sla/mock_exam/selector.py`):

1. Hard-filter the bank (drop recent + retired + low-quality).
2. Bucket by CEFR (CO/CE) or task_number (EE/EO); compute target
   bucket counts from `FEI_SPREAD` using largest-remainder rounding
   so bucket targets sum to the module total exactly.
3. **Novelty phase**: pull `≥ NEVER_SEEN_FRACTION × N` items from
   the never-seen pool first, spread across buckets so a single
   bucket doesn't exhaust its quota on novelty alone.
4. **Bucket-fill phase**: for each bucket short of its target,
   shuffle the remaining candidates (seeded by `(user_id, iso_week,
   module)`) and take from the front.
5. **Backoff phase**: if any bucket couldn't be filled (bank
   exhausted for that band), draw from any remaining and emit a
   `backoff_fill` warning. The audit catches systemic backoff.
6. **Topic-cap phase**: through the whole selection, reject any
   candidate that would push a topic_cluster_id over the per-module
   cap (`TOPIC_CLUSTER_CAP_FRACTION = 0.08`). Last-resort relax with
   a `topic_cap_override` warning.
7. **FEI ordering**: sort the result ascending by IRT difficulty.

The seed is computed deterministically from `(user_id, iso_week,
module)`. Two calls in the same week for the same user return
identical lists — which is the correct behavior because a duplicate
`/v1/mock-exam/start` returns the existing mock id (cadence cap).

## Why we rejected OR-Tools

The think doc (`phase6_think.md §5.2`) summarizes the reasons we
considered OR-Tools and chose against:

- **Dependency weight**: OR-Tools is ~80 MB of native binaries for
  what is, in our problem size, a 50 ms greedy. The deploy story
  (Phase 9 cross-platform single-host operator install) cannot
  afford the extra wheel size.
- **Determinism risk**: OR-Tools' CP-SAT has non-deterministic
  tie-breaking by default. Pinning seeds works but is fragile
  across versions; we'd need a version pin and a per-version smoke
  test. The greedy is deterministic by construction.
- **Problem size**: 84 items out of a few thousand. A constraint-
  guided greedy converges in < 50 ms in practice; OR-Tools' setup
  cost alone is in the same order.
- **Auditability**: a code reviewer can read the greedy in 60
  seconds and reason about correctness. They cannot read an
  OR-Tools model.

The diversity audit
(`packages/sla/tests/test_mock_selector.py::test_diversity_across_100_simulated_weeks_covers_majority_of_bank`)
asserts that over 100 simulated weeks the union of selected items
covers ≥ 60% of the bank. The greedy passes this; OR-Tools would
satisfy it too, but at no functional advantage.

## Consequences

- **Positive**:
  - No native dependency. Single-host operator install stays
    Python-only.
  - Determinism is free. Tests don't need to seed an external solver.
  - The selector is < 200 lines and reviewable in one pass.
- **Negative**:
  - Greedy can in principle leave a bucket undersubscribed when
    the bank has constraints OR-Tools could resolve globally. We
    surface this with a `backoff_fill` warning; the audit catches
    systemic warnings. Empirically, on the Phase 6 fixture bank
    (240 CO + 240 CE + 36 EE + 36 EO), zero warnings across 100
    simulated weeks.
- **Neutral**:
  - The 0.08 topic-cluster cap is tighter than the bank-level
    ADR-0022 cap (~0.12); reasonable because a single mock is a
    much smaller draw and topic concentration would hurt.

## Alternatives considered

- See Context (a)(b).
- **Simulated annealing**: rejected — more complex, no observed
  benefit for this problem size.
- **Pure-random sampling with rejection on constraint violation**:
  rejected — convergence depends on bank composition, and the
  backoff path is harder to reason about.

## What would change our mind

- The audit's diversity coverage drops below 60% in production
  (real banks, real user histories). We'd revisit whether the
  greedy is concentrating on a subset and either:
  - tune the bucket-fill randomization, or
  - swap to OR-Tools with the determinism tradeoff explicitly
    accepted.
- The selector starts emitting `backoff_fill` warnings on > 5% of
  selections in operator review. That's bank-side: we'd raise the
  bank fill targets per cell rather than swap the algorithm.

## References

- `06_MOCK_EXAM_ENGINE.md §2.2` (original OR-Tools proposal).
- `phase6_think.md §5`, `phase6_design.md §5`.
- `packages/sla/src/tcf_accel_sla/mock_exam/selector.py`.
- `packages/sla/tests/test_mock_selector.py`.
- ADR-0022 — bank-level topic cap (this ADR tightens for mocks).
