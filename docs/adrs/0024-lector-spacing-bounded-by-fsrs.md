# ADR-0024: LECTOR semantic-spacing penalty bounded so as not to overrule FSRS

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 4 (Learner Model)

## Context

LECTOR (arxiv 2508.03275, 2025) addresses a FSRS failure mode: when two
items are *semantically confusable* (high cosine similarity in the
content embedding space), interleaving them in the same review session
creates interference that erodes the retention gains FSRS otherwise
produces. The canonical French example is `amener` vs `emmener`:
FSRS, ignorant of semantics, may schedule both for the same day; LECTOR
proposes shifting one forward to maximize aggregate semantic distance.

The trade-off: every day LECTOR delays an item from FSRS's recommended
due-date is a day the retention probability `R(t, S)` falls below the
desired-retention target. FSRS's correctness guarantees are predicated
on the scheduler *not* delaying items past `R = 0.90` (or whatever
target the item's policy carries).

Master prompt §2.1.3 commits to FSRS-6 retention; we must not break
that contract to optimize for a *separate* interference effect.

## Decision

LECTOR runs **after** FSRS in the queue-building pipeline, and is
**hard-capped** at `MAX_LECTOR_DELAY_DAYS = 2`:

- LECTOR never delays an item by more than 2 days past FSRS's due-date.
- LECTOR only fires for item pairs with cosine similarity ≥
  `SIMILARITY_THRESHOLD = 0.75` (the empirical knee in the similarity
  distribution from the Phase 3 `confusable_pairs` table).
- The penalty curve is quadratic above the threshold:
  `delay_days = ((sim - 0.75) / 0.25)² · 2` so that mid-similarity
  pairs are mildly penalized and only the truly confusable pairs hit
  the 2-day cap.

## Consequences

- **Positive**:
  - FSRS retention guarantees stay within tolerance — the 2-day cap
    bounds the retention drop at ≤ 3% for typical stability values.
  - The "confusable interference" failure mode is mitigated for the
    items where it matters most (cosine ≥ 0.9).
  - The implementation is order-stable + idempotent (running LECTOR
    twice on its own output yields the same ordering), which the
    `test_lector_invariants` property test verifies.
- **Negative**:
  - LECTOR is *advisory*, not corrective: a queue with 10+ near-
    duplicate items will see only some of them shifted. Mitigated by
    the Phase 3 `confusable_pairs` table flagging the worst offenders
    for content review (we'd rather retire one of a near-duplicate
    pair than schedule around it).
- **Neutral**:
  - Items without embeddings (legacy data) bypass LECTOR entirely;
    they're treated as not-confusable-with-anything.

## Alternatives considered

- **Run LECTOR before FSRS** (let semantics dictate the queue, then
  let FSRS pick due-dates): rejected because LECTOR doesn't know about
  retention; it would happily schedule a confusable pair 30 days apart
  even when both are due today.
- **Uncapped LECTOR penalty**: rejected because a single high-similarity
  pair could indefinitely defer items, breaking FSRS's retention
  guarantee.
- **Linear penalty curve**: rejected because linear under-penalizes
  high-similarity pairs (where confusability actually matters) and
  over-penalizes the long tail of weakly-similar pairs.

## What would change our mind

- The Phase 4 synthetic-cohort audit shows LECTOR-shifted schedules
  produce *worse* retention than the FSRS baseline (i.e., the cap is
  not protecting retention as intended). We'd drop LECTOR entirely.
- A published study shows the optimal similarity threshold is not
  0.75 → re-tune the constant.

## References

- LECTOR paper: arxiv 2508.03275 (2025).
- ADR-0006 (FSRS-6 as the scheduler — the algorithm LECTOR defers to).
- `packages/sla/src/tcf_accel_sla/scheduler/lector.py`.
- `04_LEARNER_MODEL.md §2.2`.
