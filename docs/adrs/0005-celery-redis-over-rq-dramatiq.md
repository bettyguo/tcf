# ADR-0005: Celery + Redis over RQ / Dramatiq

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Backend
- **Phase**: 1

## Context

Background work spans short tasks (FSRS state writes, posterior updates) and long tasks (content ingestion runs that may take hours, LLM scoring of EE submissions, mock-exam grading). We need: retry with backoff, idempotency keys, chained workflows, scheduled jobs, and resumable long-running jobs with checkpoints (master prompt §7).

Master prompt §8 specifies `Celery, Redis`.

## Decision

Celery 5.4+ as the task framework, Redis as both broker and result backend (Phase 9 may switch results to Postgres if Redis memory grows pathological; documented as a known toggle).

Conventions:
- Every task is idempotent and keyed by `(task_name, content_hash)`.
- Long-running tasks use `apply_async(..., link=…)` chains with explicit checkpoint persistence to Postgres (so a worker death does not lose progress; master prompt §7).
- `task_acks_late = True` so an OOM-killed worker re-queues its task.
- Beat runs nightly jobs (IRT refit, FSRS per-user param optimization).

## Consequences

- **Positive**:
  - Mature ecosystem; retry, monitoring (Flower), and signal hooks all out-of-the-box.
  - Chained workflows (canvas) express our scoring pipeline naturally.
  - Beat handles the scheduled IRT refit in `04_LEARNER_MODEL.md §2.1`.
- **Negative**:
  - Celery has historically had memory-leak issues on long-running workers; mitigated by `worker_max_tasks_per_child` cycling.
  - Configuration surface is large; we keep a single `celery_app.py` with documented overrides.
- **Neutral**:
  - We deliberately do NOT enable Celery's `pickle` serializer; tasks are JSON-only, which limits accidental object-serialization bugs and removes a known security footgun.

## Alternatives considered

- **RQ**: simpler, but no native canvas / chains, weaker beat. Rejected because the content pipeline (Phase 3) is a natural chain (`fetch → normalize → classify → synthesize → quality-gate → embed → load`) and we want first-class workflow primitives. *Would reconsider*: if Celery's maintenance signals slow materially.
- **Dramatiq**: cleaner API, encrypted-message support. Rejected on ecosystem maturity for our specific patterns (canvas + beat). *Would reconsider*: not foreseen.
- **Postgres-as-queue (e.g., `pgmq`, `procrastinate`)**: keeps everything in one store. Rejected because Redis is already required for caching the scheduler's pre-computed queues (Phase 2 ADR-012), so removing Celery's broker dep doesn't reduce service count.

## What would change our mind

- A documented case where Celery loses tasks under our `acks_late` + checkpoint regime.
- An ecosystem-wide shift away from Celery for new Python jobs (signals: maintainer count, PyPI downloads, recent CVE response time).

## References

- Master prompt §8.
- `04_LEARNER_MODEL.md §2.1` (nightly jobs).
- `03_CONTENT_PIPELINE.md §2.1` (chained pipeline).
