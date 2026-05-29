"""`Interaction` — the public projection of one row in the `interactions` table.

Used by the `golden_learner.jsonl` fixture (`tests/pedagogy/`), by the
`GET /v1/data/export` NDJSON stream (Phase 9), and by Phase 4's
synthetic-cohort simulator. The DB row is the source of truth; this
schema is the *typed* view of it.

`correct` is nullable for EE/EO interactions where grading is async
(the rubric arrives later). `rating` is the FSRS self-rating
(1=again, 2=hard, 3=good, 4=easy), optional for MCQs where the
scheduler infers from correctness.

Phase 5 adds three optional fields (additive; SCHEMA_VERSION 0.4.0):

- `drill_kind` — the specific drill that produced the row. Distinct
  from `Module` because two drills (e.g., `co_mcq`, `ce_mcq`) share a
  `DrillType="mcq"` but write to different posteriors. Optional for
  back-compat with Phase 1–4 rows.
- `pronunciation` — `PronunciationSignal | None` for drills that
  record audio (`co_shadowing`, `eo_*`). Coarse-proxy contract per
  ADR-031.
- `audio_path` — local-only relative path under `data/` when the
  operator opted into audio retention. `None` by default per
  ADR-017 (privacy-default-local-only).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tcf_accel.schemas.api.plan import DrillKind
from tcf_accel.schemas.item import Module
from tcf_accel.schemas.pronunciation import PronunciationSignal


class Interaction(BaseModel):
    """One reviewed/answered item event.

    The DB row carries this shape (with `id` as BIGSERIAL → int);
    JSON serializations omit `id` if the row hasn't been persisted yet.
    """

    model_config = ConfigDict(extra="forbid")

    id: int | None = Field(default=None, ge=0)
    user_id: UUID
    item_id: UUID
    session_id: UUID
    module: Module
    correct: bool | None = Field(
        default=None,
        description="Null for EE/EO until the async scorer finishes.",
    )
    raw_response: dict[str, object] = Field(default_factory=dict)
    rt_ms: int | None = Field(default=None, ge=0)
    rating: int | None = Field(default=None, ge=1, le=4)
    fsrs_stability: float | None = Field(default=None, ge=0)
    fsrs_difficulty: float | None = Field(default=None)
    graded_score: dict[str, object] | None = None
    created_at: datetime

    # ─── Phase 5 additive surfaces (all optional) ──────────────
    drill_kind: DrillKind | None = Field(
        default=None,
        description=(
            "The specific drill that produced this row. Phase 5+. "
            "Two drills with different `drill_kind` may share `module` "
            "and `DrillType`; the kind disambiguates."
        ),
    )
    pronunciation: PronunciationSignal | None = Field(
        default=None,
        description=(
            "Set for drills that record audio. Coarse-proxy signal per "
            "ADR-031; the UI consumes `pronunciation.display_label`, the "
            "rubric scorer consumes `pronunciation.score`."
        ),
    )
    audio_path: str | None = Field(
        default=None,
        description=(
            "Local-only relative path under `data/` if the operator opted "
            "into audio retention. `None` by default (ADR-017)."
        ),
    )


__all__ = ["Interaction"]
