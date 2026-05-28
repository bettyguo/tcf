# apps/worker

Celery worker. Phase 1 ships a single smoke task (`tcf_accel_worker.tasks.smoke.ping`).

Long-running work lands here in later phases:

- Phase 3: content-pipeline tasks (fetch / normalize / classify / synthesize / quality-gate / embed / load).
- Phase 4: nightly FSRS per-user param optimization + IRT refit.
- Phase 5: ASR + alignment + EE/EO scoring pre-processing.
- Phase 6: mock-exam grading.
- Phase 7: EE/EO scoring + calibration.

## Run

```bash
uv run celery -A tcf_accel_worker.celery_app worker --loglevel=info
```

## Tests

Phase 1 tests run with `task_always_eager=True` so no broker is needed.

```bash
uv run pytest apps/worker
```
