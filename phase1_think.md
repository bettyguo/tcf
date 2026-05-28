# Phase 1 — THINK

> The reasoning behind Phase 1 (Repo Bootstrap, Tooling, Contracts). This document is mandatory per master prompt §5.1.

---

## 1. Problem statement

Phase 1 exists so every subsequent phase has a frictionless place to land code, tests, and audits. Concretely: a new contributor (human or agentic) must be able to clone the repo, run `make setup`, run `make verify`, and see green in ≤ 10 minutes; and any downstream phase must be able to add a feature without inventing its own conventions for layout, linting, testing, observability, or contracts.

This is **infrastructure work**, not application work. No business logic. The exit condition is *frictionlessness*, not *features*.

---

## 2. Three alternative high-level approaches

### Approach A — "Monorepo with `uv` + `pnpm` workspaces" *(chosen)*

- **Pros**: Single source of truth for tooling. Cross-package refactors are atomic. `uv` workspaces share a lockfile so dependency drift across `apps/api`, `apps/worker`, and `packages/*` is impossible. `pnpm` workspaces handle the JS half identically. Single CI pipeline. Cross-package imports work with editable installs out of the box.
- **Cons**: All-or-nothing CI cost: changing a typo in `packages/shared` triggers tests for every consumer. Less library autonomy if we ever spin out `packages/sla` as a standalone SRS lib.
- **Failure modes**: CI minutes explode at ~30 packages; mitigated by per-path test filters in `ci.yml` (Phase 1 starts simple, adds them as cost emerges). Cross-team review noise; mitigated by `CODEOWNERS` per directory in Phase 2.
- **Tradeoff against the north star (B1→C1 in 12 weeks, exam-aligned, open-source, evidence-based)**: A monorepo accelerates the first 30 days when the content pipeline (Phase 3), scheduler (Phase 4), and drills (Phase 5) all share Pydantic contracts under active iteration. Wins on velocity, neutral on rigor, wins on contributor onboarding.

### Approach B — "Polyrepo: one repo per service"

- **Pros**: Independent CI; teams own release cadence; smaller blast radius per merge.
- **Cons**: Pydantic contract drift is *guaranteed* — three repos will diverge their `Item` schema within a week. Cross-cutting refactors require coordinated PRs across N repos. New contributors must clone N repos and understand N dev loops.
- **Failure modes**: Stale clients (`packages/client-py` published from one repo, consumed by another, with no compile-time check that the OpenAPI matches reality). This is the failure mode the master prompt §1.5 explicitly singles out — bottleneck heuristics break when one service's posterior format is stale.
- **Rejected because**: at N≤5 maintainers, the coordination tax dominates. The premise of polyrepo (independent teams) doesn't hold for a team this small.

### Approach C — "Hybrid: monorepo for backend + ML + content; separate repo for `apps/web`"

- **Pros**: Frontend deployment cadence decoupled from backend. Web team can pick its own JS toolchain without polluting the Python side. Smaller initial repo.
- **Cons**: The frontend consumes the generated OpenAPI client (Phase 2). Drift between the spec and the published client is the most common production bug in this architecture. Two CI systems to maintain. Two security-audit cadences.
- **Failure modes**: The frontend ships a client built against an old spec; the API returns a new field; runtime parse error in production. We've all lived this.
- **Rejected because**: the Phase 2 contract-freeze story is most defensible when the spec, the SDK, and the consumer all live in one tree and one CI pipeline can fail-on-drift.

**Chosen: A.** Load-bearing reason: cross-phase Pydantic contracts and the OpenAPI spec are the central nervous system of this build (master prompt §6.1 — "correctness over coverage"). A monorepo makes those contracts atomically-refactorable; the alternatives make contract drift the default state.

---

## 3. Tooling-decision rationales (one-paragraph each)

- **`uv` over `pip-tools` / `poetry`**: 10–50× faster dependency resolution, deterministic lockfile, single static binary install path, first-class workspaces, supports PEP 735 dep-groups. Mind-share for new 2025+ Python projects has shifted decisively to `uv`. What would change my mind: `uv` workspace support regressing on Windows (unlikely; we use it now).
- **`pnpm` over `npm` / `yarn`**: content-addressable store saves disk + bandwidth, strict by default (no phantom deps), monorepo-native, the dominant choice for Next.js 15 / TypeScript monorepos. What would change my mind: Next.js 15 dropping support for non-npm workspaces (none signaled).
- **`pytest` for Python, `vitest` for TS unit, `playwright` for E2E**: each is the dominant choice in its niche. `vitest` over `jest` because it's 5–10× faster, ESM-native, and Next.js 15 ships ESM-first. What would change my mind: jest catching up on ESM performance (it hasn't).
- **GitHub Actions for CI**: OSS-friendly free minutes for public repos, matrix support, broad action ecosystem. What would change my mind: a CI provider materially cheaper for our minute-burn (re-evaluate at Phase 6 when k6 load tests start consuming minutes).
- **`pre-commit` for git hooks**: standard, language-agnostic, hook-version pinning is reproducible. What would change my mind: `lefthook` becoming dominant (jury still out as of 2026).
- **`ruff` for lint + format**: replaces `black`+`isort`+`flake8`+ several plugins with one Rust binary; ~100× faster; growing rule coverage. What would change my mind: a Python-specific bug in ruff's formatter (track release notes).

---

## 4. The three-role contract problem

The team's logical roles are Backend, ML, and Frontend. The Phase 1 contract surface that prevents silent breakage:

1. **API contract**: OpenAPI spec generated from FastAPI handlers; frozen in `docs/api/openapi.v1.yaml` after Phase 2; both `packages/client-py` and `packages/client-ts` (Phase 2) are regenerated from it on every change; CI fails if the generated client drifts from the spec.
2. **ML interface contract**: each ML service (CEFR classifier, ASR, scorer) exposes a typed Python interface in `packages/ml/src/.../interface.py`; the API consumes the interface, never the implementation; integration tests use a stub implementation; production swaps in the real one. This isolates expensive model swaps from API churn.
3. **Content contract**: items flow between phases as Pydantic models (`packages/shared/src/tcf_accel/schemas/item.py`) serialized to JSONL on disk; every JSONL writer validates on write, every reader validates on read; schema versions are pinned per release; migrations live in `packages/shared/migrations/`.

Phase 1 establishes the *files* that hold these contracts. It does not yet *fill them with logic*.

---

## 5. Unknowns + cheapest experiments

| Unknown | Cheapest experiment | When |
|---|---|---|
| Will `uv sync --all-extras` on Windows cleanly install scientific deps (e.g., `librosa`, `montreal-forced-aligner`) that Phase 5 needs? | A Phase 1 CI matrix entry for `windows-latest` alongside Linux+macOS, with a `--dry-run` install of the Phase 5 dep set. Fails noisily if the ABI doesn't work. | Phase 1 audit |
| Will `pnpm` workspaces play well with Next.js 15's RSC bundling for shared types from `packages/client-ts`? | Stub a `packages/client-ts` with one type alias; import it from `apps/web/app/page.tsx`; verify the build artifact. | Phase 1 audit |
| Will the `pre-commit` `mypy` hook be tolerable in incremental mode at our package count? | Run `mypy` over the seeded empty packages; baseline the cold/warm run times. If cold > 30 s, switch to per-package incremental mypy. | Phase 1 audit |
| Will GitHub Actions free-tier minutes hold for the matrix we want (Linux + macOS × 3.12 + 3.13 × node 20 + 22)? | Compute estimated minutes for a 1-week sprint at expected PR rate; cap matrix if > 2000 min/month. | Phase 1 evaluate |

---

## 6. Cross-phase dependencies + contracts created here

Phase 1 emits, and downstream phases consume:

- `packages/shared/src/tcf_accel/schemas/item.py` — `Item`, `Provenance`, `QualityFlag`, `ItemMetadata` (Phase 3 elaborates `ItemContent` via additive union).
- `packages/shared/src/tcf_accel/schemas/scoring.py` — `Score`, `NCLCEstimate` skeleton (Phase 4 fills in posterior fields; Phase 7 adds rubric schemas).
- `packages/shared/src/tcf_accel/errors.py` — `TCFAccelError` base + stable error-code registry (Phase 2 fills in the taxonomy).
- The Makefile target surface: `setup`, `setup-models`, `dev`, `test`, `test-cov`, `lint`, `typecheck`, `verify`, `audit-security`, `audit-deps`, `audit-content`, `audit-pedagogy`. Phases 3+ add phase-specific verifies hanging off these.
- The ADR numbering convention (zero-padded, `docs/adrs/NNNN-*.md`). Phase 2 starts at ADR-0011.
- The risk register format. Every phase appends.

Phase 1 also commits to *not* doing certain things, which downstream phases inherit:
- No business logic. No DB schema. No real endpoint handlers. Phase 2 owns those.
- No CI gates that depend on external services (no live API calls, no real model downloads); CI is hermetic.

---

## 7. Invariants

The following must hold during and after Phase 1, forever:

- **I1**: `make verify` is green on `main`. A red `main` is a P0.
- **I2**: No service imports from another service's internals; cross-service usage goes through `packages/shared`. Enforced by `ruff` boundaries (`ban-relative-imports`) + a per-directory import-linter rule in Phase 2.
- **I3**: No commit on `main` without a PR-style review (single-maintainer projects: a self-review on a separate branch with at least one revision pass). Enforced socially in Phase 1; via branch-protection in Phase 2 when the repo goes to GitHub.
- **I4**: No secrets in the repo. `gitleaks` runs in pre-commit + CI. Adding a secret means rewriting history and rotating the secret.
- **I5**: The `data/` directory is gitignored. A custom pre-commit hook fails any commit that adds a file under `data/`. Corpora ship via the operator's ingestion pipeline, not via the repo.
- **I6**: Every public function has a typed signature, a docstring with an example, and a complexity note (master prompt §5.3). Enforced by `ruff` (D rules) + a custom pytest collector.
- **I7**: Modules ≤ 400 lines unless justified in a docstring (master prompt §5.3). Enforced by a custom `ruff` rule or a Python linter check.
- **I8**: The `00_MASTER_PROMPT.md` and `01..09_*.md` planning files are the spec; if code diverges, code is wrong, not the spec — unless an ADR + `CHANGELOG.md` entry amends the spec (master prompt §12).

These invariants are restated at the top of `CONTRIBUTING.md`.

---

## 8. What we are *not* solving in Phase 1

Explicit non-goals (to prevent scope creep):

- Database schema (Phase 2).
- Real API handlers (Phase 2 stubs them as 501; Phase 3+ implements).
- Any ML model code or weights (Phase 3+).
- Any content ingestion (Phase 3).
- Frontend pages beyond a hello-world (Phase 8).
- Authentication (Phase 2 sketches the contract; Phase 8 wires it up).
- Helm charts (Phase 9 if time permits; explicitly stretch).
- Native binary builds via PyInstaller/Tauri (Phase 9 stretch).
