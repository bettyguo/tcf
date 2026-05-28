# infra/migrations

Alembic migrations. Phase 2 ships `0001_initial.py` with the schema from
`02_ARCHITECTURE.md §2.2`. Phase 1 reserves the directory.

Convention: every migration is named `NNNN_<short_description>.py` and
includes both `upgrade()` and `downgrade()` paths. Phase 2 audit verifies
`alembic upgrade head` + `alembic downgrade base` both succeed on a fresh DB.
