"""Item schema — the canonical content-bank record.

Phase 1 shipped `Item` with a permissive `ItemContent` placeholder.
Phase 2 narrows `ItemContent` into a discriminated union of
`COContent | CEContent | EEContent | EOContent` keyed on the `module`
discriminator (ADR-0011, `phase2_design.md §3.1`).

The narrowing is additive: any Phase 1 instance carrying a valid
`module` value continues to validate against the new union. There is no
data migration because Phase 1 only exposed in-memory example payloads
(no persisted fixtures).

Example:
    >>> from datetime import UTC, datetime
    >>> from uuid import uuid4
    >>> from tcf_accel.ids import ItemId
    >>> from tcf_accel.schemas.common import Provenance
    >>> from tcf_accel.schemas.content import CEContent, MCQ, MCQOption
    >>> Item(
    ...     id=ItemId(uuid4()),
    ...     module="CE",
    ...     cefr_level="B2",
    ...     content=CEContent(
    ...         passage=(
    ...             "Avis aux clients : nous serons fermés lundi en raison de travaux. "
    ...             "Nous rouvrirons mardi à neuf heures. Merci de votre compréhension."
    ...         ),
    ...         genre="admin",
    ...         word_count=21,
    ...         questions=[MCQ(
    ...             id="q1", prompt="Quand fermons-nous ?",
    ...             options=[MCQOption(id="a", text="lundi"),
    ...                      MCQOption(id="b", text="mardi")],
    ...             correct_option_id="a",
    ...         )],
    ...     ),
    ...     provenance=Provenance(
    ...         source="hand_authored",
    ...         source_id="phase2_example",
    ...         license="CC-BY-SA-4.0",
    ...         ingested_at=datetime(2026, 5, 27, tzinfo=UTC),
    ...         review_status="auto_passed",
    ...     ),
    ... ).module
    'CE'

Complexity: O(1) construction; Pydantic field validation is field-count-linear.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.ids import ItemId
from tcf_accel.schemas.common import ItemMetadata, Provenance, QualityFlag
from tcf_accel.schemas.content import CEContent, COContent, EEContent, EOContent
from tcf_accel.schemas.version import SCHEMA_VERSION

Module = Literal["CO", "CE", "EE", "EO"]
CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]

# Discriminated union (ADR-0011 + phase2_design.md §3.1).
# `Union[...]` is preferred over `X | Y` here for explicit Pydantic v2
# discriminator wiring — typing-checker friendly and resolves cleanly
# with `from __future__ import annotations`.
ItemContent = Annotated[
    Union[COContent, CEContent, EEContent, EOContent],
    Field(discriminator="module"),
]


class Item(BaseModel):
    """A content-bank item across CO / CE / EE / EO modules.

    Phase 1's frozen contract. Phase 2 narrowed the `content` field's
    type from a permissive placeholder to the discriminated union above.
    The wire shape is unchanged for any Phase 1-conformant payload.
    Further changes require an ADR + a `SCHEMA_VERSION` bump + a
    `CHANGELOG.md` entry.
    """

    model_config = ConfigDict(extra="forbid")

    id: ItemId
    module: Module
    cefr_level: CefrLevel
    difficulty_irt: float | None = Field(
        default=None,
        description="IRT 2PL `b` parameter; set by the nightly calibration job (Phase 4 + ADR-0013).",
    )
    discrimination_irt: float | None = Field(
        default=None,
        description="IRT 2PL `a` parameter; set by the nightly calibration job (Phase 4 + ADR-0013).",
    )
    content: ItemContent  # type: ignore[valid-type]  # discriminated union narrowed in Phase 2
    metadata: ItemMetadata = Field(default_factory=ItemMetadata)
    provenance: Provenance
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    synthetic: bool = False
    retired: bool = False
    schema_version: str = Field(default=SCHEMA_VERSION, frozen=True)

    def model_post_init(self, _context: object, /) -> None:
        """Enforce the `module` discriminator agreement.

        Pydantic's discriminated-union already routes by `content.module`,
        but we additionally check that the outer `Item.module` matches —
        the outer field is what the DB indexes on, and a mismatch would
        silently misroute queries.

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
