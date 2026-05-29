"""`/v1/submission/*` — async EE/EO grading.

Phase 7 implements the scorer; Phase 2 freezes the wire shape.

The submission lifecycle:

1. Client POSTs text (EE) or audio (EO) as multipart/form-data.
2. API stores the artifact at `payload_uri` (S3/local FS) and returns
   a `SubmissionView` with `status="pending"`.
3. The Phase 7 worker picks it up, runs the scorer, writes the
   rubric, and updates `status="graded"`.
4. Client polls `GET /v1/submission/{id}` until status flips.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.ids import ItemId, SubmissionId, UserId
from tcf_accel.schemas.api.errors import ErrorEnvelope
from tcf_accel.schemas.scoring import SpeakingRubric, WritingRubric

SubmissionModule = Literal["EE", "EO"]
SubmissionStatus = Literal["pending", "grading", "graded", "failed"]


class SubmissionView(BaseModel):
    """Read-side view of an EE/EO submission."""

    model_config = ConfigDict(extra="forbid")

    id: SubmissionId
    user_id: UserId
    item_id: ItemId
    module: SubmissionModule
    status: SubmissionStatus
    submitted_at: datetime
    graded_at: datetime | None = None
    payload_bytes: int = Field(ge=0, description="Size of the submitted artifact; the artifact itself is not in the response.")
    payload_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 of the submitted artifact.",
    )
    rubric_writing: WritingRubric | None = Field(
        default=None,
        description="Set when status='graded' and module='EE'.",
    )
    rubric_speaking: SpeakingRubric | None = Field(
        default=None,
        description="Set when status='graded' and module='EO'.",
    )
    error: ErrorEnvelope | None = Field(
        default=None,
        description="Set when status='failed'.",
    )


__all__ = ["SubmissionModule", "SubmissionStatus", "SubmissionView"]
