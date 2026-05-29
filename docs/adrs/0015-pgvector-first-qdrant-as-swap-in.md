# ADR-0015: pgvector first; Qdrant as a swap-in if scale demands (re-affirms ADR-0002 with explicit triggers)

- **Date**: 2026-05-27
- **Status**: accepted
- **Supersedes**: ADR-0002 (re-affirmed with stricter triggers; ADR-0002
  remains the historical record of the initial choice)
- **Deciders**: Lead engineer, ML lead
- **Phase**: 2

## Context

ADR-0002 chose `pgvector` over a dedicated vector DB for Phase 1. Phase 2
now actually persists vectors (`items.embedding VECTOR(768)` — the
multilingual MPNet output dim) and indexes them (`items_embedding_hnsw
USING hnsw (embedding vector_cosine_ops)`). The Phase 2 architecture
document (`02_ARCHITECTURE.md §1.2`) names pgvector as the default and
calls Qdrant the swap-in if scale demands. This ADR re-affirms the
choice with *measurable* swap triggers, so the decision is testable in
the Phase 9 launch audit.

The forces:

- **Single store ergonomics**: Phase 2 commits to atomic relational +
  vector writes (e.g., inserting an item + its embedding in one
  transaction). A separate vector DB would force a saga pattern.
- **Scale ceiling**: pgvector's HNSW is reportedly inferior to Qdrant
  / Milvus at > 5M vectors at our dim. We don't expect to be there in
  Phase 8; we may be there by Phase 12.
- **Self-hostability** (master prompt §6.4): both pgvector and Qdrant
  are self-hostable; we have no SaaS lock-in either way.

## Decision

`pgvector` is the production vector store for Phase 2 through Phase 9.
The application accesses vectors *exclusively* through the abstraction at
`packages/shared/src/tcf_accel/storage/vector_store.py` (scaffolded
Phase 2, implemented Phase 4). The abstraction has two impl backends
(`PgVectorStore`, `QdrantStore`), selected by `VECTOR_STORE_BACKEND`
env var (default `pgvector`). Phase 2 only ships `PgVectorStore`; the
`QdrantStore` exists as a stub raising `NotImplementedError`.

Swap trigger (any one of):

| Metric | Threshold | Source |
|---|---|---|
| Item bank size | > 5M items | Phase 9 audit `audit-content` |
| Recall@10 on a representative semantic-confusable benchmark | < 0.92 | Phase 4 `audit-pedagogy` |
| p95 `nearest_neighbors(k=10)` query latency | > 100 ms | Phase 9 SLO check (`tcf_api_request_duration_seconds`) |
| pgvector breaking change cost-to-absorb | > 1 engineer-week | judgement call, recorded in `RATIONALE.md` |

If a trigger fires, we run the Qdrant migration playbook (Phase 9 will
document it) which:

1. Provisions Qdrant via the existing `infra/docker-compose.yml` entry
   (already there from Phase 1).
2. Implements `QdrantStore` end-to-end.
3. Backfills vectors from Postgres to Qdrant (idempotent script).
4. Flips `VECTOR_STORE_BACKEND=qdrant` in production.
5. Keeps the `embedding` column in Postgres for one release as a
   rollback path.

## Consequences

- **Positive**:
  - One database to back up, version, and audit.
  - Atomic transactions over relational + vector data.
  - No new service to operate in Phases 2–8.
  - The vector-store abstraction means the swap is a config change, not
    a refactor.
- **Negative**:
  - We accept a known scale ceiling. If we hit it sooner than projected,
    the swap is real work (the migration playbook).
  - We pay the abstraction tax in `vector_store.py` — one extra
    interface to maintain.
- **Neutral**:
  - Qdrant remains in `infra/docker-compose.yml` for forward-compat;
    it costs ~50 MB of container image to keep there.

## Alternatives considered

- **Qdrant from day 1**: rejected because the extra service complicates
  ops without measurable benefit at < 1M items, and atomic
  relational + vector writes would require a saga pattern. *Would
  reconsider*: if any of the swap triggers above fires.
- **Pinecone / managed vector DB**: rejected on cost and on
  self-hostability (master prompt §6.4 — no cloud dependencies by
  default). *Would reconsider*: never; SaaS-only is a non-starter.
- **No vector store; nearest-neighbor in NumPy at request time**:
  viable at < 10k items but breaks the moment we scale. Rejected to
  avoid a forced refactor mid-Phase-4.
- **Defer the decision to Phase 4**: rejected because Phase 2 has to
  pick a column type and an index strategy; we cannot defer.

## What would change our mind

See the swap-trigger table above. Each row is a measurable signal that
will surface in either the Phase 4 `audit-pedagogy` job or the Phase 9
SLO check. The decision is *not* "wait until pgvector is slow"; it's
"swap when these metrics cross these thresholds."

## References

- ADR-0002 (initial pgvector choice; this ADR re-affirms).
- `02_ARCHITECTURE.md §1.2`, `§2.2`.
- `phase2_design.md §1`, `§2.2`.
- pgvector vs Qdrant benchmarks, 2025 (community-maintained;
  re-evaluated in Phase 9 launch audit).
- Master prompt §3, §6.4, §8.
