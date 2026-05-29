"""Automatic speech recognition (`phase5_design.md §5.1`, §6).

The backend is dispatched by the `TCF_ACCEL_ASR_BACKEND` environment
variable (ADR-017 — privacy-default-local-only):

- unset / "local"  → `LocalWhisperBackend` (CPU-only Whisper-large-v3-french).
- "cloud:litellm"  → `CloudLiteLLMASRBackend`. Constructing this is a
  deliberate operator deploy decision; without the env var the
  constructor refuses.
- "stub"           → `StubASRBackend`. Deterministic, no model weights;
  for tests only.

A capability test (`tests/capability/`) asserts that the *default*
inference path produces zero outbound socket connections.
"""

from __future__ import annotations

import os

from tcf_accel_ml.asr.backend import ASRBackend, ASRResult, ASRToken
from tcf_accel_ml.asr.whisper_fr import (
    CloudLiteLLMASRBackend,
    LocalWhisperBackend,
    StubASRBackend,
)

_ENV_VAR = "TCF_ACCEL_ASR_BACKEND"


def get_asr_backend() -> ASRBackend:
    """Return the ASR backend selected by `TCF_ACCEL_ASR_BACKEND`.

    Defaults to local. Unknown values raise `ValueError` so a typo in
    the env var fails loudly rather than silently picking a backend.

    Example:
        >>> import os
        >>> os.environ["TCF_ACCEL_ASR_BACKEND"] = "stub"
        >>> get_asr_backend().name
        'stub'
        >>> del os.environ["TCF_ACCEL_ASR_BACKEND"]
        >>> get_asr_backend().name
        'local'
    """
    value = os.environ.get(_ENV_VAR, "local")
    if value == "local":
        return LocalWhisperBackend()
    if value == "stub":
        return StubASRBackend()
    if value == "cloud:litellm":
        return CloudLiteLLMASRBackend()
    msg = f"Unknown {_ENV_VAR}={value!r}; expected one of {{'local','stub','cloud:litellm'}}."
    raise ValueError(msg)


__all__ = [
    "ASRBackend",
    "ASRResult",
    "ASRToken",
    "CloudLiteLLMASRBackend",
    "LocalWhisperBackend",
    "StubASRBackend",
    "get_asr_backend",
]
