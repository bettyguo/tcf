"""Fixture item pool for Phase 5 practice sessions.

The real bank + scheduler integration ships once Phase 3's `items`
table is queryable from the API (Postgres). Phase 5 needs *working*
drill sessions so the `/v1/session/*` contract can be honored
end-to-end; the pool below is a small deterministic synthetic bank of
full `Item` objects (CO + CE MCQ) spread across NCLC bands 4..10.

Mirrors `diagnostic_pool.py`. Phase 5's later steps swap this for the
real bank without touching the route shape.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from tcf_accel.ids import ItemId
from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import (
    MCQ,
    CEContent,
    COContent,
    EEContent,
    EOContent,
    MCQOption,
    Speaker,
)
from tcf_accel.schemas.item import CefrLevel, Item, Module

_BAND_TO_CEFR: Final[dict[int, CefrLevel]] = {
    4: "A2",
    5: "B1",
    6: "B1",
    7: "B2",
    8: "B2",
    9: "C1",
    10: "C1",
}


@dataclass(frozen=True)
class PooledItem:
    """A bank item plus its IRT difficulty for the posterior update."""

    item: Item
    difficulty: float
    discrimination: float
    band: int


def _seed_uuid(module: Module, band: int, idx: int) -> UUID:
    h = hashlib.sha256(f"sess::{module}::{band}::{idx}".encode()).hexdigest()
    return UUID(h[:32])


def _mcq(band: int, idx: int) -> MCQ:
    # Four options; the correct one is deterministic ("a"). The synthetic
    # bank is for wiring/contract tests, not for content realism.
    return MCQ(
        id=f"q{band}{idx}",
        prompt=f"Question (band {band}, #{idx}) — choisissez la bonne réponse.",
        options=[
            MCQOption(id="a", text="Bonne réponse"),
            MCQOption(id="b", text="Distracteur 1"),
            MCQOption(id="c", text="Distracteur 2"),
            MCQOption(id="d", text="Distracteur 3"),
        ],
        correct_option_id="a",
    )


def _co_item(band: int, idx: int) -> Item:
    return Item(
        id=ItemId(_seed_uuid("CO", band, idx)),
        module="CO",
        cefr_level=_BAND_TO_CEFR[band],
        difficulty_irt=float(band),
        discrimination_irt=1.0,
        content=COContent(
            transcript="Transcription synthétique pour la session.",
            duration_s=10.0,
            speakers=[Speaker(label="A", accent="fr-CA")],
            accent="fr-CA",
            register="standard",
            questions=[_mcq(band, idx)],
        ),
        provenance=Provenance(
            source="session_fixture",
            source_id=f"CO-{band}-{idx}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


def _ce_item(band: int, idx: int) -> Item:
    return Item(
        id=ItemId(_seed_uuid("CE", band, idx)),
        module="CE",
        cefr_level=_BAND_TO_CEFR[band],
        difficulty_irt=float(band),
        discrimination_irt=1.0,
        content=CEContent(
            passage=(
                "Passage synthétique pour la session de compréhension écrite. "
                "Il contient assez de texte pour satisfaire la borne minimale."
            ),
            genre="news",
            word_count=24,
            questions=[_mcq(band, idx)],
        ),
        provenance=Provenance(
            source="session_fixture",
            source_id=f"CE-{band}-{idx}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


_EE_TASK_RANGE: dict[int, tuple[int, int]] = {1: (48, 66), 2: (96, 132), 3: (144, 198)}


def _ee_item(band: int, idx: int, task_number: int = 2) -> Item:
    low, high = _EE_TASK_RANGE[task_number]
    return Item(
        id=ItemId(_seed_uuid("EE", band, idx)),
        module="EE",
        cefr_level=_BAND_TO_CEFR[band],
        difficulty_irt=float(band),
        discrimination_irt=1.0,
        content=EEContent(
            task_number=task_number,  # type: ignore[arg-type]
            prompt=(
                "Vous écrivez un message à votre voisin pour vous plaindre du bruit. "
                "Expliquez la situation et proposez une solution."
            ),
            target_word_count_range=(low, high),
            required_canadian_context=(task_number != 1),
            rubric_version="ee.v1",
        ),
        provenance=Provenance(
            source="session_fixture",
            source_id=f"EE-{band}-{idx}-t{task_number}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


def _eo_item(band: int, idx: int, task_number: int = 2) -> Item:
    duration = {1: 180, 2: 210, 3: 210}[task_number]
    prep = {1: 0, 2: 120, 3: 0}[task_number]
    return Item(
        id=ItemId(_seed_uuid("EO", band, idx)),
        module="EO",
        cefr_level=_BAND_TO_CEFR[band],
        difficulty_irt=float(band),
        discrimination_irt=1.0,
        content=EOContent(
            task_number=task_number,  # type: ignore[arg-type]
            examiner_prompts=[
                "Présentez-vous et parlez de votre travail.",
                "Quelles sont vos passions ?",
            ],
            candidate_prep_time_s=prep,
            target_duration_s=duration,
            rubric_version="eo.v1",
        ),
        provenance=Provenance(
            source="session_fixture",
            source_id=f"EO-{band}-{idx}-t{task_number}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


def _build_pool() -> dict[Module, list[PooledItem]]:
    pool: dict[Module, list[PooledItem]] = {"CO": [], "CE": [], "EE": [], "EO": []}
    for band in range(4, 11):
        for idx in range(3):  # 3 items per band
            pool["CO"].append(
                PooledItem(
                    item=_co_item(band, idx),
                    difficulty=float(band),
                    discrimination=1.0,
                    band=band,
                ),
            )
            pool["CE"].append(
                PooledItem(
                    item=_ce_item(band, idx),
                    difficulty=float(band),
                    discrimination=1.0,
                    band=band,
                ),
            )
        # One EE item per band, task 2 (the opinion piece, 120w / 20 min).
        pool["EE"].append(
            PooledItem(
                item=_ee_item(band, idx=0),
                difficulty=float(band),
                discrimination=1.0,
                band=band,
            ),
        )
        # One EO item per band, task 1 (Q&A, ~3 min).
        pool["EO"].append(
            PooledItem(
                item=_eo_item(band, idx=0, task_number=1),
                difficulty=float(band),
                discrimination=1.0,
                band=band,
            ),
        )
    return pool


SESSION_POOL: Final[dict[Module, list[PooledItem]]] = _build_pool()


def pooled_items_for(module: Module) -> list[PooledItem]:
    """Return the pooled items for a module (CO/CE in Phase 5 step 3)."""
    return list(SESSION_POOL.get(module, []))


def find_pooled(item_id: UUID) -> PooledItem | None:
    """Locate a pooled item by id across modules."""
    for items in SESSION_POOL.values():
        for pooled in items:
            if pooled.item.id == item_id:
                return pooled
    return None


__all__ = ["SESSION_POOL", "PooledItem", "find_pooled", "pooled_items_for"]
