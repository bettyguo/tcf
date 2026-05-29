"""ASR backend contract (`phase5_design.md §6.1`).

Every backend (local Whisper, cloud LiteLLM, the deterministic test
stub) emits the same `ASRResult` shape so the pronunciation pipeline
downstream is backend-agnostic.

`mean_confidence` is computed by the backend over the per-token
confidences; it's the value the insufficient-data gate
(`phase5_design.md §5.3`) consults to decide `display_label`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

# Whisper / faster-whisper expect 16 kHz mono input by convention; we
# pass the rate explicitly to make the contract loud at the call site.
EXPECTED_SAMPLE_RATE_HZ = 16_000


@dataclass(frozen=True)
class ASRToken:
    """One transcribed token with timing + confidence.

    The token granularity differs by backend (whisper emits subword
    pieces; the stub emits whole words). The downstream pipeline reads
    `text` and `confidence` only — alignment uses the MFA aligner, not
    the ASR's own timestamps.
    """

    text: str
    start_s: float
    end_s: float
    confidence: float


@dataclass(frozen=True)
class ASRResult:
    """A backend-agnostic ASR transcription."""

    transcript: str
    tokens: tuple[ASRToken, ...]
    mean_confidence: float
    language: str
    duration_s: float


@runtime_checkable
class ASRBackend(Protocol):
    """ASR backend protocol.

    The contract is a single `transcribe` method that takes raw audio
    bytes and a sample rate. Implementations are responsible for
    decoding the bytes (typically PCM16 mono) and producing an
    `ASRResult`. Errors that prevent transcription should raise
    `ASRBackendUnavailableError` (`tcf_accel.errors.E_ASR_001`).
    """

    name: ClassVar[str]

    def transcribe(self, audio: bytes, *, sample_rate_hz: int) -> ASRResult:
        """Transcribe `audio` (PCM16 mono at `sample_rate_hz`) to an `ASRResult`."""
        ...


__all__ = ["EXPECTED_SAMPLE_RATE_HZ", "ASRBackend", "ASRResult", "ASRToken"]
