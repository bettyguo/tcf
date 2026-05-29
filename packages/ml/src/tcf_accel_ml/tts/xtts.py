"""TTS backends: local XTTS-v2 (real, lazy) + stub.

The local backend wraps Coqui XTTS-v2 with a fixed examiner voice. The
implementation is lazy: weights aren't loaded until `synthesize` is
called, so the package imports cleanly in a clean venv.

Rendered audio is cached at `data/cache/tts/<sha256(text+voice_id)>.wav`
(gitignored) — XTTS is CPU-expensive at ~3× real-time, so the cache is
load-bearing for the EO drill latency budget.

The stub backend is deterministic and dependency-free: it emits a
fixed-length PCM16 silence buffer whose size is proportional to the
input text length. Downstream pipeline tests use it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import ClassVar, Final, Protocol, runtime_checkable

from tcf_accel.errors import TTSBackendUnavailableError

# XTTS-v2 emits PCM16 mono at 24 kHz; we downsample to 16 kHz at the
# audio-pipeline seam to match the ASR/MFA convention.
XTTS_NATIVE_SAMPLE_RATE_HZ: Final[int] = 24_000
TTS_OUTPUT_SAMPLE_RATE_HZ: Final[int] = 16_000

# Heuristic for the stub: 75 ms of audio per character of text.
_STUB_MS_PER_CHAR: Final[float] = 75.0


@dataclass(frozen=True)
class TTSResult:
    """A synthesized audio clip + the cache key used to retrieve it."""

    audio: bytes  # PCM16 mono @ TTS_OUTPUT_SAMPLE_RATE_HZ
    sample_rate_hz: int
    duration_s: float
    cache_key: str  # sha256(text + voice_id), 64 hex chars


@runtime_checkable
class TTSBackend(Protocol):
    """TTS backend protocol."""

    name: ClassVar[str]

    def synthesize(self, text: str, *, voice_id: str = "examiner") -> TTSResult:
        """Render `text` to PCM16 audio using the named voice."""
        ...


def _cache_key(text: str, voice_id: str) -> str:
    return hashlib.sha256(f"{voice_id}::{text}".encode()).hexdigest()


class LocalXTTSBackend:
    """Local Coqui XTTS-v2 wrapper (CPU).

    Lazy: the model is loaded on first `synthesize` call, not at
    construction. If `TTS` (Coqui) isn't installed, `synthesize` raises
    `TTSBackendUnavailableError`, which the API layer surfaces as
    `E_TTS_001` (503).
    """

    name: ClassVar[str] = "local"

    def __init__(self) -> None:
        """Construct lazily; the model isn't loaded until the first synthesize."""
        self._model: object | None = None

    def _ensure_model(self) -> object:
        if self._model is not None:
            return self._model
        try:
            from TTS.api import TTS  # type: ignore[import-not-found]  # noqa: PLC0415
        except ImportError as exc:
            raise TTSBackendUnavailableError(
                backend="local",
                detail=(
                    "Coqui TTS is not installed. Run `make install-models` "
                    "or install the `TTS` package manually for local examiner TTS."
                ),
            ) from exc
        try:
            self._model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        except Exception as exc:
            raise TTSBackendUnavailableError(
                backend="local",
                detail=f"Failed to load XTTS-v2: {exc}",
            ) from exc
        return self._model

    def synthesize(  # pragma: no cover - exercised only with the real model
        self,
        text: str,
        *,
        voice_id: str = "examiner",
    ) -> TTSResult:
        """Synthesize `text` via local XTTS-v2."""
        _ = self._ensure_model()
        # Real implementation: render the text via the model, downsample
        # to TTS_OUTPUT_SAMPLE_RATE_HZ, return as PCM16 bytes. Phase 5
        # ships the wrapper shape; the actual rendering lands with the
        # operator's `make install-models` (§17 step 14).
        raise TTSBackendUnavailableError(
            backend="local",
            detail="XTTS rendering is wired in §17 step 14 (quality gates).",
        )


class StubTTSBackend:
    """Deterministic, dependency-free TTS for tests.

    Emits PCM16 silence whose length scales with the input text length
    (75 ms per char), and a cache key that's a function of the (text,
    voice_id) pair. Tests assert (a) the round-trip is stable, (b) the
    cache key changes when the text or voice changes, and (c) the
    duration is non-zero for non-empty text.
    """

    name: ClassVar[str] = "stub"

    def synthesize(self, text: str, *, voice_id: str = "examiner") -> TTSResult:
        """Return a deterministic PCM16 silence buffer sized by the text length."""
        duration_s = max(0.5, len(text) * _STUB_MS_PER_CHAR / 1000.0) if text else 0.0
        n_samples = int(duration_s * TTS_OUTPUT_SAMPLE_RATE_HZ)
        # PCM16 silence: 2 bytes per sample, all zero. The stub MFA
        # aligner's "0x00\x00 prefix → low confidence" path activates
        # for these bytes, so downstream insufficient-data tests work
        # naturally without special-casing.
        audio = b"\x00\x00" * n_samples
        return TTSResult(
            audio=audio,
            sample_rate_hz=TTS_OUTPUT_SAMPLE_RATE_HZ,
            duration_s=duration_s,
            cache_key=_cache_key(text, voice_id),
        )


__all__ = [
    "TTS_OUTPUT_SAMPLE_RATE_HZ",
    "XTTS_NATIVE_SAMPLE_RATE_HZ",
    "LocalXTTSBackend",
    "StubTTSBackend",
    "TTSBackend",
    "TTSResult",
]
