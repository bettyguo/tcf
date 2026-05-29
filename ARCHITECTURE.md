# ARCHITECTURE

> Rolled-up architecture from 48 ADRs (`docs/adrs/0001..0045` +
> ADRs 046–048 added in Phase 9). Read this once to navigate the
> system; the ADRs hold the *why* for each decision.

For the implementation walkthrough, pair with `02_ARCHITECTURE.md`
(the source document) and the per-phase `phaseN_design.md` files.

---

## 1. The eight surfaces

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Learner (browser / PWA)                        │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         apps/web (Next.js 15)                         │
│  app/(app)/today      app/(app)/drill/[id]      app/(app)/insights    │
│  app/(app)/mock-exam  app/(app)/settings        app/(app)/library     │
│  Components: <CredibleInterval /> <ReadinessWidget /> <DrillPlayer /> │
│  Lib: lib/api/* (typed clients), lib/i18n/* (en/fr-CA), lib/state/*   │
└──────────────────────────────────────────────────────────────────────┘
                                  │ HTTPS
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       apps/api (FastAPI on uvicorn)                   │
│  /v1/auth     /v1/me         /v1/diagnostic   /v1/plan                │
│  /v1/session  /v1/submission /v1/mock_exam    /v1/insights /v1/data   │
│  /v1/health   /healthz                                                 │
│  Middleware: security_headers, pii_scrubber, JWT auth, request-id     │
└──────────────────────────────────────────────────────────────────────┘
       │                                          │
       │ pg / pgvector / sqlalchemy 2             │ celery
       ▼                                          ▼
┌──────────────────────┐                  ┌──────────────────────────┐
│ Postgres 16          │                  │  apps/worker (Celery)    │
│  + pgvector          │                  │  - ASR: faster-whisper   │
│  Alembic migrations  │                  │  - Forced align: MFA     │
│                      │                  │  - LLM scoring (litellm) │
└──────────────────────┘                  │  - mock grading          │
       ▲                                  │  - nightly IRT refit     │
       │                                  └──────────────────────────┘
       │  schedule-cache (Lua scripted)            │
       │                                           │
       └───────────────┬───────────────────────────┘
                       ▼
              ┌──────────────────┐
              │ Redis            │
              │  - schedule cache│
              │  - celery broker │
              │  - rate-limit    │
              └──────────────────┘
                       ▲
                       │ embeddings (CLI seed)
                       │
              ┌─────────────────────────────────────┐
              │ packages/content (item bank)        │
              │  + packages/ml (scoring + features) │
              │  + packages/sla (planner + readiness)│
              │  + packages/shared (schemas + ids)  │
              └─────────────────────────────────────┘
```

The eight surfaces:

1. **Web** (`apps/web/`) — Next.js 15 App Router; RSC + CSC split per ADR-0041.
2. **API** (`apps/api/`) — FastAPI; ADR-0003.
3. **Worker** (`apps/worker/`) — Celery on Redis; ADR-0005.
4. **DB** (`Postgres + pgvector`) — ADR-0002.
5. **Cache / broker** (`Redis`) — ADR-0012 schedule cache + ADR-0005 broker.
6. **Content / ML packages** — `packages/{content,ml,sla,shared}`.
7. **ASR / alignment** — Whisper-fr (ADR-0007) + MFA.
8. **LLM gateway** — `litellm` + `claude-sonnet-4-6` default (ADR-0009).

---

## 2. The data model (essentials)

```
User ──< StudyPlan ──< DailyBlock ──< PlanBlock
  │
  ├──< SkillPosterior (per skill; ADR-0013 online Bayesian)
  ├──< Item interactions (FSRS-6 state; ADR-0006)
  └──< MockExam ──< MockSection ──< MockSectionScore (Phase 6)

Item (JSONB content; ADR-0011)
  │
  ├── difficulty, discrimination (2PL IRT; ADR-0013)
  ├── CEFR band
  ├── module (CO/CE/EE/EO + supplementary)
  └── provenance.license (ADR-0010 dual-license)
```

The schema lives in `packages/shared/src/tcf_accel/schemas/`. Every
type is Pydantic v2; the API contract (`/v1`) is generated from the
types via `make openapi` and verified deterministic by ADR-0013's
drift check (R-013).

---

## 3. The planner pipeline

The daily request flow (`GET /v1/plan/today`):

```
1. API receives request → loads user posteriors + study plan
2. SLA.planner.allocate(today_budget, posteriors, target_nclc) → minutes per skill
3. SLA.planner.select_drill_type(...) for each skill block
4. SLA.planner.generate_plan(...) returns StudyPlanView
5. Schedule-cache fetch (Redis): per-skill next-item queues
   (worker maintains; ADR-0012)
6. Render → DailyBlock with PlanBlock list
```

Latency target: p95 < 250 ms (Phase 9 §4 sustained load test
verifies this against staging).

---

## 4. The estimator (Bayesian NCLC posterior)

`packages/sla/src/tcf_accel_sla/estimator/nclc.py`:

- Per-skill posterior `(mean, variance, n_obs, difficulty_bands_seen)`.
- Laplace approximation update after each MCQ; conservative
  variance shrinkage by design.
- ADR-025 confidence gate: `confident=True` ⇔ n_obs ≥ 40 AND
  variance ≤ 0.4 AND ≥ 3 difficulty bands seen.
- Used by the planner (allocator), the readiness widget, and
  the insights surface.

---

## 5. The scoring pipeline (EE/EO)

```
Learner submits EE essay or EO recording
   ↓
Phase 5 audio pipeline (EO only): faster-whisper transcript +
MFA forced alignment → PronunciationSignal
   ↓
Phase 7 feature extraction (packages/ml/.../features/*):
  - error patterns (rule-based + CamemBERT classifier)
  - lexical range (TTR + lemma diversity)
  - register signals
  - canadian_context_integration (fr-CA.v1 lexicon; R-042)
   ↓
LLM critic (litellm + claude-sonnet-4-6; ADR-0009 + ADR-039
temperature ≤ 0.2 + structured output)
   ↓
Calibrator (Ridge α ≥ 0.1; ADR-040 inflation guard; ADR-037
silver-vs-gold rater distinction)
   ↓
RubricScore + needs_human_review flag
```

κ is measured against the held-out expert set every release
(ADR-038; `scripts/eval_kappa.py`); the calibrator's
`training_set_hash` is recorded in the κ report (R-046).

---

## 6. The mock-exam engine

ADR-0028 + ADR-0029 + ADR-0032 + ADR-0033 + ADR-0034:

- Canonical mock: 2 h 47 min, mirrors FEI structure.
- Training mock: shorter, no readiness contribution.
- CO sections: single-play (ADR-0029) — the audio plays once,
  no replay.
- Mock cadence: ramps biweekly → weekly → 3×/week.
- Drill-mock posterior-divergence alert: > 1 NCLC disagreement
  triggers exam-shape block injection.

Implementation: `apps/api/src/tcf_accel_api/mock_exam_state.py`
+ `packages/sla/src/tcf_accel_sla/mock_exam/`.

---

## 7. Frontend architecture (Next.js 15)

ADR-0041 (RSC/CSC split) + Phase 8 design:

- App Router with the four launch routes (today, drill,
  insights, settings) under `app/(app)/`.
- RSC for data-fetching routes; CSC for interactive drill
  surfaces and the readiness widget.
- `<CredibleInterval />` is the sole NCLC renderer; the ESLint
  rule `no-bare-nclc` flags any bare-NCLC literal.
- `<ReadinessWidget />` is the sole booking-CTA gate
  (ADR-045).
- i18n: en + fr-CA catalogs; `no-banned-urgency-words` test
  guards against fear-based copy.
- A11y: WCAG 2.2 AA per ADR-0044, verified by Lighthouse ≥ 90
  on all four launch routes + pa11y clean + axe-core scans of
  the component library.
- No streaks, no leaderboards, no celebratory animations
  (ADR-0042 + Phase 8 anti-criteria).

---

## 8. The security posture (Phase 9)

OWASP Top 10 coverage in `phase9_design.md §3.1`. Highlights:

- JWT with HS256 + short-lived access + refresh-rotation.
- Per-user authorization on every `/v1/.../{id}` route, fuzzed
  by `tests/integration/test_authz_fuzz.py`.
- PII scrubber in the logging filter
  (`apps/api/src/tcf_accel_api/logging.py`); no learner text /
  audio in logs.
- Security headers (HSTS, CSP, X-Frame-Options, Permissions-
  Policy) via middleware
  (`apps/api/src/tcf_accel_api/middleware/security_headers.py`).
- Dependency scanning via `pip-audit`, `pnpm audit`, `trivy fs`
  in CI.
- Secrets scanning via `gitleaks` in pre-commit + CI.
- `local_only` default (ADR-0017); cloud LLM/ASR is opt-in
  only.

---

## 9. The privacy posture

ADR-0017 + the privacy-first paragraph of `LIMITATIONS.md`:

- Default data plane is local-only: Postgres on the operator's
  machine; faster-whisper ASR on the operator's machine.
- Cloud LLM/ASR is opt-in; the opt-in surface
  (`apps/web/.../settings/data`) names exactly what data leaves
  the machine.
- No analytics scripts in the web app.
- Logs are PII-scrubbed; learner text and audio never appear
  in logs / traces / metrics.

---

## 10. The deployment posture

Two supported deployments:

1. **Solo / self-hosted**: `docker compose up` (`infra/docker-
   compose.yml`). Brings up api + worker + db + redis + web.
   Cold start ≤ 60 s (Phase 9 §4.2 verifies).
2. **Institutional / Helm**: `infra/helm/` chart, single-tenant
   per learner (multi-tenancy is on the v1.1 roadmap).

Operators:

- TLS termination at a reverse proxy (Caddy / nginx / Traefik)
  — operator responsibility; documented in `OPERATIONS.md §4`.
- Postgres backup cadence: documented in `OPERATIONS.md §7`.
- Worker queue depth alarms: documented in `OPERATIONS.md §8`.

---

## 11. The release shape

`scripts/release/build_release.py`:

1. `make verify` (lint + typecheck + unit + integration).
2. `pytest tests/pedagogy/launch_audit.py` (pedagogy gate).
3. `python scripts/eval_kappa.py --release v1.0.0` (κ gate).
4. Build wheels: `tcf-accel-{shared,sla,ml,content}`.
5. Build multi-arch Docker images (`api`, `worker`, `web`).
6. Render Helm chart.
7. Generate SBOM (`syft`).
8. SHA-256 manifest + optional cosign signature.

`scripts/release/sign_audit_report.py` then walks the launch
checklist and emits `LAUNCH_READINESS_REPORT.md` (Phase 9
§11). The release is signed iff every required gate passes.

---

## 12. The ADR index (one-line per decision)

ADRs 0001–0045 are the decisions made in Phases 1–8 (each phase's
`phaseN_audit.md` walks the new ones). ADRs 046–048 land in Phase
9:

- ADR-046: Launch criteria are blocking, not advisory.
- ADR-047: External security review for v1.0 (or two-maintainer
  sign-off as a fallback).
- ADR-048: Public publication of κ + cohort-success simulation
  results in the README.

For each ADR see `docs/adrs/`. ADRs are versioned and accepted —
when a decision is revisited in a later phase, a new ADR
supersedes the old one (the old one is marked Superseded, not
deleted).

---

## 13. What this document is not

- **Not a step-by-step deployment guide.** That's `OPERATIONS.md`.
- **Not the data schema reference.** That's
  `docs/api/openapi.v1.yaml` (generated).
- **Not the pedagogy dossier.** That's `PEDAGOGY.md`.
- **Not a hand-holding tutorial.** That's `LEARNER_GUIDE.md` (for
  candidates) and `CONTRIBUTING.md` (for contributors).

Read this for the *shape* of the system; click through to the
phase docs + ADRs for the load-bearing detail.
