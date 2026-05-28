# ADR-0006: FSRS-6 as the spaced-repetition algorithm

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 1 (elaborated in Phase 4 as ADR-023, ADR-024)

## Context

Spaced repetition is one of the most evidence-supported SLA principles (master prompt §2.1.3). The algorithm choice determines retention quality, learner-experience smoothness, and the system's ability to claim evidence-aligned pedagogy.

Candidate algorithms:
- SM-2 (Anki's original; published 1985)
- SM-15 / SM-17 (SuperMemo's proprietary lineage)
- FSRS-4 / FSRS-5 / FSRS-6 (Free Spaced Repetition Scheduler; the active open-source line)

Master prompt §2.1.3 names "FSRS-6 (Free Spaced Repetition Scheduler v6, three-component DSR model)" with `R = 0.90` default desired retention for high-yield items.

## Decision

FSRS-6, via the reference Python package from `open-spaced-repetition`. Default parameters at v1; per-user optimization runs nightly once a user has ≥ 100 reviews (Phase 4 ADR-023).

Desired retention `R = 0.90` for high-yield items (top-tier vocabulary, grammar patterns explicitly tested on TCF), `R = 0.85` for long-tail items. The retention threshold is a per-item attribute set by the content pipeline (Phase 3).

## Consequences

- **Positive**:
  - FSRS-6 outperforms SM-2 in workload-adjusted retention by ~15–25% on published benchmarks; this directly improves the bottleneck-skill outcomes our learners care about.
  - Open-source reference implementation under MIT; no IP concerns for redistribution.
  - Per-user parameter optimization is built into the package; we get an adaptive scheduler with minimal code.
- **Negative**:
  - More compute than SM-2 (matrix math vs constant-time updates). Negligible at our review volumes.
  - More configuration surface for contributors to learn.
- **Neutral**:
  - We do not implement our own variant; we wrap the reference package behind `packages/sla/src/tcf_accel_sla/scheduler/fsrs.py` so we can swap implementations without touching callers.

## Alternatives considered

- **SM-2**: rejected because the 15–25% retention-per-review-minute gap matters when our budget is 210 hours total. *Would reconsider*: if FSRS-6 ships a regression we can't pin past.
- **SM-15+**: rejected because the algorithm is proprietary; using a black-box scheduler contradicts master prompt §6 (rigor and honesty).
- **A bespoke neural scheduler (e.g., DKT, SAKT)**: rejected because we have no training data at v1; sourcing it would push Phase 4 by months. *Would reconsider*: at > 10k users and a clean signal that FSRS-6 limits us.

## What would change our mind

- A published reproducible study showing FSRS-6 underperforms a permissively-licensed alternative on a comparable workload.
- A breaking change to the `fsrs` package that costs more to absorb than to migrate.

## References

- [open-spaced-repetition/free-spaced-repetition-scheduler](https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler)
- LECTOR paper (arxiv 2508.03275) — drives ADR-024 separately.
- Master prompt §2.1.3, Phase 4 ADR-023 / ADR-024.
