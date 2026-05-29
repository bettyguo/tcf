# Phase 3 — THINK

> Phase 3 (`03_CONTENT_PIPELINE.md §1`) — the content pipeline that turns
> open French sources into a calibrated, exam-aligned, copyright-clean item
> bank. The longest and riskiest phase. Three load-bearing decisions; for
> each, the option space, the chosen path, and the empirical signal that
> would flip the decision. Date: 2026-05-27.

---

## 0. Frame

Phase 2 froze the *system*: the `items` table with a JSONB `content`
column under a Pydantic discriminated union, the `/v1/` route stubs, the
error taxonomy, the privacy-default-local-only stance (ADR-017),
`SCHEMA_VERSION="0.2.0"`. Phase 3's job is to fill that table — and only
that table — without rewriting any of those contracts.

What makes this phase load-bearing in a way Phase 2 was not: every other
phase consumes the bank. The scheduler (Phase 4) places items by CEFR
level; the drills (Phase 5) render them; the mock exam (Phase 6) composes
sessions from them; the auto-scorer (Phase 7) is calibrated against EE/EO
prompts produced here; the frontend (Phase 8) ships nothing if the bank
is empty. A correctness bug in Phase 3 — a mis-classified CEFR level, a
distractor that leaks the answer, an item with broken provenance — does
not surface until a learner sits a real TCF Canada and fails. That is
the harm shape we are building around. Master prompt §6.1 (correctness
over coverage) and §6.2 (honest NCLC estimation) compose here: a
well-calibrated estimator over a miscalibrated bank reports a confident,
wrong number.

Three things differ from Phase 2 procedurally. (a) The work is generative,
not declarative — LLM calls produce candidate items, and we have to gate
them on quality rather than write the items by hand. (b) The work is
licensable: every item carries a copyright story, and one bad story is
R-006 territory. (c) The work is statistical: the bank's *distribution*
matters at least as much as any individual item, because the scheduler
samples from it.

The three questions below are the ones that, if revisited later, would
force the largest rewrite of the pipeline itself. Quotas, thresholds,
and model choices that are merely tunable are deferred to §3.

---

## 1. The three hardest questions

### 1.1 How do we author items so that practice transfers to the real exam?

The exam's items are written by experienced item-writers at France
Éducation International to test specific comprehension and production
constructs. We cannot replicate that workforce. We must approximate it
with some mix of scraping, synthesis, and human review.

**Options:**

| Option | What gets written by whom | Cost |
|---|---|---|
| **(a)** Pure scraping | Passages, audio, *and* the original publisher's headlines/captions are repurposed as questions; we never synthesize. | Format-mismatched: real-world prose was not written as a comprehension probe. Copyright-fragile: derivative use of captions/headlines is murkier than reuse of the body text. The "right answer" is whatever the source said, which is not the same shape as a TCF MCQ. |
| **(b)** Pure LLM authoring | A single LLM call produces the passage, the question, the correct answer, and the distractors. | Format-aligned (we can prompt the exact FEI shape) but the *passage* is synthetic — meaning the L2 input the learner reads/hears is not authentic French. The system trains comprehension of LLM-French, not real French. Detectable-tells failure mode (R-003) is also worst here: the same model that wrote the passage wrote the distractors, so it knows the surface cues. |
| **(c)** Hybrid: scrape passages from open sources → LLM authors questions + distractors → adversarial gate validates | The *input* is real L2 evidence; the *probe* is synthesized but algorithmically verified. | Two-model pipeline; need to enforce that the LLM didn't sneak passage-leakage into the question; need provenance for the scraped passage and the synthesis prompt separately. |

**Pick (c).** Load-bearing reason: the unit being tested is comprehension
of authentic French input, not "ability to answer LLM-styled probes."
The *passage* is the experimentally meaningful surface — keep it real.
The *question* is a probe whose quality we can verify mechanically: an
adversarial LLM that has not seen the passage should not be able to
guess the correct answer above chance + a small margin. If it can, the
distractors are too telegraphic and we reject the item. This converts a
hard question ("are these distractors good?") into a measurable one
("does a blind LLM beat 25% accuracy across 20 trials?"). The 0.25
threshold itself is a §3 decision; what is load-bearing here is the
*shape* of the validation, not the number.

This also resolves the copyright posture for the *question*: synthesized
text from a documented prompt with a documented LLM has clean
provenance, traceable to a commit hash. The passage is bounded to CC0,
CC-BY, CC-BY-SA, or public-domain sources (master prompt §6.3). The two
provenances compose cleanly.

**Concrete consequence:** four synthesizers (`synthesize/ce.py`, `co.py`,
`ee.py`, `eo.py`), each taking a typed input (passage / audio + transcript
/ task spec / examiner brief) and emitting a Pydantic-validated item with
both passage- and synthesis-provenance fields populated. The adversarial
gate is implemented once in `quality/adversarial.py` and called from
both CE and CO paths. EE and EO have no MCQ adversarial step — their
"items" are prompts, not probes — but they get a different gate
(rubric-coverage check; see §3).

### 1.2 What do we trust to make CEFR placement decisions?

Every item's CEFR level is consumed by the scheduler (Phase 4) as the
difficulty signal that decides whether a B2 learner sees this item next.
A mis-classification by one band is silently a Krashen-violation: the
input is no longer "i+1." A mis-classification by two bands is the
system actively training the wrong skill. We need a CEFR call we can
defend with a documented confidence.

**Options:**

| Option | Classifier | Cost |
|---|---|---|
| **(a)** Zero-shot LLM classification | Prompt Claude / GPT with the CEFR rubric and a passage; ask for the level. | Cheap, no fine-tune. But: opaque, expensive per call (which makes nightly re-classification across the bank infeasible), and the model has no documented calibration. We cannot tell the scheduler "this is B2 with 0.78 probability" honestly. |
| **(b)** Fine-tune CamemBERT on French-CEFR datasets (ADR-0008's chosen path) | Start from `JonathanStefanov/CEFR_Classifier_French`; fine-tune on CEFR-Levels-French, FLELex, and a 500-item hand-labeled TCF-style validation set. | Real work: assemble the training set, run the fine-tune, evaluate. But: produces a calibrated 6-way softmax, can be re-run cheaply over the entire bank as new data arrives, and the validation set is reusable across releases. |
| **(c)** Hand-label everything | A human (or pool) assigns CEFR to every item. | Highest quality. Infeasible at our bank size (~12k+ items) without funding we don't have. Reserve human attention for the residual that the classifier flags as uncertain. |

**Pick (b), with (c) as the residual workflow for uncertain cases.**
ADR-0008 already commits us to the CamemBERT path for the classifier
itself; the question Phase 3 inherits is *how do we make it reliable
enough to gate the bank*. The answer is three layers:

1. **Fine-tune with uncertainty.** Train with label smoothing and a
   calibration head; evaluate calibration explicitly (expected
   calibration error in the audit). The classifier's softmax must mean
   "probability," not "ranked confidence."
2. **Gate on confidence, not just argmax.** An item enters the bank with
   its CEFR level *only if* the max softmax probability exceeds a
   threshold (start at 0.65; tune in §3). Items below the threshold are
   routed to the manual-review queue, not silently labeled.
3. **Audit-set on every release.** A 500-item hand-labeled TCF-style
   validation set is a permanent fixture. Macro-F1 ≥ 0.72 and adjacent-
   level accuracy ≥ 0.93 are the gate (`03_CONTENT_PIPELINE.md §4`); if
   we cannot reproduce them on a release, the bank does not ship.

**Concrete consequence:** the CEFR classifier is not "a model" but a
*module* with three artifacts — the model weights, the calibration
parameters, and the validation set — all versioned together. The
scheduler (Phase 4) consumes `cefr_level` and `cefr_confidence` from
each item; the cache-invalidation in §1.1 of Phase 2 already accommodates
re-classification because `cefr_level` is a real column, not a JSONB
field. A nightly re-classification job is feasible because the model
is local CamemBERT-base, not a paid LLM call. We commit to running it
on every bank update.

For CO, where the input is audio, this composes with an acoustic layer:
text-CEFR of the transcript adjusted by a small ridge regression over
speech rate, lexical density, and diarized speaker count. The audio
adjustment is +0 to +1 band, never down — we never label B2 audio as
A2 because the underlying text was conversational; conversation at
speed is harder than conversation on the page.

### 1.3 Where does the license boundary live: repo vs operator machine?

The TCF Canada training market is full of services that quietly host
copyrighted audio (RFI clips, TV5MONDE excerpts, FEI sample materials)
and hope no one notices. We will not. R-006 is L-likelihood / H-impact
and would be a project-ending event for an open-source repo: a takedown
notice plus a public reputation hit means the repo cannot be hosted on
GitHub for the affected files, and the trust narrative ("ethical content
sourcing," master prompt §9 differentiator 5) collapses.

**Options:**

| Option | What lives in the repo | What lives on the operator's machine | Cost |
|---|---|---|---|
| **(a)** Repo-bundled bank | Open-license seed + ingested news cache | (nothing extra) | Smallest setup friction, largest takedown surface. Every commit to `main` is a republication; one mistakenly-staged RFI clip is a permanent git-history liability. |
| **(b)** Repo ships nothing, fetch-at-runtime | (only code) | Everything fetched on demand from upstream | Smallest legal surface, but fragile: news URLs rot (master prompt §1.5 names this), upstream availability gates the learner's session, and runtime fetches must pass each source's TOS dynamically. |
| **(c)** Repo ships only the open-license seed; operator ingests the rest into a gitignored `data/` | Open-license, CC-clean items only | News audio + transcripts the operator caches under their local responsibility | Two-tier provenance; pre-commit hook prevents `data/` from leaking; the seed alone is enough to demo and to run audits. The cost is that out-of-the-box, the bank is smaller than a "fully loaded" deployment. |

**Pick (c).** Load-bearing reason: the repository is a public artifact
with a different threat surface than a private deployment. Anything the
repo ships, the repo *redistributes*. We confine that redistribution to
content we have an explicit license to redistribute (Common Voice CC0,
Multilingual LibriSpeech CC-BY-4.0, Voxpopuli CC0, Wikisource CC-BY-SA,
Project Gutenberg public domain, FLELex). News content lives on the
operator's machine because the operator's TOS posture is different from
the repository's: an individual can lawfully cache an RFI episode for
personal study under fair-dealing arguments that do not survive
republication.

Phase 1 already shipped the technical fence: `data/` is gitignored,
`scripts/check_no_data_commit.py` is a pre-commit hook (Phase 1 I5),
and the master prompt §6.3 commits us to the policy in writing. Phase 3
operationalizes it: the ingestion script's *output* is `data/<source>/`
on the operator's disk; the bank-loader reads from disk; the operator's
DB row stores a relative path + sha256, not the bytes. Everything in
the repo's seed pipeline reads from a public, CC-compatible URL or from
the operator's `data/` and crashes loudly if neither is present.

This decision is the one we will be most tempted to relax for
convenience ("just check in one short clip; nobody will mind"). The
ADR (ADR-020: no FEI test material in the repo; sample-link proxy only)
plus the pre-commit hook plus the audit (`audit-content` license check)
together make relaxation a deliberate three-step act.

**Concrete consequence:** two `seed_bank.py` modes. `--open-only`
(default; the CI-runnable mode) produces a smaller bank from open
sources alone — this is what a contributor sees on first clone. `--with-
operator-ingest` requires the operator to have run `scripts/ingest_*.py`
under their own TOS posture, populating `data/`; this is the mode the
operator uses to grow the bank to the target sizes
(`03_CONTENT_PIPELINE.md §4`). The audit gate distinguishes "open-only
seed produced N items" from "fully-loaded bank produced M items," and
the distribution audit runs against whichever bank is present.

---

## 2. What would change our mind

These are the empirical signals that, if observed, would warrant
revisiting the decisions above. They are deliberately concrete; vague
triggers ("if quality is bad") don't count.

### 2.1 On hybrid authoring (1.1)

- **Adversarial gate rejects > 30% of synthesized items** for two
  consecutive batches. This means our LLM is reliably producing
  telegraphic distractors and the gate is doing what it should, but the
  gate's job has become the synthesis prompt's job. We'd revise the
  synthesis prompt (and possibly the LLM) before considering a fall-back
  to (a) or (b). If the prompt rewrite doesn't close the gap, we'd
  consider a constrained-decoding pass that forces distractor length and
  syntax to match the correct option.
- **Human review on a 100-item sample finds the *passage* (not the
  question) is the failure mode** — e.g., scraped Common Voice
  utterances are too clean / too short to test real comprehension. We'd
  reconsider option (b) for CE specifically (synthetic passages
  modeled on real registers), accepting the input-authenticity trade-off
  as the lesser evil for that module. CO remains real audio regardless.
- **The "blind LLM" adversarial check is itself gameable** — e.g., the
  synthesis LLM and the adversarial LLM are the same family and share
  blind spots, so the gate passes items a human could trivially answer.
  We'd swap the adversarial model to a different family (Mistral / Llama
  vs Claude) and re-run the validation; if the gate's discriminative
  power doesn't return, we'd add a small human-review sample as a third
  filter rather than relax the gate.

### 2.2 On fine-tuned CamemBERT CEFR classification (1.2)

- **Macro-F1 on the held-out 500-item set drops below 0.65** (the gate
  is 0.72). Either the validation set has drifted from the production
  distribution (mostly news / scraped prose vs synthesized TCF-style
  items) or the fine-tune regressed. We'd freeze the bank, regenerate
  the validation set against the current bank's distribution, and
  re-fine-tune.
- **Adjacent-level accuracy is above 0.93 but the *direction* of error
  is asymmetric** — e.g., we systematically under-rate C1 items as B2.
  This is worse than uniform noise because it routes hard items to
  intermediate learners and trains over-confidence. We'd add a
  difficulty-asymmetric loss to the fine-tune (penalize down-rating
  more than up-rating) before accepting the regression.
- **Calibration error exceeds 0.10** (ECE on the held-out set). The
  classifier's confidence numbers are no longer trustworthy; we cannot
  honestly gate on confidence > 0.65 if the 0.65 doesn't mean what we
  think it means. We'd recalibrate (temperature scaling) before
  re-shipping; if recalibration cannot recover, we'd raise the manual-
  review queue threshold and absorb the volume.
- **A second-opinion zero-shot LLM call disagrees with the fine-tuned
  classifier on > 15% of items**, in a spot-check audit. This doesn't
  prove the classifier is wrong (LLM zero-shot is itself uncalibrated),
  but it does suggest we're not capturing whatever signal the LLM is
  reading. We'd investigate the disagreement set in `apps/review`
  before any classifier change.

### 2.3 On the repo / operator license boundary (1.3)

- **Any commit lands a file under `data/`** (the pre-commit hook fails
  open, e.g., on a contributor's Windows machine; R-008). This is a
  P0 even if no copyrighted material was in the file. We'd treat it as
  a near-miss, harden the hook (server-side check via GitHub Actions
  on push), and verify the hook's coverage cross-platform.
- **A contributor proposes adding "just one" copyrighted clip "for the
  test suite."** This is the failure shape we are pre-empting; the
  refusal is documented in master prompt §11 and the ADR is the
  policy. We'd write a `CONTRIBUTING.md` section if the proposal
  recurs (currently the master prompt + ADR-020 is enough).
- **The open-license seed bank cannot reach minimum quotas** (e.g., not
  enough Canadian-accent CO audio in Common Voice). We'd treat the
  quota matrix as a heuristic in the open-only seed mode while
  preserving it as a hard gate in the full-bank mode, and we'd
  document the gap in `LIMITATIONS.md`. We would *not* relax (c) by
  shipping non-open content to compensate.

---

## 3. Adjacent decisions deferred to design (`phase3_design.md`)

These are real decisions, but they are tunable parameters of the chosen
architecture rather than load-bearing pivots. The design doc locks
specific values and the rationale; here we record what is up for
binding.

- **Adversarial-rejection threshold.** 0.25 (`03_CONTENT_PIPELINE.md
  §1.4`). This is "blind-LLM accuracy above which the item is too
  guessable." 0.25 is chance for a 4-option MCQ. Raising it loosens
  the gate (more items pass) at quality cost; lowering it tightens at
  yield cost. Will be ADR-019.
- **Synthetic-item cap per module.** 40% (`§1.2`, `§2.4`). Per *module*
  is the right denominator (each module is consumed independently);
  per-cell would force synthesis to backfill rare cells regardless of
  quality, defeating the cap. Will be ADR-021.
- **Quota-matrix tolerance.** ±10% per cell on the final audit
  (`§2.4`). Will be ADR-022.
- **CEFR-classifier confidence floor.** 0.65 (`§2.5`). Items below
  this go to manual review. Will be locked in the design doc, not as
  an ADR (numerical threshold, tunable per release).
- **Duplicate-similarity threshold.** 0.92 cosine on multilingual-MPNet
  embeddings (`§2.5`). Locked in design.
- **Embedder choice.** `sentence-transformers/paraphrase-multilingual-
  mpnet-base-v2` (master prompt §8). No ADR — already chosen at the
  master-prompt level.
- **Topic-cluster cap.** ≤ 5% of bank per HDBSCAN cluster (`§2.4`).
  Locked in design.
- **Acoustic-CEFR adjustment.** Ridge regression on (speech rate WPM,
  lexical density, # speakers diarized, MFCC-noisiness proxy) vs
  text-CEFR target. Adjustment range: +0 to +1 band only (§1.2
  above). Locked in design.
- **Manual-review UI.** Streamlit at `apps/review`, not user-facing,
  ships with the repo but launches separately. No ADR — operational
  tool, not a product surface.
- **Pipeline orchestration.** Celery tasks under `apps/worker/tasks/
  ingest.py` with content-hash idempotent keys + resumable checkpoint
  (`§2.1`). Reuses the Celery/Redis seam Phase 1 shipped (ADR-0005).
  No new ADR.
- **Provenance schema.** The JSON shape in `§2.8` is additive to the
  Phase 2 `Item.provenance` field; SCHEMA_VERSION bumps to `0.3.0` if
  any field is required-new, `0.2.1` if all-additive-optional.
- **FEI sample materials.** Linked, never bundled; thin proxy in the
  UI fetches at runtime. Will be ADR-020.

The five new ADRs to be drafted in design:

- **ADR-018**: Hybrid scraped-passage + LLM-question authoring.
- **ADR-019**: Adversarial-distractor rejection threshold = 0.25.
- **ADR-020**: No FEI test material in the repo; sample-link proxy only.
- **ADR-021**: Synthetic-item cap = 40% per module.
- **ADR-022**: Quota matrix as a hard release gate, not a guideline.

---

## 4. Out of scope for Phase 3

Phase 3 produces the bank. It does not consume it. The following are
deliberate non-goals, and the design doc must not drift into them:

- **Scheduler placement, Bayesian posterior update, IRT calibration.**
  Phase 4. Phase 3 reserves the `items.difficulty_irt` and
  `items.discrimination_irt` columns (already in the Phase 2 schema)
  with `NULL` until Phase 4's nightly job populates them.
- **Drill rendering and the practice loop.** Phase 5. Phase 3 ships
  items, not UIs.
- **Mock-exam composition.** Phase 6. Phase 3 ships items tagged with
  enough metadata (CEFR, genre, accent, register, Canadian-context
  flag) that the composer can do its job; it does not implement the
  composer.
- **EE / EO auto-scoring.** Phase 7. Phase 3 ships *prompts* for EE
  and EO and model-response calibration anchors at NCLC 7/9/11; it
  does not ship the scorer that grades a learner's response.
- **Learner-audio ASR.** Phase 5 / 7. Phase 3 uses Whisper-large-v3-
  french only for *transcript verification* of cached source audio
  (the WER check in `§2.3`), never for learner audio. Confusing the
  two would be a privacy-default violation (master prompt §6.4,
  ADR-017).
- **The frontend.** Phase 8. The manual-review UI at `apps/review` is
  Streamlit for the operator, not Next.js for the learner.
- **Any change to Phase 2 contracts.** Phase 3 is allowed to *narrow*
  the `ItemContent` discriminated union (e.g., add a `co.audio_path`
  required field once we know the cache layout) but not to break it.
  SCHEMA_VERSION bumps additively.
- **Helm / Docker production deploy.** Phase 9. Phase 3 runs locally
  via `make` targets and the existing `docker-compose.yml`.

---

## 5. Phase 3 invariants going into design

These must hold during and after Phase 3, forever:

1. **Every item in the bank has complete provenance.** No nullable
   `source`, `license`, `ingested_at`, or `synthesizer_version`.
   Enforced by `Provenance` Pydantic validation at the repository
   write path and by the `quality_gate` rejection criterion.
2. **Every item in the bank passes the quality gate or is in the
   manual-review queue.** Nothing enters the `items` table by a path
   that bypasses the gate. Repository writes are funneled through
   `ItemRepository.create_validated()`.
3. **No item in the bank carries content the repo cannot legally
   redistribute.** `license_compatible(item.provenance)` returns
   True for every row at every release. `audit-content` enforces.
4. **`data/` is gitignored.** Re-affirms Phase 1 I5. The pre-commit
   hook is part of the seal; the audit verifies no commit on `main`
   has ever added a file under `data/`.
5. **The bank is reproducible from `seeds.lock` modulo LLM
   stochasticity.** Rerunning `scripts/seed_bank.py --open-only`
   against the same lockfile produces an identical sha256 over the
   deterministic columns (scraping, normalizing, CEFR-classifying,
   clustering); the LLM-synthesized columns may vary but the
   *items selected* and their *provenance* do not.
6. **Synthetic items are tagged.** `Item.provenance.synthesizer_version`
   is non-null iff the item is synthetic; the synthetic share per
   module ≤ 40% at every release (ADR-021).
7. **Phase 2 contracts hold.** No SCHEMA_VERSION downgrade; only
   additive bumps. `SCHEMA_VERSION` becomes `0.3.0` if any required
   field is added to `ItemContent` or `Provenance`, otherwise it
   stays at `0.2.x`. Phase 2's round-trip tests must continue to pass.
8. **The CEFR classifier is versioned with the bank.** Bank releases
   pin a classifier version, its calibration parameters, and the
   validation-set sha256. A bank shipped with a different classifier
   version is a different bank.
9. **The quota matrix is a hard gate.** Violation > 10% on any cell
   on the final audit fails the phase (ADR-022). No
   "ship-it-and-fix-it-in-Phase-4" exception.
10. **No FEI test material in the repo, ever.** Master prompt §11
    refusal, re-codified as ADR-020.

These invariants are restated at the top of `phase3_design.md`'s §0.

---

## 6. Hand-off to DESIGN

`phase3_design.md` takes these decisions and turns them into:

- The pipeline DAG (`§2.1` of the spec) rendered as Mermaid, with
  Celery task names, idempotency keys, and checkpoint semantics on
  each edge.
- The four synthesizer module shapes (`synthesize/{ce,co,ee,eo}.py`)
  with typed inputs, typed outputs (`Item` variants from the Phase 2
  discriminated union), and the per-module gate-check sequence.
- The CEFR classifier module shape: training data spec, fine-tune
  recipe, calibration step, validation-set protocol, version
  artifact.
- The acoustic-CEFR ridge regression: feature list, training data
  spec, evaluation protocol.
- The `quality_gate(item) → QualityReport` implementation: P0 vs P1
  checks, rejection-reason taxonomy, manual-review-queue protocol.
- The embedder + HDBSCAN clusterer config, with the topic-cluster cap
  enforcement.
- The provenance schema in full (additive to Phase 2).
- The Streamlit manual-review UI shape (3 pages: queue, item detail,
  CEFR-override + confusable-pair-tag).
- The two `seed_bank.py` modes (`--open-only` and `--with-operator-
  ingest`), the ingestion-script set per source, and the audit
  protocol that runs against either.
- The five new ADRs (018 through 022).
- The test plan: unit per synthesizer + per gate check; property tests
  on the Provenance shape and the quality gate's idempotence;
  integration test that runs `seed_bank.py --open-only` end-to-end on
  a 50-item slice; contract test that every item in the bank
  validates against `Item.model_validate`; pedagogical regression
  that the synthetic-cohort trajectory (Phase 4) is not destabilized
  by a bank-only re-seed.
