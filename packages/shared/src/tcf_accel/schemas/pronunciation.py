"""`PronunciationSignal` — coarse-proxy pronunciation feedback (ADR-031).

The structural complement to ADR-025 (`NCLCEstimate.confident`): a
pronunciation score is a *prediction*, not a measurement, and the
contract makes that fact load-bearing rather than decorative.

The UI consumes `display_label`; the rubric scorer consumes `score`.
A future contributor cannot reify the raw score as evaluative without
deleting (a) the `signal_kind="coarse_proxy"` literal, (b) the
`disclaimer_version` requirement, or (c) the static lint rule against
`.score` access outside the rubric scorer and the planner.

`display_label="insufficient_data"` is the refuse-to-predict path: the
score field is still present but the planner ignores it. The audit
asserts this invariant on 1000 short-utterance synthetic samples.

Example:
    >>> sig = PronunciationSignal(
    ...     score=0.86,
    ...     disclaimer_version="v1.0",
    ...     display_label="fair",
    ...     per=0.14,
    ...     asr_mean_confidence=0.82,
    ...     n_phonemes_aligned=42,
    ...     duration_s=6.3,
    ...     prosody=PronunciationProsody(
    ...         pitch_range_hz=180.0,
    ...         speech_rate_wpm=132.0,
    ...         pause_count=2,
    ...         mean_pause_ms=240.0,
    ...     ),
    ... )
    >>> sig.signal_kind
    'coarse_proxy'

Complexity: O(1) construction; the model is frozen.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PronunciationDisplayLabel = Literal[
    "weak",
    "fair",
    "strong",
    "insufficient_data",
]


class PronunciationProsody(BaseModel):
    """Aggregated prosody features for a single utterance.

    Computed by `tcf_accel_ml.prosody.*` from the learner's waveform.
    All values are *observed*, not predicted; the coarseness is in the
    aggregation, not in the measurement.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    pitch_range_hz: float = Field(
        ge=0.0,
        description="f0 max minus f0 min over the utterance (Hz).",
    )
    speech_rate_wpm: float = Field(
        ge=0.0,
        description="Words per minute, computed from the ASR transcript and utterance duration.",
    )
    pause_count: int = Field(
        ge=0,
        description="Number of silences ≥ 200 ms inside the utterance.",
    )
    mean_pause_ms: float = Field(
        ge=0.0,
        description="Mean duration in ms across detected pauses; 0 if pause_count == 0.",
    )


class PronunciationSignal(BaseModel):
    """Coarse-proxy pronunciation signal (ADR-031).

    Structural contract:

    - `signal_kind` is fixed at `"coarse_proxy"`. The UI surface treats
      this as a load-bearing literal; pronunciation feedback is never
      reified as evaluative.
    - `disclaimer_version` is required and non-empty. The UI renders
      the matching disclaimer text alongside any surfaced label.
    - `display_label` is the field the UI displays. `score` is for the
      rubric scorer and the planner; direct access from elsewhere is
      lint-blocked.
    - `display_label == "insufficient_data"` ⇒ the planner ignores
      this signal entirely. The drill's other grading paths (e.g.,
      shadowing WPM band) still apply.

    Construction sites: only `packages/ml/src/tcf_accel_ml/
    pronunciation/signal.py::build_signal()`. Direct construction in
    application code is discouraged; the constructor exists so that
    Phase 7's rubric tests and Phase 5's audit can build instances.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Continuous pronunciation score in [0, 1]. Consumed by the rubric "
            "scorer and the planner; the UI consumes `display_label` instead."
        ),
    )
    signal_kind: Literal["coarse_proxy"] = Field(
        default="coarse_proxy",
        description="Load-bearing literal; ADR-031. Do not interpret as evaluative.",
    )
    disclaimer_version: str = Field(
        min_length=1,
        description=(
            "Version of the disclaimer copy the UI must render adjacent to "
            "any surfaced label. The copy lives in "
            "`packages/content/data/pron_disclaimers.{en,fr}.yaml`."
        ),
    )
    display_label: PronunciationDisplayLabel = Field(
        description=(
            "The UI-renderable label. `insufficient_data` means the pipeline "
            "refused to predict; the planner ignores this row's contribution."
        ),
    )

    per: float = Field(
        ge=0.0,
        description="Phoneme error rate against the canonical reference.",
    )
    asr_mean_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Mean per-token confidence from the ASR (Whisper-large-v3-french).",
    )
    n_phonemes_aligned: int = Field(
        ge=0,
        description="Number of phonemes the forced aligner placed against the reference.",
    )
    duration_s: float = Field(
        ge=0.0,
        description="Utterance duration in seconds.",
    )
    prosody: PronunciationProsody


__all__ = [
    "PronunciationDisplayLabel",
    "PronunciationProsody",
    "PronunciationSignal",
]
