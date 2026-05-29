# tcf-accel-client (Python)

Python client SDK for the tcf-accel API. Phase 2 ships a thin `httpx`
wrapper that knows the `/v1/` base URL and decodes the canonical
`ErrorEnvelope` shape. The fully-typed surface arrives in Phase 3+
once implementations stabilize and the generator (see
`scripts/generate_clients.py`) runs against a stable spec.

## Usage

```python
from tcf_accel_client import Client

with Client("http://localhost:8000", token="…") as c:
    health = c.get("/v1/health")
    print(health["status"])
```

## Regeneration

```bash
uv run python scripts/generate_clients.py --target python
```

Subsequent phases consume this client rather than re-typing routes
(per `02_ARCHITECTURE.md §5`).
