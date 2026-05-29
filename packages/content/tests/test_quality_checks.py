"""Tests for the Phase 3 foundation quality checks."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tcf_accel.ids import ItemId
from tcf_accel.schemas import (
    MCQ,
    CEContent,
    EEContent,
    Item,
    MCQOption,
    Provenance,
)
from tcf_accel_content.quality.length import LengthBalancedDistractorsCheck
from tcf_accel_content.quality.license_check import LicenseCompatibleCheck

# ─── license_compatible ────────────────────────────────────────


def test_license_check_passes_on_allowlisted_license(passing_ce_item: Item) -> None:
    result = LicenseCompatibleCheck()(passing_ce_item)
    assert result.passed
    assert result.severity == "P0"


def test_license_check_rejects_non_allowlisted(passing_ce_item: Item) -> None:
    bad = passing_ce_item.model_copy(
        update={
            "provenance": passing_ce_item.provenance.model_copy(
                update={"license": "proprietary"},
            ),
        },
    )
    result = LicenseCompatibleCheck()(bad)
    assert not result.passed
    assert result.severity == "P0"
    assert "not in redistribution allowlist" in (result.detail or "")


def test_license_check_permit_local_only_downgrades_to_p1(
    passing_ce_item: Item,
) -> None:
    bad = passing_ce_item.model_copy(
        update={
            "provenance": passing_ce_item.provenance.model_copy(
                update={"license": "RFI-TOS-personal-study"},
            ),
        },
    )
    result = LicenseCompatibleCheck(permit_local_only=True)(bad)
    assert result.passed  # downgraded, so it passes the gate
    assert result.severity == "P1"
    assert "local-only" in (result.detail or "")


# ─── length-balanced distractors ───────────────────────────────


def _ce_item_with_options(opts: list[tuple[str, str]], correct: str = "a") -> Item:
    return Item(
        id=ItemId(uuid4()),
        module="CE",
        cefr_level="B2",
        content=CEContent(
            passage=" ".join(["lorem"] * 30),
            genre="news",
            word_count=30,
            questions=[
                MCQ(
                    id="q1",
                    prompt="?",
                    options=[MCQOption(id=i, text=t) for i, t in opts],
                    correct_option_id=correct,
                ),
            ],
        ),
        provenance=Provenance(
            source="x", source_id="1", license="CC0-1.0",
            ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )


def test_length_check_passes_when_distractors_within_tolerance() -> None:
    item = _ce_item_with_options([
        ("a", "one two three four"),
        ("b", "five six seven eight"),
        ("c", "nine ten eleven twelve"),
        ("d", "thirteen fourteen fifteen sixteen"),
    ])
    result = LengthBalancedDistractorsCheck()(item)
    assert result.passed
    assert result.metric == pytest.approx(0.0)


def test_length_check_passes_at_exact_tolerance() -> None:
    # Correct = 8 tokens; distractor = 6 tokens; delta = 0.25 = tolerance.
    item = _ce_item_with_options([
        ("a", "one two three four five six seven eight"),
        ("b", "one two three four five six"),
        ("c", "one two three four five six"),
        ("d", "one two three four five six"),
    ])
    result = LengthBalancedDistractorsCheck()(item)
    assert result.passed
    assert result.metric == pytest.approx(0.25)


def test_length_check_flags_when_distractor_too_short() -> None:
    item = _ce_item_with_options([
        ("a", "one two three four five six seven eight"),
        ("b", "tiny"),
        ("c", "still tiny"),
        ("d", "also tiny"),
    ])
    result = LengthBalancedDistractorsCheck()(item)
    assert not result.passed
    assert result.severity == "P1"
    assert (result.metric or 0.0) > 0.25


def test_length_check_ignores_correct_option_in_comparison() -> None:
    # All distractors are uniform; only the correct option is short.
    # The check compares distractors to *correct*, so a short correct
    # → all distractors look long → should fail.
    item = _ce_item_with_options([
        ("a", "one"),
        ("b", "two three four five six seven eight nine"),
        ("c", "two three four five six seven eight nine"),
        ("d", "two three four five six seven eight nine"),
    ])
    result = LengthBalancedDistractorsCheck()(item)
    assert not result.passed


def test_length_check_returns_info_for_ee_items() -> None:
    item = Item(
        id=ItemId(uuid4()),
        module="EE",
        cefr_level="B2",
        content=EEContent(
            task_number=2,
            prompt="Discutez de l'immigration au Canada.",
            target_word_count_range=(110, 130),
            required_canadian_context=True,
            rubric_version="ee.v1",
        ),
        provenance=Provenance(
            source="x", source_id="1", license="CC0-1.0",
            ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )
    result = LengthBalancedDistractorsCheck()(item)
    assert result.passed
    assert result.severity == "info"


def test_length_check_fails_when_correct_option_missing() -> None:
    item = _ce_item_with_options(
        opts=[("a", "x x"), ("b", "y y"), ("c", "z z"), ("d", "w w")],
        correct="a",
    )
    # Force the mismatch: rewrite the question to declare a different correct id.
    object.__setattr__(item.content.questions[0], "correct_option_id", "missing")
    result = LengthBalancedDistractorsCheck()(item)
    assert not result.passed
    assert "missing from options" in (result.detail or "")
