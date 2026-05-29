"""CO (Compréhension orale) item content + supporting types.

A CO item is a French audio clip (interview, dialogue, announcement,
news segment) with a transcript and one or more multiple-choice
questions. Phase 2 freezes the shape; Phase 5 builds the player UI.

The `Speaker`, `MCQOption`, and `MCQ` helpers also serve CE items.
"""

from __future__ import annotations

import warnings
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

# `register` is a TCF spec term for formality level; the field name collides
# with `BaseModel.register` and Pydantic emits a (harmless) UserWarning at
# class definition time. Suppress it here so the warning doesn't propagate
# into the strict-warnings pytest config.
warnings.filterwarnings(
    "ignore",
    message=r'Field name "register" in "COContent" shadows.*',
    category=UserWarning,
)

Accent = Literal["fr-FR", "fr-CA", "fr-BE", "fr-CH", "fr-AF", "mixed"]
Register = Literal["soutenu", "standard", "familier"]


class Speaker(BaseModel):
    """A single speaker in a dialogue or multi-voice clip."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, description="Display label, e.g. 'Speaker A' or 'Annick'.")
    accent: Accent


class MCQOption(BaseModel):
    """One option in a multiple-choice question."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=8, description="Short stable slug, e.g. 'a', 'b', 'c'.")
    text: str = Field(min_length=1)


class MCQ(BaseModel):
    """A multiple-choice question.

    Used by both CO and CE items. Invariant: `correct_option_id` must
    appear in `options`.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Stable question id within the item.")
    prompt: str = Field(min_length=1)
    options: list[MCQOption] = Field(min_length=2)
    correct_option_id: str
    explanation: str | None = None

    @model_validator(mode="after")
    def _correct_in_options(self) -> Self:
        ids = {opt.id for opt in self.options}
        if self.correct_option_id not in ids:
            msg = (
                f"correct_option_id={self.correct_option_id!r} not in options={sorted(ids)}"
            )
            raise ValueError(msg)
        if len(ids) != len(self.options):
            msg = "MCQ option ids must be unique"
            raise ValueError(msg)
        return self


class COContent(BaseModel):
    """Compréhension orale item content.

    Example:
        >>> COContent(
        ...     transcript="Bonjour, c'est Annick.",
        ...     duration_s=8.5,
        ...     speakers=[Speaker(label='A', accent='fr-FR')],
        ...     accent='fr-FR',
        ...     register='standard',
        ...     questions=[MCQ(
        ...         id='q1', prompt='Qui parle ?',
        ...         options=[MCQOption(id='a', text='Annick'),
        ...                  MCQOption(id='b', text='Pierre')],
        ...         correct_option_id='a',
        ...     )],
        ... ).module
        'CO'
    """

    model_config = ConfigDict(extra="forbid")

    module: Literal["CO"] = "CO"
    transcript: str = Field(min_length=1)
    audio_url: AnyHttpUrl | None = None
    audio_local_path: str | None = Field(
        default=None,
        description="Filesystem path for operator-cached audio (privacy_mode=local_only).",
    )
    duration_s: float = Field(ge=1.0, le=600.0)
    speakers: list[Speaker] = Field(min_length=1)
    accent: Accent
    # `Field(...)` explicitly marks required and prevents Pydantic from inferring
    # a default from `BaseModel.register` (a name collision; see pyproject filterwarnings).
    register: Register = Field(...)
    questions: list[MCQ] = Field(min_length=1)


__all__ = ["Accent", "COContent", "MCQ", "MCQOption", "Register", "Speaker"]
