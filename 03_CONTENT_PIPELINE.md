# PHASE 3 — Content Pipeline: Ingestion, CEFR Classification, Item Bank

> Goal: a working content pipeline that turns raw French-language sources into a calibrated, exam-aligned item bank with ≥ 5000 CO items, ≥ 5000 CE items, ≥ 500 EE prompts, ≥ 800 EO prompts, all CEFR-classified, level-balanced, and copyright-clean.

This is the longest, riskiest phase. Budget 4–6 days; checkpoint daily.

---

## 1. THINK (produce `phase3_think.md`)

### 1.1 What is "an item"?

For each module, an item must (a) match the official TCF Canada format closely enough that practice transfers, (b) be CEFR-classifiable so the scheduler can place it on the difficulty ladder, (c) carry enough metadata for IRT calibration in Phase 4. Specifically:

- **CO item:** 5–90s audio clip + 1 MCQ + 4 options + transcript + speaker/accent metadata. Following the FEI sample format: items range progressively from A1 announcement-style to C2 academic-lecture-style.
- **CE item:** 30–400 word passage + 1 MCQ + 4 options + genre + register. Six genres per FEI guidance: news, ad, letter, admin notice, academic excerpt, narrative.
- **EE prompt:** task spec for Tâche 1 (60w descriptive message), Tâche 2 (120w opinion piece), or Tâche 3 (180w argumentative essay), with required Canadian context flag for Tasks 2 & 3.
- **EO prompt:** examiner script for Task 1 (Q&A, ~3 min), Task 2 (compare/contrast, ~3.5 min), Task 3 (argue + defend, ~3.5 min), with model responses at NCLC 7, 9, and 11 ceilings for calibration.

### 1.2 Where does content come from?

A four-tier provenance hierarchy:

1. **Public domain / open-license corpora** (preferred):
   - Common Voice fr (CC0) — for CO seed audio
   - Multilingual LibriSpeech fr (CC BY 4.0)
   - Voxpopuli fr (CC0) — European Parliament speeches; tilted formal
   - TEDx fr (CC BY-NC-ND — note ND, cannot derive transcripts)
   - Wikisource fr (CC BY-SA) — narrative CE
   - Project Gutenberg fr (PD) — older registers; flag as "soutenu/historical"
2. **Operator-ingested cached content** (RFI, TV5MONDE, ICI Première RSS — by the operator, on their machine, never redistributed):
   - The repo ships an *ingestion script* the operator runs locally; the cached content lives in `data/` (gitignored).
   - Strict TOS check: only Creative-Commons feeds and items whose feeds explicitly permit downstream use are auto-imported. Everything else surfaces as a "manual review" queue.
3. **LLM-authored synthetic items** (capped, audited):
   - Used for: distractors (the wrong MCQ options), CE passages mimicking authentic registers, EE prompts in Canadian context, EO examiner scripts.
   - Never used for: the authoritative transcript of CO audio.
   - Capped at ≤ 40% of any module's bank; flagged `synthetic=true`.
4. **Official FEI sample materials** — *referenced, never bundled*. The repo links to FEI's public sample pages; users practice via a thin proxy in the UI that fetches at runtime.

### 1.3 The CEFR-Classification Subproblem

Item difficulty determines scheduler placement. Two layers:

- **Text-level CEFR**: start from `JonathanStefanov/CEFR_Classifier_French` (CamemBERT, MIT). Fine-tune on:
  - Cambridge ESOL CEFR-labeled French texts (where licensable)
  - CEFR-Levels-French (HuggingFace dataset)
  - FLELex (an A1–C2 lexicon for French L2)
  - A 500-item hand-labeled TCF-style validation set
- **Audio-level CEFR for CO**: combine text CEFR of transcript + acoustic complexity (speech rate, lexical density, noise level, multi-speaker overlap). A simple ridge regression over those features against the text-level label works as a first cut.

### 1.4 Three Alternatives for Item Authoring

- **(a) Pure scraping**: cheap but format-mismatched and copyright-fragile.
- **(b) Pure LLM authoring**: format-aligned but synthetic, risk of detectable distractor patterns.
- **(c) Hybrid: scrape passages from open sources → LLM authors questions+distractors → human-style validators check.** ← chosen
  - Rationale: the *passage* (CE) or *audio transcript* (CO) is the authentic L2-graded input. The *questions* test comprehension and are the lower-risk surface to synthesize. LLM-generated distractors are validated by an "adversarial" pass: a second LLM tries to answer using ONLY the question (no passage); if it gets > 25% accuracy, the distractors are too telegraphic and the item is rejected.

### 1.5 Failure Modes to Pre-empt

- **Distractor leakage**: synthetic distractors that are syntactically distinguishable from the correct option (length, plausibility cues). Mitigate with adversarial pass + length-balancing constraint.
- **Topic over-concentration**: hundreds of items about the same news cycle. Mitigate with topic-cluster cap (≤ 5% per cluster via embedding clustering).
- **Register/dialect monoculture**: too much Hexagonal French, no Canadian or African accents. Mitigate with explicit quotas (§2.4).
- **CEFR mis-classification**: classifier confidently assigns B1 to a C1 text. Mitigate with classifier-uncertainty thresholds; ambiguous items go to manual review.
- **Stale audio links**: external URLs rot. Mitigate by caching audio locally during ingestion + content-hash verification.

---

## 2. DESIGN (produce `phase3_design.md`)

### 2.1 Pipeline Stages

```
[Sources] → [Fetcher] → [Normalizer] → [CEFR-Classifier] → [Item Synthesizer]
                                          ↓                       ↓
                                     [Quality Gate]  ←──────────────
                                          ↓
                                    [Embedder + Clusterer]
                                          ↓
                                    [Bank Loader (DB)]
```

Each stage is a Celery task with idempotent input/output, content-hash keying, and a resumable checkpoint.

### 2.2 The Item Synthesizer (CE example)

```python
# packages/content/src/synthesize/ce.py
@dataclass
class CESynthesisInput:
    passage: str
    genre: str
    cefr_level: str
    seed: int            # for reproducibility
    n_questions: int = 1

def synthesize_ce_item(inp: CESynthesisInput) -> CEContent:
    """
    Generates a 1-question CE item from a passage.

    Pipeline:
      1. LLM call (Claude Sonnet 4.6) with structured prompt → candidate question, correct answer, 3 distractors
      2. Adversarial pass: ask a second LLM to answer with no passage; reject if > 0.25 accuracy over 20 trials
      3. Plausibility pass: each distractor must be supported by *some* part of the passage (so it's a comprehension test, not a logic test)
      4. Length-balance check: distractors within ±25% of correct-answer length in tokens
      5. CEFR check: classify question itself; reject if higher than passage level
    Returns CEContent with full metadata + rejection reasons if any.
    """
    ...
```

The structured prompt (`packages/content/prompts/ce_synthesis.j2`) enforces JSON output, level-appropriate vocabulary (constrained by the FLELex lexicon at the target level), and Canadian-context flags where applicable.

### 2.3 The CO Item Synthesizer

CO is harder because audio is the input. Pipeline:

1. Pull 30–90s audio segment from cached source.
2. Transcribe with whisper-large-v3-french → expected transcript.
3. Cross-check: forced-align transcript to audio (Montreal Forced Aligner); reject segments with WER > 10% against ground-truth where available, or low aligner confidence.
4. Compute acoustic complexity features (speech rate WPM, MFCC-based noisiness proxy, # speakers via diarization).
5. CEFR-classify the transcript + adjust for acoustic complexity.
6. Synthesize the MCQ using the transcript as the source, identical adversarial pass to CE.
7. Cache the audio locally; store relative path + sha256.

### 2.4 Quota Matrix (the bank's "balanced diet")

| Dimension | Required distribution | Min items per cell (per module) |
|---|---|---|
| CEFR level | A1: 5%, A2: 10%, B1: 25%, B2: 30%, C1: 20%, C2: 10% | 50 |
| Genre (CE) | News 25%, Ad 10%, Letter 15%, Admin 15%, Academic 20%, Narrative 15% | 30 |
| Audio accent (CO) | fr-FR 50%, fr-CA 25%, fr-BE/CH 10%, fr-AF 10%, mixed 5% | 25 |
| Register | Standard 60%, Familier 20%, Soutenu 20% | 100 |
| Canadian context (EE T2/T3) | ≥ 60% Canadian-flavored | 50 |
| Topic cluster (any) | No cluster > 5% of bank | — |

A bank that violates any cell by > 10% on the final audit fails the phase.

### 2.5 Quality Gate (every item)

```python
def quality_gate(item: Item) -> QualityReport:
    checks = [
        cefr_classifier_confidence(item) > 0.65,
        topic_cluster_share(item) < 0.05,
        not contains_pii(item),
        not contains_explicit_content(item),
        not duplicates_existing(item, similarity_threshold=0.92),
        license_compatible(item.provenance),
        adversarial_accuracy(item) <= 0.25 if item.module in ("CO","CE") else True,
        length_balanced_distractors(item) if item.module in ("CO","CE") else True,
    ]
    ...
```

Failure on any P0 check → item rejected with reason logged. Failure on P1 → routed to manual-review queue.

### 2.6 Embedder + Clusterer

Every item is embedded (multilingual MPNet) and:

- Stored in pgvector for retrieval (LECTOR semantic-confusable family detection in Phase 4).
- Clustered with HDBSCAN; clusters are the basis of the "no topic over 5%" rule.
- Confusable families (e.g., synonymous vocab pairs) detected for the scheduler.

### 2.7 The Manual-Review UI (lightweight)

A `streamlit` mini-app at `apps/review` lets a human reviewer:

- Approve/reject items flagged by the gate.
- Override CEFR level with a confidence weight.
- Tag confusable pairs manually.

This is not user-facing; it's for the operator/maintainer. Ships with the repo but launches separately.

### 2.8 Data Lineage & Reproducibility

Every item carries `provenance`:

```json
{
  "source": "common_voice_fr_v17",
  "source_id": "common_voice_fr_19284732",
  "license": "CC0",
  "ingested_at": "2026-06-01T12:00:00Z",
  "fetcher_version": "0.3.1",
  "synthesizer_version": "0.3.1",
  "llm_model": "claude-sonnet-4-6",
  "llm_prompt_hash": "sha256:...",
  "review_status": "auto_passed | human_approved | human_modified",
  "review_notes": null
}
```

Reproducibility check: given the same provenance, the same synthesizer version + LLM prompt should yield an equivalent item (modulo LLM stochasticity). We commit a `seeds.lock` for reproducibility on the deterministic stages.

### 2.9 ADRs added in this phase

- ADR-018: Hybrid (scraped-passage + LLM-question) authoring.
- ADR-019: Adversarial-distractor rejection threshold = 0.25 accuracy.
- ADR-020: No FEI test material in the repo; sample-link proxy only.
- ADR-021: Synthetic-item cap = 40% per module.
- ADR-022: Quota matrix as a hard release gate, not a guideline.

---

## 3. CODE

- `packages/content/src/sources/` — one module per source (common_voice, voxpopuli, librispeech, …).
- `packages/content/src/synthesize/` — `ce.py`, `co.py`, `ee.py`, `eo.py`.
- `packages/content/src/quality/` — all gate checks.
- `packages/content/src/cefr/` — fine-tuned CamemBERT classifier with a CLI.
- `apps/worker/tasks/ingest.py` — Celery tasks orchestrating the pipeline with retry + checkpoint.
- `scripts/seed_bank.py` — one-command bootstrap that runs the whole pipeline against open-license sources only, producing a default bank of ~3k items in ~6 hours on a 16-core machine.
- `apps/review/` — Streamlit manual-review UI.

---

## 4. AUDIT (produce `phase3_audit.md`)

Run and document:

- **Bank size:** CO ≥ 5000, CE ≥ 5000, EE ≥ 500, EO ≥ 800. (Initial seed may be smaller; gate requires the script to demonstrably produce a bank of this size in N hours.)
- **Distribution audit:** every cell in the quota matrix within tolerance.
- **CEFR classifier accuracy:** on a held-out 500-item hand-labeled set, macro-F1 ≥ 0.72 and adjacent-level accuracy (off-by-one) ≥ 0.93.
- **Adversarial-distractor failure rate:** < 10% of synthesized items rejected at this gate (else the synthesis prompt needs work).
- **License audit:** for every item in the bank, `license_compatible()` returns True. Spot-check 100 items by hand.
- **PII scan:** zero PII matches across the bank.
- **Duplicate audit:** no two items with cosine similarity > 0.92.
- **Acoustic audit (CO):** spectrograms render; durations within 5–90 s; sample rate normalized to 16 kHz.
- **Reproducibility:** rerunning `scripts/seed_bank.py` with the same `seeds.lock` produces a bank with identical sha256 over the deterministic columns.

---

## 5. EVALUATE (produce `phase3_evaluate.md`)

Acceptance criteria:

- ✅ Bank meets size, distribution, license, quality thresholds.
- ✅ CEFR classifier metrics meet target.
- ✅ Manual-review UI usable; a maintainer can review 100 flagged items in ≤ 30 min.
- ✅ All Phase 2 contracts honored (no schema changes).
- ✅ ADRs ADR-018 through ADR-022 accepted.

Anti-criteria:

- ❌ Any item in the bank without complete provenance.
- ❌ Any item where the `correct_answer` index doesn't match the labeled correct option.
- ❌ Any pipeline stage that, when killed mid-run, leaves the DB in an inconsistent state.
- ❌ A synthetic-item share above 40% in any module.
- ❌ A CEFR distribution skewed by > 10% from the quota matrix.

Hand-off: a `BANK_STATS.md` snapshot showing the current bank's size, distribution, and quality metrics. A "if you only have 60 minutes" recipe for re-running the pipeline on a fresh machine.
