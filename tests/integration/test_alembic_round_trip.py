"""Alembic up/down round-trip on a live Postgres + pgvector.

`02_ARCHITECTURE.md §4`: Alembic `upgrade head` and `downgrade base`
both succeed on a fresh DB. Phase 2 audit verifies this end-to-end.

These tests require the docker-compose `db` service running
(`make dev` provisions it). They're marked `@pytest.mark.integration`
and skipped if `DATABASE_URL_SYNC` is unreachable.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

REPO_ROOT = Path(__file__).resolve().parents[2]


def _engine() -> Engine | None:
    url = os.environ.get(
        "DATABASE_URL_SYNC", "postgresql://tcf:tcf@localhost:5432/tcf",
    )
    try:
        eng = sa.create_engine(url, connect_args={"connect_timeout": 2})
        with eng.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return eng
    except Exception:
        return None


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_engine() -> Engine:
    eng = _engine()
    if eng is None:
        pytest.skip("Postgres not reachable; start `make dev` or set DATABASE_URL_SYNC")
    return eng


def _run_alembic(cmd: str) -> None:
    """Invoke alembic via the Python API so we don't shell out."""
    from alembic.command import downgrade, upgrade
    from alembic.config import Config

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
    if cmd == "upgrade-head":
        upgrade(cfg, "head")
    elif cmd == "downgrade-base":
        downgrade(cfg, "base")
    else:
        msg = f"unknown alembic cmd: {cmd}"
        raise ValueError(msg)


def test_upgrade_then_downgrade(db_engine: Engine) -> None:
    # Ensure starting clean.
    _run_alembic("downgrade-base")
    _run_alembic("upgrade-head")

    expected_tables = {
        "users", "items", "interactions", "skill_estimates", "study_plans",
        "mock_exams", "submissions", "diagnostic_sessions", "sessions",
        "alembic_version",
    }
    with db_engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'",
            ),
        ).fetchall()
    actual = {r[0] for r in rows}
    missing = expected_tables - actual
    assert not missing, f"missing tables after upgrade: {missing}"

    _run_alembic("downgrade-base")
    with db_engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'",
            ),
        ).fetchall()
    # After downgrade, only alembic_version may remain.
    leftover = {r[0] for r in rows} - {"alembic_version"}
    assert not leftover, f"leftover tables after downgrade: {leftover}"


def test_pgvector_extension_present(db_engine: Engine) -> None:
    """The migration enables `vector`; verify it's installed after upgrade."""
    _run_alembic("upgrade-head")
    with db_engine.connect() as conn:
        result = conn.execute(
            sa.text(
                "SELECT extname FROM pg_extension WHERE extname='vector'",
            ),
        ).fetchall()
    assert result, "pgvector extension not present after upgrade"
