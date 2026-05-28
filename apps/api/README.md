# apps/api

FastAPI service. Phase 1 ships a `/healthz` endpoint only. Phase 2 freezes
the full `/v1/...` surface from `02_ARCHITECTURE.md §2.4`.

## Run

```bash
uv run uvicorn tcf_accel_api.main:app --reload --port 8000
```

Then visit `http://localhost:8000/healthz` — returns `{"status":"ok"}`.

## Tests

```bash
uv run pytest apps/api
```
