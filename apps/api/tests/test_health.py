"""Smoke tests for `/healthz`.

Phase 1 anti-criterion: any "Hello World" route returning 500 fails the gate.
These tests ensure the most basic endpoint round-trips correctly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tcf_accel.schemas.version import SCHEMA_VERSION
from tcf_accel_api.main import app

client = TestClient(app)


def test_healthz_returns_200() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200


def test_healthz_payload_shape() -> None:
    body = client.get("/healthz").json()
    assert body == {"status": "ok", "phase": 1, "schema_version": SCHEMA_VERSION}


def test_openapi_is_published() -> None:
    body = client.get("/openapi.json").json()
    assert body["info"]["title"] == "tcf-accel API"
    assert "/healthz" in body["paths"]
