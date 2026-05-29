"""Phase 3 additive: `confusable_pairs` table.

Phase 3 creates the table because the manual-review UI (`apps/review`)
writes to it as the operator tags semantically-confusable item pairs
(e.g., `amener / emmener / apporter / emporter`). Phase 4 consumes the
table for LECTOR semantic-aware scheduling
(master prompt §2.1.4, ADR-0006-adjacent).

The `item_a_id < item_b_id` CHECK enforces canonical ordering so that
`(A, B)` and `(B, A)` cannot both exist as separate rows. The unique
constraint backs that up at the DB level.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "confusable_pairs",
        sa.Column(
            "id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
        ),
        sa.Column(
            "item_a_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "item_b_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("confusability", sa.Integer(), nullable=False),
        sa.Column(
            "source", sa.Text(), nullable=False, server_default="manual",
        ),
        sa.Column(
            "created_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "confusability BETWEEN 1 AND 3",
            name="confusable_pairs_confusability_ck",
        ),
        sa.CheckConstraint(
            "source IN ('manual','llm_proposed','embedding_neighbor')",
            name="confusable_pairs_source_ck",
        ),
        sa.CheckConstraint(
            "item_a_id < item_b_id",
            name="confusable_pairs_canonical_order_ck",
        ),
        sa.UniqueConstraint(
            "item_a_id", "item_b_id", name="confusable_pairs_pair_uq",
        ),
    )
    op.create_index(
        "confusable_pairs_a", "confusable_pairs", ["item_a_id"],
    )
    op.create_index(
        "confusable_pairs_b", "confusable_pairs", ["item_b_id"],
    )


def downgrade() -> None:
    op.drop_index("confusable_pairs_b", table_name="confusable_pairs")
    op.drop_index("confusable_pairs_a", table_name="confusable_pairs")
    op.drop_table("confusable_pairs")
