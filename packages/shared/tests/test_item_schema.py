"""Tests for the `Item` schema.

Phase 1 used a permissive `ItemContent(module=X)` placeholder. Phase 2
narrows `ItemContent` to a discriminated union; the tests below build
the minimum valid per-module content payload via small helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tcf_accel.ids import ItemId
from tcf_accel.schemas.common import Provenance, QualityFlag
from tcf_accel.schemas.content import (
    CEContent,
    COContent,
    EEContent,
    EOContent,
    MCQ,
    MCQOption,
    Speaker,
)
from tcf_accel.schemas.item import Item
from tcf_accel.schemas.version import SCHEMA_VERSION


def _make_provenance() -> Provenance:
    return Provenance(
        source="test",
        source_id="t-1",
        license="CC0-1.0",
        ingested_at=datetime(2026, 5, 27, tzinfo=UTC),
        review_status="auto_passed",
    )


def _make_mcq() -> MCQ:
    return MCQ(
        id="q1",
        prompt="Quand fermons-nous ?",
        options=[
            MCQOption(id="a", text="lundi"),
            MCQOption(id="b", text="mardi"),
        ],
        correct_option_id="a",
    )


def _ce_content() -> CEContent:
    return CEContent(
        passage=(
            "Avis aux clients : nous serons fermés lundi en raison de travaux "
            "de maintenance. Nous rouvrirons mardi à neuf heures. Merci de "
            "votre compréhension et bonne journée à toutes et à tous."
        ),
        genre="admin",
        word_count=30,
        questions=[_make_mcq()],
    )


def _co_content() -> COContent:
    return COContent(
        transcript="Bonjour.",
        duration_s=3.0,
        speakers=[Speaker(label="A", accent="fr-FR")],
        accent="fr-FR",
        register="standard",
        questions=[_make_mcq()],
    )


def _ee_content() -> EEContent:
    return EEContent(
        task_number=1,
        prompt="Présentez-vous en 60 mots.",
        target_word_count_range=(40, 80),
        required_canadian_context=False,
        rubric_version="ee.v1",
    )


def _eo_content() -> EOContent:
    return EOContent(
        task_number=1,
        examiner_prompts=["Présentez-vous."],
        candidate_prep_time_s=0,
        target_duration_s=90,
        rubric_version="eo.v1",
    )


def test_minimum_valid_ce_item() -> None:
    item = Item(
        id=ItemId(uuid4()),
        module="CE",
        cefr_level="B2",
        content=_ce_content(),
        provenance=_make_provenance(),
    )
    assert item.module == "CE"
    assert item.cefr_level == "B2"
    assert item.synthetic is False
    assert item.retired is False
    assert item.schema_version == SCHEMA_VERSION
    assert item.metadata.tags == []


def test_co_item_round_trip() -> None:
    item = Item(
        id=ItemId(uuid4()),
        module="CO",
        cefr_level="A2",
        content=_co_content(),
        provenance=_make_provenance(),
    )
    assert item.content.module == "CO"


def test_module_content_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="does not match"):
        Item(
            id=ItemId(uuid4()),
            module="CE",
            cefr_level="B2",
            content=_co_content(),  # mismatch: CO content with CE module
            provenance=_make_provenance(),
        )


def test_unknown_module_rejected() -> None:
    with pytest.raises(ValidationError):
        Item(
            id=ItemId(uuid4()),
            module="XX",  # type: ignore[arg-type]
            cefr_level="B2",
            content=_ce_content(),
            provenance=_make_provenance(),
        )


def test_unknown_cefr_rejected() -> None:
    with pytest.raises(ValidationError):
        Item(
            id=ItemId(uuid4()),
            module="CE",
            cefr_level="D1",  # type: ignore[arg-type]
            content=_ce_content(),
            provenance=_make_provenance(),
        )


def test_extra_keys_rejected_at_top_level() -> None:
    with pytest.raises(ValidationError):
        Item.model_validate({
            "id": str(uuid4()),
            "module": "CE",
            "cefr_level": "B2",
            "content": _ce_content().model_dump(mode="json"),
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
        content=_ee_content(),
        provenance=_make_provenance(),
        quality_flags=[QualityFlag.SYNTHETIC, QualityFlag.NEEDS_HUMAN_REVIEW],
    )
    dumped = item.model_dump(mode="json")
    assert dumped["quality_flags"] == ["synthetic", "needs_human_review"]


def test_eo_item_round_trip() -> None:
    item = Item(
        id=ItemId(uuid4()),
        module="EO",
        cefr_level="C1",
        content=_eo_content(),
        provenance=_make_provenance(),
    )
    payload = item.model_dump_json()
    reparsed = Item.model_validate_json(payload)
    assert reparsed == item


def test_discriminated_union_routes_by_module() -> None:
    raw = {
        "id": str(uuid4()),
        "module": "CO",
        "cefr_level": "A2",
        "content": _co_content().model_dump(mode="json"),
        "provenance": _make_provenance().model_dump(mode="json"),
    }
    item = Item.model_validate(raw)
    assert isinstance(item.content, COContent)


def test_mcq_correct_must_be_in_options() -> None:
    with pytest.raises(ValueError, match="not in options"):
        MCQ(
            id="q",
            prompt="?",
            options=[MCQOption(id="a", text="x"), MCQOption(id="b", text="y")],
            correct_option_id="z",
        )
