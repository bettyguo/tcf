"""Phase 5 additive: pronunciation + drill-kind columns on interactions.

The `interactions` table was created in `0001_initial.py`. Phase 5
(`phase5_design.md §13.2`) adds three columns matching the additive
fields on the `Interaction` Pydantic model (SCHEMA_VERSION 0.4.0):

- `drill_kind` — the specific drill that produced the row. CHECK
  against the closed set of `DrillKind` values so a typo can't enter.
- `pronunciation_signal` — JSONB carrying the `PronunciationSignal`
  shape (ADR-031). Not indexed; the rubric scorer reads the whole blob.
- `audio_path` — local-only relative path under `data/` if the
  operator opted into audio retention; `NULL` by default (ADR-017).

All columns are nullable, so the migration is safe on a populated
table and existing Phase-4-era rows read back with `NULL` in the new
columns (downgrade-safe).

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-28

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Kept in sync with `tcf_accel.schemas.api.plan.DrillKind`. The CHECK
# constraint is the DB-side enforcement of the closed set; the Pydantic
# Literal is the app-side enforcement.
_DRILL_KINDS = (
    "co_mcq",
    "co_dictation",
    "co_shadowing",
    "co_accent",
    "co_gapfill",
    "co_lexical_alt",
    "ce_mcq",
    "ce_skim_scan",
    "ce_vocab_context",
    "ce_register_id",
    "ce_summary",
    "ee_task",
    "ee_rewrite",
    "ee_connector",
    "ee_error_correction",
    "ee_register_adjust",
    "eo_task",
    "eo_picture",
    "eo_spontaneous",
    "eo_roleplay",
    "eo_repair",
    "eo_text_alt",
    "mock_section",
    "diagnostic_item",
)


def upgrade() -> None:
    op.add_column(
        "interactions",
        sa.Column("drill_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "interactions",
        sa.Column(
            "pronunciation_signal",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
        ),
    )
    op.add_column(
        "interactions",
        sa.Column("audio_path", sa.Text(), nullable=True),
    )
    _kinds = ",".join(f"'{k}'" for k in _DRILL_KINDS)
    op.create_check_constraint(
        "interactions_drill_kind_ck",
        "interactions",
        f"drill_kind IS NULL OR drill_kind IN ({_kinds})",
    )
    # Audit invariant (phase5_audit.md §7): a lexical-alt drill must not
    # masquerade as CO. co_lexical_alt rows always carry module='CE'.
    op.create_check_constraint(
        "interactions_lexical_alt_module_ck",
        "interactions",
        "drill_kind IS DISTINCT FROM 'co_lexical_alt' OR module = 'CE'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "interactions_lexical_alt_module_ck", "interactions", type_="check",
    )
    op.drop_constraint(
        "interactions_drill_kind_ck", "interactions", type_="check",
    )
    op.drop_column("interactions", "audio_path")
    op.drop_column("interactions", "pronunciation_signal")
    op.drop_column("interactions", "drill_kind")
