"""Smoke task. Confirms the Celery app boots and round-trips a payload.

Example:
    >>> from tcf_accel_worker.celery_app import celery_app
    >>> celery_app.conf.task_always_eager = True
    >>> from tcf_accel_worker.tasks.smoke import ping
    >>> ping.delay().get(timeout=1)
    'pong'

Complexity: O(1).
"""

from __future__ import annotations

from tcf_accel_worker.celery_app import celery_app


@celery_app.task(name="tcf_accel.smoke.ping")
def ping() -> str:
    """Return the literal string ``"pong"``."""
    return "pong"
