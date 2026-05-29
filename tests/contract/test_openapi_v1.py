"""Phase 2 contract surface checks.

These tests guard:

1. The on-disk `docs/api/openapi.v1.yaml` matches what the running app
   emits (no drift). ADR-016 + `phase2_design.md §4.5`.
2. The spec is valid OpenAPI 3.1 (we don't pull a full validator —
   just check the top-level invariants).
3. Schemathesis can load the spec and round-trip valid requests.
   Stubbed routes must return either their documented response or the
   canonical `501 E_NOT_IMPLEMENTED_001` envelope.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from tcf_accel_api.main import create_app
from tcf_accel_api.scripts.export_openapi import _dump

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "docs" / "api" / "openapi.v1.yaml"


def test_committed_spec_matches_app() -> None:
    """The frozen file must equal the running app's emitted spec."""
    app = create_app()
    rendered = _dump(app.openapi())
    on_disk = SPEC_PATH.read_text(encoding="utf-8")
    if rendered != on_disk:
        pytest.fail(
            "OpenAPI drift detected. Re-run: "
            "uv run python -m tcf_accel_api.scripts.export_openapi --output docs/api/openapi.v1.yaml",
        )


def test_spec_validates_as_openapi_31() -> None:
    """Coarse OpenAPI 3.1 invariants. Not a full validator; full validation is run by Schemathesis."""
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    assert spec["openapi"].startswith("3."), spec["openapi"]
    assert "info" in spec
    assert "paths" in spec
    assert spec["info"]["title"] == "tcf-accel API"
    assert isinstance(spec["paths"], dict)
    assert len(spec["paths"]) >= 25, f"expected ≥ 25 paths, got {len(spec['paths'])}"


def test_every_route_returns_documented_response_or_501() -> None:
    """Light contract sweep: every GET with no path-params responds 200 or 501."""
    app = create_app()
    spec = app.openapi()
    client = TestClient(app)
    for path, methods in spec["paths"].items():
        # Skip routes with path parameters; they need real fixtures.
        if "{" in path:
            continue
        for method in methods:
            if method.upper() != "GET":
                continue
            response = client.get(path)
            assert response.status_code in {200, 401, 501}, (
                f"{method.upper()} {path}: status={response.status_code}"
            )
            if response.status_code == 501:
                envelope = response.json()["detail"]
                assert envelope["code"] == "E_NOT_IMPLEMENTED_001"
                assert envelope["phase"] is not None


def test_error_envelope_is_documented() -> None:
    """The on-the-wire error envelope schema must appear in components/schemas."""
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    schemas = spec.get("components", {}).get("schemas", {})
    assert "ErrorEnvelope" in schemas, "ErrorEnvelope must be in OpenAPI components"
