"""Scoring schemas — `Score`, `NCLCEstimate`, `WritingRubric`, `SpeakingRubric`.

Phase 1 enforced the load-bearing invariants on `Score` and
`NCLCEstimate`:

- `ci_low ≤ nclc ≤ ci_high` for every `Score`.
- `confident=False` makes the consumer (UI) refuse to render a final NCLC
  number; the application layer enforces this contract.

Phase 2 adds `WritingRubric` and `SpeakingRubric` per
`02_ARCHITECTURE.md §2.3` and `phase2_design.md §3.2`. Phase 7 implements
the scorers; the *shape* is fixed here so the API stubs, the OpenAPI
spec, and the generated clients can lock to it now.

Phase 4 will elaborate `NCLCEstimate` with posterior variance and
difficulty-band spread (see ADR-0013); the public surface here is what
the API will emit.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from tcf_accel.schemas.content.ee import ErrorAnnotation

SkillCode = Literal["CO", "CE", "EE", "EO"]


class Score(BaseModel):
    """A single skill's NCLC-mapped score with a credible interval.

    Master prompt §6.2: every NCLC point estimate MUST come with a CI.
    The `confident` flag is the launch-blocking gate: when `False`, the
    UI is forbidden from showing the estimate as a final number.

    Example:
        >>> Score(nclc=8, raw=510.0, ci_low=7, ci_high=9, n_observations=45,
        ...       confident=True).nclc
        8

    Complexity: O(1) construction + validation.
    """

    model_config = ConfigDict(extra="forbid")

    nclc: int = Field(ge=1, le=12, description="Predicted NCLC band, 1..12.")
    raw: float = Field(
        description="Raw score on the module's native scale (0–699 for CO/CE, 0–20 for EE/EO).",
    )
    ci_low: int = Field(ge=1, le=12)
    ci_high: int = Field(ge=1, le=12)
    n_observations: int = Field(ge=0)
    confident: bool = Field(
        description=(
            "If False, callers MUST NOT render a final point estimate. "
            "See `04_LEARNER_MODEL.md §2.3` for the rules that set this."
        ),
    )

    @model_validator(mode="after")
    def _ci_invariant(self) -> Self:
        if self.ci_low > self.ci_high:
            msg = f"ci_low={self.ci_low} > ci_high={self.ci_high}"
            raise ValueError(msg)
        if not (self.ci_low <= self.nclc <= self.ci_high):
            msg = (
                f"Point estimate nclc={self.nclc} must lie within "
                f"CI=[{self.ci_low}, {self.ci_high}]"
            )
            raise ValueError(msg)
        return self


class NCLCEstimate(BaseModel):
    """Per-skill NCLC posterior — the public-facing API shape.

    Phase 4's internal `SkillPosterior` carries additional state
    (posterior_variance, difficulty-band spread); this `NCLCEstimate`
    is the projection the API and the generated clients see.
    """

    model_config = ConfigDict(extra="forbid")

    skill: SkillCode
    posterior_mean: float = Field(ge=1, le=12)
    ci_low: int = Field(ge=1, le=12)
    ci_high: int = Field(ge=1, le=12)
    confident: bool
    n_observations: int = Field(ge=0)

    @model_validator(mode="after")
    def _ci_invariant(self) -> Self:
        if self.ci_low > self.ci_high:
            msg = f"ci_low={self.ci_low} > ci_high={self.ci_high}"
            raise ValueError(msg)
        # Posterior mean is continuous; CI bounds are integer bands.
        # Allow a 0.5-band tolerance on either side so a posterior at
        # the band edge does not raise.
        if not (self.ci_low - 0.5 <= self.posterior_mean <= self.ci_high + 0.5):
            msg = (
                f"posterior_mean={self.posterior_mean} must lie within "
                f"CI=[{self.ci_low}, {self.ci_high}] (±0.5)"
            )
            raise ValueError(msg)
        return self


# ─── Writing & Speaking rubrics (Phase 2 additions) ─────────────


class WritingRubric(BaseModel):
    """The graded output of the Phase 7 EE auto-scorer.

    Component invariant: `total_20` is derived from the five primary
    components (`task_completion`, `coherence_cohesion`, `lexical_range`,
    `grammatical_accuracy`, `register_appropriateness`) by scaling
    `sum(components)` from `[0, 25]` to `[0, 20]`; off-by-one is
    tolerated to allow the Phase 7 calibration layer to nudge the
    total without breaking the contract.

    `canadian_context_integration` is non-null only for Task 2 & 3
    (the prompts that require Canadian context per
    `EEContent.required_canadian_context`).
    """

    model_config = ConfigDict(extra="forbid")

    task_completion: int = Field(ge=0, le=5)
    coherence_cohesion: int = Field(ge=0, le=5)
    lexical_range: int = Field(ge=0, le=5)
    grammatical_accuracy: int = Field(ge=0, le=5)
    register_appropriateness: int = Field(ge=0, le=5)
    canadian_context_integration: int | None = Field(default=None, ge=0, le=5)
    total_20: int = Field(ge=0, le=20)
    error_density_per_100w: float = Field(ge=0.0)
    type_token_ratio: float = Field(ge=0.0, le=1.0)
    discourse_marker_count: int = Field(ge=0)
    error_list: list[ErrorAnnotation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _total_consistent_with_components(self) -> Self:
        components = [
            self.task_completion,
            self.coherence_cohesion,
            self.lexical_range,
            self.grammatical_accuracy,
            self.register_appropriateness,
        ]
        expected = round(sum(components) * 4.0 / 5.0)  # scale [0..25] → [0..20]
        if abs(self.total_20 - expected) > 1:
            msg = (
                f"total_20={self.total_20} inconsistent with components "
                f"{components} (expected ≈ {expected}, ±1)"
            )
            raise ValueError(msg)
        return self


class SpeakingRubric(BaseModel):
    """The graded output of the Phase 7 EO auto-scorer.

    Component invariant: `total_20` is derived from the six components
    by scaling `sum(components)` from `[0, 30]` to `[0, 20]`; off-by-one
    tolerated as in `WritingRubric`.

    `phoneme_error_rate` is null when the ASR didn't deliver a confident
    phoneme alignment (Phase 7 ADR-031 — pronunciation as a coarse
    proxy); the rubric is still valid without it.
    """

    model_config = ConfigDict(extra="forbid")

    task_completion: int = Field(ge=0, le=5)
    fluency_pace: int = Field(ge=0, le=5)
    pronunciation_prosody: int = Field(ge=0, le=5)
    lexical_range: int = Field(ge=0, le=5)
    grammatical_accuracy: int = Field(ge=0, le=5)
    interaction_responsiveness: int = Field(ge=0, le=5)
    total_20: int = Field(ge=0, le=20)
    wpm: float = Field(ge=0.0)
    pause_ratio: float = Field(ge=0.0, le=1.0)
    phoneme_error_rate: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _total_consistent_with_components(self) -> Self:
        components = [
            self.task_completion,
            self.fluency_pace,
            self.pronunciation_prosody,
            self.lexical_range,
            self.grammatical_accuracy,
            self.interaction_responsiveness,
        ]
        expected = round(sum(components) * 2.0 / 3.0)  # scale [0..30] → [0..20]
        if abs(self.total_20 - expected) > 1:
            msg = (
                f"total_20={self.total_20} inconsistent with components "
                f"{components} (expected ≈ {expected}, ±1)"
            )
            raise ValueError(msg)
        return self


__all__ = [
    "NCLCEstimate",
    "Score",
    "SkillCode",
    "SpeakingRubric",
    "WritingRubric",
]
