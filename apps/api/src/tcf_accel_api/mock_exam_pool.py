"""Mock-exam bank fixture.

Phase 6 needs a bank large enough that the selector-diversity audit
(≥ 60% bank coverage across 100 weeks) is meaningful, but small
enough to keep test fixtures bearable.

We synthesize:

- **CO**: 240 items — 40 per CEFR band × 6 bands, with 3 accents and
  3 registers cycling through each band.
- **CE**: 240 items — 40 per CEFR band × 6 bands, with 6 genres cycling.
- **EE**: 30 items — 10 per task-number, spread across CEFR bands.
- **EO**: 30 items — 10 per task-number, spread across CEFR bands.

Item ids are deterministic (sha-256 of `mock::{module}::{band}::{idx}`)
so two test runs return identical banks.

The pool is built at import time and frozen. Tests can substitute a
smaller pool via the `set_pool_override` hook (used by the diversity
audit to inject corner-case banks).
"""

from __future__ import annotations

import hashlib
import threading
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
from tcf_accel.schemas.content.ce import Genre
from tcf_accel.schemas.content.co import Accent, Register
from tcf_accel.schemas.item import CefrLevel, Item, Module
from tcf_accel_sla.mock_exam.selector import PooledMockItem

# CEFR → mid-range IRT difficulty (NCLC-scale). The difficulty span is
# wider than the session pool's 4..10 because the mock must touch
# every CEFR band (NCLC 1..12).
_CEFR_TO_DIFFICULTY: Final[dict[CefrLevel, float]] = {
    "A1": 2.0,
    "A2": 4.0,
    "B1": 6.0,
    "B2": 8.0,
    "C1": 10.0,
    "C2": 11.5,
}

_ACCENTS: Final[tuple[Accent, ...]] = ("fr-FR", "fr-CA", "fr-BE")
_REGISTERS: Final[tuple[Register, ...]] = ("soutenu", "standard", "familier")
_GENRES: Final[tuple[Genre, ...]] = (
    "news", "ad", "letter", "admin", "academic", "narrative",
)

CO_PER_BAND: Final[int] = 40
CE_PER_BAND: Final[int] = 40
EE_PER_TASK: Final[int] = 10
EO_PER_TASK: Final[int] = 10


def _seed_uuid(module: Module, band: CefrLevel, idx: int) -> UUID:
    h = hashlib.sha256(f"mock::{module}::{band}::{idx}".encode()).hexdigest()
    return UUID(h[:32])


def _mcq(band: CefrLevel, idx: int) -> MCQ:
    return MCQ(
        id=f"q{band}{idx}",
        prompt=f"Question ({band}, #{idx}) — choisissez la bonne réponse.",
        options=[
            MCQOption(id="a", text="Bonne réponse"),
            MCQOption(id="b", text="Distracteur 1"),
            MCQOption(id="c", text="Distracteur 2"),
            MCQOption(id="d", text="Distracteur 3"),
        ],
        correct_option_id="a",
    )


def _co_item(band: CefrLevel, idx: int) -> Item:
    accent = _ACCENTS[idx % len(_ACCENTS)]
    register = _REGISTERS[idx % len(_REGISTERS)]
    return Item(
        id=ItemId(_seed_uuid("CO", band, idx)),
        module="CO",
        cefr_level=band,
        difficulty_irt=_CEFR_TO_DIFFICULTY[band],
        discrimination_irt=1.0,
        content=COContent(
            transcript=(
                "Transcription synthétique pour l'examen blanc. "
                "Niveau et contexte adaptés au CEFR."
            ),
            duration_s=20.0,
            speakers=[Speaker(label="A", accent=accent)],
            accent=accent,
            register=register,
            questions=[_mcq(band, idx)],
        ),
        provenance=Provenance(
            source="mock_fixture",
            source_id=f"CO-{band}-{idx}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


def _ce_item(band: CefrLevel, idx: int) -> Item:
    genre = _GENRES[idx % len(_GENRES)]
    return Item(
        id=ItemId(_seed_uuid("CE", band, idx)),
        module="CE",
        cefr_level=band,
        difficulty_irt=_CEFR_TO_DIFFICULTY[band],
        discrimination_irt=1.0,
        content=CEContent(
            passage=(
                "Passage synthétique pour la compréhension écrite de l'examen blanc. "
                "Adapté au niveau CEFR et au genre cible."
            ),
            genre=genre,
            word_count=28,
            questions=[_mcq(band, idx)],
        ),
        provenance=Provenance(
            source="mock_fixture",
            source_id=f"CE-{band}-{idx}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


_EE_TASK_RANGE: dict[int, tuple[int, int]] = {1: (48, 66), 2: (96, 132), 3: (144, 198)}


def _ee_item(band: CefrLevel, idx: int, task_number: int) -> Item:
    low, high = _EE_TASK_RANGE[task_number]
    return Item(
        id=ItemId(_seed_uuid("EE", band, idx * 10 + task_number)),
        module="EE",
        cefr_level=band,
        difficulty_irt=_CEFR_TO_DIFFICULTY[band],
        discrimination_irt=1.0,
        content=EEContent(
            task_number=task_number,  # type: ignore[arg-type]
            prompt=(
                f"Tâche {task_number} (niveau {band}) : "
                "Rédigez un message en respectant le format demandé."
            ),
            target_word_count_range=(low, high),
            required_canadian_context=(task_number != 1),
            rubric_version="ee.v1",
        ),
        provenance=Provenance(
            source="mock_fixture",
            source_id=f"EE-{band}-{idx}-t{task_number}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


def _eo_item(band: CefrLevel, idx: int, task_number: int) -> Item:
    duration = {1: 180, 2: 210, 3: 210}[task_number]
    prep = {1: 0, 2: 120, 3: 0}[task_number]
    return Item(
        id=ItemId(_seed_uuid("EO", band, idx * 10 + task_number)),
        module="EO",
        cefr_level=band,
        difficulty_irt=_CEFR_TO_DIFFICULTY[band],
        discrimination_irt=1.0,
        content=EOContent(
            task_number=task_number,  # type: ignore[arg-type]
            examiner_prompts=[
                f"Tâche {task_number} : prompt d'examinateur.",
                "Question de relance.",
            ],
            candidate_prep_time_s=prep,
            target_duration_s=duration,
            rubric_version="eo.v1",
        ),
        provenance=Provenance(
            source="mock_fixture",
            source_id=f"EO-{band}-{idx}-t{task_number}",
            license="CC0-1.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
        synthetic=True,
    )


_BANDS: Final[tuple[CefrLevel, ...]] = ("A1", "A2", "B1", "B2", "C1", "C2")


def _build_pool() -> dict[Module, list[PooledMockItem]]:
    pool: dict[Module, list[PooledMockItem]] = {"CO": [], "CE": [], "EE": [], "EO": []}
    cluster_id = 0
    for band in _BANDS:
        for idx in range(CO_PER_BAND):
            pool["CO"].append(
                PooledMockItem(
                    item=_co_item(band, idx),
                    difficulty=_CEFR_TO_DIFFICULTY[band],
                    discrimination=1.0,
                    cefr=band,
                    topic_cluster_id=cluster_id % 50,
                ),
            )
            cluster_id += 1
        for idx in range(CE_PER_BAND):
            pool["CE"].append(
                PooledMockItem(
                    item=_ce_item(band, idx),
                    difficulty=_CEFR_TO_DIFFICULTY[band],
                    discrimination=1.0,
                    cefr=band,
                    topic_cluster_id=cluster_id % 50,
                ),
            )
            cluster_id += 1
        for task in (1, 2, 3):
            # 2 EE items per band per task = ~12/task across 6 bands;
            # selector picks 1 per task → plenty of diversity.
            for idx in range(2):
                pool["EE"].append(
                    PooledMockItem(
                        item=_ee_item(band, idx, task),
                        difficulty=_CEFR_TO_DIFFICULTY[band],
                        discrimination=1.0,
                        cefr=band,
                        task_number=task,
                    ),
                )
                pool["EO"].append(
                    PooledMockItem(
                        item=_eo_item(band, idx, task),
                        difficulty=_CEFR_TO_DIFFICULTY[band],
                        discrimination=1.0,
                        cefr=band,
                        task_number=task,
                    ),
                )
    return pool


_POOL_LOCK = threading.Lock()
_POOL: Final[dict[Module, list[PooledMockItem]]] = _build_pool()
_OVERRIDE: dict[Module, list[PooledMockItem]] | None = None


def mock_bank() -> dict[Module, list[PooledMockItem]]:
    """Return the active mock bank (override-aware)."""
    if _OVERRIDE is not None:
        return _OVERRIDE
    return _POOL


def set_pool_override(pool: dict[Module, list[PooledMockItem]] | None) -> None:
    """Replace the active bank (tests + audit)."""
    global _OVERRIDE
    with _POOL_LOCK:
        _OVERRIDE = pool


def find_pooled_mock(item_id: UUID) -> PooledMockItem | None:
    """Locate a pooled mock item by id across modules."""
    bank = mock_bank()
    for items in bank.values():
        for p in items:
            if p.item.id == item_id:
                return p
    return None


_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {"correct_option_id", "explanation", "rubric_version", "answer_key"},
)


def redact_item_dump(item: Item) -> dict[str, object]:
    """Serialize `item` to a dict with answer fields stripped.

    Required at every API boundary that returns mock items
    (`phase6_design.md §10.1`). The no-leak audit walks the response
    body and asserts none of `_FORBIDDEN_KEYS` appears.

    The pydantic `MCQ` model requires `correct_option_id`; rather than
    fight the validator we serialize first and *then* strip — the
    server-side `Item` remains valid; only the wire payload is
    redacted.
    """
    raw = item.model_dump(mode="json")
    _strip_keys(raw)
    return raw


def _strip_keys(node: object) -> None:
    if isinstance(node, dict):
        for key in list(node.keys()):
            if key in _FORBIDDEN_KEYS:
                node.pop(key)
            else:
                _strip_keys(node[key])
    elif isinstance(node, list):
        for child in node:
            _strip_keys(child)


__all__ = [
    "CO_PER_BAND",
    "CE_PER_BAND",
    "EE_PER_TASK",
    "EO_PER_TASK",
    "find_pooled_mock",
    "mock_bank",
    "redact_item_dump",
    "set_pool_override",
]
