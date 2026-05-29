"""Examiner TTS for EO drills (`phase5_design.md §12.1`).

Wraps Coqui XTTS-v2 with a fixed examiner-style voice. The voice file
(`packages/content/data/voices/examiner.wav`) is a CC-BY recording
landing with the EO drill content (deferred to step 14 quality gates);
in CI the stub backend produces deterministic placeholder PCM bytes
so the EO pipeline can be exercised without the model weights.

Dispatch by `TCF_ACCEL_TTS_BACKEND` env var. Default is local; there
is **no** cloud-opt-in for TTS in Phase 5 — XTTS-v2 runs on CPU at ~3x
real-time on the documented baseline (`phase5_design.md §12.1`); the
operator who wants cloud TTS is on their own.
"""

from __future__ import annotations

import os

from tcf_accel_ml.tts.xtts import (
    LocalXTTSBackend,
    StubTTSBackend,
    TTSBackend,
    TTSResult,
)

_ENV_VAR = "TCF_ACCEL_TTS_BACKEND"


def get_tts_backend() -> TTSBackend:
    """Return the TTS backend selected by `TCF_ACCEL_TTS_BACKEND`.

    Defaults to local (`LocalXTTSBackend`). Unknown values raise
    `ValueError` so a typo fails loudly.

    Example:
        >>> import os
        >>> os.environ["TCF_ACCEL_TTS_BACKEND"] = "stub"
        >>> get_tts_backend().name
        'stub'
        >>> del os.environ["TCF_ACCEL_TTS_BACKEND"]
        >>> get_tts_backend().name
        'local'
    """
    value = os.environ.get(_ENV_VAR, "local")
    if value == "local":
        return LocalXTTSBackend()
    if value == "stub":
        return StubTTSBackend()
    msg = f"Unknown {_ENV_VAR}={value!r}; expected one of {{'local','stub'}}."
    raise ValueError(msg)


__all__ = [
    "LocalXTTSBackend",
    "StubTTSBackend",
    "TTSBackend",
    "TTSResult",
    "get_tts_backend",
]
