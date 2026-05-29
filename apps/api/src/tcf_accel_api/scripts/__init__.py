"""Operational scripts shipped with the API.

Phase 2: `export_openapi` freezes the running app's OpenAPI 3.1 spec to
`docs/api/openapi.v1.yaml`. CI verifies the committed file matches the
running app's output (drift → contract change → ADR + SCHEMA_VERSION bump).
"""

from __future__ import annotations
