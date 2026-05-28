# tcf-accel

> An open-source, evidence-based, exam-aligned French training system for
> candidates moving from CEFR **B1 → NCLC 9+ (C1)** on the **TCF Canada** in
> 12 weeks (≤ 84 days).

[![License: MIT (code)](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![License: CC BY-SA 4.0 (content)](https://img.shields.io/badge/content-CC%20BY--SA%204.0-lightgrey.svg)](CONTENT_LICENSE)
[![Status: pre-1.0 build](https://img.shields.io/badge/status-pre--1.0%20build-orange.svg)](#status)

---

## What it is

A self-hostable system that gives a learner:

- An evidence-aligned **12-week study plan** with daily blocks, regenerated
  whenever your skill posteriors shift.
- **Drills** for all four TCF Canada modules — Compréhension orale (CO),
  Compréhension écrite (CE), Expression écrite (EE), Expression orale (EO) —
  plus shadowing, dictation, pronunciation feedback, and supplementary
  sub-skill drills.
- **Spaced repetition** via FSRS-6 with LECTOR-style semantic-confusable
  spacing for vocabulary, collocations, and grammar patterns.
- A **full 2 h 47 min mock exam simulator** that mirrors the published FEI
  exam-day structure, with proctor mode and post-exam item-by-item review.
- **Auto-scoring** for EE writing and EO speaking with rubric-aligned feedback
  (per-criterion, error-annotated), calibrated against expert raters where
  available; κ published on every release.
- A **honest readiness signal**: traffic-light booking advice with credible
  intervals on every NCLC estimate. The system refuses to claim "ready" until
  two consecutive canonical mocks land green and all four skills are
  posterior-confident.

## What it is *not*

- A guarantee. The system does not promise a score. See `LIMITATIONS.md` (Phase 9).
- A path to **CEFR C2** in 12 weeks from B1. That target violates every
  credible CEFR guided-learning-hour estimate; see `RATIONALE.md` R-001.
  Realistic target band: NCLC 7 floor / NCLC 9 ceiling.
- A replacement for human tutoring on production-skill gaps. We link to
  italki, Tandem, HelloTalk for practice with native speakers (Library page).
- Accessible for the CO module to Deaf or hard-of-hearing candidates — the
  exam itself is the source of that inaccessibility. We provide a "CE/EE/EO
  only" mode and document the structural exam constraint clearly. See
  `RISK_REGISTER.md` R-007.

---

## Status

Pre-1.0. The build proceeds in nine phases (`00_MASTER_PROMPT.md §4`); each
phase has acceptance criteria and a gate. The repository currently lives
inside **Phase 1**: scaffolding, contracts, and the dev loop. Application
behavior begins to land in Phase 2 (architecture skeleton + API contracts) and
accelerates from Phase 3 (content pipeline).

For a phase-by-phase progress check, see each phase's `phaseN_evaluate.md`.

---

## Quickstart (5 minutes, after Phase 1)

### Prerequisites

- **git** 2.40+
- **Python 3.12+** (3.13 supported)
- **Node 22+** with **pnpm 9+**
- **uv 0.5+** (Python dep + workspace manager): `pip install --user uv` or
  see [installation docs](https://docs.astral.sh/uv/getting-started/installation/)
- **Docker** + **Docker Compose** v2 (for Postgres/Redis/Qdrant)
- **Linux / macOS / WSL2 on Windows** for the Makefile-driven dev loop
  (Windows-native: use `scripts/windows_dev.ps1`)

### Setup

```bash
git clone <repo-url>
cd tcf-accel
make setup        # installs Python + JS deps + pre-commit hooks; ~5 min on a warm cache
make verify       # lint + typecheck + test; should print "green"
```

`make verify` is the **only** command you need to remember before pushing.

### Run the dev stack

```bash
make dev          # brings up Postgres/Redis/Qdrant via docker-compose, then API on :8000 and web on :3000
```

### Phase 3+ — populate the item bank

After Phase 3 has shipped:

```bash
make setup-models                       # one-time pull of Whisper-fr + CEFR classifier + embeddings
python scripts/seed_bank.py             # ~6 hours on a 16-core machine
```

`scripts/seed_bank.py` only ingests open-license sources. To ingest news
audio (RFI, TV5MONDE, ICI Première, Radio-Canada), see `docs/runbooks/news_ingest.md`
(Phase 3) and respect publisher TOS — the cached content lives in `data/`
(gitignored) and is never redistributed.

---

## How it works

```
┌────────────┐   ┌───────────────┐   ┌────────────────┐
│  Learner   │──▶│  Web (Next15) │──▶│   API (FastAPI)│
└────────────┘   └───────────────┘   └───────┬────────┘
                                             │
              ┌──────────────────────────────┼────────────────────┐
              ▼                              ▼                    ▼
       ┌─────────────┐               ┌────────────┐       ┌──────────────┐
       │  Planner    │               │ Estimator  │       │ Scoring +    │
       │ (FSRS+      │               │ (Bayesian  │       │ Feedback     │
       │  LECTOR +   │               │  NCLC      │       │ (EE/EO       │
       │  Allocator) │               │  posterior)│       │  rubrics)    │
       └─────┬───────┘               └─────┬──────┘       └──────┬───────┘
             │                             │                     │
             └────────────────┬────────────┴─────────────────────┘
                              ▼
             ┌─────────────────────────────────────┐
             │   Postgres + pgvector + Redis       │
             └─────────────────────────────────────┘
                              ▲
                              │
                ┌─────────────┴────────────────┐
                │  Worker (Celery)             │
                │  - content pipeline ingest   │
                │  - ASR + alignment           │
                │  - LLM scoring + critic      │
                │  - mock exam grading         │
                └──────────────────────────────┘
```

For the detailed architecture, read `02_ARCHITECTURE.md` (or, after Phase 2,
the rolled-up `docs/ARCHITECTURE.md` and the ADRs in `docs/adrs/`).

---

## Pedagogy in one paragraph

We enforce eight evidence-aligned SLA principles (master prompt §2.1):
comprehensible input + 1 (Krashen i+1) via CEFR-classified item placement;
pushed output (Swain) via mandatory daily production minimums; spaced
retrieval via **FSRS-6**; **LECTOR**-style semantic spacing for confusable
families (`amener/emmener`, etc.); deliberate practice on weakness (the
allocator over-weights the production-skill bottleneck β = 1.4 EE, β = 1.5 EO);
daily shadowing for prosody; interleaved retrieval in mocks; and a testing-effect
ramp (mocks biweekly → weekly → 3×/week in the final fortnight).

The system optimizes the **minimum** across skills, not the average — because
the immigration rule (IRCC NCLC, §1.2 of the master prompt) caps the profile
on the lowest skill, not the mean.

---

## Honesty defaults

- **NCLC estimates** ship with credible intervals; the system refuses to show
  a number until `confident=True` (n_obs ≥ 40, variance ≤ 0.4, difficulty-band
  spread ≥ 3).
- **Readiness 🟢** requires *two consecutive* canonical-mock 🟢 sessions
  *and* all four skills `confident=True`.
- **Privacy default** is `local_only`. ASR runs on-device. Cloud LLM/ASR is
  opt-in only.
- **Pronunciation feedback** is labelled "coarse proxy" everywhere; we are
  modest about what a phoneme error rate can tell you.
- **No streaks, no leaderboards, no fear-based notifications.**

---

## Tech stack (defaults; see ADRs for rationale)

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Background jobs | Celery + Redis |
| DB | PostgreSQL 16 + pgvector (Qdrant swap-in via config) |
| Frontend | Next.js 15 App Router, React 19, Tailwind 4, shadcn/ui |
| ASR | `bofenghuang/whisper-large-v3-french` via faster-whisper |
| Alignment | Montreal Forced Aligner |
| CEFR classifier | CamemBERT-based (fine-tuned from `JonathanStefanov/CEFR_Classifier_French`) |
| LLM gateway | `litellm`; default model `claude-sonnet-4-6` |
| Embeddings | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` |
| Testing | pytest, hypothesis, vitest, playwright, k6 |
| Packaging | `uv` (Python), `pnpm` (JS) |
| CI | GitHub Actions (Linux + macOS) |
| Deploy | Docker Compose (solo); Helm chart (institutions; Phase 9) |

---

## Repository layout

```
apps/        # api, web, worker
packages/    # shared (Phase 1 contracts), sla, ml, content
infra/       # docker-compose, migrations
docs/        # ADRs, pedagogy dossier, API reference, runbooks
tests/       # unit, integration, contract, e2e, pedagogy
scripts/     # license_check, abandoned_check, seed_bank (Phase 3), download_models
00_MASTER_PROMPT.md, 01..09_*.md   # the planning docs
phase1_*.md  # phase artifacts (think / design / audit / evaluate)
Makefile, pyproject.toml, pnpm-workspace.yaml, .pre-commit-config.yaml
LICENSE, CONTENT_LICENSE, SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md
RATIONALE.md   # refusal log
RISK_REGISTER.md
CHANGELOG.md
```

---

## Contributing

See `CONTRIBUTING.md` for the dev loop, branching, commits, PR checklist, and
the project invariants you should re-read before every PR. The phase
discipline is enforced; don't write Phase N+1 code in a Phase N branch.

---

## License

- Software: **MIT** (`LICENSE`).
- Original learning content: **CC BY-SA 4.0** (`CONTENT_LICENSE`).
- Third-party content keeps its own license; recorded in each item's
  `provenance.license`.

See ADR-0010 for the dual-licensing rationale.

---

## References

- TCF Canada official source: <https://www.france-education-international.fr/test/tcf-canada>
- IRCC NCLC scale: <https://www.canada.ca/en/immigration-refugees-citizenship.html>
- FSRS: <https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler>
- LECTOR (semantic-aware scheduling): arxiv 2508.03275
