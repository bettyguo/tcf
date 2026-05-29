# ADR-0012: Pre-computed schedule cache (Redis) with explicit invalidation; no on-demand compute on the request path

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, ML lead, Backend lead
- **Phase**: 2

## Context

The scheduler (FSRS-6 per ADR-0006) and the planner (per-skill posterior +
study-plan regenerator, Phase 4) are *bursty*: at the end of a 30-minute
session, ~50 cards get re-rated, the per-skill posterior moves, and the
study plan may need regeneration. A naive request-bound implementation
would block `POST /v1/session/{id}/finish` for several hundred
milliseconds at a moment when the user is staring at a "submitting…"
spinner.

Three topologies were considered (`phase2_think.md §1.1`):

1. In-process scheduler inside `apps/api` — simplest, but couples API
   health to scheduler perf.
2. Dedicated `sla-service` consumed via gRPC — clean isolation, but
   adds a deploy unit and a hop.
3. API consumes pre-computed schedules from a cache; Celery workers
   compute on `session.finished` events — decouples bursty compute
   from the request path, at the cost of cache invalidation complexity.

Master prompt §3 names "Celery + Redis 7 (queue + cache)" — ADR-0005
provisioned both in Phase 1; this ADR is about *how to use them*.

## Decision

The API never computes a schedule on the request path. Schedules and
per-skill posteriors are pre-computed by Celery workers in
`apps/worker` and read from:

- **Postgres** for the durable state: `skill_estimates`, `study_plans`,
  `interactions` (the source of truth).
- **Redis** for the hot cache: the next-N-items queue per (user, module),
  keyed `sched:queue:{user_id}:{module}` with a JSON-list payload and
  a `sched:version:{user_id}:{module}` integer that bumps on every
  invalidation.

Invalidation is **explicit, not TTL-driven**:

- `POST /v1/session/{id}/answer` enqueues a "delta" event; the worker
  rebuilds the queue if the FSRS rating changes the next-due time of
  the head card.
- `POST /v1/session/{id}/finish` enqueues a "session_finished" event;
  the worker rebuilds the queue + recomputes the per-skill posterior +
  decides whether to regenerate the study plan (threshold: posterior
  delta > 0.5 NCLC bands).
- TTL is a **safety net** (24 h), not the contract.

The version key (`sched:version:{user_id}:{module}`) is the only
linearization point: the API reads the version + queue atomically (via
a Lua script), and the worker writes the version + queue atomically.
Clients that read a stale version retry once or fall back to a
synchronous compute.

## Consequences

- **Positive**:
  - API p95 on `/session/finish` becomes "write the event + return
    summary from cache" — well under 100 ms in steady state.
  - Scheduler bugs degrade *cache freshness*, not API uptime.
  - Workers can be scaled independently of API instances.
  - Different worker pools (scheduler, IRT refit, scorer) can have
    different concurrency settings without coupling.
- **Negative**:
  - **Cache invalidation complexity**. We own a non-trivial
    invariant: "the cached queue must be consistent with the FSRS
    state in Postgres." Mitigated by:
    - Atomic version bumps via Lua (`EVAL` script).
    - The TTL safety net.
    - A graceful degradation path (`SchedulerCacheMissError` →
      synchronous compute with published SLO).
    - Cache-hit-rate as a P9 SLO metric (`tcf_itembank_hit_rate`).
  - **Eventual consistency window**. The user may see "what's next"
    based on a 100 ms-old view. This is acceptable for our use case
    (the user can't review faster than the worker can catch up at
    realistic rates).
  - **Operational surface**: two services to monitor instead of one.
    Acceptable; Celery + Redis are widely-known operational primitives.
- **Neutral**:
  - We do not pick a separate workflow engine (Temporal, Airflow).
    The work is simple enough for Celery; revisit if Phase 6/7
    workflows grow stateful.

## Alternatives considered

- **In-process scheduler (option a)**: rejected because a slow
  scheduler regression would directly degrade API p95 — a key Phase 9
  SLO. *Would reconsider*: if Phase 4 ships a scheduler whose p95
  per-card cost is < 5 ms and the queue fan-out is small enough to do
  inline (< 100 ms total per session-finish), folding back into the
  API would simplify deploy.
- **Dedicated `sla-service` (option b)**: rejected because the extra
  deploy unit + the gRPC hop buy isolation we don't yet need.
  Pre-Phase-4 we cannot justify the operational cost. *Would
  reconsider*: at > 10k concurrent learners where Celery's broker
  becomes a bottleneck, or if we need stricter SLOs on scheduler
  latency than Celery + Redis can deliver.
- **TTL-only invalidation, no explicit invalidate**: rejected because a
  user can complete many cards within a single TTL window, and a stale
  queue would show them an out-of-order review schedule. *Would
  reconsider*: never; explicit invalidation is the contract.

## What would change our mind

- **Cache invalidation incidents > 3 / quarter** causing learner-visible
  wrong-queue bugs. If we cannot keep the cache consistent at scale,
  the option (a) latency cost might be the lesser evil.
- **Worker queue backlog > 30 s at p95** on `session.finished` events.
  Indicates either we under-provisioned workers (operational fix) or
  the workload doesn't fit the queue model. We'd shard worker pools
  before going to option (b).
- **TTL safety net repeatedly firing in production** (i.e., we observe
  Redis evictions of valid queues). Indicates Redis is undersized;
  operational fix before architectural.

## References

- `02_ARCHITECTURE.md §1.1.1`, `§2.6`.
- `phase2_think.md §1.1`.
- ADR-0005 (Celery + Redis).
- ADR-0006 (FSRS-6).
- Phase 4 `04_LEARNER_MODEL.md §3` (scheduler implementation; consumes
  this contract).
