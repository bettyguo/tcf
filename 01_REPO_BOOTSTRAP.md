# PHASE 1 — Repository Bootstrap, Tooling, and Contracts

> Goal: a clean, audited monorepo with `make verify` green, all toolchain decisions written down, and the dev loop usable by a contributor on day one.

**Do not write application code in this phase.** This phase exists so every subsequent phase has a frictionless place to land code, tests, and audits.

---

## 1. THINK (produce `phase1_think.md`)

Address explicitly:

- **Monorepo vs polyrepo?** Recommendation: monorepo (`apps/web`, `apps/api`, `packages/sla`, `packages/ml`, `packages/content`). Reason: tight coupling between content pipeline, ML services, and the planner; cross-package refactors will be frequent in the first 30 days. The cost (slower CI, less library autonomy) is acceptable for a team-of-N≤5 build.
- **Python build system?** `uv` over `pip-tools`/`poetry`. Reason: 10–50× faster resolution, deterministic locks, single-binary install. Has surpassed Poetry in mind-share for new 2025+ projects.
- **JS build system?** `pnpm` workspaces over npm/yarn. Reason: hard-linked node_modules saves space, strict by default, monorepo-native.
- **Test runner?** `pytest` for Python (universal). `vitest` for TS unit tests (Jest's faster successor); `playwright` for E2E.
- **CI provider?** GitHub Actions for OSS visibility + free minutes for public repos.
- **What is the contract between the team's three roles** (Backend, ML, Frontend) such that a change in one does not silently break another? → API contracts pinned via OpenAPI; ML services exposed through versioned interfaces; content via typed Pydantic schemas serialized to JSONL.

Discuss what would change your mind on each.

---

## 2. DESIGN (produce `phase1_design.md`)

### 2.1 Repository Layout

```
tcf-accel/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # lint + typecheck + test on PR
│       ├── audit.yml              # weekly security + dep audit
│       └── release.yml            # tag-triggered Docker/Helm publish
├── apps/
│   ├── api/                       # FastAPI service (Phase 2+)
│   ├── web/                       # Next.js 15 (Phase 8)
│   └── worker/                    # Celery workers (Phase 3+)
├── packages/
│   ├── sla/                       # FSRS + LECTOR + scheduler (Phase 4)
│   ├── ml/                        # CEFR classifier, ASR, scorer (Phase 7)
│   ├── content/                   # ingestion + corpus tools (Phase 3)
│   └── shared/                    # Pydantic schemas, errors, types
├── infra/
│   ├── docker-compose.yml         # single-command local up
│   ├── docker-compose.gpu.yml     # GPU override for ML services
│   ├── helm/                      # institutional deploy (stretch)
│   └── migrations/                # Alembic
├── docs/
│   ├── adrs/                      # Architecture Decision Records
│   ├── pedagogy/                  # SLA evidence dossier
│   ├── api/                       # OpenAPI HTML
│   └── runbooks/                  # on-call ops
├── data/                          # gitignored; symlink to corpus
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
├── scripts/                       # one-off + dev helpers
├── 00_MASTER_PROMPT.md … 09_…md   # the planning docs (this file etc.)
├── Makefile
├── pyproject.toml                 # workspace root
├── pnpm-workspace.yaml
├── .pre-commit-config.yaml
├── LICENSE                        # MIT
├── CONTENT_LICENSE                # CC BY-SA 4.0 for content
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── RISK_REGISTER.md
└── README.md
```

### 2.2 The Makefile (Canonical Dev Loop)

```make
# Bootstrapping
setup:           uv sync --all-extras && pnpm install && pre-commit install
setup-models:    python scripts/download_models.py  # whisper-fr, embeddings, CEFR classifier

# Daily loop
dev:             docker compose up -d db redis qdrant && uvicorn ... & pnpm --filter web dev
test:            pytest -x -q && pnpm -r test
test-cov:        pytest --cov=packages --cov=apps --cov-fail-under=80
lint:            ruff check . && ruff format --check . && pnpm -r lint
typecheck:       mypy packages apps && pnpm -r typecheck
verify:          lint typecheck test           # the "green light" gate

# Audits (run weekly + on release)
audit-security:  pip-audit && bandit -r packages apps && pnpm audit && trivy fs .
audit-deps:      python scripts/license_check.py && python scripts/abandoned_check.py
audit-content:   python scripts/audit_content_distribution.py
audit-pedagogy:  pytest tests/pedagogy -v

# Phase-specific (added per phase)
phase-N-verify:  ...                          # each phase defines its own gate

# Release
release:         python scripts/build_release.py
```

### 2.3 Pre-commit Hooks

- `ruff format` + `ruff check --fix`
- `mypy` (touched files)
- `pnpm lint-staged`
- `gitleaks detect` (no committed secrets)
- `markdownlint`
- A custom hook that fails if a commit touches `data/` (never commit corpora)

### 2.4 ADR Template (`docs/adrs/0000-template.md`)

```
# ADR-{NNNN}: {decision title}
Date: YYYY-MM-DD  |  Status: proposed | accepted | superseded by ADR-NNNN
## Context
## Decision
## Consequences (positive / negative / neutral)
## Alternatives considered (with the load-bearing reason for rejection)
## What would change our mind
```

First 10 ADRs to write in Phase 1:

1. Monorepo with uv + pnpm
2. PostgreSQL + pgvector over a separate vector DB initially
3. FastAPI over Django/Flask
4. Next.js 15 App Router over Remix/SvelteKit
5. Celery + Redis over RQ/Dramatiq
6. FSRS-6 as the SRS algorithm
7. `bofenghuang/whisper-large-v3-french` as primary ASR
8. CamemBERT-derived CEFR classifier over zero-shot LLM classification
9. litellm as the LLM gateway, Claude Sonnet 4.6 as default
10. MIT for code + CC BY-SA 4.0 for content (with a section on why not GPL)

### 2.5 Risk Register (initial entries)

| ID | Risk | Likelihood | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R-001 | TCF Canada format changes during build (real "2026 reform") | M | H | Subscribe to FEI updates; re-verify on each release; abstract format into a versioned config | Lead | Open |
| R-002 | Whisper-fr accuracy on Canadian/African accents inadequate for pronunciation scoring | M | H | Build multi-accent eval set in Phase 5; allow ASR vendor swap | ML | Open |
| R-003 | LLM-authored synthetic items contain detectable "tells" | H | M | Adversarial review pass; tag synthetic items; cap their share of bank ≤ 40% | Content | Open |
| R-004 | NCLC estimator overconfident → learner books exam prematurely | M | H | Mandatory CI reporting; refuse-to-predict mode; cohort calibration study | ML | Open |
| R-005 | Compute budget for daily learner-tier hosting exceeds OSS sustainability | M | M | Profile early; gate cloud ASR/LLM behind explicit opt-in | DevOps | Open |
| R-006 | Copyright complaint from a news source whose audio we redistribute | L | H | Never redistribute; ingest-and-cache pipeline runs on operator's machine | Lead | Open |
| R-007 | Deaf/HoH candidates have no path for CO; what do we do? | Certain | Medium-ethical | Build a "TCF Canada eligible-skills-only" mode + clear documentation that CO accessibility is a structural exam issue, not a system gap | Product | Open |

### 2.6 Contracts (the surface that downstream phases consume)

In `packages/shared/`:

```python
# packages/shared/src/tcf_accel/schemas/item.py  (excerpt — full in Phase 3)
class Item(BaseModel):
    id: ItemId
    module: Literal["CO", "CE", "EE", "EO"]
    cefr_level: Literal["A1","A2","B1","B2","C1","C2"]
    difficulty_irt: float | None   # 1PL b-parameter, set in Phase 4
    content: ItemContent           # discriminated union per module
    metadata: ItemMetadata
    provenance: Provenance
    quality_flags: list[QualityFlag]

class Score(BaseModel):
    nclc: int          # 1..12
    raw: int | float
    ci_low: int
    ci_high: int
    n_observations: int
    confident: bool    # False ⇒ caller MUST NOT show as a final estimate
```

These contracts are frozen after Phase 1. Changes go through ADRs and a deprecation path.

---

## 3. CODE

Implement only what is needed to pass `make verify` on an empty service:

- `pyproject.toml` (workspace), `pnpm-workspace.yaml`.
- Empty `apps/api`, `apps/web`, `apps/worker` Hello-World endpoints (so CI has something to test).
- The `packages/shared` schemas above.
- `.pre-commit-config.yaml`.
- `.github/workflows/ci.yml` running `make verify` on push and PR.
- The Makefile.
- The docker-compose for `db`, `redis`, `qdrant`.
- `scripts/license_check.py` and `scripts/abandoned_check.py`.
- README with a "5-minute setup" section actually verified to work on a fresh Ubuntu 22.04 + macOS 14 + WSL2 machine.

---

## 4. AUDIT (produce `phase1_audit.md`)

- `make verify` passes locally and in CI on Linux + macOS.
- `make audit-security` returns clean.
- `make audit-deps` flags no GPL/AGPL infections.
- Pre-commit catches a deliberately-added secret in a test commit.
- A new contributor — simulated by an empty container — can clone, run `make setup`, run `make verify`, and see green in ≤ 10 minutes.
- The 10 ADRs are written and reviewed.
- `RISK_REGISTER.md` exists with at least the 7 entries above.
- `LICENSE`, `CONTENT_LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` exist and have non-placeholder content.

---

## 5. EVALUATE (produce `phase1_evaluate.md`)

Acceptance criteria:

- ✅ `make verify` green
- ✅ All 10 ADRs accepted
- ✅ Pre-commit + CI enforce style + types + security
- ✅ Risk register seeded
- ✅ Contracts in `packages/shared` published with semver tag `0.1.0`
- ✅ A README "Quickstart" section a new dev can actually follow
- ✅ Total lines of application code ≤ 500 (this is scaffolding, not features)

Anti-criteria (the phase FAILS if any of these are true):

- ❌ Any `# TODO` in a public docstring
- ❌ Any failing pre-commit hook bypassed with `--no-verify`
- ❌ Any service imports from another service's internals (only via `packages/shared`)
- ❌ Any "Hello World" route returning 500
- ❌ Any commit on `main` without a PR review (even from one-person teams: ADR-006 mandates self-review on a separate branch)

Hand-off: produce a one-page summary listing the contracts now available, the dev-loop commands, and the dependencies the next phase will rely on.
