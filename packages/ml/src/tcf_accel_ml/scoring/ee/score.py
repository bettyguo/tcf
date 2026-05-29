"""EE scoring orchestrator (Phase 7).

Composes feature extraction, the LLM critic, the inflation guard, the
calibrator, error dedup, and the feedback render into a single
`EEScorer.score()` call. The `EEWorkerScorer` adapter is what the
Celery `score_ee` task calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tcf_accel.schemas.content.ee import ErrorAnnotation
from tcf_accel.schemas.scoring import WritingRubric

from tcf_accel_ml.scoring.calibrate.calibrator import RubricCalibrator
from tcf_accel_ml.scoring.feedback import FeedbackBlock, render_feedback
from tcf_accel_ml.scoring.features.errors import detect_errors
from tcf_accel_ml.scoring.features.writing import (
    WritingFeatures,
    extract_writing_features,
)
from tcf_accel_ml.scoring.inflation_guard import (
    InflationGuardResult,
    apply_inflation_guard,
)
from tcf_accel_ml.scoring.llm.critic import (
    EE_RUBRIC_DIMENSIONS,
    LLMCritic,
    LLMCritique,
)
from tcf_accel_ml.scoring.llm.stub import LLMCriticStub
from tcf_accel_ml.scoring.rubric_table import nclc_from_total_20


@dataclass(frozen=True)
class EEScoringResult:
    rubric: WritingRubric
    features: WritingFeatures
    llm_critique: LLMCritique
    inflation_guard: InflationGuardResult
    needs_human_review: bool
    confidence: float
    feedback_blocks: list[FeedbackBlock]
    rubric_version: str
    calibrator_version: str | None
    under_length: bool

    def as_graded_score(self) -> dict[str, Any]:
        """The dict shape persisted in `Interaction.graded_score`."""
        return {
            "phase7_status": "graded",
            "rubric_version": self.rubric_version,
            "calibrator_version": self.calibrator_version,
            "needs_human_review": self.needs_human_review,
            "confidence": self.confidence,
            "under_length": self.under_length,
            "inflation_guard": {
                "clamped_dimensions": list(self.inflation_guard.clamped_dimensions),
            },
            "rubric": self.rubric.model_dump(),
            "features": {
                "word_count": self.features.word_count,
                "type_token_ratio": self.features.type_token_ratio,
                "moving_average_ttr_25": self.features.moving_average_ttr_25,
                "discourse_marker_count": self.features.discourse_marker_count,
                "distinct_discourse_categories": self.features.distinct_discourse_categories,
                "error_density_per_100w": self.features.error_density_per_100w,
                "canadian_lexicon_density": self.features.canadian_lexicon_density,
                "register_score": self.features.register_score,
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
class EEScorer:
    """Orchestrator for EE rubric scoring.

    Construct once per process; reuse across submissions.
    """

    critic: LLMCritic = field(default_factory=LLMCriticStub)
    calibrator: RubricCalibrator | None = None
    rubric_version: str = "ee.v1"
    inflation_threshold: float = 3.0
    inflation_clamp_offset: float = 2.0

    def score(
        self,
        *,
        text: str,
        prompt: str,
        task_number: int,
        target_word_count_range: tuple[int, int],
        required_canadian_context: bool,
        target_nclc: int = 9,
    ) -> EEScoringResult:
        """Score an EE submission. Pure function once configured."""
        features = extract_writing_features(text)
        under_length = features.word_count < int(0.5 * target_word_count_range[0])

        critique = self.critic.critique_ee(
            prompt=prompt,
            text=text,
            rubric_version=self.rubric_version,
            task_number=task_number,
            target_word_count_range=target_word_count_range,
            required_canadian_context=required_canadian_context,
        )

        feature_floor = _feature_floor_scores(
            features,
            required_canadian_context=required_canadian_context,
            target_word_count_range=target_word_count_range,
        )

        guard = apply_inflation_guard(
            llm_scores={dim: float(critique.rubric_scores.get(dim, 0)) for dim in EE_RUBRIC_DIMENSIONS},
            feature_predicted_scores=feature_floor,
            threshold=self.inflation_threshold,
            clamp_offset=self.inflation_clamp_offset,
        )

        # Calibration: predict per-dimension expert score from features + clamped LLM.
        if self.calibrator is not None:
            calibrated = self.calibrator.predict(
                features=features.as_vector(),
                llm_scores=guard.clamped_scores,
            )
            # Backfill any dimension the calibrator does not own.
            for dim in EE_RUBRIC_DIMENSIONS:
                calibrated.setdefault(dim, guard.clamped_scores.get(dim, 0.0))
            calibrator_version = self.calibrator.training_set_hash[:12] or None
            calibration_confidence = 0.85
        else:
            calibrated = dict(guard.clamped_scores)
            calibrator_version = None
            calibration_confidence = 0.55

        # Convert to integer rubric scores and assemble the WritingRubric.
        def to_int(v: float) -> int:
            return max(0, min(5, int(round(v))))

        task_completion = to_int(calibrated.get("task_completion", 0.0))
        coherence = to_int(calibrated.get("coherence_cohesion", 0.0))
        lexical = to_int(calibrated.get("lexical_range", 0.0))
        grammar = to_int(calibrated.get("grammatical_accuracy", 0.0))
        register = to_int(calibrated.get("register_appropriateness", 0.0))
        if required_canadian_context:
            canadian: int | None = to_int(calibrated.get("canadian_context_integration", 0.0))
        else:
            canadian = None

        # total_20 derived from the 5 primary dims (schema invariant).
        components_sum = task_completion + coherence + lexical + grammar + register
        total_20 = max(0, min(20, round(components_sum * 4.0 / 5.0)))

        all_errors = _merge_errors(detect_errors(text), critique.error_annotations)

        rubric = WritingRubric(
            task_completion=task_completion,
            coherence_cohesion=coherence,
            lexical_range=lexical,
            grammatical_accuracy=grammar,
            register_appropriateness=register,
            canadian_context_integration=canadian,
            total_20=total_20,
            error_density_per_100w=features.error_density_per_100w,
            type_token_ratio=features.type_token_ratio,
            discourse_marker_count=features.discourse_marker_count,
            error_list=all_errors,
        )

        # Confidence: calibrator confidence × LLM confidence × length factor.
        length_factor = 1.0 if not under_length else 0.5
        confidence = float(calibration_confidence * max(0.3, critique.confidence) * length_factor)

        needs_review = guard.needs_human_review or under_length or critique.refused

        blocks = render_feedback(
            rubric=rubric,
            features=features,
            text=text,
            errors=all_errors,
            target_nclc=target_nclc,
            is_speaking=False,
        )

        return EEScoringResult(
            rubric=rubric,
            features=features,
            llm_critique=critique,
            inflation_guard=guard,
            needs_human_review=needs_review,
            confidence=confidence,
            feedback_blocks=blocks,
            rubric_version=self.rubric_version,
            calibrator_version=calibrator_version,
            under_length=under_length,
        )


def _feature_floor_scores(
    features: WritingFeatures,
    *,
    required_canadian_context: bool,
    target_word_count_range: tuple[int, int],
) -> dict[str, float]:
    """Convert the feature vector into per-rubric *floor* scores in 0–5.

    These are the conservative estimates the inflation guard tests
    against. Independent of the LLM critic.
    """
    lo, hi = target_word_count_range
    out: dict[str, float] = {}
    out["task_completion"] = _scale_bucket(features.word_count / max(1, lo), [0.4, 0.7, 1.0, 1.3])
    out["coherence_cohesion"] = float(min(5, features.distinct_discourse_categories + 1))
    out["lexical_range"] = _scale_bucket(
        features.moving_average_ttr_25, [0.30, 0.45, 0.55, 0.65],
    )
    ed = features.error_density_per_100w
    out["grammatical_accuracy"] = (
        1.0 if ed >= 6 else 2.0 if ed >= 4 else 3.0 if ed >= 2 else 4.0
    )
    out["register_appropriateness"] = _scale_bucket(
        1.0 - abs(features.register_score), [0.3, 0.55, 0.75, 0.9],
    )
    if required_canadian_context:
        out["canadian_context_integration"] = _scale_bucket(
            features.canadian_lexicon_density * 100.0, [0.5, 1.5, 3.0, 5.0],
        )
    else:
        out["canadian_context_integration"] = 0.0
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
    """Dedupe annotations across detectors by `(span, type)`; keep max-confidence."""
    by_key: dict[tuple[int, int, str], ErrorAnnotation] = {}
    for e in (*a, *b):
        key = (e.span_start, e.span_end, e.error_type)
        prev = by_key.get(key)
        if prev is None or e.confidence > prev.confidence:
            by_key[key] = e
    return sorted(by_key.values(), key=lambda e: (e.span_start, e.span_end, e.error_type))


@dataclass(frozen=True)
class EEWorkerScorer:
    """Adapter — implements the worker's `RubricScorer` protocol.

    Held by the worker registry. Constructs a fresh `EEScorer` per call
    so test code can swap the critic/calibrator without holding global
    state on the worker side.
    """

    rubric_version: str = "ee.v1"

    def score_ee(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", ""))
        prompt = str(payload.get("prompt", ""))
        task_number = int(payload.get("task_number", 1) or 1)
        target_range_raw = payload.get("target_word_count_range") or (120, 200)
        target_range = (int(target_range_raw[0]), int(target_range_raw[1]))
        required_canadian = bool(payload.get("required_canadian_context", False))
        target_nclc = int(payload.get("target_nclc", 9) or 9)

        scorer = EEScorer(rubric_version=self.rubric_version)
        result = scorer.score(
            text=text,
            prompt=prompt,
            task_number=task_number,
            target_word_count_range=target_range,
            required_canadian_context=required_canadian,
            target_nclc=target_nclc,
        )
        return result.as_graded_score()


__all__ = ["EEScorer", "EEScoringResult", "EEWorkerScorer"]
