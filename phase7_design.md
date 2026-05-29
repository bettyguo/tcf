# Phase 7 — DESIGN

> Implements the THINK doc. The packages live in
> `packages/ml/src/tcf_accel_ml/scoring/` (with sub-packages for `ee/`
> and `eo/`); the Celery wiring lives in
> `apps/worker/src/tcf_accel_worker/tasks/` (already-existing stubs
> become real); the HTTP surface is `apps/api/.../routes/submission.py`.

The design is intentionally **small**: no heavy ML deps, no
fine-tuned classifier. The whole pipeline is implementable in pure
Python + a tiny linear-algebra calibrator + an optional cloud LLM call
behind a protocol.

---

## 1. Package layout

```
packages/ml/src/tcf_accel_ml/scoring/
    __init__.py
    rubric_table.py            # 0–20 ↔ NCLC band lookup table
    features/
        __init__.py
        writing.py             # WritingFeatures + extractor
        speaking.py            # SpeakingFeatures + extractor (inherits writing)
        connectors.py          # discourse-marker registry
        register.py            # familier↔soutenu register scorer
        canadian.py            # Canadian-lexicon density
        errors.py              # heuristic span-level error detector
    llm/
        __init__.py
        critic.py              # LLM critic protocol + structured-prompt builder
        stub.py                # deterministic local stand-in (no network)
        prompts.py             # rubric prompt + few-shot anchors
    calibrate/
        __init__.py
        ridge.py               # tiny stdlib Ridge regressor
        calibrator.py          # RubricCalibrator (per-dimension Ridge)
        kappa.py               # Cohen's quadratic-weighted κ
    inflation_guard.py         # ADR-040 clamp
    feedback.py                # render the learner-facing block
    ee/
        __init__.py
        score.py               # EEScorer (orchestrates features+LLM+calibrator)
    eo/
        __init__.py
        score.py               # EOScorer (same shape, includes pronunciation)
```

### 1.1 Why no third-party ML deps

Pure-Python keeps the package importable in CI without operator setup
and dodges the platform-specific install pain (spaCy on Windows
without VC++ is a hostile environment). The features we compute are
all linear-time string operations + simple counters; the calibrator is
a 20-line Ridge regressor over a 6-dim feature vector. spaCy is added
as an optional dep gated behind an env flag (`TCF_ACCEL_SCORING_SPACY=1`)
for production deployments that want the richer POS / lemma signals.

---

## 2. Features pipeline (writing)

```python
# packages/ml/src/tcf_accel_ml/scoring/features/writing.py
@dataclass(frozen=True)
class WritingFeatures:
    word_count: int
    type_token_ratio: float
    moving_average_ttr_25: float          # MATTR-25 (more stable than TTR)
    mean_sentence_length: float
    discourse_marker_count: int
    discourse_marker_density_per_100w: float
    distinct_discourse_categories: int
    error_density_per_100w: float
    flesch_reading_ease_fr: float
    canadian_lexicon_density: float
    register_score: float                 # -1 familier, +1 soutenu
    subjunctive_count: int
    conditional_count: int
    passive_count: int
```

Extractor:

```python
def extract_writing_features(text: str) -> WritingFeatures: ...
```

Pure function, deterministic. Internally:

- **MATTR-25** moves a 25-word window across the text and averages the
  per-window TTR; if `word_count < 25` falls back to raw TTR. More
  stable than raw TTR for short essays.
- **Discourse markers** counted from a 5-category seed
  (addition / contrast / cause / consequence / conclusion / temporal)
  in `connectors.py`. Phase 5 already inlines a smaller seed; Phase 7
  reuses it.
- **Error density** uses the heuristic detector in `errors.py`: a
  union of (a) regex rules for the highest-frequency L2 French errors
  (`Si j'aurais`, `*ai allé`, gender-agreement on common nouns),
  (b) optional LanguageTool when available, (c) the LLM critic's
  output (deduplicated). Reported per-100w.
- **Register score** sits on a familier↔soutenu axis: counts of
  familier markers (`ben`, `du coup`, contractions) vs soutenu markers
  (subjunctive, complex connectors) → tanh-normalized.
- **Canadian lexicon density** counts tokens matching a curated
  Canadian-French lexicon (`canadian.py`).

### 2.1 Feature stability

Every feature is **bounded** (counts are non-negative; rates are in
[0, ∞) but clamped at output time). The extractor never raises; an
empty input yields a zero-vector with `word_count=0`.

---

## 3. Features pipeline (speaking)

```python
# packages/ml/src/tcf_accel_ml/scoring/features/speaking.py
@dataclass(frozen=True)
class SpeakingFeatures:
    # Content dims (computed on the transcript).
    writing: WritingFeatures
    # Audio / prosody dims.
    duration_s: float
    wpm: float
    pause_count_per_minute: float
    pause_total_ratio: float
    filler_count_per_minute: float        # "euh", "ben", "hein", "hmm"
    mean_pitch: float
    pitch_range: float
    phoneme_error_rate: float | None
    asr_mean_confidence: float
    self_correction_count: int
    pronunciation_display_label: str      # from PronunciationSignal
```

Built by:

```python
def extract_speaking_features(
    *,
    transcript: str,
    duration_s: float,
    asr_mean_confidence: float,
    pronunciation_signal: PronunciationSignal | None,
) -> SpeakingFeatures: ...
```

The pronunciation pipeline outputs (Phase 5) are an *input* to this
function; Phase 7 does not re-run Whisper. When the signal is `None`
(e.g., legacy interactions) the pronunciation fields are filled with
neutral defaults and the calibrator's pronunciation dimension is
flagged `low_confidence`.

---

## 4. LLM critic

The LLM critic is a structured-prompt wrapper. The protocol:

```python
class LLMCritic(Protocol):
    def critique_ee(self, *, prompt: str, text: str,
                    rubric_version: str, task_number: int,
                    target_word_count_range: tuple[int, int]
                    ) -> LLMCritique: ...

    def critique_eo(self, *, prompt: str, transcript: str,
                    rubric_version: str, task_number: int,
                    duration_s: float
                    ) -> LLMCritique: ...
```

Returned `LLMCritique`:

```python
@dataclass(frozen=True)
class LLMCritique:
    rubric_scores: dict[str, int]              # rubric dim → 0..5
    justifications: dict[str, str]
    error_annotations: list[ErrorAnnotation]
    suggested_rewrites: list[SuggestedRewrite] # up to 3 weakest sentences
    confidence: float                          # 0..1; LLM self-reported
    refused: bool                              # true if critic refused
```

### 4.1 Two implementations

- **`stub.LLMCriticStub`** — deterministic local stand-in. Derives
  rubric scores from the feature vector via a hand-tuned mapping
  (e.g., `lexical_range = bucket(MATTR, [.3, .45, .55, .65, .75])`).
  Used in CI, unit tests, and offline-mode operators. Returns a
  zero-error annotation list and no rewrites; sufficient for the
  calibration pipeline.
- **`critic.CloudLLMCritic`** — opt-in cloud call (Claude Sonnet 4.6
  + structured output enforcement; temperature ≤ 0.2 per ADR-039).
  Disabled by default; enabled per-deploy via
  `TCF_ACCEL_SCORING_LLM=cloud`. Privacy: per ADR-017, learner
  artifacts never leave the device without explicit operator opt-in.

### 4.2 Strict-grading instruction

The prompt template includes a hard refuse-to-inflate rule: "If you
cannot justify a 5/5 with a quoted text span as evidence, the score is
4/5 maximum." Few-shot anchors at NCLC 7, 9, and 11 ceilings are
included. Temperature ≤ 0.2; structured output enforcement (ADR-039).

---

## 5. Calibration layer

### 5.1 The Ridge model

```python
# packages/ml/src/tcf_accel_ml/scoring/calibrate/ridge.py
class Ridge:
    """Pure-Python Ridge regression.

    Solves (X^T X + α I) w = X^T y via Gaussian elimination. No numpy
    dependency — keeps the package importable in CI. For our 6-input,
    ~200-row use case the closed-form solve is microseconds.
    """
    def fit(self, X: list[list[float]], y: list[float], *, alpha: float = 1.0): ...
    def predict(self, x: list[float]) -> float: ...
```

### 5.2 RubricCalibrator

```python
# packages/ml/src/tcf_accel_ml/scoring/calibrate/calibrator.py
class RubricCalibrator:
    """
    For each rubric dimension, a Ridge regressor:
        rubric_score = w_features · features + w_llm · llm_score + bias
    Trained on the expert-labeled set; evaluated by κ + Pearson r + MAE.
    """
    def __init__(self, *, dimensions: list[str], alpha: float = 1.0): ...
    def fit(self,
            features_per_row: list[list[float]],
            llm_scores_per_row: dict[str, list[float]],
            expert_scores_per_row: dict[str, list[float]]) -> None: ...
    def predict(self,
                features: list[float],
                llm_scores: dict[str, float]) -> dict[str, float]: ...
    @property
    def training_set_hash(self) -> str: ...
    @property
    def version(self) -> str: ...
```

The calibrator is **persisted as JSON** (weights, bias, training-set
hash, dimension list). No joblib / pickle dependency; the JSON-on-disk
format is forward-compatible and human-auditable. Versioned by
`(rubric_version, training_set_hash)`.

When no calibrator exists for a `rubric_version`, the scorer falls
back to an **uncalibrated identity** path: the LLM scores pass
through, with `confident=False` set on the resulting rubric. This is
the safe default for fresh deployments — the audit will catch any
release that ships an uncalibrated rubric without the experimental
badge (ADR-038).

### 5.3 Inflation guard (ADR-040)

```python
def apply_inflation_guard(
    *, llm_scores: dict[str, float],
    feature_predicted_scores: dict[str, float],
    threshold: float = 3.0,
    clamp_offset: float = 2.0,
) -> tuple[dict[str, float], bool]:
    """If any LLM score is > feature_predicted + threshold, clamp.

    Returns (clamped_scores, needs_human_review).
    """
```

Called inside the EE/EO scorer before the calibrator predict step. The
clamp is logged; the resulting rubric carries `needs_human_review` so
the audit can flag flagged rows.

---

## 6. Cohen's κ

```python
# packages/ml/src/tcf_accel_ml/scoring/calibrate/kappa.py
def quadratic_weighted_kappa(
    *,
    rater_a: Sequence[int],
    rater_b: Sequence[int],
    min_rating: int = 0,
    max_rating: int = 5,
) -> float: ...
```

Pure-Python; no numpy dependency. Used by:

- The calibrator's internal LOO-CV during fit.
- `scripts/eval_kappa.py` for the release-time report.
- The audit tests.

---

## 7. EE scorer (the orchestrator)

```python
# packages/ml/src/tcf_accel_ml/scoring/ee/score.py
class EEScorer:
    def __init__(self,
                 *,
                 critic: LLMCritic | None = None,
                 calibrator: RubricCalibrator | None = None,
                 rubric_version: str = "ee.v1"): ...

    def score(self, *,
              text: str,
              prompt: str,
              task_number: int,
              target_word_count_range: tuple[int, int],
              required_canadian_context: bool,
              ) -> EEScoringResult: ...

@dataclass(frozen=True)
class EEScoringResult:
    rubric: WritingRubric
    features: WritingFeatures
    llm_critique: LLMCritique | None
    needs_human_review: bool
    confidence: float
    feedback_blocks: list[FeedbackBlock]
    rubric_version: str
    calibrator_version: str | None
```

The orchestrator:

1. Extract `WritingFeatures` from the text.
2. Call the LLM critic (if registered) for structured rubric scores +
   error annotations.
3. Apply the inflation guard.
4. Apply the calibrator (or pass-through if uncalibrated).
5. Dedupe + merge errors across detectors.
6. Render feedback blocks (top-3 fix suggestions, drill links).
7. Build the `WritingRubric` — `total_20` derived from the calibrated
   components per the schema invariant.

### 7.1 The `score_ee` worker hand-off

Phase 5 already created the registry pattern. Phase 7 registers an
`EEWorkerScorer` adapter at import-time of
`tcf_accel_ml.scoring.ee.score`:

```python
# packages/ml/src/tcf_accel_ml/scoring/ee/__init__.py
def install_default_scorer() -> None:
    """Register the calibrated EE scorer under 'ee.v1' (idempotent)."""
    from tcf_accel_worker.tasks.score_ee import register_scorer
    register_scorer("ee.v1", EEWorkerScorer())
```

The worker module continues to expose only the `score_ee` Celery
task; the registry indirection is preserved so the scorer can be
swapped per release without touching the worker.

---

## 8. EO scorer

Same shape as EE plus the pronunciation pipeline glue:

```python
# packages/ml/src/tcf_accel_ml/scoring/eo/score.py
class EOScorer:
    def __init__(self, *,
                 critic: LLMCritic | None = None,
                 calibrator: RubricCalibrator | None = None,
                 rubric_version: str = "eo.v1"): ...

    def score(self, *,
              transcript: str,
              prompt: str,
              task_number: int,
              duration_s: float,
              asr_mean_confidence: float,
              pronunciation_signal: PronunciationSignal | None,
              ) -> EOScoringResult: ...
```

Inherits the content dimensions from the writing scorer (computed on
the transcript) and adds:

- Pronunciation & prosody dimension from `PronunciationSignal.score` +
  the prosody features.
- Fluency & pace dimension from WPM + pause distribution + filler
  count.
- Interaction responsiveness from the LLM critic (no good heuristic).

When `pronunciation_signal.display_label == "insufficient_data"`, the
pronunciation dimension is flagged `confidence=0` and the rubric
carries `needs_human_review=True`.

---

## 9. Feedback rendering

```python
# packages/ml/src/tcf_accel_ml/scoring/feedback.py
@dataclass(frozen=True)
class FeedbackBlock:
    kind: Literal["strength", "fix", "context", "disclaimer"]
    headline: str
    detail: str
    learner_quote: str | None       # MUST render as a styled blockquote
    drill_id: str | None            # link into Phase 5 drills

def render_feedback(
    *, rubric: WritingRubric | SpeakingRubric,
    features: WritingFeatures | SpeakingFeatures,
    errors: list[ErrorAnnotation],
    pedagogical_tags: dict[int, str],
    target_nclc: int,
) -> list[FeedbackBlock]: ...
```

The render obeys the §8.4 anti-criterion: any learner-text fragment
included in a block is carried in `learner_quote`, never inlined into
`detail`. The UI is responsible for styling it as a blockquote.

The renderer caps fixes at 3 per rubric (the THINK doc's published
example is the canonical shape). When the rubric is below the learner's
`target_nclc`, the renderer prefers fixes whose error class is
*pedagogically actionable* (an `[ai+conditional] si-clause` fix is
preferred over a `[spelling] typo` fix when both are present).

---

## 10. The expert-labelled set (path 1–3)

`scripts/calibrate.py` consumes a JSONL of rated submissions:

```jsonl
{"id": "ee-0001", "rubric_version": "ee.v1",
 "task_number": 2, "text": "...", "prompt": "...",
 "target_word_count_range": [120, 150],
 "required_canadian_context": true,
 "expert_scores": {"task_completion": 4, "coherence_cohesion": 3, ...},
 "rater_kind": "gold"}
```

Trains a `RubricCalibrator` per rubric_version. Outputs:

- `data/calibration/ee.v1.json` — the calibrator weights.
- `data/calibration/ee.v1.kappa.json` — the κ table.
- `data/calibration/ee.v1.report.md` — human-readable summary.

`scripts/eval_kappa.py` is the release-time evaluator:

```bash
python scripts/eval_kappa.py --module EE --rubric-version ee.v1 \
    --expert data/calibration/ee.v1.holdout.jsonl
```

Emits the κ table per rubric dimension + Pearson r + MAE on total_20,
plus the `gold`/`silver` label flag.

---

## 11. HTTP surface

`POST /v1/submission/ee` — multipart form: `text`, `item_id`.

`POST /v1/submission/eo` — multipart form: `audio` (file), `item_id`.

`GET /v1/submission/{id}` — poll for grading status.

The API:

1. Persists the submission artifact (in-process store for Phase 7;
   Postgres+S3 swap-in is Phase 7's deferred step, paralleling the
   Phase 5 pattern).
2. Returns `SubmissionView` with `status="pending"` and the SHA-256.
3. Enqueues a Celery task; in tests with `task_always_eager=True` the
   scoring runs in-line, status flips to `graded` synchronously.
4. The `GET` route reads the in-process store and returns the current
   state.

The route is intentionally thin: the scoring lives in the Celery
task, the HTTP layer is upload + poll.

---

## 12. ADRs

- **ADR-036:** Hybrid feature + LLM + calibration architecture (this
  doc §4, §7).
- **ADR-037:** Expert-labelled set ≥ 200/skill is launch-blocking for
  "claimed κ" reporting; without it, the system reports κ_silver
  vs LLM rater + caveat.
- **ADR-038:** Publish κ with every release; κ < 0.55 requires the
  "experimental" badge in the rubric UI.
- **ADR-039:** LLM scoring uses temperature ≤ 0.2 + structured-output
  enforcement; no chain-of-thought leakage in the response.
- **ADR-040:** Inflation guard: LLM score > feature + 3 ⇒ clamp to
  feature + 2 + set `needs_human_review`.

---

## 13. What this design deliberately does NOT do

- No fine-tuned classifier. (Phase 10+ if labels arrive.)
- No PDF / Word document parsing. The UI restricts to plain text.
- No "explain why this is wrong" beyond one sentence per error.
  Pedagogically richer explanations belong in Phase 8's UX layer.
- No real-time word-by-word feedback during typing. The wire shape is
  async (`SubmissionView.status`).
- No grading of partial submissions. A submission below
  `target_word_count_range.min * 0.5` returns `needs_human_review=True`
  with an `under_length` flag.
