"""Shared fixtures for the content package tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tcf_accel.ids import ItemId
from tcf_accel.schemas import (
    MCQ,
    CEContent,
    Item,
    MCQOption,
    Provenance,
)


def _balanced_options() -> list[MCQOption]:
    """Four options of equal token count, for the gate happy path."""
    return [
        MCQOption(id="a", text="le chat dort sur le tapis"),
        MCQOption(id="b", text="le chien court dans le jardin"),
        MCQOption(id="c", text="la souris mange dans la cuisine"),
        MCQOption(id="d", text="le lapin saute par la fenêtre"),
    ]


@pytest.fixture
def passing_ce_item() -> Item:
    """A CE item that should pass every Phase 3 foundation gate check."""
    return Item(
        id=ItemId(uuid4()),
        module="CE",
        cefr_level="B2",
        content=CEContent(
            passage=(
                "Le matin, Marie prend son café avant de partir au travail. "
                "Elle marche jusqu'à la station de métro, lit un livre, "
                "et arrive au bureau à neuf heures."
            ),
            genre="narrative",
            word_count=27,
            questions=[
                MCQ(
                    id="q1",
                    prompt="À quelle heure Marie arrive-t-elle au bureau ?",
                    options=_balanced_options(),
                    correct_option_id="a",
                ),
            ],
        ),
        provenance=Provenance(
            source="wikisource_fr",
            source_id="test-1",
            license="CC-BY-SA-4.0",
            ingested_at=datetime(2026, 5, 27, tzinfo=UTC),
            review_status="auto_passed",
        ),
    )
