# ADR-0001: Monorepo with `uv` (Python) and `pnpm` (JS)

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer
- **Phase**: 1

## Context

`tcf-accel` spans Python (FastAPI, Celery, ML), TypeScript (Next.js 15), SQL, and content pipelines. The first 30 days of build will see frequent cross-cutting refactors: a Pydantic schema in `packages/shared` is consumed by the API, the worker, the planner, and the frontend (via a generated client). Master prompt §3 specifies a "self-hostable Python+TypeScript monorepo" and §8 names `uv` and `pnpm` as the default toolchain. The decision here is to record *why* this default is right, and what would supersede it.

## Decision

Single monorepo with `uv` workspaces for Python (root `pyproject.toml` + per-package `pyproject.toml`) and `pnpm` workspaces for JS (`pnpm-workspace.yaml` covering `apps/web` and forthcoming `packages/client-ts`).

Rationale: cross-package atomic refactors (schema changes are the steady state in the first 30 days), single lockfile per language eliminates dependency-drift bugs at zero ongoing cost, single CI pipeline, single dev loop.

## Consequences

- **Positive**:
  - One `make verify` for the whole repo.
  - Generated clients (Phase 2) and their server cannot drift — they're tested together.
  - Contributor onboarding is one `make setup` away.
  - License audit (master prompt §6.3) is a single sweep.
- **Negative**:
  - CI minutes scale with repo size; a typo in `packages/shared` re-runs everything. Mitigated by path-filtered test selection in Phase 2 if minute burn becomes painful.
  - If we ever want to spin out `packages/sla` (FSRS+LECTOR scheduler) as a standalone OSS library, we'll pay an extraction cost. Acceptable; not on the v1.0 roadmap.
- **Neutral**:
  - Per-package READMEs become noise in the directory listing. We push concise overviews into per-package `README.md` files anyway, since `pnpm publish` and `uv build` both consume them.

## Alternatives considered

- **Polyrepo (one repo per service)**: rejected because cross-service Pydantic-contract drift is the single most-reported failure mode in microservice projects of this size, and we have no fewer than four consumers of `Item` and `Score` schemas. *Would reconsider*: only at > 10 maintainers or after a clear team-ownership split.
- **Hybrid (Python monorepo + separate `apps/web` repo)**: rejected because OpenAPI-spec ↔ client drift is the failure mode the hybrid optimizes *for*, not against. *Would reconsider*: if the frontend team grows large enough to need its own release cadence and the OpenAPI contract is provably stable for > 6 months.
- **`poetry` + `npm`**: rejected because `uv` is 10–50× faster on resolution, has a deterministic lock, and ships workspaces as a first-class concept. `npm` workspaces are usable but `pnpm`'s content-addressable store is materially better for monorepo disk/bandwidth use. *Would reconsider*: regression in `uv` workspace support for our platform set.

## What would change our mind

- `uv` introduces a breaking change to workspace semantics that costs more to absorb than to migrate off (re-evaluate on every uv 1.0/2.0 major bump).
- A maintainer count above 8 with clear sub-team ownership emerges.
- A documented case where CI minute cost exceeds $200/mo in the OSS tier despite path filtering.

## References

- [uv workspaces docs](https://docs.astral.sh/uv/concepts/workspaces/)
- [pnpm workspaces docs](https://pnpm.io/workspaces)
- Master prompt §3, §8.
