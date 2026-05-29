"""tcf-accel Python client SDK.

Generated from `docs/api/openapi.v1.yaml`. Phase 2 ships this package
as a thin handwritten wrapper around `httpx`; the full generated SDK
lands when Phase 3+ implementations stabilize.

The handwritten Phase 2 surface is:

- `Client(base_url, token=None)` — a thin httpx wrapper that knows the
  v1 base URL and decodes `ErrorEnvelope` payloads into `tcf_accel.errors`
  exceptions.

Phases 3–8 incrementally replace this with the generated client by
running `scripts/generate_clients.py`.
"""

from __future__ import annotations

from tcf_accel_client.client import Client

__version__ = "0.2.0"
__all__ = ["Client"]
