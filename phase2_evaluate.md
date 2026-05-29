# Phase 2 — EVALUATE

> Phase 2 acceptance check + hand-off to Phase 3, per master prompt §5.5
> and `02_ARCHITECTURE.md §5`. Date: 2026-05-27.

---

## 1. Acceptance criteria (from `02_ARCHITECTURE.md §5`)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | DB schema migrated and tested | PASS (static) / DEFERRED-TO-CI (live) | `infra/migrations/versions/0001_initial.py` ships every table + index from `02_ARCHITECTURE.md §2.2`. Static review: `phase2_audit.md §4.1`. Live up/down: `tests/integration/test_alembic_round_trip.py` (runs on first CI with a Postgres service block; skips on fresh-clone without Docker). |
| 2 | OpenAPI v1 frozen and committed | ✅ PASS | `docs/api/openapi.v1.yaml` (2802 lines, 27 path entries, 38 schemas). The drift check (`tests/contract/test_openapi_v1.py::test_committed_spec_matches_app`) is wired and green. `make openapi-check` is the operator-facing equivalent. |
| 3 | All seventeen ADRs through ADR-017 written and reviewed | ✅ PASS | Phase 1 shipped 0001–0010; Phase 2 adds 0011 (JSONB), 0012 (schedule cache), 0013 (online posterior + nightly IRT), 0014 (error-code stability), 0015 (pgvector → Qdrant swap criteria), 0016 (URL `/v1/` versioning), 0017 (privacy default `local_only`). All seven carry the "what would change our mind" empirical-trigger section. |
| 4 | Property-based + contract tests passing | ✅ PASS | `uv run pytest packages apps/api/tests tests/contract tests/pedagogy -q` → 73 passed in 2.14s on Win Python 3.12. Hypothesis covers the full discriminated `ItemContent` union + the `Score`/`NCLCEstimate` CI invariants. Schemathesis-style contract sweep covers every GET route. |
| 5 | Risk register updated; new risks logged | ✅ PASS | Three new risks added (R-011 schedule-cache invalidation, R-012 IRT-refit cost, R-013 OpenAPI determinism). Phase 1 risks R-001 through R-010 re-evaluated and unchanged. See `RISK_REGISTER.md` deltas at the bottom. |

## 2. Anti-criteria check

| # | Anti-criterion | Status | Evidence |
|---|---|---|---|
| 1 | Any schema field without a Pydantic validator | ✅ NO VIOLATIONS | Every model under `tcf_accel.schemas.*` uses Pydantic v2 BaseModel with `ConfigDict(extra="forbid")` for the wire-shaped models. Custom invariants are enforced via `@model_validator(mode="after")` where the cross-field shape matters (`MCQ`, `EEContent`, `WritingRubric`, `SpeakingRubric`, `Item`, `Score`, `NCLCEstimate`). |
| 2 | Any API route without an OpenAPI annotation | ✅ NO VIOLATIONS | Every route in `apps/api/src/tcf_accel_api/routes/*.py` declares `response_model=` (or, in the case of `/v1/data/export`, a `responses=` entry with the streaming content type). `tests/contract/test_openapi_v1.py::test_spec_validates_as_openapi_31` asserts ≥ 25 paths in the spec. |
| 3 | Any error raised without a stable error code | ✅ NO VIOLATIONS | The only `raise` paths in `apps/api` go through `_stub.raise_not_implemented_for`, which raises `NotImplementedRouteError` (code `E_NOT_IMPLEMENTED_001`). Phase 2 audit §6 grepped for unguarded raises and found none. |
| 4 | Any TODO referencing post-Phase-2 work without a tracking issue | ✅ NO VIOLATIONS | The Phase 1 pre-commit hook `scripts/check_no_todo_docstring.py` continues to enforce this on public docstrings. The few `# Phase 3` etc. comments in code are not TODOs; they are intentional pointers to the owning phase (matching the route stubs' `phase: N` field). |

---

## 3. Lines of code delta (Phase 1 → Phase 2)

| Surface | Files Δ | LoC Δ | Notes |
|---|---|---|---|
| `packages/shared` (production) | +12 | ~+1100 | `content/` subpackage (4 files), `api/` subpackage (8 files), `interaction.py`, `errors/` subpackage (2 files; replaces single `errors.py`). |
| `packages/shared` (tests) | 0 | ~+170 | Updates to existing 5 test files; richer Hypothesis strategies. |
| `apps/api` (production) | +11 | ~+550 | 10 route modules (`auth`, `me`, `diagnostic`, `plan`, `session`, `submission`, `mock_exam`, `insights`, `data`, `health`) + `_stub.py` + the `scripts/export_openapi.py` CLI + an updated `main.py`. |
| `apps/api` (tests) | +1 | ~+120 | `test_v1_stubs.py` (Phase 2 stub-surface check). |
| `packages/client-py` (production) | +3 | ~+90 | New package: `__init__.py`, `client.py`, `pyproject.toml`. |
| `packages/client-ts` (production) | +3 | ~+90 | New package: `index.ts`, `package.json`, `README.md`. |
| `infra/migrations/versions` | +1 | ~+330 | `0001_initial.py`. |
| `infra/migrations` | +2 | ~+70 | `env.py`, `script.py.mako`. |
| `tests/{contract,integration,pedagogy}` | +3 | ~+200 | `test_openapi_v1.py`, `test_alembic_round_trip.py`, `test_golden_learner.py`. |
| `tests/pedagogy/golden_learner.jsonl` | +1 | 200 lines | Fixture (deterministic, generator at `scripts/generate_golden_learner.py`). |
| `scripts/` | +2 | ~+220 | `generate_golden_learner.py`, `generate_clients.py`. |
| `docs/adrs/` | +7 | ~+700 | ADR-0011 through ADR-0017. |
| `docs/api/openapi.v1.yaml` | +1 | 2802 lines | Frozen spec. |
| **Application code total (production, excluding tests/scripts/docs/migrations)** | **+29** | **~+1830** | |

Application code grew from ~495 LoC (Phase 1) to ~2325 LoC. The Phase 1
hard cap of 500 LoC was scoped to *Phase 1 deliverables*; Phase 2's
budget is implicit (the contract surface is necessarily larger than
the bootstrap). The dominant share is the 38 Pydantic schemas
(contract surface) and the 27 route stubs (also contract surface).

---

## 4. Tooling additions (Phase 1 baseline + Phase 2 deltas)

| Tool | Phase | Source |
|---|---|---|
| alembic >=1.13,<2.0 | 2 | root `pyproject.toml` dev group |
| sqlalchemy >=2.0,<3.0 | 2 | root `pyproject.toml` dev group |
| asyncpg >=0.29,<1.0 | 2 | root `pyproject.toml` dev group |
| psycopg[binary] >=3.2,<4.0 | 2 | root `pyproject.toml` dev group |
| schemathesis >=3.39,<4.0 | 2 | root `pyproject.toml` dev group |
| pyyaml >=6.0,<7.0 | 2 | root `pyproject.toml` dev group |
| openapi-typescript (npm) | 2 | `packages/client-ts/package.json` devDependencies |
| openapi-fetch (npm) | 2 | `packages/client-ts/package.json` dependencies |
| httpx >=0.27,<1.0 (re-affirmed) | 2 | `packages/client-py/pyproject.toml` |

---

## 5. Differentiator preservation (master prompt §9)

Identical to `phase2_audit.md §9`. All five differentiators preserved:

1. **Coverage** — All four `ItemContent` variants typed + validated;
   the `/v1/` surface enumerates every module's flow.
2. **Pedagogical rigor** — ADR-0012 + ADR-0013 lock the math shape;
   `study_plans.rationale` is required.
3. **Auto-scoring** — `WritingRubric` + `SpeakingRubric` shipped with
   the component-sum invariant; the `submissions` table separates
   artifact from typed rubric.
4. **Open-source** — ADR-0017 makes `local_only` the durable default
   at the DB level.
5. **Honesty** — `NCLCEstimate` retains the CI invariants; the
   `Readiness.canonical_mock_streak_green ≥ 2` rule is typed.

---

## 6. Risk register changes this phase

### Added (Phase 2)

- **R-011 — Schedule cache invalidation bug exposes wrong queue** (M, M). Mitigated by atomic version key + TTL safety net (ADR-0012) + a Phase 4 invariant test that posterior is recoverable from history. Owner: ML / Backend. Open.
- **R-012 — Nightly IRT refit cost grows unboundedly at scale** (L→M, M). Mitigated by ADR-0013 swap path to streaming variational IRT if > 4 hours; CEFR-shard fallback in Phase 4. Owner: ML. Open.
- **R-013 — OpenAPI spec generation is non-deterministic across machines** (L, M). Mitigated by `_dump` sorting keys + YAML default-flow off + CI runs the drift check on Linux + macOS. Owner: Backend. Open.

### Re-evaluated (Phase 1 risks)

R-001 through R-010 unchanged in disposition; all Open with documented mitigations active. Notes:

- R-004 (NCLC overconfidence): Phase 2 strengthens by typing `Readiness.canonical_mock_streak_green` as a required ≥ 2 gate. Mitigation status: stronger.
- R-005 (compute budget): Phase 2 ADR-0017 makes `local_only` the durable default. Status: stronger.
- R-008 (Windows-native drift): Phase 2 work was authored on Windows + Python 3.12 + uv 0.11.15 without issue. Status: no change.

---

## 7. One-page hand-off to Phase 3

**What is now true that wasn't before**

- The full `/v1/` API surface is frozen at `docs/api/openapi.v1.yaml`
  (28 routes including `/healthz`; 27 under `/v1/`). The drift gate is
  wired in CI.
- Every Pydantic model the contract needs is in `packages/shared`:
  `COContent` / `CEContent` / `EEContent` / `EOContent`,
  `WritingRubric` / `SpeakingRubric`, `Interaction`, `ErrorEnvelope`,
  the API request/response models for every route group.
- The error taxonomy is 19 stable-coded subclasses across 7 domains
  with EN + FR localized messages and the wire-shape `to_envelope()`
  serializer.
- The DB schema is one Alembic migration (`0001_initial.py`) shipping
  9 tables, all required indexes (including HNSW for embeddings and
  GIN for `metadata->'tags'`), and a complete `downgrade()` path.
- The Phase 2 dev loop is canonical: `make {openapi-export,
  openapi-check, migrate-up, migrate-down, clients-generate,
  phase2-verify}`.
- Seven new ADRs (0011–0017) lock the architectural decisions.
- A 200-interaction `golden_learner.jsonl` is committed; its
  generator (`scripts/generate_golden_learner.py`) is deterministic
  and byte-equality checked.

**What Phase 3 depends on (contracts to honor)**

- The OpenAPI spec is the law. Phase 3's first route implementations
  *must* match the documented shape. The drift check is the gate.
- `SCHEMA_VERSION="0.2.0"` may bump to `0.3.0` for an additive Phase 3
  change (new optional field), but breaking changes are forbidden
  until `/v2/` (ADR-0016).
- Error codes are stable (ADR-0014). Phase 3 adds new codes (e.g.,
  `E_AUTH_006` for token-blacklist) but never renames.
- The `ItemRepository.create(item: Item)` discipline is the contract
  for JSONB validation (ADR-0011). Direct `INSERT INTO items` in
  Phase 3 code is a review-rejection signal.
- The `users.privacy_mode` default is `'local_only'` (ADR-0017). Any
  cloud-touching code must check this column via a `PrivacyGuard`
  dependency.
- Alembic ownership: every Phase 3+ schema change ships in a *new*
  `NNNN_*.py` revision file; `0001_initial.py` is never edited
  post-merge.
- `infra/docker-compose.yml` (Phase 1) + the `vector` extension auto-
  enable (Phase 1's `initdb/`) + the Alembic migration (Phase 2) → a
  fresh `make dev` brings up a working data plane.

**Phase 3 cannot start until**

- The first CI run on the seeded Phase 2 repo is green (verifies the
  drift gate + Alembic round-trip).
- This file is signed off by a second reviewer per the Phase 1 ADR-006
  self-review policy. For a single-maintainer project, this is a
  separate-branch revision pass on this evaluate doc, recorded in
  `CHANGELOG.md`.

Once those two boxes are checked, Phase 3 (`03_CONTENT_PIPELINE.md`)
opens with ADR-018 (content ingest abstraction) and starts replacing
the first `/v1/` stubs with real handlers — beginning with auth
(`/v1/auth/signup`, `/v1/auth/login`, `/v1/auth/refresh`) and the
profile endpoints (`/v1/me`).
