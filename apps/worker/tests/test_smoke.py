"""Smoke tests for the Celery worker. Run with `task_always_eager`."""

from __future__ import annotations

import pytest

from tcf_accel_worker.celery_app import celery_app
from tcf_accel_worker.tasks.smoke import ping


@pytest.fixture(autouse=True)
def _eager_celery() -> None:
    """Force in-process execution so tests don't need a broker."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


def test_ping_returns_pong() -> None:
    result = ping.delay().get(timeout=1)
    assert result == "pong"


def test_celery_serializer_is_json_only() -> None:
    # ADR-0005 forbids pickle for security + reproducibility.
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
