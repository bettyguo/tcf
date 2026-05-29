"""In-process submission store for Phase 7.

Mirrors `session_state.py`: dicts behind a `threading.Lock`, swap-in to
Postgres + S3 deferred to the same persistence step. The artifact bytes
are held in-memory keyed by `SubmissionId`; in production the bytes go
to an S3 prefix and the in-memory entry holds only the `payload_uri`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Final
from uuid import uuid4

from tcf_accel.ids import ItemId, SubmissionId, UserId
from tcf_accel.schemas.api.errors import ErrorEnvelope
from tcf_accel.schemas.api.submission import SubmissionStatus, SubmissionView
from tcf_accel.schemas.scoring import SpeakingRubric, WritingRubric


@dataclass
class SubmissionRecord:
    """One EE or EO submission, in-flight or graded."""

    id: SubmissionId
    user_id: UserId
    item_id: ItemId
    module: str  # "EE" | "EO"
    status: SubmissionStatus
    submitted_at: datetime
    payload_bytes: int
    payload_sha256: str
    artifact: bytes  # raw bytes — staged for the worker; not exposed via the API
    graded_at: datetime | None = None
    rubric_writing: WritingRubric | None = None
    rubric_speaking: SpeakingRubric | None = None
    error: ErrorEnvelope | None = None
    graded_score: dict[str, object] = field(default_factory=dict)

    def to_view(self) -> SubmissionView:
        return SubmissionView(
            id=self.id,
            user_id=self.user_id,
            item_id=self.item_id,
            module=self.module,  # type: ignore[arg-type]
            status=self.status,
            submitted_at=self.submitted_at,
            graded_at=self.graded_at,
            payload_bytes=self.payload_bytes,
            payload_sha256=self.payload_sha256,
            rubric_writing=self.rubric_writing,
            rubric_speaking=self.rubric_speaking,
            error=self.error,
        )


_STORE: Final[dict[SubmissionId, SubmissionRecord]] = {}
_LOCK: Final[Lock] = Lock()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_submission(
    *,
    user_id: UserId,
    item_id: ItemId,
    module: str,
    artifact: bytes,
) -> SubmissionRecord:
    sub_id = SubmissionId(uuid4())
    rec = SubmissionRecord(
        id=sub_id,
        user_id=user_id,
        item_id=item_id,
        module=module,
        status="pending",
        submitted_at=datetime.now(UTC),
        payload_bytes=len(artifact),
        payload_sha256=_sha256(artifact),
        artifact=artifact,
    )
    with _LOCK:
        _STORE[sub_id] = rec
    return rec


def get_submission(sub_id: SubmissionId) -> SubmissionRecord | None:
    with _LOCK:
        return _STORE.get(sub_id)


def update_submission(rec: SubmissionRecord) -> None:
    with _LOCK:
        _STORE[rec.id] = rec


def reset_submissions() -> None:
    """Drop all in-memory submissions (used by tests)."""
    with _LOCK:
        _STORE.clear()


__all__ = [
    "SubmissionRecord",
    "create_submission",
    "get_submission",
    "reset_submissions",
    "update_submission",
]
