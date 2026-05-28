# ADR-0002: PostgreSQL 16 + `pgvector` initially; Qdrant as a swap-in

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, ML lead
- **Phase**: 1 (re-affirmed in Phase 2 as ADR-015)

## Context

The system needs vector search for two distinct purposes:

1. **LECTOR-style semantic-confusable family detection** (Phase 4) over the item bank — typically ≤ 50k items at v1 scale.
2. **Retrieval for content recommendation** within the planner — also bounded by bank size.

Master prompt §8 names `PostgreSQL 16 + pgvector (or Qdrant 1.10 if pgvector becomes the bottleneck)`. Phase 2 ADR-015 affirms pgvector-first. This ADR records *why pgvector first* and what would trigger the swap.

## Decision

Use PostgreSQL 16 with the `pgvector` extension as the single store for relational + vector data. Qdrant remains in `infra/docker-compose.yml` for forward-compatibility, but the application layer reads/writes vectors only via `pgvector` initially.

Embedding schema: `VECTOR(768)` (multilingual MPNet output dim). Indexed via `hnsw` with `vector_cosine_ops`.

## Consequences

- **Positive**:
  - Single database to back up, version, and audit.
  - JOINs between items, interactions, and embeddings work in pure SQL.
  - Transaction guarantees over both relational and vector writes (e.g., inserting an item + its embedding atomically).
  - No additional service to operate in Phase 1–8.
- **Negative**:
  - `pgvector` HNSW indexing is slower to build than dedicated vector stores; mitigated by infrequent bulk re-indexing.
  - At very large bank sizes (> 5M vectors at our dim) pgvector's `hnsw` recall vs latency is reportedly worse than Qdrant or Milvus; we accept this for v1.
- **Neutral**:
  - Vector-store-agnostic abstraction (`packages/shared/src/tcf_accel/storage/vector_store.py`, introduced in Phase 2) wraps both backends so the swap is a config change, not a refactor.

## Alternatives considered

- **Qdrant from day 1**: rejected because the extra service complicates ops without measurable benefit at our scale, and atomic relational+vector writes would require a saga pattern. *Would reconsider*: if Phase 3 ships a bank > 1M items and pgvector recall@10 falls below 0.92.
- **Pinecone / managed vector DB**: rejected on cost (paid SaaS) and on self-hostability (master prompt §6.4 — no cloud dependencies by default).
- **No vector store; nearest-neighbor in NumPy**: viable at < 10k items but breaks the moment we scale. Rejected to avoid a forced refactor mid-Phase-4.

## What would change our mind

- Bank size > 1M items and pgvector p95 query latency > 100 ms for our HNSW config.
- pgvector recall@10 < 0.92 on a representative semantic-confusable benchmark.
- A breaking change to pgvector that costs more to absorb than to migrate.

## References

- [pgvector benchmarks vs alternatives, 2025](https://github.com/pgvector/pgvector)
- Master prompt §3, §8.
- Phase 2 ADR-015 (downstream affirmation).
