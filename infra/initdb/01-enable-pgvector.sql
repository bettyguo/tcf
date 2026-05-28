-- Enable pgvector on the tcf database at first boot.
-- The image (pgvector/pgvector:pg16) ships the extension; we just CREATE it.
CREATE EXTENSION IF NOT EXISTS vector;

-- Phase 2 (Alembic migration 0001_initial) defines all tables; this script
-- only enables the extension and is idempotent.
