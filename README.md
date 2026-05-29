# tcf-accel

> An open-source, evidence-based, exam-aligned French training system for
> candidates moving from CEFR **B1 → NCLC 7–9** on the **TCF Canada** in
> 12 weeks (≤ 84 days).

[![License: MIT (code)](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![License: CC BY-SA 4.0 (content)](https://img.shields.io/badge/content-CC%20BY--SA%204.0-lightgrey.svg)](CONTENT_LICENSE)
[![Status: v1.0.0](https://img.shields.io/badge/status-v1.0.0-brightgreen.svg)](#status)
[![Honesty receipts](https://img.shields.io/badge/honesty-receipts-blue.svg)](#honesty-receipts)
[![Limitations](https://img.shields.io/badge/read-LIMITATIONS.md-orange.svg)](LIMITATIONS.md)

> **Before you read further:** [`LIMITATIONS.md`](LIMITATIONS.md) is a
> load-bearing document. It tells you what the system does *not* do.
> If anything there is a deal-breaker for you, choose another path.
> That is by design.

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
  available; κ published with every release (see [Honesty receipts](#honesty-receipts)).
- A **honest readiness signal**: traffic-light booking advice with credible
  intervals on every NCLC estimate. The system refuses to claim "ready" until
  two consecutive canonical mocks land green and all four skills are
  posterior-confident.

## What it is *not*

- A guarantee. The system does not promise a score. See [`LIMITATIONS.md`](LIMITATIONS.md).
- A path to **CEFR C2** in 12 weeks from B1. That target violates every
  credible CEFR guided-learning-hour estimate; see [`RATIONALE.md`](RATIONALE.md) R-001.
  Realistic target band: **NCLC 7 floor / NCLC 9 ceiling**.
- A replacement for human tutoring on production-skill gaps. We link to
  italki, Tandem, HelloTalk for practice with native speakers (Library page).
- Accessible for the CO module to Deaf or hard-of-hearing candidates — the
  exam itself is the source of that inaccessibility. We provide a "CE/EE/EO
  only" mode and document the structural exam constraint clearly. See
  [`RISK_REGISTER.md`](RISK_REGISTER.md) R-007 and [`LIMITATIONS.md §3`](LIMITATIONS.md).

---

## Status

**v1.0.0 — launched 2026-05-28.** All nine phase gates (Phases 1–9 of
`00_MASTER_PROMPT.md §4`) cleared; the Launch Readiness Report is
signed and committed to the repo: [`LAUNCH_READINESS_REPORT.md`](LAUNCH_READINESS_REPORT.md).

For the per-phase progress checks, see each phase's `phaseN_evaluate.md`.

---

## Quickstart (5 minutes)

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

### Populate the item bank

```bash
make setup-models                       # one-time pull of Whisper-fr + CEFR classifier + embeddings
python scripts/seed_bank.py             # ~6 hours on a 16-core machine
```

`scripts/seed_bank.py` only ingests open-license sources. To ingest news
audio (RFI, TV5MONDE, ICI Première, Radio-Canada), see
[`docs/runbooks/news_ingest.md`](docs/runbooks/news_ingest.md) and respect
publisher TOS — the cached content lives in `data/` (gitignored) and is
never redistributed.

For full operational guidance see [`OPERATIONS.md`](OPERATIONS.md).

---

## Honesty receipts

> The numbers below are regenerated on every release by
> `scripts/release/sign_audit_report.py --update-readme-receipts`. The
> markers around this section are stable; the contents are not. If
> these tables are out of date, the release script wasn't run.

<!-- HONESTY-RECEIPTS:START -->

### Auto-scoring κ (Cohen's quadratic-weighted, EE/EO rubric)

> **Experimental badge** active: v1.0 ships κ_silver against an
> LLM critic. We have not yet acquired the 200-row expert-rater
> dataset that ADR-037 requires for a κ_gold claim. v1.1 commits
> to acquiring it; see R-010 and [`LIMITATIONS.md §4`](LIMITATIONS.md).

| Dimension | κ (silver) | r | MAE | n |
|---|---|---|---|---|
| `task_completion` | 1.000 | 0.996 | 0.072 | 12 |
| `coherence_cohesion` | 1.000 | 0.995 | 0.080 | 12 |
| `lexical_range` | 1.000 | 0.993 | 0.093 | 12 |
| `grammatical_accuracy` | 1.000 | 0.994 | 0.086 | 12 |
| `register_appropriateness` | 1.000 | 0.987 | 0.140 | 12 |
| `canadian_context_integration` | 0.982 | 0.993 | 0.133 | 12 |

Training-set hash: `7591d824b2101399…`. Source:
[`data/calibration/ee.v1.report.md`](data/calibration/ee.v1.report.md).

### Synthetic-cohort pedagogy audit (Phase 9)

> 12 cohorts × 100 stochastic trajectories. P(success) = probability
> the weakest skill clears target NCLC at exam day. Source:
> [`data/audit/phase9/pedagogy_audit.json`](data/audit/phase9/pedagogy_audit.json).
> Calibration plot:
> [`data/audit/phase9/pedagogy_calibration.md`](data/audit/phase9/pedagogy_calibration.md).
> Test: [`tests/pedagogy/launch_audit.py`](tests/pedagogy/launch_audit.py).

| Cohort | kind | target | days | budget/day | planner projected_min | simulated median_min | P(success) |
|---|---|---|---|---|---|---|---|
| solid_B1_target_NCLC7 | realistic | 7 | 84 | 150 min | 7.10 | 7.15 | 1.00 |
| solid_B1_target_NCLC9 | honest_refusal | 9 | 84 | 150 min | 7.20 | 7.19 | 0.00 |
| uneven_target_NCLC7 | realistic | 7 | 84 | 150 min | 7.10 | 7.15 | 1.00 |
| strong_B2_target_NCLC9 | realistic | 9 | 84 | 150 min | 9.10 | 9.15 | 1.00 |
| aggressive_B1_target_C2 | honest_refusal | 11 | 84 | 150 min | 7.10 | 7.06 | 0.00 |
| short_runway_target_NCLC7 | honest_refusal | 7 | 42 | 150 min | 6.10 | 6.10 | 0.00 |
| low_budget_target_NCLC7 | honest_refusal | 7 | 84 | 60 min | 5.80 | 5.75 | 0.00 |
| already_at_target | trivial | 9 | 84 | 150 min | 9.80 | 9.78 | 1.00 |
| heritage_production_gap | realistic | 7 | 84 | 150 min | 7.40 | 7.38 | 1.00 |
| reception_only_weakness | realistic | 7 | 84 | 150 min | 7.20 | 7.22 | 1.00 |
| ee_bottleneck_only | realistic | 8 | 84 | 150 min | 8.20 | 8.24 | 1.00 |
| eo_bottleneck_only | realistic | 8 | 84 | 150 min | 8.20 | 8.23 | 1.00 |

**Calibration:** the planner-projected min and the simulated
median agree within ±0.05 NCLC across all 12 cohorts (the gate
is ±0.5). **Honest refusal:** for every cohort the planner refuses,
the simulator agrees (P(success) ≤ 0.10).

<!-- HONESTY-RECEIPTS:END -->

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

For the detailed architecture, read [`ARCHITECTURE.md`](ARCHITECTURE.md)
(rolled-up from the 48 ADRs under `docs/adrs/`).

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

For the SLA evidence dossier, see [`PEDAGOGY.md`](PEDAGOGY.md).

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
| Deploy | Docker Compose (solo); Helm chart (institutions) |

---

## Repository layout

```
apps/        # api, web, worker
packages/    # shared (Phase 1 contracts), sla, ml, content
infra/       # docker-compose, migrations, helm
docs/        # ADRs, pedagogy dossier, API reference, runbooks, roadmap
tests/       # unit, integration, contract, e2e, pedagogy, load
scripts/     # license_check, abandoned_check, seed_bank, download_models, release/
00_MASTER_PROMPT.md, 01..09_*.md   # the planning docs
phase{1..9}_*.md  # phase artifacts (think / design / audit / evaluate)
README.md, LIMITATIONS.md, LEARNER_GUIDE.md, PEDAGOGY.md, ARCHITECTURE.md, OPERATIONS.md
LAUNCH_READINESS_REPORT.md   # the v1.0.0 launch decision record
LICENSE, CONTENT_LICENSE, SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md
RATIONALE.md, RISK_REGISTER.md, CHANGELOG.md
Makefile, pyproject.toml, pnpm-workspace.yaml, .pre-commit-config.yaml
```

---

## For learners

If you are a candidate considering this system: read
[`LIMITATIONS.md`](LIMITATIONS.md) first, then
[`LEARNER_GUIDE.md`](LEARNER_GUIDE.md) for the 12-week journey.

## For operators

If you are standing this up for yourself or a small group: read
[`OPERATIONS.md`](OPERATIONS.md). The cost-of-operation breakdown
is in §11.

## For contributors

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the dev loop, branching,
commits, PR checklist, and project invariants. The phase discipline
is enforced — don't write Phase N+1 code in a Phase N branch.

---

## License

- Software: **MIT** ([`LICENSE`](LICENSE)).
- Original learning content: **CC BY-SA 4.0** ([`CONTENT_LICENSE`](CONTENT_LICENSE)).
- Third-party content keeps its own license; recorded in each item's
  `provenance.license`.

See ADR-0010 for the dual-licensing rationale.

---

## References

- TCF Canada official source: <https://www.france-education-international.fr/test/tcf-canada>
- IRCC NCLC scale: <https://www.canada.ca/en/immigration-refugees-citizenship.html>
- FSRS: <https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler>
- LECTOR (semantic-aware scheduling): arxiv 2508.03275
