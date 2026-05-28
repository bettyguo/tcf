# Contributing to tcf-accel

Thank you for considering a contribution. This project's mission is unusual:
it exists to help adults pass an immigration milestone. That mission imposes
discipline that you'll see throughout: honesty over engagement, evidence over
convenience, learner welfare over feature breadth.

If you're here to add a "streak" or "leaderboard" or "Pass guaranteed" badge,
please read `RATIONALE.md` first — these are pre-emptively refused.

---

## TL;DR — Five-Minute Setup

```bash
# Prereqs: git, Python 3.12+, Node 22+, uv, pnpm. WSL2 strongly recommended on Windows.

git clone <repo-url>
cd tcf-accel
make setup        # installs Python + JS deps + pre-commit hooks
make verify       # runs lint + typecheck + test; should be green
```

Windows-native (no WSL2): use `scripts/windows_dev.ps1` for the equivalent of
`make setup` / `make verify`. Most other targets assume POSIX shell.

---

## Project Invariants (Re-read Before Every PR)

These are **load-bearing**. Phase 1 (`phase1_think.md` §7) committed to them.

1. **`make verify` is green on `main`.** A red `main` is a P0.
2. **No service imports from another service's internals.** Cross-service
   usage goes through `packages/shared`.
3. **No commit on `main` without a review.** Single-maintainer projects:
   self-review on a separate branch with at least one revision pass.
4. **No secrets in the repo.** `gitleaks` enforces this in pre-commit + CI.
5. **The `data/` directory is gitignored.** A custom pre-commit hook fails any
   commit that adds a file under `data/`. Corpora come from the operator's
   ingestion pipeline, not from this repo.
6. **Every public function has a typed signature, a docstring with an example,
   and a complexity note.**
7. **Modules ≤ 400 lines unless justified in a docstring.**
8. **The `00_MASTER_PROMPT.md` and `01..09_*.md` planning files are the spec.**
   If code diverges, code is wrong, not the spec — unless an ADR + `CHANGELOG.md`
   entry amends the spec (master prompt §12).
9. **NCLC point estimates are never shown without their CI.** See `RATIONALE.md`
   R-006.
10. **No "Pass guaranteed" copy anywhere.** See `RATIONALE.md` R-002.

---

## Development Workflow

### Branching

- `main` is protected. All changes land via PR.
- Feature branches: `feat/<short-slug>`.
- Bug fixes: `fix/<short-slug>`.
- Docs / chore: `docs/<…>`, `chore/<…>`.

### Commits

Conventional Commits (`type(scope): subject`). Examples:

```
feat(scheduler): add FSRS-6 per-user param optimization
fix(api): redact learner text from error logs
docs(adr): record ADR-0011 — IRT 2PL vs 3PL
chore(deps): bump ruff to 0.16
```

Body explains *why*, not *what* (the diff shows what). For non-trivial changes,
reference the phase and any relevant ADR.

End every commit message with the harness footer (see `.gitmessage` template
if present):

```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Pull Requests

A PR is ready to merge when:

- [ ] `make verify` is green locally.
- [ ] CI is green.
- [ ] The PR description references the phase and any ADR(s).
- [ ] Tests added for new behavior; bug fixes include a regression test.
- [ ] Any new public API has a docstring + example.
- [ ] Any new module ≤ 400 lines or has an "exception" note in the docstring.
- [ ] If schemas in `packages/shared` changed: a migration note is in
      `CHANGELOG.md`, and any consumer using the changed field is updated in
      the same PR.
- [ ] If an architectural decision was made: an ADR is included in `docs/adrs/`.
- [ ] If a risk surfaced: `RISK_REGISTER.md` updated.
- [ ] If a directive was refused: `RATIONALE.md` updated.

For solo-maintainer projects, the same checklist applies — including the
"reviewed by someone other than the author" criterion. Self-review on a
separate branch, then one revision pass, then merge.

---

## Phase Discipline

The build proceeds in phases (`00_MASTER_PROMPT.md §4`). Each phase has a gate
that must be passed before the next begins. Don't write Phase N+1 code in a
Phase N branch. Each phase produces, at minimum:

- `phaseN_think.md` — the reasoning artifact (§5.1 of the master prompt).
- `phaseN_design.md` — the design artifact (§5.2).
- `phaseN_audit.md` — the audit results (§5.4).
- `phaseN_evaluate.md` — the acceptance check + handoff (§5.5).

A PR that crosses phase boundaries should be exceptional and called out
explicitly in the description.

---

## Tests

- **Unit**: `apps/<app>/tests/` or `packages/<pkg>/tests/`. Fast.
- **Integration**: `tests/integration/`. Uses the docker-compose stack.
- **Contract**: `tests/contract/`. Schemathesis against the frozen OpenAPI.
- **E2E**: `tests/e2e/`. Playwright; covers user journeys.
- **Pedagogy**: `tests/pedagogy/`. Synthetic-cohort + scheduler-invariant tests.
- **Property**: where applicable, use Hypothesis (e.g., schema round-trip,
  NCLC-estimator monotonicity).

LLM-backed tests use seeded fixtures + recorded responses (VCR-style). Never
let a flaky LLM gate CI. (Master prompt §6.5.)

---

## Local Tooling

- **Format**: `make format` (writes). `make lint` checks only.
- **Type-check**: `make typecheck`.
- **Run the dev stack**: `make dev` brings up Postgres/Redis/Qdrant + API + web.
- **Security audit**: `make audit-security`. Some tools (`trivy`) are CI-only.
- **License audit**: `make audit-deps`.

The Makefile is the source of truth for the dev loop. If you find yourself
running a long ad-hoc command, propose a target.

---

## Documentation

- New public function → docstring + example + complexity note.
- New architectural decision → ADR in `docs/adrs/`. Number sequentially.
- New runbook (operator-facing) → `docs/runbooks/`.
- New SLA citation → `docs/pedagogy/`.

The README and the `LIMITATIONS.md` (Phase 9) are the learner-facing surfaces
of the project. Keep them honest.

---

## Releasing

Releases are tag-driven (`vMAJOR.MINOR.PATCH`). `release.yml` builds Docker
images and publishes the release notes. Phase 9 elaborates the full release
process; for now, only maintainers cut tags.

Semver:
- MAJOR: a breaking change in the Phase 2 OpenAPI contract or in
  `packages/shared` schemas.
- MINOR: additive features, new ADRs, new content quotas.
- PATCH: bug fixes, security patches, doc updates.

---

## Getting Help

- Browse the planning docs in repo root (`00_MASTER_PROMPT.md`, `01..09_*.md`).
- Read existing ADRs (`docs/adrs/`).
- Open a Discussion (not an Issue) for design questions.
- Open an Issue for reproducible bugs.

Welcome aboard.
