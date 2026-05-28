"""Scoring schemas — `Score` and `NCLCEstimate`.

Phase 1 enforces the load-bearing invariants:

- `ci_low ≤ nclc ≤ ci_high` for every `Score`.
- `confident=False` makes the consumer (UI) refuse to render a final NCLC
  number; the application layer enforces this contract.

Phase 4 elaborates `NCLCEstimate` with posterior variance, observation
history, and difficulty-band spread (`04_LEARNER_MODEL.md §2.3`).
Phase 7 adds the rubric schemas (`02_ARCHITECTURE.md §2.3`).
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SkillCode = Literal["CO", "CE", "EE", "EO"]


class Score(BaseModel):
    """A single skill's NCLC-mapped score with a credible interval.

    Master prompt §6.2: every NCLC point estimate MUST come with a CI. The
    `confident` flag is the launch-blocking gate: when `False`, the UI is
    forbidden from showing the estimate as a final number.

    Example:
        >>> Score(nclc=8, raw=510.0, ci_low=7, ci_high=9, n_observations=45,
        ...       confident=True).nclc
        8

    Complexity: O(1) construction + validation.
    """

    model_config = ConfigDict(extra="forbid")

    nclc: int = Field(ge=1, le=12, description="Predicted NCLC band, 1..12.")
    raw: float = Field(description="Raw score on the module's native scale (0–699 for CO/CE, 0–20 for EE/EO).")
    ci_low: int = Field(ge=1, le=12)
    ci_high: int = Field(ge=1, le=12)
    n_observations: int = Field(ge=0)
    confident: bool = Field(
        description="If False, callers MUST NOT render a final point estimate. "
        "See `04_LEARNER_MODEL.md §2.3` for the rules that set this.",
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
    """Per-skill NCLC posterior — the Phase 1 public-facing shape.

    Phase 4's `SkillPosterior` carries additional internal state (variance,
    difficulty-band spread). This `NCLCEstimate` is the API-surface
    projection; Phase 4 emits it via the API layer.
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
        rounded = int(round(self.posterior_mean))
        # Posterior mean is continuous; we allow it to lie within [ci_low - 0.5, ci_high + 0.5]
        # since CI bounds are integer bands. Outside that, raise.
        if not (self.ci_low - 0.5 <= self.posterior_mean <= self.ci_high + 0.5):
            msg = (
                f"posterior_mean={self.posterior_mean} (band {rounded}) must lie "
                f"within CI=[{self.ci_low}, {self.ci_high}]"
            )
            raise ValueError(msg)
        return self


__all__ = ["NCLCEstimate", "Score", "SkillCode"]
