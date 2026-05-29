"""LLM critic protocol — shared by `LLMCriticStub` and the cloud adapter.

The cloud adapter (`tcf_accel_ml.scoring.llm.cloud`) is intentionally
not implemented in v1. The protocol is the hand-off so a deployment
can plug in a Claude / OpenAI / litellm client without touching the
scorer.

The structured output rule (ADR-039) is part of the protocol contract:
implementations MUST return a `LLMCritique`; refusal returns `refused=True`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from tcf_accel.schemas.content.ee import ErrorAnnotation

EE_RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "task_completion",
    "coherence_cohesion",
    "lexical_range",
    "grammatical_accuracy",
    "register_appropriateness",
    "canadian_context_integration",
)

EO_RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "task_completion",
    "fluency_pace",
    "pronunciation_prosody",
    "lexical_range",
    "grammatical_accuracy",
    "interaction_responsiveness",
)


@dataclass(frozen=True)
class SuggestedRewrite:
    """A LLM-proposed rewrite of one weak sentence.

    `original_span` is the character range in the source text. The
    renderer wraps `original_text` in a blockquote (ADR-040
    anti-criterion).
    """

    original_span: tuple[int, int]
    original_text: str
    suggested_text: str
    rationale_en: str
    rationale_fr: str


@dataclass(frozen=True)
class LLMCritique:
    """Structured output of an LLM critic call.

    Fields are stable across stub and cloud implementations.
    """

    rubric_scores: dict[str, int]
    justifications: dict[str, str] = field(default_factory=dict)
    error_annotations: list[ErrorAnnotation] = field(default_factory=list)
    suggested_rewrites: list[SuggestedRewrite] = field(default_factory=list)
    confidence: float = 0.0
    refused: bool = False


class LLMCritic(Protocol):
    """Phase 7 LLM critic protocol.

    Implementations:
    - `LLMCriticStub` — deterministic local stand-in (CI, offline).
    - A cloud adapter — opt-in per ADR-017.
    """

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
        """Score an EE submission. Must return a `LLMCritique`; refusal uses `refused=True`."""
        ...

    def critique_eo(
        self,
        *,
        prompt: str,
        transcript: str,
        rubric_version: str,
        task_number: int,
        duration_s: float,
    ) -> LLMCritique:
        """Score an EO submission. Must return a `LLMCritique`; refusal uses `refused=True`."""
        ...


__all__ = [
    "EE_RUBRIC_DIMENSIONS",
    "EO_RUBRIC_DIMENSIONS",
    "LLMCritic",
    "LLMCritique",
    "SuggestedRewrite",
]
