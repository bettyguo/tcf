"""Typed identifier aliases.

We use `NewType` so type-checkers distinguish, e.g., an `ItemId` from a
`UserId` even though both are UUIDs at runtime. Saves a class of bugs where
"a UUID is a UUID" hides a real swap.

Example:
    >>> from uuid import uuid4
    >>> from tcf_accel.ids import ItemId, UserId
    >>> item = ItemId(uuid4())
    >>> user = UserId(uuid4())
    >>> type(item) is type(user)  # both are UUID at runtime
    True

Complexity: O(1) construction.
"""

from __future__ import annotations

from typing import NewType
from uuid import UUID

ItemId = NewType("ItemId", UUID)
UserId = NewType("UserId", UUID)
SessionId = NewType("SessionId", UUID)
SubmissionId = NewType("SubmissionId", UUID)
MockExamId = NewType("MockExamId", UUID)
StudyPlanId = NewType("StudyPlanId", UUID)

# `interactions` is a BIGSERIAL in Postgres (Phase 2 schema).
InteractionId = NewType("InteractionId", int)

__all__ = [
    "InteractionId",
    "ItemId",
    "MockExamId",
    "SessionId",
    "StudyPlanId",
    "SubmissionId",
    "UserId",
]
