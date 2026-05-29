# ADR-0011: JSONB `items.content` with Pydantic validation, over polymorphic per-module tables

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Backend lead
- **Phase**: 2

## Context

The system handles four item modules (`CO`, `CE`, `EE`, `EO`) whose
`content` payloads share nothing structurally:

- **CO**: transcript, audio reference, speakers, accent, register, MCQs.
- **CE**: passage, genre, word count, MCQs.
- **EE**: writing prompt, target word count range, rubric version.
- **EO**: examiner prompts, prep time, target duration, rubric version.

Three storage shapes were considered (`phase2_think.md §1.2`):

1. One `items` table with a JSONB `content` column.
2. Four tables, one per module.
3. SQLAlchemy polymorphic inheritance over a base + four subclasses.

Master prompt §3 names "PostgreSQL 16 + pgvector" and "Pydantic v2" as
the canonical persistence + validation primitives. `02_ARCHITECTURE.md
§2.2` makes the JSONB choice explicit.

The forces:

- **Cross-module queries are constant**: mock-exam composition, the
  recommender, the diagnostic adaptive engine — all query across modules.
- **The query columns are stable**: `module`, `cefr_level`,
  `difficulty_irt`, `tags`, `retired`. These need to be real columns
  for index speed.
- **The payload columns are unstable**: each module's `content` will
  evolve as we add features (alternate transcripts, prompt variants,
  multi-rubric versions). We want schema evolution without migrations.
- **The validation has to be strict**: a malformed item is a learner
  harm (R-003); we cannot rely on the DB to catch shape bugs.

## Decision

Use a single `items` table with:

- **Queryable columns as real columns**: `id`, `module`, `cefr_level`,
  `difficulty_irt`, `discrimination_irt`, `embedding`, `quality_flags`,
  `synthetic`, `retired`, `schema_version`, `created_at`.
- **`content JSONB NOT NULL`** validated at the application boundary by
  the Pydantic `ItemContent` discriminated union
  (`packages/shared/src/tcf_accel/schemas/content/`).
- **`metadata JSONB NOT NULL DEFAULT '{}'::jsonb`** with a GIN index on
  the `tags` array for retrieval.
- **CHECK constraints** on `module ∈ {'CO','CE','EE','EO'}` and
  `cefr_level ∈ {'A1'..'C2'}` so the DB enforces the discriminator
  domain even if the application layer has a bug.

All writes go through `ItemRepository.create(item: Item)` which calls
`Item.model_validate(...)` before INSERT. Direct SQL writes from
ad-hoc scripts are forbidden; the linter (`ruff` rule + a manual code
review check) catches `INSERT INTO items` outside the repository.

## Consequences

- **Positive**:
  - Single physical table → cross-module queries are plain SQL with no
    UNION / no polymorphic loading.
  - Schema evolution within a module's payload is a Pydantic-only
    change; no migration required.
  - The vector index (`items_embedding_hnsw`) covers all modules
    uniformly.
  - One JSONB GIN index on `metadata->'tags'` serves all modules.
- **Negative**:
  - The DB does not enforce `content` shape. We rely on the application
    layer (Pydantic) for that. Mitigated by:
    - All writes routed through `ItemRepository`.
    - Nightly audit (Phase 9 §2.3) re-validates every row against the
      current `ItemContent` union and flags drift.
    - A property-based test that round-trips JSON → `Item.model_validate
      → model_dump → equal`.
  - `content` field queries (`content->>'transcript'`) bypass the typed
    layer; we restrict these to read-only reporting / debugging scripts
    and never to production code paths.
- **Neutral**:
  - We pay the JSONB serialization cost on every read. At our row
    sizes (≤ ~10 KB per item), this is sub-millisecond.

## Alternatives considered

- **Four tables, one per module**: rejected because cross-module queries
  become UNIONs; the recommender's vector index would either fan out
  across four tables or require a denormalized view. *Would reconsider*:
  if a nightly drift audit shows > 0.1% of rows failing current-schema
  validation, indicating we've lost the JSONB invariant in practice.
- **SQLAlchemy polymorphic inheritance**: rejected because it inherits
  both the JOIN cost of multi-table reads and the ORM complexity of
  polymorphic loading; SQLAlchemy's async polymorphic loaders are a
  known sharp edge. *Would reconsider*: never; this is a strict
  superset of the multi-table cost.
- **A single `content TEXT NOT NULL` column with JSON-as-text**:
  rejected because we lose GIN indexability on `metadata->'tags'` and
  the Postgres-side validation that comes with JSONB type checks.

## What would change our mind

- **Drift incident**: the Phase 9 nightly audit reports > 0.1% of items
  failing `ItemContent` validation in a 30-day window. This indicates
  the application-layer invariant is leaking, and the DB-side enforcement
  of option (b) would have caught it.
- **Query bottleneck**: pgvector or JSONB extraction becomes the dominant
  cost in `GET /v1/session/next` p95 > 300 ms attributable to the items
  table. We'd consider per-module materialized views before splitting
  tables.
- **Bank > 10M items**: HNSW degradation triggers the ADR-015 swap to
  Qdrant; at the same time we'd revisit the items-table layout.

## References

- `02_ARCHITECTURE.md §1.1.2`, `§2.2`, `§2.3`.
- `phase2_think.md §1.2`.
- ADR-0002 (pgvector first).
- ADR-015 (re-affirms pgvector with explicit swap criteria).
- Pydantic v2 discriminated unions: <https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions>
