# Changelog

All notable changes to `tcf-accel` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once `v1.0.0` is reached (Phase 9).

Until `v1.0.0`, the project is in active build per the phase plan in
`00_MASTER_PROMPT.md §4`. Each phase's `phaseN_evaluate.md` records the
phase-level changes; this file rolls them up at release boundaries.

---

## [Unreleased]

### Phase 1 — Repository Bootstrap, Tooling, Contracts

Added:

- Monorepo layout (`apps/`, `packages/`, `infra/`, `docs/`, `tests/`, `scripts/`).
- Workspace configuration: `pyproject.toml` (uv workspace), `pnpm-workspace.yaml`.
- Canonical dev loop in `Makefile` (`setup`, `verify`, `audit-security`, `audit-deps`, etc.).
- `.pre-commit-config.yaml` with `ruff`, `mypy`, `gitleaks`, and custom data-commit + TODO-docstring hooks.
- `.gitignore`, `.gitattributes` (LF normalization), `.editorconfig`, `.env.example`.
- GitHub Actions workflows: `ci.yml` (lint + typecheck + test on Linux + macOS), `audit.yml` (weekly), `release.yml` (tag-triggered stub).
- Hello-world stubs: `apps/api` (FastAPI `/healthz`), `apps/web` (Next.js 15 page), `apps/worker` (Celery smoke task).
- Frozen Phase 1 contracts in `packages/shared/src/tcf_accel/schemas/`: `Item`, `ItemContent` (placeholder; Phase 2 narrows), `Provenance`, `QualityFlag`, `ItemMetadata`, `Score`, `NCLCEstimate`, error taxonomy base.
- Package stubs: `packages/sla`, `packages/ml`, `packages/content` (each with `pyproject.toml` + `__init__.py`).
- Infrastructure: `infra/docker-compose.yml` (Postgres 16 + pgvector, Redis 7, Qdrant 1.10), `infra/docker-compose.gpu.yml` (GPU override stub).
- Helper scripts: `scripts/license_check.py`, `scripts/abandoned_check.py`, `scripts/download_models.py` (stub).
- Governance docs: `LICENSE` (MIT), `CONTENT_LICENSE` (CC BY-SA 4.0), `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `RATIONALE.md`, `RISK_REGISTER.md`, `README.md`.
- 10 ADRs (`docs/adrs/0001..0010`) covering: monorepo with uv + pnpm, pgvector-first, FastAPI, Next.js 15 App Router, Celery + Redis, FSRS-6, `bofenghuang/whisper-large-v3-french`, CamemBERT CEFR classifier, litellm with `claude-sonnet-4-6` default, MIT + CC BY-SA dual licensing.
- Phase 1 artifacts: `phase1_think.md`, `phase1_design.md`, `phase1_audit.md`, `phase1_evaluate.md`.

Refused (per master prompt §11; logged in `RATIONALE.md`):

- C2 in 12 weeks from B1 (target re-set to NCLC 7–9; C2 offered as stretch).
- "Pass guaranteed" copy.
- Cloud telemetry of learner audio by default (default is `local_only`).
- Bundling FEI copyrighted test material (links only).
- Features contradicting the bottleneck heuristic.
- NCLC point estimates without credible intervals.
- Unbounded synthetic-item share (capped at 40%/module).
