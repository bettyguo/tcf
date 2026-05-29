"""EO scoring orchestrator (Phase 7).

Same shape as `EEScorer` plus a pronunciation pipeline glue: consumes
the Phase-5 `PronunciationSignal` (already coarse-proxy gated) and
the prosody summary to drive the `pronunciation_prosody` and
`fluency_pace` dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tcf_accel.schemas.content.ee import ErrorAnnotation
from tcf_accel.schemas.pronunciation import PronunciationProsody, PronunciationSignal
from tcf_accel.schemas.scoring import SpeakingRubric

from tcf_accel_ml.scoring.calibrate.calibrator import RubricCalibrator
from tcf_accel_ml.scoring.feedback import FeedbackBlock, render_feedback
from tcf_accel_ml.scoring.features.errors import detect_errors
from tcf_accel_ml.scoring.features.speaking import (
    SpeakingFeatures,
    extract_speaking_features,
)
from tcf_accel_ml.scoring.inflation_guard import (
    InflationGuardResult,
    apply_inflation_guard,
)
from tcf_accel_ml.scoring.llm.critic import (
    EO_RUBRIC_DIMENSIONS,
    LLMCritic,
    LLMCritique,
)
from tcf_accel_ml.scoring.llm.stub import LLMCriticStub
from tcf_accel_ml.scoring.rubric_table import nclc_from_total_20


@dataclass(frozen=True)
class EOScoringResult:
    rubric: SpeakingRubric
    features: SpeakingFeatures
    llm_critique: LLMCritique
    inflation_guard: InflationGuardResult
    needs_human_review: bool
    confidence: float
    feedback_blocks: list[FeedbackBlock]
    rubric_version: str
    calibrator_version: str | None
    pronunciation_display_label: str

    def as_graded_score(self) -> dict[str, Any]:
        return {
            "phase7_status": "graded",
            "rubric_version": self.rubric_version,
            "calibrator_version": self.calibrator_version,
            "needs_human_review": self.needs_human_review,
            "confidence": self.confidence,
            "inflation_guard": {
                "clamped_dimensions": list(self.inflation_guard.clamped_dimensions),
            },
            "pronunciation_display_label": self.pronunciation_display_label,
            "rubric": self.rubric.model_dump(),
            "features": {
                "duration_s": self.features.duration_s,
                "wpm": self.features.wpm,
                "pause_count_per_minute": self.features.pause_count_per_minute,
                "filler_count_per_minute": self.features.filler_count_per_minute,
                "asr_mean_confidence": self.features.asr_mean_confidence,
                "phoneme_error_rate": self.features.phoneme_error_rate,
                "self_correction_count": self.features.self_correction_count,
            },
            "nclc_band": nclc_from_total_20(self.rubric.total_20),
            "feedback_blocks": [
                {
                    "kind": fb.kind,
                    "headline": fb.headline,
                    "detail": fb.detail,
                    "learner_quote": fb.learner_quote,
                    "drill_id": fb.drill_id,
                }
                for fb in self.feedback_blocks
            ],
        }


@dataclass
class EOScorer:
    """Orchestrator for EO rubric scoring."""

    critic: LLMCritic = field(default_factory=LLMCriticStub)
    calibrator: RubricCalibrator | None = None
    rubric_version: str = "eo.v1"
    inflation_threshold: float = 3.0
    inflation_clamp_offset: float = 2.0

    def score(
        self,
        *,
        transcript: str,
        prompt: str,
        task_number: int,
        duration_s: float,
        asr_mean_confidence: float,
        pronunciation_signal: PronunciationSignal | None,
        pause_count: int = 0,
        pause_total_s: float = 0.0,
        target_nclc: int = 9,
    ) -> EOScoringResult:
        features = extract_speaking_features(
            transcript=transcript,
            duration_s=duration_s,
            asr_mean_confidence=asr_mean_confidence,
            pronunciation_signal=pronunciation_signal,
            pause_count=pause_count,
            pause_total_s=pause_total_s,
        )

        critique = self.critic.critique_eo(
            prompt=prompt,
            transcript=transcript,
            rubric_version=self.rubric_version,
            task_number=task_number,
            duration_s=duration_s,
        )

        feature_floor = _eo_feature_floor_scores(features, task_number=task_number)

        guard = apply_inflation_guard(
            llm_scores={dim: float(critique.rubric_scores.get(dim, 0)) for dim in EO_RUBRIC_DIMENSIONS},
            feature_predicted_scores=feature_floor,
            threshold=self.inflation_threshold,
            clamp_offset=self.inflation_clamp_offset,
        )

        if self.calibrator is not None:
            calibrated = self.calibrator.predict(
                features=features.as_vector(),
                llm_scores=guard.clamped_scores,
            )
            for dim in EO_RUBRIC_DIMENSIONS:
                calibrated.setdefault(dim, guard.clamped_scores.get(dim, 0.0))
            calibrator_version = self.calibrator.training_set_hash[:12] or None
            calibration_confidence = 0.85
        else:
            calibrated = dict(guard.clamped_scores)
            calibrator_version = None
            calibration_confidence = 0.55

        def to_int(v: float) -> int:
            return max(0, min(5, int(round(v))))

        # Override the pronunciation/prosody dimension with the dedicated
        # pipeline's signal (Phase 5 owns this); the LLM critic should
        # not over-rule the coarse-proxy gate.
        pron_dim_from_signal = _pronunciation_dim_from_signal(pronunciation_signal)
        if pron_dim_from_signal is not None:
            calibrated["pronunciation_prosody"] = float(pron_dim_from_signal)

        task_completion = to_int(calibrated.get("task_completion", 0.0))
        fluency = to_int(calibrated.get("fluency_pace", 0.0))
        pronunciation = to_int(calibrated.get("pronunciation_prosody", 0.0))
        lexical = to_int(calibrated.get("lexical_range", 0.0))
        grammar = to_int(calibrated.get("grammatical_accuracy", 0.0))
        interaction = to_int(calibrated.get("interaction_responsiveness", 0.0))

        components_sum = (
            task_completion + fluency + pronunciation + lexical + grammar + interaction
        )
        total_20 = max(0, min(20, round(components_sum * 2.0 / 3.0)))

        pron_display_label = (
            pronunciation_signal.display_label
            if pronunciation_signal is not None
            else "insufficient_data"
        )

        rubric = SpeakingRubric(
            task_completion=task_completion,
            fluency_pace=fluency,
            pronunciation_prosody=pronunciation,
            lexical_range=lexical,
            grammatical_accuracy=grammar,
            interaction_responsiveness=interaction,
            total_20=total_20,
            wpm=features.wpm,
            pause_ratio=features.pause_total_ratio,
            phoneme_error_rate=features.phoneme_error_rate,
        )

        all_errors = _merge_errors(detect_errors(transcript), critique.error_annotations)

        confidence = float(calibration_confidence * max(0.3, critique.confidence))
        if pron_display_label == "insufficient_data":
            confidence *= 0.6

        needs_review = (
            guard.needs_human_review
            or critique.refused
            or pron_display_label == "insufficient_data"
        )

        blocks = render_feedback(
            rubric=rubric,
            features=features,
            text=transcript,
            errors=all_errors,
            target_nclc=target_nclc,
            is_speaking=True,
        )

        return EOScoringResult(
            rubric=rubric,
            features=features,
            llm_critique=critique,
            inflation_guard=guard,
            needs_human_review=needs_review,
            confidence=confidence,
            feedback_blocks=blocks,
            rubric_version=self.rubric_version,
            calibrator_version=calibrator_version,
            pronunciation_display_label=pron_display_label,
        )


def _pronunciation_dim_from_signal(signal: PronunciationSignal | None) -> int | None:
    """Map a Phase-5 pronunciation signal to a 0..5 rubric score."""
    if signal is None:
        return None
    label = signal.display_label
    if label == "insufficient_data":
        return 2  # neutral, low-confidence default
    if label == "weak":
        return 1
    if label == "fair":
        return 3
    if label == "strong":
        return 5
    return None


def _eo_feature_floor_scores(
    features: SpeakingFeatures, *, task_number: int,
) -> dict[str, float]:
    out: dict[str, float] = {}
    out["task_completion"] = _scale_bucket(
        features.writing.word_count / 30.0, [0.5, 1.0, 1.5, 2.5],
    )
    # Fluency: WPM in the 130–180 band scores high.
    wpm = features.wpm
    if wpm == 0:
        out["fluency_pace"] = 0.0
    elif 130 <= wpm <= 180:
        out["fluency_pace"] = 4.0
    elif 100 <= wpm < 130 or 180 < wpm <= 220:
        out["fluency_pace"] = 3.0
    elif 70 <= wpm < 100 or 220 < wpm <= 240:
        out["fluency_pace"] = 2.0
    else:
        out["fluency_pace"] = 1.0
    # Pronunciation handled by signal.
    out["pronunciation_prosody"] = 2.0
    out["lexical_range"] = _scale_bucket(
        features.writing.moving_average_ttr_25, [0.30, 0.45, 0.55, 0.65],
    )
    ed = features.writing.error_density_per_100w
    out["grammatical_accuracy"] = (
        1.0 if ed >= 6 else 2.0 if ed >= 4 else 3.0 if ed >= 2 else 4.0
    )
    out["interaction_responsiveness"] = _scale_bucket(
        features.writing.distinct_discourse_categories, [1, 2, 3, 4],
    )
    return out


def _scale_bucket(value: float, breakpoints: list[float]) -> float:
    band = 0
    for bp in breakpoints:
        if value >= bp:
            band += 1
    return float(min(band, len(breakpoints)))


def _merge_errors(
    a: list[ErrorAnnotation],
    b: list[ErrorAnnotation],
) -> list[ErrorAnnotation]:
    by_key: dict[tuple[int, int, str], ErrorAnnotation] = {}
    for e in (*a, *b):
        key = (e.span_start, e.span_end, e.error_type)
        prev = by_key.get(key)
        if prev is None or e.confidence > prev.confidence:
            by_key[key] = e
    return sorted(by_key.values(), key=lambda e: (e.span_start, e.span_end, e.error_type))


@dataclass(frozen=True)
class EOWorkerScorer:
    """Adapter — implements the worker's `EORubricScorer` protocol."""

    rubric_version: str = "eo.v1"

    def score_eo(self, payload: dict[str, Any]) -> dict[str, Any]:
        transcript = str(payload.get("transcript", ""))
        prompt = str(payload.get("prompt", ""))
        task_number = int(payload.get("task_number", 1) or 1)
        duration_s = float(payload.get("duration_s", 0.0) or 0.0)
        asr_conf = float(payload.get("asr_mean_confidence", 0.0) or 0.0)
        pause_count = int(payload.get("pause_count", 0) or 0)
        pause_total_s = float(payload.get("pause_total_s", 0.0) or 0.0)
        target_nclc = int(payload.get("target_nclc", 9) or 9)

        signal = _signal_from_payload(payload)

        scorer = EOScorer(rubric_version=self.rubric_version)
        result = scorer.score(
            transcript=transcript,
            prompt=prompt,
            task_number=task_number,
            duration_s=duration_s,
            asr_mean_confidence=asr_conf,
            pronunciation_signal=signal,
            pause_count=pause_count,
            pause_total_s=pause_total_s,
            target_nclc=target_nclc,
        )
        return result.as_graded_score()


def _signal_from_payload(payload: dict[str, Any]) -> PronunciationSignal | None:
    """Best-effort reconstruction of a `PronunciationSignal` from the payload.

    The worker may receive the signal already-serialised (under
    `pronunciation_signal`) or with the partial coarse-proxy fields
    (`pronunciation_display_label`, `phoneme_error_rate`,
    `asr_mean_confidence`, `duration_s`, `prosody`). Both paths are
    accepted; on a partial payload the missing fields are filled with
    neutral defaults.
    """
    raw = payload.get("pronunciation_signal")
    if isinstance(raw, dict):
        try:
            return PronunciationSignal.model_validate(raw)
        except Exception:
            pass

    label = payload.get("pronunciation_display_label")
    per = payload.get("phoneme_error_rate")
    if label is None and per is None:
        return None
    prosody_dict = payload.get("prosody") or {}
    prosody = PronunciationProsody(
        pitch_range_hz=float(prosody_dict.get("pitch_range_hz", 0.0)),
        speech_rate_wpm=float(prosody_dict.get("speech_rate_wpm", 0.0)),
        pause_count=int(prosody_dict.get("pause_count", 0)),
        mean_pause_ms=float(prosody_dict.get("mean_pause_ms", 0.0)),
    )
    return PronunciationSignal(
        score=max(0.0, 1.0 - float(per or 0.0)),
        disclaimer_version="v1.0",
        display_label=label or "insufficient_data",
        per=float(per or 0.0),
        asr_mean_confidence=float(payload.get("asr_mean_confidence", 0.0) or 0.0),
        n_phonemes_aligned=int(payload.get("n_phonemes_aligned", 0) or 0),
        duration_s=float(payload.get("duration_s", 0.0) or 0.0),
        prosody=prosody,
    )


__all__ = ["EOScorer", "EOScoringResult", "EOWorkerScorer"]
