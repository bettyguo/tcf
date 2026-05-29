# tcf-accel — canonical dev loop.
# POSIX shell semantics. Use WSL2 on Windows, or `scripts/windows_dev.ps1`.

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

PY_PACKAGES := packages/shared packages/sla packages/ml packages/content
PY_APPS     := apps/api apps/worker

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── Bootstrapping ─────────────────────────────────────────────
setup: ## Install Python + JS deps; install git hooks.
	uv sync --all-extras --all-packages
	pnpm install --frozen-lockfile
	uv run pre-commit install
	@echo ""
	@echo "✓ Setup complete. Try: make verify"

setup-models: ## Download ML models (Phase 3+). Stub in Phase 1.
	uv run python scripts/download_models.py

# ─── Daily loop ────────────────────────────────────────────────
dev: ## Run docker-compose deps + api + web in dev mode.
	docker compose -f infra/docker-compose.yml up -d db redis qdrant
	@echo "Waiting for Postgres to be healthy…"
	@until docker compose -f infra/docker-compose.yml exec -T db pg_isready -U tcf > /dev/null 2>&1; do sleep 1; done
	uv run uvicorn tcf_accel_api.main:app --reload --port 8000 &
	pnpm --filter web dev

test: ## Run all unit + integration tests.
	uv run pytest -x -q
	pnpm -r test

test-cov: ## Run tests with coverage gate.
	uv run pytest --cov=packages --cov=apps --cov-report=term --cov-report=xml --cov-fail-under=80

lint: ## Lint Python and JS.
	uv run ruff check .
	uv run ruff format --check .
	pnpm -r lint

format: ## Auto-format (writes).
	uv run ruff format .
	uv run ruff check . --fix
	pnpm -r format

typecheck: ## Static type checks.
	uv run mypy $(PY_PACKAGES) $(PY_APPS)
	pnpm -r typecheck

verify: ## The green-light gate. Run before push.
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test
	@echo ""
	@echo "✓ make verify green"

# ─── Audits ────────────────────────────────────────────────────
audit-security: ## OSS security audit (deps + static).
	uv run pip-audit --disable-pip
	uv run bandit -q -r packages apps
	pnpm audit --prod || true   # pnpm audit exits non-zero on advisories; we track but don't block in dev
	@command -v trivy >/dev/null 2>&1 && trivy fs --exit-code 1 --severity HIGH,CRITICAL . || echo "trivy not installed locally; CI runs it"
	@command -v gitleaks >/dev/null 2>&1 && gitleaks detect --no-banner || echo "gitleaks not installed locally; pre-commit + CI run it"

audit-deps: ## License + abandoned-package audit.
	uv run python scripts/license_check.py
	uv run python scripts/abandoned_check.py

audit-content: ## Phase 3+. Content distribution + NSFW + copyright.
	@echo "Phase 3+ owns this target. Skipped in Phase 1."

audit-pedagogy: ## Phase 4+. Scheduler / estimator invariants.
	@echo "Phase 4+ owns this target. Skipped in Phase 1."

# ─── Release ───────────────────────────────────────────────────
release: ## Build Docker + Helm artifacts. Phase 9 wires this.
	@echo "Phase 9 owns this target."

# ─── Phase gates (each phase appends its own) ──────────────────
phase1-verify: ## Phase 1 acceptance run.
	@$(MAKE) verify
	@$(MAKE) audit-security
	@$(MAKE) audit-deps
	@echo ""
	@echo "✓ phase1-verify green"

phase2-verify: ## Phase 2 acceptance run.
	@$(MAKE) verify
	@$(MAKE) openapi-check
	@uv run pytest tests/contract -q
	@uv run pytest tests/pedagogy -q
	@echo ""
	@echo "✓ phase2-verify green"

phase2-verify-full: ## Phase 2 acceptance + live-DB integration.
	@$(MAKE) phase2-verify
	@uv run pytest tests/integration -q
	@echo ""
	@echo "✓ phase2-verify-full green (DB up/down + integration suite)"

# ─── OpenAPI ───────────────────────────────────────────────────
openapi-export: ## Re-export the frozen OpenAPI spec.
	uv run python -m tcf_accel_api.scripts.export_openapi --output docs/api/openapi.v1.yaml

openapi-check: ## Verify the on-disk spec matches the running app.
	uv run python -m tcf_accel_api.scripts.export_openapi --check docs/api/openapi.v1.yaml

# ─── Migrations ────────────────────────────────────────────────
migrate-up: ## Apply all migrations.
	uv run alembic -c alembic.ini upgrade head

migrate-down: ## Roll back to base (drops all tables).
	uv run alembic -c alembic.ini downgrade base

# ─── Clients ───────────────────────────────────────────────────
clients-generate: ## Regenerate TS + Python client SDKs from openapi.v1.yaml.
	uv run python scripts/generate_clients.py

golden-learner-regenerate: ## Regenerate the golden_learner trajectory.
	uv run python scripts/generate_golden_learner.py tests/pedagogy/golden_learner.jsonl

# ─── Cleanup ───────────────────────────────────────────────────
clean: ## Remove caches + build artifacts. Keeps the venv.
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +

distclean: clean ## Full clean including venv + node_modules.
	rm -rf .venv node_modules apps/*/node_modules apps/*/.next

.PHONY: help setup setup-models dev test test-cov lint format typecheck verify \
        audit-security audit-deps audit-content audit-pedagogy release \
        phase1-verify phase2-verify phase2-verify-full \
        openapi-export openapi-check migrate-up migrate-down \
        clients-generate golden-learner-regenerate \
        clean distclean
