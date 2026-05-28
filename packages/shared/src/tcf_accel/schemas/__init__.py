"""Pydantic schemas — the frozen Phase 1 contract surface.

Re-exported so consumers can `from tcf_accel.schemas import Item, Score`.
"""

from __future__ import annotations

from tcf_accel.schemas.common import (
    ItemMetadata,
    Provenance,
    QualityFlag,
    ReviewStatus,
)
from tcf_accel.schemas.item import Item, ItemContent, Module
from tcf_accel.schemas.scoring import NCLCEstimate, Score, SkillCode
from tcf_accel.schemas.version import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
    "Item",
    "ItemContent",
    "ItemMetadata",
    "Module",
    "NCLCEstimate",
    "Provenance",
    "QualityFlag",
    "ReviewStatus",
    "Score",
    "SkillCode",
]
