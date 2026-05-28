"""Tests for the `Item` schema."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tcf_accel.ids import ItemId
from tcf_accel.schemas.common import Provenance, QualityFlag
from tcf_accel.schemas.item import Item, ItemContent
from tcf_accel.schemas.version import SCHEMA_VERSION


def _make_provenance() -> Provenance:
    return Provenance(
        source="test",
        source_id="t-1",
        license="CC0-1.0",
        ingested_at=datetime(2026, 5, 27, tzinfo=UTC),
        review_status="auto_passed",
    )


def test_minimum_valid_item() -> None:
    item = Item(
        id=ItemId(uuid4()),
        module="CE",
        cefr_level="B2",
        content=ItemContent(module="CE"),
        provenance=_make_provenance(),
    )
    assert item.module == "CE"
    assert item.cefr_level == "B2"
    assert item.synthetic is False
    assert item.retired is False
    assert item.schema_version == SCHEMA_VERSION
    assert item.metadata.tags == []


def test_module_content_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="does not match"):
        Item(
            id=ItemId(uuid4()),
            module="CE",
            cefr_level="B2",
            content=ItemContent(module="CO"),       # mismatch
            provenance=_make_provenance(),
        )


def test_unknown_module_rejected() -> None:
    with pytest.raises(ValidationError):
        Item(
            id=ItemId(uuid4()),
            module="XX",                            # type: ignore[arg-type]
            cefr_level="B2",
            content=ItemContent(module="CE"),
            provenance=_make_provenance(),
        )


def test_unknown_cefr_rejected() -> None:
    with pytest.raises(ValidationError):
        Item(
            id=ItemId(uuid4()),
            module="CE",
            cefr_level="D1",                        # type: ignore[arg-type]
            content=ItemContent(module="CE"),
            provenance=_make_provenance(),
        )


def test_extra_keys_rejected_at_top_level() -> None:
    # We promise `extra="forbid"` on Item; protects against silent contract drift.
    with pytest.raises(ValidationError):
        Item.model_validate({
            "id": str(uuid4()),
            "module": "CE",
            "cefr_level": "B2",
            "content": {"module": "CE"},
            "provenance": _make_provenance().model_dump(mode="json"),
            "synthetic": False,
            "retired": False,
            "unknown_key": "boom",
        })


def test_quality_flags_serialize_to_strings() -> None:
    item = Item(
        id=ItemId(uuid4()),
        module="EE",
        cefr_level="B2",
        content=ItemContent(module="EE"),
        provenance=_make_provenance(),
        quality_flags=[QualityFlag.SYNTHETIC, QualityFlag.NEEDS_HUMAN_REVIEW],
    )
    dumped = item.model_dump(mode="json")
    assert dumped["quality_flags"] == ["synthetic", "needs_human_review"]


def test_schema_version_pinned() -> None:
    item = Item(
        id=ItemId(uuid4()),
        module="CO",
        cefr_level="A1",
        content=ItemContent(module="CO"),
        provenance=_make_provenance(),
    )
    # Attempting to bump version on a single instance is forbidden (frozen=True).
    with pytest.raises(ValidationError):
        item.model_copy(update={"schema_version": "9.9.9"}).model_validate(
            item.model_copy(update={"schema_version": "9.9.9"}).model_dump(),
        )
