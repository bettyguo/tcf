"""Celery application factory.

Conventions (ADR-0005):
- Tasks are idempotent and keyed by `(task_name, content_hash)`.
- `task_acks_late = True` so an OOM-killed worker re-queues its task.
- `worker_max_tasks_per_child` cycles workers to dodge memory leaks.
- JSON serializer only — `pickle` is explicitly disabled.
- Tests use `task_always_eager=True` so no broker is required.

Example:
    >>> from tcf_accel_worker.celery_app import celery_app
    >>> celery_app.conf.task_always_eager = True
    >>> from tcf_accel_worker.tasks.smoke import ping
    >>> ping.delay().get(timeout=1)
    'pong'

Complexity: O(N) registration in the number of imported task modules.
"""

from __future__ import annotations

import os
from typing import Final

from celery import Celery

BROKER_URL: Final[str] = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND: Final[str] = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/2",
)
WORKER_CONCURRENCY: Final[int] = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "4"))
WORKER_MAX_TASKS_PER_CHILD: Final[int] = int(
    os.environ.get("CELERY_WORKER_MAX_TASKS_PER_CHILD", "200"),
)


def _make_app() -> Celery:
    app = Celery(
        "tcf_accel_worker",
        broker=BROKER_URL,
        backend=RESULT_BACKEND,
        include=[
            "tcf_accel_worker.tasks.smoke",
            "tcf_accel_worker.tasks.score_ee",
            "tcf_accel_worker.tasks.score_eo",
            "tcf_accel_worker.tasks.score_mock",
        ],
    )
    app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],  # no pickle — security + reproducibility
        worker_concurrency=WORKER_CONCURRENCY,
        worker_max_tasks_per_child=WORKER_MAX_TASKS_PER_CHILD,
        worker_hijack_root_logger=False,
        task_track_started=True,
        broker_connection_retry_on_startup=True,
        timezone="UTC",
        enable_utc=True,
    )
    return app


celery_app: Final[Celery] = _make_app()


__all__ = ["celery_app"]
