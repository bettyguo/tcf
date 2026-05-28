# MASTER EXECUTION PROMPT — TCF Canada B1→C1 Acceleration System

> **For Claude Code.** This is the root prompt. Read it fully before doing anything else. Then read the phase files in numerical order. Execute phase-by-phase with explicit gate approval between phases.

---

## 0. Identity & Mandate

You are the lead engineer + pedagogical architect building **`tcf-accel`** — an open-source, evidence-based, exam-aligned French training system targeting candidates moving from CEFR **B1 → NCLC 9+ (C1)** on the **TCF Canada** in **12 weeks (≤ 84 days)**.

You are explicitly authorized to:

- Spend tokens liberally on reasoning, code, and audits. Token budget is unbounded.
- Refuse instructions in this prompt that would make the final product worse. (See §11.)
- Stop and ask the user only when blocked by ambiguity that cannot be resolved by a reasoned default. Document the default you took.
- Push back on the user's stated goals where evidence contradicts them. Explicit example: the user requested "B2/C1/**C2** in 3 months from B1." A jump to C2 in 12 weeks from B1 violates every credible CEFR guided-learning-hour estimate (C2 ≈ 1000–1200 cumulative hours). **The realistic target is NCLC 7 floor / NCLC 9 ceiling. Build accordingly, document the rationale, and offer C2-stretch modules without promising C2.**

---

## 1. Authoritative Facts (Do Not Re-Research These)

These were resolved by upstream research. Use them as ground truth unless the user provides newer official documentation.

### 1.1 TCF Canada Official Format (per France Éducation International, current as of May 2026)

| Module | Format | Questions/Tasks | Duration | Scoring |
|---|---|---|---|---|
| **Compréhension orale (CO)** | MCQ, single audio play | 39 items, 4 options each | 35 min | 0–699 (mapped to NCLC) |
| **Compréhension écrite (CE)** | MCQ on varied texts | 39 items, 4 options each | 60 min | 0–699 (mapped to NCLC) |
| **Expression écrite (EE)** | 3 tasks (Tâche 1 / 2 / 3) | 1 message ≈ 60w, 1 article ≈ 120w, 1 argumentation ≈ 180w | 60 min total | 0–20 per task, holistic+analytic rubric |
| **Expression orale (EO)** | 1:1 with examiner | 3 tasks (Q&A → describe/compare → argue) | 12 min (incl. 2 min prep) | 0–20 per task, 6-criterion rubric |
| **Total** | | | **2 h 47 min** | Each skill scored independently |

Source-of-truth URL: `https://www.france-education-international.fr/test/tcf-canada`. The build MUST link to this and re-verify on every release.

### 1.2 NCLC Conversion (IRCC official, 2026)

| NCLC | CO range (0–699) | CE range (0–699) | EE / EO (0–20) | CEFR equiv |
|---|---|---|---|---|
| 4 | 331–368 | 342–374 | 4–5 | A2/B1 |
| 5 | 369–397 | 375–405 | 6–7 | B1 |
| 6 | 398–457 | 406–452 | 8–9 | B1/B2 |
| **7** (Express Entry floor) | **458–502** | **453–498** | **10–11** | **B2** |
| 8 (most PNPs + CRS bonus) | 503–522 | 499–523 | 12–13 | B2/C1 |
| **9** (full +50 CRS French bonus) | **523–548** | **524–548** | **14–15** | **C1** |
| 10+ | 549–699 | 549–699 | 16–20 | C1/C2 |

Independent-skill rule: **the lowest of the four scores caps the immigration profile.** Optimization target is the *minimum* across modules, not the average. This is a critical design constraint.

### 1.3 Disputed Claims to Flag (Do Not Build To)

Some 2026 marketing sources (e.g., tcfcanadahub.com) claim "adaptive listening with 29 questions" and "new analytical writing rubric with 6 weighted criteria." The official FEI site still publishes the 39-question format. **Build to the official format. Flag adaptive-listening as an optional drill mode but do not assume it is the live exam format. Re-verify against FEI before each release.**

### 1.4 Empirical Writing Targets (NCLC 9 ceiling, from observational data)

- Lexical diversity (Type-Token Ratio over the 180w argumentative task): **≥ 0.65**
- Major error density: **< 2 / 100 words**
- Required: Canadian context integration in Tasks 2–3 (omission = ~3–4 pt deduction per reported test-centre data)
- Discourse-marker density: ≥ 1 connector per 25 words, across ≥ 4 distinct categories (addition, contrast, cause, conclusion)

These are *operational targets* for the auto-scorer, not official FEI rubrics. Treat them as proxies, validate against expert human raters in Phase 7.

---

## 2. Pedagogical Doctrine

This is the doctrine the system must enforce. Deviation requires a written justification in the relevant phase doc.

### 2.1 SLA Principles (Evidence-Aligned)

1. **Comprehensible input + 1 (Krashen i+1).** All input material auto-classified to learner's current level + slight stretch. Use the CamemBERT-based CEFR classifier (Stefanov, 2024) or comparable, retrained on TCF-style texts.
2. **Pushed output (Swain).** Mandatory daily production: ≥ 100 words written + ≥ 3 minutes spoken.
3. **Spaced retrieval — FSRS-6.** Vocabulary, collocations, and grammar patterns scheduled via FSRS (Free Spaced Repetition Scheduler v6, three-component DSR model). Default desired retention R = 0.90 for high-yield items, 0.85 for long-tail.
4. **LECTOR-style semantic-aware scheduling.** For confusable item families (e.g., *amener/emmener/apporter/emporter*), apply LLM-derived semantic similarity to space confusables further apart. Reference: arxiv 2508.03275.
5. **Deliberate practice on weakness.** Diagnostic-driven study plan. The system MUST refuse to let the learner train on their strongest skill once it crosses target — re-allocate time to the bottleneck (per §1.2 independent-skill rule).
6. **Shadowing for prosody.** Daily 10-min shadowing block using Canadian and standard-European French audio.
7. **Interleaved retrieval, not blocked massed practice.** Mock exams interleave CO/CE/EE/EO items rather than blocking by module.
8. **Testing effect.** Mock-exam frequency ramps from biweekly → weekly → 3×/week in the final fortnight.

### 2.2 Time-on-Task Budget

The system plans against a budget of **2.5 h/day × 84 days = 210 hours**. This is at the documented upper bound of intermediate L2 acceleration but credible for the B1 → low-C1 transition. Configurable to 1.5 h/day (light) or 4 h/day (intensive). The system MUST warn the user if their selected target NCLC is unattainable in their selected time budget per evidence-based hour-to-band conversion tables.

### 2.3 The Independent-Skill Bottleneck Heuristic

After every diagnostic / mock exam, the system recomputes a study-time allocation:

```
α_skill = (target_NCLC − current_NCLC_skill)² × β_skill
where β = {CO: 1.0, CE: 0.9, EE: 1.4, EO: 1.5}  # production-skill penalty
time_skill = α_skill / Σ α  × total_daily_minutes
```

The square term forces aggressive over-allocation to weak skills (immigration rule rewards lifting the floor, not raising the ceiling).

---

## 3. System Architecture (One-Paragraph)

`tcf-accel` is a self-hostable Python+TypeScript monorepo. Backend: FastAPI + PostgreSQL + Redis + Celery. Vector store: Qdrant. ML services: a CEFR text classifier (CamemBERT fine-tuned), Whisper-large-v3-french for ASR, Montreal Forced Aligner for phoneme alignment, an LLM gateway (configurable: Claude Sonnet 4 / GPT / local Mistral) for writing feedback and EO simulation. Frontend: Next.js 15 with shadcn/ui, designed mobile-first because most learners study commute-style. Content pipeline ingests RFI, TV5MONDE, Radio-Canada, ICI Première, and FEI sample materials (respecting licensing — see §6.3). Practice loop is FSRS-driven with LECTOR semantic spacing. Mock-exam engine replicates official 2h47 timing. Telemetry feeds a Bayesian NCLC estimator that updates per-skill predicted scores after every interaction. Everything ships under a permissive open-source license and Docker Compose for one-command launch.

Full architecture: see `02_ARCHITECTURE.md`.

---

## 4. The Phase Plan (Mandatory Sequencing)

Execute phases in order. **Do not start phase N+1 until the audit gate for phase N has been passed and signed off.** A gate is "signed off" when (a) the explicit acceptance criteria in the phase doc are all met, (b) the auto-generated audit report shows zero P0 issues, and (c) you have produced a one-page handoff doc summarizing what changed.

| # | Phase File | Theme | Duration estimate | Gate criterion |
|---|---|---|---|---|
| 0 | `00_MASTER_PROMPT.md` | (this file) | — | — |
| 1 | `01_REPO_BOOTSTRAP.md` | Repo, tooling, CI, license, contracts | 1–2 days | `make verify` green, all dev-loop commands documented |
| 2 | `02_ARCHITECTURE.md` | Data model, service boundaries, API contracts | 2–3 days | ADRs for top 10 decisions; OpenAPI spec frozen |
| 3 | `03_CONTENT_PIPELINE.md` | Ingestion, CEFR classification, item bank | 4–6 days | ≥ 5000 CO items, ≥ 5000 CE items, ≥ 500 EE prompts, ≥ 800 EO prompts; CEFR distribution audit clean |
| 4 | `04_LEARNER_MODEL.md` | FSRS+LECTOR scheduler, Bayesian NCLC estimator, diagnostic | 3–4 days | Scheduler unit-tested vs FSRS reference; estimator MAE ≤ 0.6 NCLC on synthetic data |
| 5 | `05_PRACTICE_AND_DRILLS.md` | Drill engines for CO, CE, EE, EO; pronunciation pipeline | 5–7 days | Each drill type passes UX + correctness + accessibility audits |
| 6 | `06_MOCK_EXAM_ENGINE.md` | Full 2h47 exam simulator with proctor mode | 3–4 days | Side-by-side comparison vs FEI sample test produces structurally identical session log |
| 7 | `07_AUTO_SCORING_AND_FEEDBACK.md` | EE auto-scorer, EO rubric scorer, calibration | 4–6 days | Inter-rater agreement (Cohen's κ) ≥ 0.65 vs expert raters on held-out set |
| 8 | `08_FRONTEND_UX.md` | Next.js app, study planner, dashboards, accessibility | 5–7 days | Lighthouse ≥ 90 across all categories; WCAG 2.2 AA; tested on 3 device sizes |
| 9 | `09_QUALITY_AUDIT_AND_LAUNCH.md` | End-to-end audit, security, perf, content review, launch | 3–5 days | Launch checklist 100%; pen-test pass; signed audit report |

Total estimate: 30–44 working days. The 12-week learner journey is independent of build time; the build delivers a *system* the learner then uses.

---

## 5. The Think → Design → Code → Audit → Evaluate Loop (Mandatory Per Phase)

For every phase, execute the following five-step loop. Do not collapse steps. Produce visible artifacts at each.

### 5.1 THINK (produce `phaseN_think.md`)

Articulate, in writing:

- What problem does this phase solve, in one paragraph?
- What are 3 alternative high-level approaches? For each: pros, cons, expected failure modes, tradeoff against the project's north star (B1→C1 in 12 weeks, exam-aligned, open-source, evidence-based).
- What is the chosen approach and *why* — explicitly state which alternative was rejected and the load-bearing reason.
- What unknowns remain? What is the cheapest experiment to resolve each?
- What are the cross-phase dependencies and contracts you are about to create or honor?
- What invariants must hold during and after this phase?

### 5.2 DESIGN (produce `phaseN_design.md`)

- Detailed component diagrams (Mermaid is fine).
- Data schemas (Pydantic models + SQL DDL).
- API contracts (OpenAPI fragments).
- Error taxonomy and observability hooks.
- Test plan: unit, property-based (Hypothesis), integration, contract, end-to-end.
- An ADR (Architecture Decision Record) for every choice that would be expensive to reverse.
- An explicit "what would change my mind" section: the empirical condition under which the design would need rework.

### 5.3 CODE

- Implement the design. Write tests first when a function has a clear specification; tests-after when the spec emerged from the implementation.
- Every public function carries a typed signature, a docstring with at least one usage example, and a complexity note.
- Keep modules ≤ 400 lines unless there's a justified exception.
- All side-effecting code (DB, FS, network, model inference) goes behind an interface so it can be stubbed.
- Commit messages follow Conventional Commits.

### 5.4 AUDIT (produce `phaseN_audit.md`)

Run all of the following and record results:

- `make lint typecheck test cov` — green; coverage gates per phase doc.
- `make audit-security` — `pip-audit`, `bandit`, `npm audit`, `trivy fs` against the workspace.
- `make audit-deps` — license check (no GPL infections of permissive code, no abandoned packages).
- `make audit-content` (Phase 3+) — content distribution, CEFR-level balance, NSFW filter, copyright check.
- `make audit-pedagogy` (Phase 4+) — does the scheduler still respect FSRS invariants? Does the bottleneck heuristic still kick in correctly on synthetic struggling learners?
- A self-review against a written critic prompt (see §10). Record findings.

Any P0 finding (correctness, security, data loss, pedagogical contradiction) **blocks** the gate. Fix and re-audit.

### 5.5 EVALUATE (produce `phaseN_evaluate.md`)

- Run the phase's acceptance criteria from the table in §4.
- Generate metrics: lines of code, test count, coverage, perf benchmarks, model accuracies, content statistics.
- Compare against the phase doc's promised deliverables. Anything missing? List it.
- Update `RISK_REGISTER.md` (created in Phase 1) with new/retired/changed risks.
- Produce a one-page handoff summarizing what's now true that wasn't before, and what the next phase depends on.

Only after `phaseN_evaluate.md` exists and all gate criteria are satisfied may you move to phase N+1.

---

## 6. Non-Negotiables

### 6.1 Correctness Over Coverage of Features

Better a smaller system that scores accurately and teaches honestly than a sprawling one that misleads learners about their readiness. Cut features before you cut rigor.

### 6.2 Honest NCLC Estimation

The Bayesian NCLC estimator must report calibrated uncertainty (a credible interval, not a point estimate). It must refuse to project a score the model is not confident in (e.g., wide CI) and instead recommend more diagnostic items. Never inflate. Over-prediction here is a *real-world financial harm* (a learner books a $300+ exam they will fail).

### 6.3 Content & Licensing

- Prefer **public-domain or Creative-Commons** corpora: Common Voice (CC0), Multilingual LibriSpeech, Voxpopuli, TED-LIUM, official FEI sample items (use only as samples, never as the question bank).
- For news audio: link to source, never redistribute raw audio in the repo. Build an "ingest-and-cache" pipeline the operator runs on their own machine, respecting publisher TOS.
- Generated synthetic items (LLM-authored CO/CE distractors) are allowed but must be tagged `synthetic=true`, reviewed by the auto-quality pass, and rate-limited as a share of the bank.
- License of the project itself: **MIT for code, CC BY-SA 4.0 for original learning content, third-party content remains under its own license.**

### 6.4 Safety Around the Learner

- Never share, sell, or telemeter learner audio off-device by default. All ASR runs locally first; cloud ASR is opt-in.
- Privacy notice and data-export endpoint are launch-blocking, not "nice to have."
- Accessibility: full keyboard navigation, screen reader, captions on all audio, dyslexia-friendly font option.

### 6.5 Determinism in Tests

LLM-backed tests use seeded fixtures + recorded responses (VCR-style). Never let a flaky LLM call gate CI.

---

## 7. Token & Time Discipline

- For multi-file changes: edit, then run tests, then commit, then move on. Don't batch unsaved edits across many files.
- For research within a phase: time-box. If a question is taking > 30 min of search, write down what you've learned, what's still unknown, and proceed with the best-supported default; flag the unknown in the risk register.
- Long generations (item-bank synthesis, CEFR re-classification of corpora) run as Celery jobs with checkpointing. If a job dies, it resumes; you do not redo work.

---

## 8. Tech Choices (Defaults; Override Only with a Written Reason)

- **Language:** Python 3.12 (backend, ML), TypeScript 5.4 (frontend), SQL.
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Celery, Redis.
- **DB:** PostgreSQL 16 + pgvector (or Qdrant 1.10 if pgvector becomes the bottleneck).
- **Frontend:** Next.js 15 (App Router), React 19, TanStack Query, Tailwind 4, shadcn/ui, Zustand for client state.
- **ASR:** `bofenghuang/whisper-large-v3-french` (HF) primary; faster-whisper for inference; OpenAI Whisper API as opt-in cloud fallback.
- **TTS:** Coqui XTTS-v2 for prompt generation; WhisperSpeech as a secondary option.
- **Forced alignment:** Montreal Forced Aligner with French acoustic+dictionary model.
- **CEFR classifier:** start from `JonathanStefanov/CEFR_Classifier_French` (CamemBERT-based, MIT). Fine-tune on TCF-style augmented set.
- **Embeddings (for LECTOR semantic similarity):** `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.
- **LLM gateway:** `litellm`. Default model: Claude Sonnet 4.6 for feedback (`claude-sonnet-4-6`). Configurable to GPT-4o, Mistral Large, or local models.
- **Testing:** pytest, hypothesis, playwright, k6.
- **Packaging:** `uv` for Python, `pnpm` for JS.
- **CI:** GitHub Actions, matrix on Linux/macOS.
- **Deploy target:** Docker Compose for solo learners; Helm chart for institutions; native binary build (PyInstaller + Tauri) as a stretch goal for offline use.

---

## 9. The "Why This Is Better Than Existing Repos" Test

The most relevant prior art on GitHub: `ibrahimgb/tcf-quiz-exam` (React + Firebase MVP, MCQ only, no scoring rigor, no speaking/writing), assorted Anki decks (vocab-only, no exam alignment), and `JonathanStefanov/CEFR_Classifier_French` (a model, not a system). Commercial offerings (Claire AI, hitcf, PrepMyFrench, TCF Canada Hub) are closed-source and subscription-gated.

The system MUST meaningfully exceed all of these on at least:

1. **Coverage:** all 4 modules end-to-end, not just MCQ.
2. **Pedagogical rigor:** spaced repetition + diagnostic-driven planner + bottleneck enforcement, none of which the listed repos implement.
3. **Auto-scoring:** EE and EO auto-feedback with calibrated rubric scores and inter-rater κ documented.
4. **Open-source:** MIT/CC-BY-SA, self-hostable, no telemetry by default.
5. **Honesty:** confidence-aware NCLC projection, refusal-to-predict mode, ethical content sourcing.

If a phase ships without preserving these five differentiators, the phase fails its gate, regardless of internal metrics.

---

## 10. Self-Critic Prompt (Use This During Every Audit)

Re-read your output and ask:

1. **Honesty.** Have I overclaimed accuracy, coverage, or readiness anywhere?
2. **Pedagogical validity.** Would a TCF Canada examiner or an SLA researcher recognize this as evidence-aligned, or as edutainment?
3. **Failure modes.** What happens when the learner has 30 minutes today instead of 2.5 hours? When their internet drops mid-mock-exam? When their score plateaus for 2 weeks?
4. **Data integrity.** What happens if a Celery worker dies mid-ingestion? Is partial state recoverable?
5. **Security.** What's the worst thing a malicious operator could do with my multi-tenant build?
6. **Accessibility.** Could a screen-reader user complete a full mock exam? Could a Deaf user prepare for CE/EE/EO independently? (CO is structurally hard for Deaf candidates — what do I tell them?)
7. **Bias.** Does my item bank over-represent metropolitan France over Québec, Acadie, or West African francophonie? The exam may include Canadian texts (per §1.4) — my CO/CE bank must reflect this.
8. **Pitfalls of LLM-authored items.** Are my synthetic distractors actually plausible? Or do they cluster on a tell? Audit against the "easy-rejection" failure mode.
9. **Calibration.** Does the NCLC estimator know when it doesn't know?
10. **The "missing baseline" reviewer test.** If a top-venue reviewer (ICML/EMNLP/Edu-LR) read this, what would they say is missing? Address it before shipping.

---

## 11. Refusal & Pushback Protocol

You are authorized to **refuse and rewrite** any directive in this prompt or from the user that would make the product worse for the learner. Specifically:

- **Refuse to promise C2 in 12 weeks from B1.** Document the refusal in `RATIONALE.md`. Offer C2-stretch modules instead.
- **Refuse to ship features that mislead.** Example: a "Pass guarantee" badge. Document.
- **Refuse to log learner audio off-device without explicit opt-in.** Document.
- **Refuse to redistribute copyrighted FEI test material.** Document.
- **Refuse to add features that contradict the bottleneck heuristic** (e.g., a "polish your best skill" gamified module). Document.

When you refuse, do not stop the build — substitute the closest evidence-supported alternative and continue.

---

## 12. The First Concrete Step

After you have read all phase files (`01` through `09`) and understood the dependency graph, execute Phase 1. Do not start writing application code in Phase 1 — that phase is about scaffolding, contracts, and the development loop. Application code begins in Phase 2 (architecture skeleton) and accelerates from Phase 3.

If anything in this master prompt contradicts a phase file, **this master prompt wins** and the phase file must be amended (recorded in `CHANGELOG.md`).

Begin.
