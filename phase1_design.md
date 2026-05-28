# Phase 1 — DESIGN

> The detailed design for Phase 1. Mandatory per master prompt §5.2.

---

## 1. Repository layout (final)

```
tcf-accel/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # lint + typecheck + test on push/PR (Linux + macOS matrix)
│       ├── audit.yml              # weekly security + dep audit + on-demand
│       └── release.yml            # tag-triggered Docker/Helm publish (stub in Phase 1)
├── apps/
│   ├── api/                       # FastAPI service. Phase 1 ships a /healthz only.
│   │   ├── pyproject.toml
│   │   ├── src/tcf_accel_api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── routes/healthz.py
│   │   └── tests/test_health.py
│   ├── web/                       # Next.js 15. Phase 1 ships a hello page only.
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── next.config.mjs
│   │   ├── eslint.config.mjs
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   └── tests/smoke.test.ts    # vitest smoke
│   └── worker/                    # Celery. Phase 1 ships a single dummy task.
│       ├── pyproject.toml
│       ├── src/tcf_accel_worker/
│       │   ├── __init__.py
│       │   └── celery_app.py
│       └── tests/test_smoke.py
├── packages/
│   ├── shared/                    # Pydantic schemas, errors, types. The Phase 1 contracts.
│   │   ├── pyproject.toml
│   │   ├── src/tcf_accel/
│   │   │   ├── __init__.py
│   │   │   ├── errors.py
│   │   │   ├── ids.py
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       ├── common.py        # Provenance, QualityFlag, ItemMetadata
│   │   │       ├── item.py          # Item, ItemContent (placeholder, Phase 2 narrows)
│   │   │       ├── scoring.py       # Score, NCLCEstimate skeleton
│   │   │       └── version.py       # SCHEMA_VERSION = "0.1.0"
│   │   └── tests/
│   │       ├── test_item_schema.py
│   │       ├── test_scoring_schema.py
│   │       ├── test_errors.py
│   │       └── test_roundtrip.py    # property-based round-trip (Hypothesis)
│   ├── sla/                       # Phase 4 fills in.
│   │   ├── pyproject.toml
│   │   └── src/tcf_accel_sla/__init__.py
│   ├── ml/                        # Phase 3+ fills in.
│   │   ├── pyproject.toml
│   │   └── src/tcf_accel_ml/__init__.py
│   └── content/                   # Phase 3 fills in.
│       ├── pyproject.toml
│       └── src/tcf_accel_content/__init__.py
├── infra/
│   ├── docker-compose.yml         # db (postgres+pgvector), redis, qdrant
│   ├── docker-compose.gpu.yml     # GPU override for ML services (Phase 5+)
│   └── migrations/                # Alembic (Phase 2)
│       └── .gitkeep
├── docs/
│   ├── adrs/
│   │   ├── 0000-template.md
│   │   ├── 0001-monorepo-with-uv-and-pnpm.md
│   │   ├── 0002-postgres-pgvector-over-separate-vector-db.md
│   │   ├── 0003-fastapi-over-django-or-flask.md
│   │   ├── 0004-nextjs15-app-router.md
│   │   ├── 0005-celery-redis-over-rq-dramatiq.md
│   │   ├── 0006-fsrs6-as-srs-algorithm.md
│   │   ├── 0007-whisper-large-v3-french-primary-asr.md
│   │   ├── 0008-camembert-cefr-classifier-over-zero-shot-llm.md
│   │   ├── 0009-litellm-gateway-with-claude-sonnet-46-default.md
│   │   └── 0010-mit-code-cc-by-sa-content-license.md
│   ├── pedagogy/.gitkeep          # SLA evidence dossier (Phase 4+)
│   ├── api/.gitkeep               # OpenAPI HTML (Phase 2)
│   └── runbooks/.gitkeep          # on-call ops (Phase 9)
├── data/                          # gitignored. Operator-supplied corpus location.
│   └── .gitkeep                   # only file ever allowed under data/
├── tests/
│   ├── unit/.gitkeep
│   ├── integration/.gitkeep
│   ├── contract/.gitkeep
│   ├── e2e/.gitkeep
│   └── pedagogy/.gitkeep
├── scripts/
│   ├── license_check.py           # fails build on GPL/AGPL
│   ├── abandoned_check.py         # flags deps with no release in 24mo
│   ├── download_models.py         # Phase 3+ uses; stub in Phase 1
│   └── windows_dev.ps1            # PowerShell convenience for non-WSL contributors
├── 00_MASTER_PROMPT.md … 09_*.md  # planning docs (unmodified except via CHANGELOG)
├── phase1_think.md / design.md / audit.md / evaluate.md
├── Makefile                       # canonical dev loop (POSIX shell)
├── pyproject.toml                 # workspace root
├── pnpm-workspace.yaml
├── .pre-commit-config.yaml
├── .editorconfig
├── .gitignore
├── .gitattributes                 # forces LF on .sh/.py; preserves CRLF on .ps1
├── .env.example                   # documented placeholders only; no real secrets
├── LICENSE                        # MIT
├── CONTENT_LICENSE                # CC BY-SA 4.0
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── RISK_REGISTER.md
├── RATIONALE.md                   # refusal log per master prompt §11
└── README.md
```

---

## 2. The Makefile (canonical dev loop)

POSIX shell semantics. Run via `make <target>` on Linux/macOS/WSL2. Windows-native contributors use `scripts/windows_dev.ps1` or WSL2.

```make
SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

PY_PACKAGES := packages/shared packages/sla packages/ml packages/content
PY_APPS     := apps/api apps/worker

help:               ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── Bootstrapping ─────────────────────────────────────────────
setup:              ## Install Python + JS deps; install git hooks.
	uv sync --all-extras --all-packages
	pnpm install --frozen-lockfile
	uv run pre-commit install

setup-models:       ## Download ML models (Phase 3+). Stub in Phase 1.
	uv run python scripts/download_models.py

# ─── Daily loop ────────────────────────────────────────────────
dev:                ## Run docker-compose deps + api + web in dev mode.
	docker compose -f infra/docker-compose.yml up -d db redis qdrant
	uv run uvicorn tcf_accel_api.main:app --reload --port 8000 &
	pnpm --filter web dev

test:               ## Run all unit + integration tests.
	uv run pytest -x -q
	pnpm -r test

test-cov:           ## Run tests with coverage gate.
	uv run pytest --cov=packages --cov=apps --cov-report=term --cov-report=xml --cov-fail-under=80

lint:               ## Lint Python and JS.
	uv run ruff check .
	uv run ruff format --check .
	pnpm -r lint

format:             ## Auto-format (writes).
	uv run ruff format .
	uv run ruff check . --fix
	pnpm -r format

typecheck:          ## Static type checks.
	uv run mypy $(PY_PACKAGES) $(PY_APPS)
	pnpm -r typecheck

verify:             ## The green-light gate. Run before push.
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

# ─── Audits ────────────────────────────────────────────────────
audit-security:     ## OSS security audit (deps + static).
	uv run pip-audit
	uv run bandit -q -r packages apps
	pnpm audit --prod
	# trivy fs is optional locally; CI runs it. Uncomment when trivy is on PATH:
	# trivy fs --exit-code 1 --severity HIGH,CRITICAL .

audit-deps:         ## License + abandoned-package audit.
	uv run python scripts/license_check.py
	uv run python scripts/abandoned_check.py

audit-content:      ## Phase 3+. Content distribution + NSFW + copyright.
	@echo "Phase 3+ owns this target. Skipped in Phase 1."

audit-pedagogy:     ## Phase 4+. Scheduler / estimator invariants.
	@echo "Phase 4+ owns this target. Skipped in Phase 1."

# ─── Release ───────────────────────────────────────────────────
release:            ## Build Docker + Helm artifacts. Phase 9 wires this.
	@echo "Phase 9 owns this target."

# ─── Phase gates (each phase adds its own) ─────────────────────
phase1-verify:      ## Phase 1 acceptance run.
	$(MAKE) verify
	$(MAKE) audit-security
	$(MAKE) audit-deps

.PHONY: help setup setup-models dev test test-cov lint format typecheck verify \
        audit-security audit-deps audit-content audit-pedagogy release phase1-verify
```

Design notes:

- `verify` is the *only* command a contributor needs to remember before pushing. It chains lint → typecheck → test. Failing any stops the chain.
- `audit-*` targets are separated from `verify` because they require additional tools (security scanners) and minutes; they run in `audit.yml` weekly + on-demand.
- `phase-N-verify` targets are append-only; each phase adds its own without modifying the others. Phase 1 only defines `phase1-verify`.

---

## 3. Workspace configuration

### 3.1 Root `pyproject.toml`

Declares the `uv` workspace and the union dev-dependency set. Member packages have their own `pyproject.toml` files that depend on `tcf-accel-shared` via workspace path.

Pinning rationale:
- `requires-python = ">=3.12"` — matches master prompt §8; allows 3.13 in dev so we don't block on minor version drift.
- Dev tools pinned to a known-good minor (ruff, mypy, pytest, hypothesis, pre-commit). Major bumps require an ADR.
- ML / app runtime deps live in *each app's* pyproject, not the workspace root. Keeps the workspace lean.

### 3.2 `pnpm-workspace.yaml`

```yaml
packages:
  - "apps/web"
  - "packages/client-ts"   # exists from Phase 2; Phase 1 leaves placeholder
```

### 3.3 `.pre-commit-config.yaml` hooks

- `ruff` (format + check + fix)
- `mypy` (touched files only; pre-commit-mypy)
- `pnpm exec eslint --fix` (web)
- `gitleaks` (no committed secrets)
- `check-yaml`, `check-toml`, `check-json`
- `end-of-file-fixer`, `trailing-whitespace`, `mixed-line-ending` (handles Windows CRLF)
- `markdownlint-cli2`
- **Custom**: `python scripts/check_no_data_commit.py` — fails any staged file under `data/`
- **Custom**: `python scripts/check_no_todo_docstring.py` — fails any public docstring containing `TODO` (phase 1 anti-criterion ❌)

### 3.4 `.env.example`

Documents every env var the system reads, with placeholder values + a comment per var. No real secrets ever committed.

```bash
# Database (docker-compose default values)
DATABASE_URL=postgresql+asyncpg://tcf:tcf@localhost:5432/tcf
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# LLM gateway (litellm). Default model per master prompt §8.
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=                     # required for cloud LLM; leave blank for local

# ASR. Default: local whisper-large-v3-french via faster-whisper.
ASR_PROVIDER=local
WHISPER_MODEL=bofenghuang/whisper-large-v3-french

# Privacy default per master prompt §6.4
PRIVACY_DEFAULT_MODE=local_only        # local_only | cloud_optin

# Observability
LOG_LEVEL=INFO
OTEL_EXPORTER_OTLP_ENDPOINT=
PROMETHEUS_METRICS_PORT=9090
```

---

## 4. GitHub Actions

### 4.1 `ci.yml`

Triggered on `push` and `pull_request`. Matrix: `{os: [ubuntu-latest, macos-latest], python: ['3.12'], node: ['22']}`. Steps:

1. Checkout (with submodules off; no big artifacts).
2. Install `uv` (astral-sh/setup-uv@v3); cache `~/.cache/uv`.
3. Setup pnpm + Node 22; cache `~/.local/share/pnpm/store`.
4. `make setup`.
5. `make verify`.
6. Upload `coverage.xml` to artifact (no Codecov dep in Phase 1).

Concurrency group: `ci-${{ github.ref }}`, `cancel-in-progress: true`.

### 4.2 `audit.yml`

Triggered on `schedule: cron '0 4 * * 1'` (Mondays 04:00 UTC) and `workflow_dispatch`. Runs `make audit-security` and `make audit-deps`. Installs `trivy` via apt for the Linux runner. Posts results to a GitHub Issue with label `audit` if any finding is HIGH+.

### 4.3 `release.yml`

Triggered on tags matching `v*.*.*`. Phase 1 stub: builds Docker images (placeholder Dockerfile) and creates a GitHub release with the changelog. Phase 9 elaborates with multi-arch builds + Helm publish + signed checksums.

---

## 5. Pre-commit hook design (rationale)

The custom hooks are the load-bearing ones:

- **`check_no_data_commit.py`**: blocks accidental commit of corpus data. Without this, a contributor could `git add data/` and accidentally push 20 GB.
- **`check_no_todo_docstring.py`**: Phase 1 anti-criterion. Public docstrings are the contract; TODOs there are bugs. Internal `# TODO` comments inside function bodies are allowed (we encourage them as bookmarks).

Both hooks are simple Python scripts with a stable exit-code contract.

---

## 6. Docker Compose topology

`infra/docker-compose.yml`:

- `db`: `pgvector/pgvector:pg16` — Postgres 16 with `pgvector` preinstalled. Volume-mounted to `./data/pg`. Healthcheck via `pg_isready`.
- `redis`: `redis:7-alpine`. Volume-mounted to `./data/redis`. Healthcheck via `redis-cli ping`.
- `qdrant`: `qdrant/qdrant:v1.10.0` — vector DB. Phase 2 ADR-015 keeps this as a swap-in if pgvector becomes the bottleneck.

`infra/docker-compose.gpu.yml`: an override file that adds GPU device reservation for ML services (Phase 5+). Empty placeholder in Phase 1 with a `# Phase 5 elaborates` comment.

All ports bound to `127.0.0.1` (no exposure to LAN). Phase 9 audit will re-verify.

---

## 7. Pydantic contracts (Phase 1 freeze)

`packages/shared/src/tcf_accel/schemas/`:

```python
# version.py
SCHEMA_VERSION: Final[str] = "0.1.0"

# ids.py
ItemId = NewType("ItemId", UUID)
UserId = NewType("UserId", UUID)
SessionId = NewType("SessionId", UUID)
InteractionId = NewType("InteractionId", int)

# common.py
class Provenance(BaseModel):
    source: str
    source_id: str
    license: str                       # SPDX-style identifier or "proprietary"
    ingested_at: datetime
    fetcher_version: str | None = None
    synthesizer_version: str | None = None
    llm_model: str | None = None
    llm_prompt_hash: str | None = None
    review_status: Literal["auto_passed", "human_approved", "human_modified", "rejected"]
    review_notes: str | None = None

class QualityFlag(str, Enum):
    SYNTHETIC = "synthetic"
    LOW_CONFIDENCE_CEFR = "low_confidence_cefr"
    POTENTIAL_DUPLICATE = "potential_duplicate"
    HIGH_ADVERSARIAL = "high_adversarial"
    PII_SUSPECTED = "pii_suspected"
    NEEDS_HUMAN_REVIEW = "needs_human_review"

class ItemMetadata(BaseModel):
    topic: str | None = None
    topic_cluster_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    created_by: str | None = None
    seed: int | None = None            # for reproducibility on synthesized items

# item.py
class ItemContent(BaseModel):
    """Phase 1 placeholder. Phase 2 narrows into a discriminated union
    of COContent | CEContent | EEContent | EOContent."""
    model_config = ConfigDict(extra="allow")  # narrowed in Phase 2
    module: Literal["CO", "CE", "EE", "EO"]

class Item(BaseModel):
    id: ItemId
    module: Literal["CO", "CE", "EE", "EO"]
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"]
    difficulty_irt: float | None = None
    discrimination_irt: float | None = None
    content: ItemContent
    metadata: ItemMetadata = Field(default_factory=ItemMetadata)
    provenance: Provenance
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    synthetic: bool = False
    retired: bool = False
    schema_version: str = SCHEMA_VERSION

# scoring.py
class Score(BaseModel):
    nclc: int = Field(ge=1, le=12)
    raw: float
    ci_low: int = Field(ge=1, le=12)
    ci_high: int = Field(ge=1, le=12)
    n_observations: int = Field(ge=0)
    confident: bool

    @model_validator(mode="after")
    def _ci_invariant(self) -> "Score":
        if self.ci_low > self.ci_high:
            raise ValueError("ci_low must be ≤ ci_high")
        if not (self.ci_low <= self.nclc <= self.ci_high):
            raise ValueError("point estimate must lie within CI")
        return self

class NCLCEstimate(BaseModel):
    """Phase 4 elaborates; Phase 1 ships the public-facing shape only."""
    skill: Literal["CO", "CE", "EE", "EO"]
    posterior_mean: float = Field(ge=1, le=12)
    ci_low: int = Field(ge=1, le=12)
    ci_high: int = Field(ge=1, le=12)
    confident: bool
    n_observations: int = Field(ge=0)
```

`errors.py`:

```python
class TCFAccelError(Exception):
    """Base for all in-house errors. Every subclass MUST have a stable
    `code` class-var (E_DOMAIN_NNN) and a learner-facing `message_template`."""
    code: ClassVar[str] = "E_BASE_000"
    message_template: ClassVar[str] = "tcf-accel error"
    http_status: ClassVar[int] = 500

    def __init__(self, **context: object) -> None:
        super().__init__(self.message_template.format(**context))
        self.context = context

class ContentNotAvailableError(TCFAccelError):
    code = "E_CONTENT_001"
    message_template = "No items match constraints: {constraints}"
    http_status = 404

class SchedulerError(TCFAccelError):
    code = "E_SCHED_001"
    http_status = 500

class CalibrationError(TCFAccelError):
    code = "E_CALIB_001"
    http_status = 503

class InsufficientObservationsError(CalibrationError):
    code = "E_CALIB_002"
    message_template = "Need {needed} more observations; have {have}"
```

Phase 2 fills in the full taxonomy from `02_ARCHITECTURE.md §2.5`.

---

## 8. Test plan (Phase 1)

- **Unit**: every schema validates round-trip; every error has a stable code; Makefile targets exist and are documented.
- **Property-based (Hypothesis)**: random valid `Item` JSON → parse → re-serialize → equal. Random `Score` → invariants (`ci_low ≤ nclc ≤ ci_high`) hold or error raised.
- **Integration**: `apps/api`'s `/healthz` returns 200. `apps/worker`'s smoke task runs locally with `eager=True` Celery.
- **Contract**: skipped in Phase 1 (the OpenAPI freeze is Phase 2's deliverable).
- **E2E**: skipped in Phase 1 (Phase 8 owns this).

Coverage gate for Phase 1: `--cov-fail-under=80` over `packages/shared` only. Apps are too thin to count; their coverage requirements ramp in their owning phase.

---

## 9. ADRs added in this phase

Numbered 0001–0010. The list is in §4 above; full bodies live in `docs/adrs/`.

---

## 10. "What would change my mind" register

- If `uv workspace`'s lockfile becomes painful at > 50 packages, re-evaluate vs `rye` / `hatch`.
- If `pnpm` ships a breaking change on workspace semantics, re-evaluate vs `npm`'s now-decent workspace support.
- If GitHub Actions free minutes are insufficient, move CI to a self-hosted runner (a single $20/mo VPS suffices for OSS minutes).
- If `pre-commit`'s `mypy` hook becomes unbearable, drop it from pre-commit and rely on CI alone; add a `make typecheck-staged` for opt-in local use.
- If a hard-licensing review surfaces that any pinned dev tool is AGPL-bound, swap immediately.

---

## 11. Anti-criteria, restated

The Phase 1 evaluate step (`phase1_evaluate.md`) will check each:

- ❌ No `# TODO` in any public docstring.
- ❌ No `--no-verify` bypass of pre-commit anywhere in history.
- ❌ No service imports from another service's internals (only via `packages/shared`).
- ❌ No "Hello World" route returning 500.
- ❌ No commit on `main` without a PR-style review.

If any of these is true at gate time, Phase 1 fails and must be re-run.
