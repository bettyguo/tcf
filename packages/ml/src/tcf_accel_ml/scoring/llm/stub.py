"""`LLMCriticStub` — deterministic local stand-in for the cloud LLM.

Used in CI, unit tests, and offline-mode deployments. The stub
derives per-rubric scores from the feature vector via a hand-tuned
bucket map; no network calls, no randomness.

The stub's scores are intentionally **conservative**: they hover
around NCLC 7–9 for plausible submissions, undershoot for short or
error-heavy inputs, and never give a 5/5 (the strict-grading rule
demands quoted evidence the stub cannot produce).

For tests that need a higher LLM score (e.g., inflation-guard tests),
pass `force_scores=` to the constructor.
"""

from __future__ import annotations

from dataclasses import dataclass

from tcf_accel_ml.scoring.features.errors import detect_errors
from tcf_accel_ml.scoring.features.writing import extract_writing_features
from tcf_accel_ml.scoring.llm.critic import (
    EE_RUBRIC_DIMENSIONS,
    EO_RUBRIC_DIMENSIONS,
    LLMCritique,
    SuggestedRewrite,
)


def _bucket(value: float, breakpoints: list[float]) -> int:
    """Bucket a continuous value into `[0..len(breakpoints)]`."""
    band = 0
    for bp in breakpoints:
        if value >= bp:
            band += 1
    return min(band, len(breakpoints))


@dataclass(frozen=True)
class LLMCriticStub:
    """Deterministic stub. Construct once, share across calls."""

    force_scores: dict[str, int] | None = None
    confidence: float = 0.6

    def critique_ee(
        self,
        *,
        prompt: str,
        text: str,
        rubric_version: str,
        task_number: int,
        target_word_count_range: tuple[int, int],
        required_canadian_context: bool,
    ) -> LLMCritique:
        if self.force_scores is not None:
            scores = dict(self.force_scores)
        else:
            scores = self._derive_ee_scores(
                text=text,
                target_range=target_word_count_range,
                required_canadian_context=required_canadian_context,
                task_number=task_number,
            )
        return LLMCritique(
            rubric_scores=scores,
            justifications={k: "stub: derived from feature pipeline" for k in scores},
            error_annotations=detect_errors(text),
            suggested_rewrites=[],
            confidence=self.confidence,
            refused=False,
        )

    def critique_eo(
        self,
        *,
        prompt: str,
        transcript: str,
        rubric_version: str,
        task_number: int,
        duration_s: float,
    ) -> LLMCritique:
        if self.force_scores is not None:
            scores = dict(self.force_scores)
        else:
            scores = self._derive_eo_scores(
                transcript=transcript,
                duration_s=duration_s,
                task_number=task_number,
            )
        return LLMCritique(
            rubric_scores=scores,
            justifications={k: "stub: derived from feature pipeline" for k in scores},
            error_annotations=detect_errors(transcript),
            suggested_rewrites=[],
            confidence=self.confidence,
            refused=False,
        )

    # ─── Internals ────────────────────────────────────────────────

    def _derive_ee_scores(
        self,
        *,
        text: str,
        target_range: tuple[int, int],
        required_canadian_context: bool,
        task_number: int,
    ) -> dict[str, int]:
        f = extract_writing_features(text)
        lo, hi = target_range
        scores: dict[str, int] = {dim: 0 for dim in EE_RUBRIC_DIMENSIONS}

        # Task completion: bands by under/over-length + presence.
        if f.word_count == 0:
            scores["task_completion"] = 0
        else:
            ratio = f.word_count / max(1, lo)
            scores["task_completion"] = _bucket(ratio, [0.4, 0.7, 1.0, 1.3])

        # Coherence & cohesion: density × diversity.
        scores["coherence_cohesion"] = max(
            _bucket(f.discourse_marker_density_per_100w, [0.5, 1.5, 3.0, 4.5]),
            _bucket(f.distinct_discourse_categories, [1, 2, 3, 4]),
        )

        # Lexical range: MATTR-25 buckets.
        scores["lexical_range"] = _bucket(f.moving_average_ttr_25, [0.30, 0.45, 0.55, 0.65])

        # Grammatical accuracy: inverse of error density.
        ed = f.error_density_per_100w
        if ed >= 6:
            scores["grammatical_accuracy"] = 1
        elif ed >= 4:
            scores["grammatical_accuracy"] = 2
        elif ed >= 2:
            scores["grammatical_accuracy"] = 3
        elif ed >= 0.5:
            scores["grammatical_accuracy"] = 4
        else:
            scores["grammatical_accuracy"] = 4  # stub never gives 5/5
            if f.word_count >= max(lo, 60):
                scores["grammatical_accuracy"] = 4

        # Register: closeness to soutenu axis for formal tasks.
        if task_number == 1:
            # informal letter — neutral register acceptable
            target = 0.0
        else:
            target = 0.4
        delta = abs(f.register_score - target)
        scores["register_appropriateness"] = _bucket(1.0 - delta, [0.3, 0.55, 0.75, 0.9])

        # Canadian context: only Tasks 2/3.
        if required_canadian_context:
            scores["canadian_context_integration"] = _bucket(
                f.canadian_lexicon_density * 100.0, [0.5, 1.5, 3.0, 5.0],
            )
        else:
            scores["canadian_context_integration"] = 0  # null path handled by orchestrator
        return {k: int(min(4, max(0, v))) for k, v in scores.items()}

    def _derive_eo_scores(
        self,
        *,
        transcript: str,
        duration_s: float,
        task_number: int,
    ) -> dict[str, int]:
        f = extract_writing_features(transcript)
        scores: dict[str, int] = {dim: 0 for dim in EO_RUBRIC_DIMENSIONS}
        scores["task_completion"] = _bucket(f.word_count / 30.0, [0.5, 1.0, 1.5, 2.5])
        scores["lexical_range"] = _bucket(f.moving_average_ttr_25, [0.30, 0.45, 0.55, 0.65])
        ed = f.error_density_per_100w
        scores["grammatical_accuracy"] = (
            1 if ed >= 6 else 2 if ed >= 4 else 3 if ed >= 2 else 4
        )
        scores["fluency_pace"] = _bucket(duration_s, [10, 30, 60, 120])
        scores["pronunciation_prosody"] = 3  # the dedicated signal supersedes; stub stays neutral
        scores["interaction_responsiveness"] = _bucket(
            f.distinct_discourse_categories, [1, 2, 3, 4],
        )
        return {k: int(min(4, max(0, v))) for k, v in scores.items()}


__all__ = ["LLMCriticStub", "SuggestedRewrite"]
