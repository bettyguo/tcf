"""CE (Compréhension écrite) item content.

A CE item is a French text passage (news, ad, letter, admin notice,
academic paragraph, narrative) with one or more multiple-choice
questions. Phase 2 freezes the shape; Phase 5 builds the reader UI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.schemas.content.co import MCQ

Genre = Literal["news", "ad", "letter", "admin", "academic", "narrative"]


class CEContent(BaseModel):
    """Compréhension écrite item content.

    Example:
        >>> from tcf_accel.schemas.content.co import MCQ, MCQOption
        >>> CEContent(
        ...     passage=(
        ...         "Avis aux clients : nous serons fermés lundi en raison de travaux. "
        ...         "Nous rouvrirons mardi à neuf heures. Merci de votre compréhension."
        ...     ),
        ...     genre='admin',
        ...     word_count=21,
        ...     questions=[MCQ(
        ...         id='q1', prompt='Quand fermons-nous ?',
        ...         options=[MCQOption(id='a', text='lundi'),
        ...                  MCQOption(id='b', text='mardi')],
        ...         correct_option_id='a',
        ...     )],
        ... ).module
        'CE'
    """

    model_config = ConfigDict(extra="forbid")

    module: Literal["CE"] = "CE"
    passage: str = Field(min_length=1)
    genre: Genre
    word_count: int = Field(ge=20, le=2000)
    questions: list[MCQ] = Field(min_length=1)


__all__ = ["CEContent", "Genre"]
