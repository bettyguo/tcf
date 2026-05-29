"""Phase 2 initial schema.

The canonical DDL from `02_ARCHITECTURE.md §2.2` and `phase2_design.md §2`.

Creates: extension `vector`, then tables `users`, `items`, `interactions`,
`skill_estimates`, `study_plans`, `mock_exams`, `submissions`,
`diagnostic_sessions`, `sessions`, plus indexes.

`downgrade()` drops everything in reverse order, leaving the `vector`
extension installed (the extension is shared with the operator's other
databases and is harmless to leave).

Revision ID: 0001
Revises:
Create Date: 2026-05-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Extensions ────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ─── users ─────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("target_nclc", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("target_exam_date", sa.Date(), nullable=True),
        sa.Column(
            "daily_minutes_budget", sa.Integer(), nullable=False, server_default="150",
        ),
        sa.Column("locale", sa.Text(), nullable=False, server_default="en"),
        sa.Column(
            "privacy_mode", sa.Text(), nullable=False, server_default="local_only",
        ),
        sa.Column(
            "deleted_at", sa.dialects.postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.CheckConstraint("target_nclc BETWEEN 4 AND 12", name="users_target_nclc_ck"),
        sa.CheckConstraint(
            "daily_minutes_budget BETWEEN 15 AND 480",
            name="users_daily_minutes_budget_ck",
        ),
        sa.CheckConstraint(
            "locale IN ('en','fr','es','ar','zh')", name="users_locale_ck",
        ),
        sa.CheckConstraint(
            "privacy_mode IN ('local_only','cloud_optin')", name="users_privacy_mode_ck",
        ),
    )
    op.create_index(
        "users_email_active",
        "users",
        ["email"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ─── items ─────────────────────────────────────────────────
    op.create_table(
        "items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("cefr_level", sa.Text(), nullable=False),
        sa.Column("difficulty_irt", sa.Float(), nullable=True),
        sa.Column(
            "discrimination_irt", sa.Float(), nullable=True, server_default="1.0",
        ),
        sa.Column("content", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("provenance", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "quality_flags",
            sa.dialects.postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::TEXT[]"),
        ),
        sa.Column("synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retired", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "module IN ('CO','CE','EE','EO')", name="items_module_ck",
        ),
        sa.CheckConstraint(
            "cefr_level IN ('A1','A2','B1','B2','C1','C2')", name="items_cefr_level_ck",
        ),
    )
    # Vector column + HNSW index need raw SQL (pgvector is not in sqlalchemy core).
    op.execute("ALTER TABLE items ADD COLUMN embedding vector(768)")
    op.create_index(
        "items_module_level_difficulty",
        "items",
        ["module", "cefr_level", "difficulty_irt"],
        postgresql_where=sa.text("NOT retired"),
    )
    op.execute(
        "CREATE INDEX items_tags_gin ON items USING gin ((metadata->'tags'))",
    )
    op.execute(
        "CREATE INDEX items_embedding_hnsw "
        "ON items USING hnsw (embedding vector_cosine_ops)",
    )

    # ─── interactions ──────────────────────────────────────────
    op.create_table(
        "interactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "session_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False,
        ),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("raw_response", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("rt_ms", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("fsrs_stability", sa.Float(), nullable=True),
        sa.Column("fsrs_difficulty", sa.Float(), nullable=True),
        sa.Column("graded_score", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "module IN ('CO','CE','EE','EO')", name="interactions_module_ck",
        ),
        sa.CheckConstraint(
            "rt_ms IS NULL OR rt_ms >= 0", name="interactions_rt_ms_ck",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 4",
            name="interactions_rating_ck",
        ),
    )
    op.create_index(
        "interactions_user_created",
        "interactions",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "interactions_item_created",
        "interactions",
        ["item_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "interactions_user_session",
        "interactions",
        ["user_id", "session_id", "created_at"],
    )

    # ─── skill_estimates ───────────────────────────────────────
    op.create_table(
        "skill_estimates",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("skill", sa.Text(), primary_key=True),
        sa.Column("posterior_mean", sa.Float(), nullable=False),
        sa.Column("posterior_variance", sa.Float(), nullable=False),
        sa.Column("n_obs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_updated",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "skill IN ('CO','CE','EE','EO')", name="skill_estimates_skill_ck",
        ),
        sa.CheckConstraint(
            "posterior_variance >= 0", name="skill_estimates_variance_ck",
        ),
        sa.CheckConstraint("n_obs >= 0", name="skill_estimates_n_obs_ck"),
    )

    # ─── study_plans ───────────────────────────────────────────
    op.create_table(
        "study_plans",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("daily_blocks", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "superseded", sa.Boolean(), nullable=False, server_default=sa.false(),
        ),
        sa.CheckConstraint(
            "horizon_days BETWEEN 1 AND 365", name="study_plans_horizon_ck",
        ),
    )
    op.create_index(
        "study_plans_user_active",
        "study_plans",
        ["user_id", sa.text("generated_at DESC")],
        postgresql_where=sa.text("NOT superseded"),
    )

    # ─── mock_exams ────────────────────────────────────────────
    op.create_table(
        "mock_exams",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mode", sa.Text(), nullable=False, server_default="canonical",
        ),
        sa.Column(
            "started_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "finished_at", sa.dialects.postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("per_module_score", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("estimated_nclc", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("raw_log", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "mode IN ('canonical','training')", name="mock_exams_mode_ck",
        ),
    )
    op.create_index(
        "mock_exams_user_started",
        "mock_exams",
        ["user_id", sa.text("started_at DESC")],
    )

    # ─── submissions ───────────────────────────────────────────
    op.create_table(
        "submissions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id"),
            nullable=False,
        ),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("payload_uri", sa.Text(), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.Column("payload_sha256", sa.Text(), nullable=False),
        sa.Column("rubric", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "graded_at", sa.dialects.postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.CheckConstraint(
            "module IN ('EE','EO')", name="submissions_module_ck",
        ),
        sa.CheckConstraint(
            "status IN ('pending','grading','graded','failed')",
            name="submissions_status_ck",
        ),
        sa.CheckConstraint(
            "payload_bytes >= 0", name="submissions_payload_bytes_ck",
        ),
    )
    op.create_index(
        "submissions_user_submitted",
        "submissions",
        ["user_id", sa.text("submitted_at DESC")],
    )
    op.create_index(
        "submissions_status_submitted",
        "submissions",
        ["status", "submitted_at"],
        postgresql_where=sa.text("status IN ('pending','grading')"),
    )

    # ─── diagnostic_sessions ───────────────────────────────────
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "finished_at", sa.dialects.postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("state", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("final_estimates", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "diagnostic_sessions_user_started",
        "diagnostic_sessions",
        ["user_id", sa.text("started_at DESC")],
    )

    # ─── sessions (practice) ───────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("drill_type", sa.Text(), nullable=False),
        sa.Column("target_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "finished_at", sa.dialects.postgresql.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("summary", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "module IN ('CO','CE','EE','EO')", name="sessions_module_ck",
        ),
        sa.CheckConstraint(
            "target_minutes BETWEEN 1 AND 240", name="sessions_target_minutes_ck",
        ),
    )
    op.create_index(
        "sessions_user_started",
        "sessions",
        ["user_id", sa.text("started_at DESC")],
    )


def downgrade() -> None:
    # Drop in reverse creation order so FKs resolve cleanly.
    op.drop_index("sessions_user_started", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index(
        "diagnostic_sessions_user_started", table_name="diagnostic_sessions",
    )
    op.drop_table("diagnostic_sessions")

    op.drop_index("submissions_status_submitted", table_name="submissions")
    op.drop_index("submissions_user_submitted", table_name="submissions")
    op.drop_table("submissions")

    op.drop_index("mock_exams_user_started", table_name="mock_exams")
    op.drop_table("mock_exams")

    op.drop_index("study_plans_user_active", table_name="study_plans")
    op.drop_table("study_plans")

    op.drop_table("skill_estimates")

    op.drop_index("interactions_user_session", table_name="interactions")
    op.drop_index("interactions_item_created", table_name="interactions")
    op.drop_index("interactions_user_created", table_name="interactions")
    op.drop_table("interactions")

    op.execute("DROP INDEX IF EXISTS items_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS items_tags_gin")
    op.drop_index("items_module_level_difficulty", table_name="items")
    op.drop_table("items")

    op.drop_index("users_email_active", table_name="users")
    op.drop_table("users")

    # Leave the `vector` extension installed; it may be shared with other DBs.
