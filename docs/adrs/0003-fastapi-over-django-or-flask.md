# ADR-0003: FastAPI over Django or Flask

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Backend
- **Phase**: 1

## Context

The API has three demanding properties: it must (a) speak a strict, machine-readable contract (OpenAPI) that the generated TypeScript client consumes (Phase 2), (b) handle long-running async work efficiently (audio scoring, LLM calls), and (c) integrate cleanly with Pydantic v2 (already chosen for the shared schemas).

Master prompt §8 specifies `FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Celery, Redis`. This ADR records *why* FastAPI over the two obvious alternatives.

## Decision

FastAPI as the HTTP layer for `apps/api`. Pydantic v2 models from `packages/shared` are the *only* request/response types. OpenAPI spec is generated from handler signatures and frozen as `docs/api/openapi.v1.yaml` in Phase 2.

## Consequences

- **Positive**:
  - OpenAPI generation is automatic; the spec cannot diverge from the code by construction.
  - Async-native; well-matched to our I/O-bound workloads (LLM calls, DB queries, file uploads).
  - Pydantic v2's `model_validator` and discriminated unions express our schemas precisely (the Phase 2 `ItemContent = COContent | CEContent | EEContent | EOContent` union is idiomatic).
  - `Schemathesis` (Phase 2) fuzz-tests the spec for free.
- **Negative**:
  - Less batteries-included than Django; we hand-roll the admin (Phase 3 ships a Streamlit review UI separately).
  - The ecosystem of "FastAPI plugins" is thinner than Flask's; we accept this for the contract-first benefit.
- **Neutral**:
  - We use `FastAPI[standard]` (uvicorn + httpx + orjson) — the documented "full stack" install.

## Alternatives considered

- **Django + DRF**: rejected because (a) ORM is its main selling point but we prefer SQLAlchemy 2 for the query expressiveness our learner-model joins will need, (b) async support is improving but not yet as native as FastAPI, (c) OpenAPI generation via `drf-spectacular` is good but not as automatic. *Would reconsider*: if we ever ship a multi-tenant admin UI that benefits from Django Admin (the v1.1 "tutor mode" might).
- **Flask + Flask-RESTX**: rejected because async story is bolt-on, OpenAPI generation requires manual decorators (drift risk), Pydantic integration is weaker. *Would reconsider*: not foreseen.
- **Litestar**: a strong contender (faster than FastAPI, Pydantic v2 native). Rejected for v1 on ecosystem maturity and team familiarity. *Would reconsider*: if FastAPI maintenance signals slow materially.

## What would change our mind

- A FastAPI release that breaks Pydantic v2 integration without a migration path.
- A documented 3× or better throughput improvement from Litestar on our exact workload, sustained over a quarter.

## References

- Master prompt §8.
- FastAPI docs, Pydantic v2 docs.
