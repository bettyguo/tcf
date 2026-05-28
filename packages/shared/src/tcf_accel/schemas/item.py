"""Item schema — the canonical content-bank record.

Phase 1 ships `Item` with `ItemContent` as a permissive placeholder. Phase 2
narrows `ItemContent` to a discriminated union of `COContent | CEContent |
EEContent | EOContent` per `02_ARCHITECTURE.md §2.3`. This narrowing is
additive: the Phase 1 `Item.content` shape continues to validate against the
Phase 2 union via the `module` discriminator.

Example:
    >>> from datetime import UTC, datetime
    >>> from uuid import uuid4
    >>> from tcf_accel.ids import ItemId
    >>> from tcf_accel.schemas.common import Provenance
    >>> from tcf_accel.schemas.item import Item, ItemContent
    >>> Item(
    ...     id=ItemId(uuid4()),
    ...     module="CE",
    ...     cefr_level="B2",
    ...     content=ItemContent(module="CE"),
    ...     provenance=Provenance(
    ...         source="hand_authored",
    ...         source_id="phase1_example",
    ...         license="CC-BY-SA-4.0",
    ...         ingested_at=datetime(2026, 5, 27, tzinfo=UTC),
    ...         review_status="auto_passed",
    ...     ),
    ... ).module
    'CE'

Complexity: O(1) construction; Pydantic field validation is field-count-linear.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.ids import ItemId
from tcf_accel.schemas.common import ItemMetadata, Provenance, QualityFlag
from tcf_accel.schemas.version import SCHEMA_VERSION

Module = Literal["CO", "CE", "EE", "EO"]
CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class ItemContent(BaseModel):
    """Phase 1 placeholder for module-specific item content.

    Phase 2 narrows this into a discriminated union of `COContent | CEContent
    | EEContent | EOContent`. Phase 1's permissive `extra="allow"` accepts
    any forward-compatible payload provided it carries the `module`
    discriminator.
    """

    model_config = ConfigDict(extra="allow")
    module: Module = Field(description="Discriminator. Must match `Item.module`.")


class Item(BaseModel):
    """A content-bank item across CO / CE / EE / EO modules.

    Frozen Phase 1 contract. Changes require an ADR + a `SCHEMA_VERSION` bump
    + a `CHANGELOG.md` entry (Phase 1 §11 anti-criteria).
    """

    model_config = ConfigDict(extra="forbid")

    id: ItemId
    module: Module
    cefr_level: CefrLevel
    difficulty_irt: float | None = Field(
        default=None,
        description="IRT 2PL `b` parameter; set by the calibration job (Phase 4).",
    )
    discrimination_irt: float | None = Field(
        default=None,
        description="IRT 2PL `a` parameter; set by the calibration job (Phase 4).",
    )
    content: ItemContent
    metadata: ItemMetadata = Field(default_factory=ItemMetadata)
    provenance: Provenance
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    synthetic: bool = False
    retired: bool = False
    schema_version: str = Field(default=SCHEMA_VERSION, frozen=True)

    def model_post_init(self, _context: object, /) -> None:
        """Enforce the `module` discriminator agreement.

        Raises:
            ValueError: if `content.module` does not match `module`.
        """
        if self.content.module != self.module:
            msg = (
                f"Item.module={self.module!r} does not match "
                f"Item.content.module={self.content.module!r}"
            )
            raise ValueError(msg)


__all__ = ["CefrLevel", "Item", "ItemContent", "Module"]
