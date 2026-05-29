"""Phase 5 additive: practice-session columns for the drill lifecycle.

The `sessions` table was created in `0001_initial.py` with the
columns the Phase 2 wire shape needed (id, user_id, module, drill_type,
target_minutes, started_at, finished_at, summary). Phase 5's drill
lifecycle (`phase5_design.md §13.1`) needs four more columns:

- `paused_at` — pause/resume support (resumable ≤ 24 h).
- `items_seen` / `items_correct` — running session counters, surfaced
  in `SessionState` without parsing the `summary` JSONB.
- `exam_shape` — flags exam-shape sessions so the rolling-7-day
  exam-shape-floor query (ADR-028) is a cheap indexed SUM rather than
  a JSONB scan.

All columns are nullable or server-defaulted, so the migration is safe
on a populated table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-28

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "paused_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "items_seen", sa.Integer(), nullable=False, server_default="0",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "items_correct", sa.Integer(), nullable=False, server_default="0",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "exam_shape", sa.Boolean(), nullable=False, server_default=sa.false(),
        ),
    )
    op.create_check_constraint(
        "sessions_items_seen_ck", "sessions", "items_seen >= 0",
    )
    op.create_check_constraint(
        "sessions_items_correct_ck",
        "sessions",
        "items_correct >= 0 AND items_correct <= items_seen",
    )
    # Backs the rolling-7-day exam-shape-floor query (ADR-028):
    #   SELECT SUM(target_minutes) FROM sessions
    #   WHERE user_id = $1 AND exam_shape AND finished_at > now() - '7 days'
    op.create_index(
        "sessions_user_exam_shape_finished",
        "sessions",
        ["user_id", sa.text("finished_at DESC")],
        postgresql_where=sa.text("exam_shape AND finished_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("sessions_user_exam_shape_finished", table_name="sessions")
    op.drop_constraint("sessions_items_correct_ck", "sessions", type_="check")
    op.drop_constraint("sessions_items_seen_ck", "sessions", type_="check")
    op.drop_column("sessions", "exam_shape")
    op.drop_column("sessions", "items_correct")
    op.drop_column("sessions", "items_seen")
    op.drop_column("sessions", "paused_at")
