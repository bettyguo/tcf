# PHASE 7 — Auto-Scoring & Feedback (EE Writing + EO Speaking Rubrics, Calibration)

> Goal: produce per-rubric scores for EE and EO that achieve Cohen's κ ≥ 0.65 against expert human raters on a held-out set, and that come with actionable error-level feedback. This is the most reviewer-skeptical surface of the system.

---

## 1. THINK (produce `phase7_think.md`)

### 1.1 The Honesty Imperative

Auto-scoring of L2 writing/speaking is a 40-year-old research problem. Even commercial systems (e.g., the ETS e-rater) achieve ~κ 0.65–0.75 against human raters on prompt-controlled essays — and they have decades of calibration data. **We will not exceed the state of the art in this phase.** We will instead:

- Score *reliably* in the published-research range.
- Be honest about the proxy nature of automated subscale scores.
- Provide *qualitative* feedback (error annotations, specific suggestions) that has higher learner-value than the numeric score itself.
- Calibrate against a small set of expert ratings we can either commission, source from a partner Alliance Française, or approximate via the highest-quality LLM as a stand-in (with a documented degradation factor).

### 1.2 The Rubric (Pinned in Phase 2 Schemas)

For **EE**:

- Task completion (0–5)
- Coherence & cohesion (0–5)
- Lexical range (0–5)
- Grammatical accuracy (0–5)
- Register appropriateness (0–5)
- Canadian context integration (0–5; Tasks 2 & 3 only)
- → mapped to 0–20 per task via a published lookup table

For **EO**: same six dimensions, with "Interaction responsiveness" replacing "Canadian context" + "Pronunciation & prosody" replacing "Register" for Tasks 1–2 (Task 3 keeps register).

Total per task: 0–20. The TCF Canada uses a 6-band coarse scale (1 through 6) that maps to NCLC; we score finer-grained internally and aggregate.

### 1.3 The Scoring Architecture

```
EE submission:
  text → linguistic analyzer (spaCy fr + custom error detector) → feature vector
                                                                     ↓
                              + LLM critic (Claude Sonnet 4.6, structured prompt)
                                                                     ↓
                                                     calibration layer (per-rubric regressors)
                                                                     ↓
                                                                Rubric scores + error list

EO submission:
  audio → Whisper-fr → transcript → (same EE pipeline for content dimensions)
        → MFA + prosody → pronunciation features
        → calibration layer
        → SpeakingRubric
```

### 1.4 Why a Linguistic-Features + LLM Hybrid?

- **Features alone** (TTR, error density, syntactic complexity) are interpretable but plateau in accuracy.
- **LLM alone** is brittle, prompt-sensitive, and inflates scores.
- **Hybrid**: the LLM provides structured per-rubric scores; the feature pipeline provides objective floor measurements (TTR ≥ 0.65 for NCLC 9, error density < 2/100w, etc.). The calibration layer fuses them.

The calibration layer is a small Ridge regression per rubric, trained on the expert-labeled set (~200 essays + 200 recordings minimum, ideally 500).

### 1.5 Alternatives Considered

- **Pure regex/feature scoring**: brittle on prompts that vary in topic.
- **Fine-tuned classifier (e.g., BERT-fr on rubric scores)**: needs more labeled data than we'll have for v1.
- **LLM-only with chain-of-thought**: documented to inflate (LLMs are generous graders).
- **Hybrid feature + LLM + calibration**: ← chosen.

### 1.6 Error Annotation

Every flagged error has:

- type: agreement | tense | gender | preposition | spelling | lexical | register | discourse | task | other
- span: (start_char, end_char)
- detected_by: spacy_rule | llm | language_tool | custom
- severity: minor | major
- correction: a single proposed fix
- explanation: a one-sentence explanation, EN + FR
- pedagogical_tag: links to a drill that targets this error class

Errors are deduplicated across detectors (LanguageTool + LLM + custom often overlap).

### 1.7 The Pronunciation Sub-Score

Pronunciation feeds the SpeakingRubric.pronunciation_prosody dimension. Components:

- Phoneme error rate (PER) from MFA + canonical pronunciation dict.
- Prosody score: pitch range, stress placement on final syllable, pause distribution.
- WPM ratio (target: 130–180 WPM for connected speech at B2+).

Reported separately in the report with the "coarse proxy" disclaimer from Phase 5.

---

## 2. DESIGN (produce `phase7_design.md`)

### 2.1 Feature Pipeline (Writing)

```python
# packages/ml/src/scoring/ee/features.py
@dataclass
class WritingFeatures:
    word_count: int
    type_token_ratio: float
    moving_average_ttr_25: float   # MATTR-25, more stable than raw TTR
    mean_sentence_length: float
    discourse_marker_count_per_100w: float
    distinct_discourse_categories: int
    error_density_per_100w: float
    flesch_reading_ease_fr: float
    cefr_predicted_level: str
    canadian_lexicon_density: float  # share of tokens matching a Canadian-French lexicon
    register_score: float            # familier-to-soutenu axis, -1..+1
    pos_distribution: dict[str, float]
    subjunctive_count: int
    conditional_count: int
    passive_count: int
```

### 2.2 Feature Pipeline (Speaking)

Inherits writing features (computed on transcript) + adds:

```python
@dataclass
class SpeakingFeatures(WritingFeatures):
    wpm: float
    pause_count_per_minute: float
    pause_total_ratio: float
    filler_count_per_minute: float    # "euh", "ben", "hein"
    mean_pitch: float
    pitch_range: float
    phoneme_error_rate: float
    stress_correctness_rate: float
    self_correction_count: int
```

### 2.3 LLM Critic (Structured Prompt)

The LLM is given:

- The task prompt (so it knows what was asked).
- The submission (text or transcript).
- The rubric, verbatim.
- An instruction to score *strictly* and to refuse to inflate ("if you cannot justify a 5/5 with quoted text evidence, the score is 4/5 maximum").
- Few-shot examples at NCLC 7, 9, and 11 ceilings.

Returns structured JSON: per-rubric score, justification, error annotations, suggested rewrites for 3 weakest sentences.

### 2.4 Calibration Layer

```python
# packages/ml/src/scoring/calibration.py
class RubricCalibrator:
    """
    For each rubric dimension, a Ridge regressor:
        rubric_score = w_features · features + w_llm · llm_score + bias
    Trained on the expert-labeled set; evaluated by κ + Pearson r + MAE.
    """
    def __init__(self): ...
    def fit(self, X: list[WritingFeatures], llm_scores: list[float], expert_scores: list[float]): ...
    def predict(self, features: WritingFeatures, llm_score: float) -> float: ...
```

Per-rubric calibrators are versioned and stored as joblib pickles + their training-set hash.

### 2.5 The Expert-Labeled Set

For v1 we need 200+ EE submissions and 200+ EO recordings, each rated by at least 2 expert raters using the official rubric. Three acquisition paths, in priority:

1. **Partner Alliance Française or DELF/TCF examiners** — pay a small honorarium for 200 ratings; reproducible reference set, gold-standard.
2. **Crowd-sourced learners on the project's mailing list** (with consent + license to use for training).
3. **LLM-as-rater stand-in** — use an ensemble of GPT-4o + Claude Sonnet 4.6 with explicit per-criterion scoring; treat as "silver" labels with a documented ~5-pt-deflated calibration to match expert-rater behavior, validated against a smaller (~30-essay) actual-expert subset.

Path 1 is the target; paths 2–3 bootstrap until path 1 is in place. Critically: the system MUST publish, with every release, the κ achieved against the expert subset at hand.

### 2.6 Feedback Rendering

The feedback shown to the learner is more elaborate than the score:

```
EE Tâche 3 — 14/20 (NCLC 9 floor)

Strengths:
• Lexical range is solid (TTR 0.68).
• Clear thesis-evidence-conclusion structure.

Three things to fix for NCLC 11:

1. (Grammar) "Si j'aurais le choix..." → "Si j'avais le choix..." 
   The conditional protase in a Type-II hypothetical must use the imperfect, not the conditional.
   [drill: si-clause-types]

2. (Discourse) Three of your four paragraphs begin with "Et". Vary your connectors:
   "Par ailleurs", "De surcroît", "En outre", "Cela étant".
   [drill: connectors-c1]

3. (Canadian context) Your essay on housing policy could mention Quebec's Régie du logement
   or rent-control specifics from Montréal/Toronto. The exam's writing rubric rewards
   Canadian-context integration in Tasks 2 & 3.
   [drill: canadian-context-ee]

Auto-feedback is approximate. A trained examiner could see more.
```

### 2.7 ADRs

- ADR-036: Hybrid feature + LLM + calibration architecture.
- ADR-037: Expert-labeled set ≥ 200/skill is launch-blocking for "claimed κ" reporting; without it, the system reports κ_silver vs LLM rater + caveat.
- ADR-038: Publish κ with every release.
- ADR-039: LLM scoring uses temperature ≤ 0.2 + structured-output enforcement.
- ADR-040: Inflation guard: if LLM score is more than 3 points above feature-predicted score on any rubric, the score is clamped to feature+2 and a "needs human review" flag is set.

---

## 3. CODE

- `packages/ml/src/scoring/ee/` (features, llm_critic, calibrator, run).
- `packages/ml/src/scoring/eo/` (same shape, includes pronunciation pipeline glue).
- `apps/worker/tasks/score_ee.py`, `score_eo.py`.
- `apps/api/routes/submission.py` (multipart upload + async scoring).
- `scripts/calibrate.py` — trains calibrators from expert ratings.
- `scripts/eval_kappa.py` — reports inter-rater agreement on every release.

---

## 4. AUDIT (produce `phase7_audit.md`)

- **κ on expert-held-out set:** ≥ 0.65 (Cohen's quadratic-weighted κ on 0–5 rubric scores). If using silver labels only, report κ_silver and a sample-of-30 κ_gold.
- **MAE on total-20 score:** ≤ 2 points.
- **Pearson r:** ≥ 0.80.
- **Inflation guard test:** synthetic learner essays at NCLC 5 stay at NCLC 5 ± 1 (no inflation to 7).
- **Calibration over levels:** plot predicted vs expert across NCLC 5–11; slope ∈ [0.85, 1.15], intercept ≈ 0.
- **Error annotation precision/recall:** on a hand-annotated 50-essay set, precision ≥ 0.75, recall ≥ 0.65 against expert annotations.
- **Pronunciation pipeline:** PER MAE ≤ 0.06 on the 50-utterance test set from Phase 5.
- **Cost discipline:** scoring a single EE submission costs ≤ N tokens; budget tracked.

---

## 5. EVALUATE (produce `phase7_evaluate.md`)

Acceptance criteria:

- ✅ All κ / MAE / r targets met (or honestly reported below with mitigation plan).
- ✅ Feedback rendering passes a usability review with at least 3 representative learners (or, if not available, 3 maintainers).
- ✅ Inflation guard demonstrably engages on synthetic inflated cases.
- ✅ ADRs ADR-036 through ADR-040 accepted.

Anti-criteria:

- ❌ Any scoring path that returns a number without an accompanying confidence indicator.
- ❌ A feedback message that quotes the learner's text without flagging it as quoted-back (privacy: even quoted-back content is the user's; render as a styled blockquote, not as our prose).
- ❌ A release whose published κ < 0.55 without an explicit "experimental" badge.
- ❌ Any pronunciation feedback without the coarse-proxy disclaimer.

Hand-off: a calibration report, the κ table per rubric, sample feedback messages on the 12 archetypal cohorts.
