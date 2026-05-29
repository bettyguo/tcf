"""EO (Expression orale) item content.

A EO item is a speaking prompt (one of three TCF Canada task numbers)
with examiner-side prompts, optional candidate prep time, and the
target duration of the candidate's response. Phase 7 grades the
candidate's recorded response.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EOContent(BaseModel):
    """Expression orale item content.

    Example:
        >>> EOContent(
        ...     task_number=1,
        ...     examiner_prompts=['Présentez-vous.', "Parlez de votre travail."],
        ...     candidate_prep_time_s=0,
        ...     target_duration_s=120,
        ...     rubric_version='eo.v1',
        ... ).module
        'EO'
    """

    model_config = ConfigDict(extra="forbid")

    module: Literal["EO"] = "EO"
    task_number: Literal[1, 2, 3]
    examiner_prompts: list[str] = Field(min_length=1)
    candidate_prep_time_s: int = Field(
        ge=0,
        le=600,
        description="Allowed preparation time before the candidate speaks; usually 0 for Task 1.",
    )
    target_duration_s: int = Field(
        ge=30,
        le=600,
        description="Target speaking duration; the rubric penalizes large deviations.",
    )
    rubric_version: str = Field(
        min_length=1,
        description="Pinned per release; the Phase 7 rubric scorer uses this to select the correct prompt template.",
    )


__all__ = ["EOContent"]
