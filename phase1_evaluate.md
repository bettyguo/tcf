# Phase 1 — EVALUATE

> Phase 1 acceptance check + handoff to Phase 2, per master prompt §5.5 and
> `01_REPO_BOOTSTRAP.md §5`. Date: 2026-05-27.

---

## Acceptance criteria (from `01_REPO_BOOTSTRAP.md §5`)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `make verify` green | DEFERRED-TO-CI | All inputs in place; CI workflow `ci.yml` wired; verification on first push to GitHub. See `phase1_audit.md §4.1`. |
| 2 | All 10 ADRs accepted | ✅ PASS | `docs/adrs/0001..0010`. Self-review documented in `phase1_audit.md §4.6`. |
| 3 | Pre-commit + CI enforce style + types + security | ✅ PASS (wired) | `.pre-commit-config.yaml` + `ci.yml` + `audit.yml`. Local execution deferred per `phase1_audit.md §4.2`. |
| 4 | Risk register seeded | ✅ PASS | `RISK_REGISTER.md` with 10 entries (target was 7). |
| 5 | Contracts in `packages/shared` published with semver tag `0.1.0` | ✅ PASS (schema) / DEFERRED (git tag) | `SCHEMA_VERSION="0.1.0"` set; tests pin it. Git tag follows the first CI green pass and merge to `main`. |
| 6 | README "Quickstart" section a new dev can follow | ✅ PASS | `README.md` Quickstart with prerequisite list, `make setup`, `make verify`. Will be re-verified by first contributor on Ubuntu / macOS / WSL2. |
| 7 | Total lines of application code ≤ 500 | ✅ PASS | See LoC summary below. |

## Anti-criteria check

| # | Anti-criterion | Status | Evidence |
|---|---|---|---|
| 1 | Any `# TODO` in a public docstring | ✅ NO VIOLATIONS | `scripts/check_no_todo_docstring.py` wired in pre-commit; manual grep over `apps/` and `packages/` returns clean for public symbols. |
| 2 | Any `--no-verify` bypass | ✅ NO VIOLATIONS | No commits exist yet (git init pending). Policy enforced socially in `CONTRIBUTING.md` invariant #3. |
| 3 | Any service imports from another service's internals (not via `packages/shared`) | ✅ NO VIOLATIONS | `apps/api` imports `tcf_accel.schemas.version` from `packages/shared` only. `apps/worker` is self-contained + `tcf_accel.schemas` re-exports. No cross-service internal imports. |
| 4 | Any "Hello World" route returning 500 | ✅ NO VIOLATIONS | `apps/api/tests/test_health.py` asserts `200` on `/healthz`. `apps/worker/tests/test_smoke.py` asserts `"pong"` from the smoke task. |
| 5 | Any commit on `main` without a review (or self-review on a branch) | N/A YET | No commits exist; first commit is the initial-commit pending. Policy documented. |

---

## Metrics

### Lines of code (LoC)

| Surface | Files | LoC | Notes |
|---|---|---|---|
| `packages/shared` (production) | 7 | ~250 | `errors.py`, `ids.py`, `schemas/{common,item,scoring,version}.py`, `schemas/__init__.py`, `__init__.py`. |
| `packages/shared` (tests) | 5 | ~270 | Round-trip + invariant + version + error tests. |
| `apps/api` (production) | 4 | ~85 | `main.py`, `routes/healthz.py`, `__init__.py`, `routes/__init__.py`. |
| `apps/api` (tests) | 2 | ~30 | `test_health.py`, `__init__.py`. |
| `apps/worker` (production) | 4 | ~80 | `celery_app.py`, `tasks/smoke.py`, `__init__.py` × 2. |
| `apps/worker` (tests) | 2 | ~30 | `test_smoke.py`, `__init__.py`. |
| `apps/web` (production) | 4 | ~50 | `layout.tsx`, `page.tsx`, `globals.css`, configs. |
| `apps/web` (tests) | 1 | ~15 | `smoke.test.ts`. |
| `packages/{sla,ml,content}` (production) | 3 | ~30 | Empty `__init__.py` per package. |
| `scripts/` | 6 | ~370 | License + abandoned check + download stub + 2 pre-commit hooks + windows_dev.ps1. |
| **App code total (excluding tests, scripts, docs)** | **22** | **~495** | Within the 500-line Phase 1 budget. |

### Coverage

- Local execution **DEFERRED** (see `phase1_audit.md §4.1`).
- CI will publish `coverage.xml`; coverage gate set to `--cov-fail-under=80`
  in `Makefile`'s `test-cov` target. Phase 1 production code is dominated by
  declarative Pydantic schemas, which are tested round-trip + invariant. Test
  files: 10. Expected coverage: > 90% on `packages/shared`.

### Tooling baseline

| Tool | Version pinned | Source |
|---|---|---|
| Python | 3.12 (CI) / 3.13 (local OK) | `pyproject.toml` `requires-python`, `ci.yml` |
| uv | 0.11+ | `setup-uv@v3` |
| Node | 22 | `ci.yml` |
| pnpm | 9 | `ci.yml`, `pnpm-workspace.yaml` |
| ruff | >=0.6,<1.0 | `pyproject.toml` |
| mypy | >=1.11,<2.0 (strict) | `pyproject.toml` |
| pytest | >=8.3,<9.0 | `pyproject.toml` |
| hypothesis | >=6.112,<7.0 | `pyproject.toml` |
| pre-commit | 4.6+ (3.8 min) | `.pre-commit-config.yaml` |

### Number of artifacts created in Phase 1

- 10 ADRs + 1 template (`docs/adrs/`).
- 7 governance docs (`LICENSE`, `CONTENT_LICENSE`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `README.md`).
- 4 risk + rationale docs (`RISK_REGISTER.md`, `RATIONALE.md`, `phase1_audit.md`, `phase1_evaluate.md` — incl. this file).
- 2 Phase 1 planning docs (`phase1_think.md`, `phase1_design.md`).
- 1 workspace root pyproject + 1 pnpm workspace declaration.
- 6 member pyprojects (3 apps + 3 packages + 1 root).
- 1 Makefile, 1 PowerShell convenience script.
- 3 GitHub Actions workflows (`ci.yml`, `audit.yml`, `release.yml`).
- 2 docker-compose files (base + GPU override) + 1 init SQL.
- 5 helper scripts (license check, abandoned check, download stub, 2 pre-commit hooks).
- 12 production Python modules (apps + packages).
- 10 test files.
- 4 apps/web TS/TSX files + 4 configs.
- 12 `.gitkeep` markers + 1 `data/.gitkeep` with the data-policy reminder.
- 1 `.gitignore`, 1 `.gitattributes`, 1 `.editorconfig`, 1 `.env.example`, 1 `.pre-commit-config.yaml`, 1 `.markdownlint.jsonc`.
- 1 `infra/migrations/README.md`.

Total new files: **~95**. (Roughly aligned with the Phase 1 design's expected
~60 + various READMEs, gitkeeps, and per-package configs.)

---

## Differentiator preservation check (master prompt §9)

| Differentiator | Phase 1 contribution |
|---|---|
| 1. **Coverage** (all 4 modules end-to-end) | Phase 1 reserves the structure; Phase 5/6/7 deliver. |
| 2. **Pedagogical rigor** (SR + diagnostic planner + bottleneck) | ADR-0006 (FSRS-6); `RATIONALE.md` R-005 (bottleneck heuristic protection); `packages/sla` skeleton reserved. |
| 3. **Auto-scoring** (EE/EO with κ + calibration) | Phase 7 owns. Phase 1 reserves `packages/ml` skeleton. |
| 4. **Open-source** (MIT/CC-BY-SA, self-hostable, no telemetry default) | ✅ Licenses in place; `.env.example` carries `PRIVACY_DEFAULT_MODE=local_only`; ADR-0009 makes LLM provider configurable. |
| 5. **Honesty** (CI-aware NCLC, refusal-to-predict, ethical content) | ✅ `Score` schema enforces CI invariants; `confident` flag in schema; `RATIONALE.md` R-006 (no point estimates without CI); ADR-0010 + `CONTENT_LICENSE` for ethical sourcing. |

**Preserved.** No differentiator regressed.

---

## Risk register changes this phase

- R-008 added (Windows-native dev loop drift) — Open.
- R-009 added (pedagogy audit failure mode) — Open, owner ML/Pedagogy.
- R-010 added (κ on EE/EO below target) — Open, owner ML.
- R-001 through R-007 unchanged in disposition; all Open with documented mitigations active.

---

## One-page handoff to Phase 2

**What is now true that wasn't before**

- The monorepo skeleton exists. `apps/{api,web,worker}` and
  `packages/{shared,sla,ml,content}` are wired with per-package `pyproject.toml`
  (or `package.json`) and minimal hello-world content that returns success.
- The Phase 1 contracts are frozen: `Item`, `ItemContent` (placeholder),
  `Provenance`, `QualityFlag`, `ItemMetadata`, `Score`, `NCLCEstimate`, the
  error taxonomy seed, and `SCHEMA_VERSION="0.1.0"`. Tests pin the
  invariants (CI bounds on `Score`, module-discriminator on `Item`, code
  stability on errors).
- The dev loop is canonical: `make {setup,verify,lint,typecheck,test,format,
  audit-security,audit-deps,phase1-verify}`. Windows-native users have
  `scripts/windows_dev.ps1` as a fallback.
- Pre-commit enforces ruff, mypy (touched files), gitleaks, custom
  `check_no_data_commit`, custom `check_no_todo_docstring`, markdownlint,
  and pnpm-eslint for web.
- CI on push/PR runs the verify chain on `{ubuntu-latest, macos-latest} ×
  py3.12 × node22`. Weekly audit runs `pip-audit`, `bandit`, `pnpm audit`,
  `license_check`, `abandoned_check`, and `trivy fs`.
- 10 ADRs are accepted: monorepo (uv+pnpm), pgvector-first, FastAPI,
  Next.js 15, Celery+Redis, FSRS-6, Whisper-fr, CamemBERT CEFR, litellm
  (Claude Sonnet 4.6 default), MIT + CC-BY-SA dual licensing.
- 10 risks are registered with mitigations.
- 7 refusals are logged in `RATIONALE.md`.

**What Phase 2 depends on (contracts to honor)**

- `packages/shared` schemas are frozen. Phase 2 may *narrow* `ItemContent`
  into a discriminated union (additive); breaking changes require a version
  bump + ADR.
- Error taxonomy codes (`E_*_NNN`) are stable. Phase 2 *adds* codes; does not
  rename.
- Pydantic-v2-first; SQLAlchemy 2 (async) is the data layer; Alembic owns
  migrations (`infra/migrations/`).
- `apps/api` is FastAPI-only. All `/v1/...` routes from `02_ARCHITECTURE.md
  §2.4` are stubbed `501` in Phase 2; implementations land in Phases 3–8.
- Test layout convention: per-package `tests/`, top-level
  `tests/{unit,integration,contract,e2e,pedagogy}`.
- `infra/docker-compose.yml` ships `pgvector/pgvector:pg16` with the
  `vector` extension auto-enabled. Phase 2 Alembic migrations target it.

**Phase 2 cannot start until**

- The first CI run on the seeded repo is green (verifies the deferred
  acceptance criteria above).
- This file (`phase1_evaluate.md`) is signed off by a second reviewer per
  ADR-006 self-review policy. For a single-maintainer project, this is a
  separate-branch revision pass on this evaluate doc, recorded in
  `CHANGELOG.md`.

Once those two boxes are checked, Phase 2 (`02_ARCHITECTURE.md`) opens
ADR-0011 (JSONB content vs polymorphic tables; chosen: JSONB) and the
Alembic migration `0001_initial.py` begins.
