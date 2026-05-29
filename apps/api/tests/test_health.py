"""Smoke tests for `/healthz` and `/v1/health`.

Phase 1 anti-criterion: any "Hello World" route returning 500 fails the
gate. These tests ensure the most basic endpoints round-trip correctly
and that the Phase 2 versioned route is mounted.
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
    assert body == {"status": "ok", "phase": 2, "schema_version": SCHEMA_VERSION}


def test_v1_health_returns_200() -> None:
    body = client.get("/v1/health").json()
    assert body["status"] == "ok"
    assert body["api_version"] == "v1"
    assert body["schema_version"] == SCHEMA_VERSION


def test_openapi_is_published() -> None:
    body = client.get("/openapi.json").json()
    assert body["info"]["title"] == "tcf-accel API"
    assert "/healthz" in body["paths"]
    assert "/v1/health" in body["paths"]
