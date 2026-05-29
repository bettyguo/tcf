"""ASR backends: local Whisper-fr (real), cloud LiteLLM (opt-in), and a stub.

The local backend wraps `bofenghuang/whisper-large-v3-french` via
`faster-whisper`. The model weights are *not* bundled with the repo —
the operator runs `make install-models` once to populate the local
cache (`phase5_design.md §6.4`). If the weights aren't present,
`transcribe` raises `ASRBackendUnavailableError`, which the API layer
surfaces as `E_ASR_001` (503).

The cloud backend is gated by the `TCF_ACCEL_ASR_BACKEND=cloud:litellm`
env var; constructing it without the var raises (`phase5_audit.md §9`,
ADR-017). The capability test enforces this.

The stub backend is deterministic and dependency-free: it produces
fixed-shape `ASRResult`s seeded by the audio's hash. Use it in tests
that exercise the pipeline without depending on model availability.
"""

from __future__ import annotations

import os
from typing import ClassVar, Final

from tcf_accel.errors import ASRBackendUnavailableError

from tcf_accel_ml.asr.backend import ASRResult, ASRToken

_ENV_VAR: Final[str] = "TCF_ACCEL_ASR_BACKEND"

# `bofenghuang/whisper-large-v3-french` is the published checkpoint
# (ADR-0007; master prompt §8). The local backend pins this name so a
# silent model swap can't drift the WER calibration.
WHISPER_MODEL_ID: Final[str] = "bofenghuang/whisper-large-v3-french"


class LocalWhisperBackend:
    """Local CPU Whisper-large-v3-french.

    Lazy: the model is loaded on first `transcribe` call, not at
    construction. This keeps imports cheap and lets the API/worker
    start even when the model cache is absent (the first inference is
    the one that fails loudly).

    The backend raises `ASRBackendUnavailableError` (E_ASR_001) when
    `faster-whisper` is not installed or the model weights aren't in
    the local cache; the API layer maps this to a 503.
    """

    name: ClassVar[str] = "local"

    def __init__(self) -> None:
        """Construct lazily; the model isn't loaded until the first `transcribe`."""
        self._model: object | None = None  # lazy

    def _ensure_model(self) -> object:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import (  # noqa: PLC0415
                WhisperModel,  # type: ignore[import-not-found]
            )
        except ImportError as exc:
            raise ASRBackendUnavailableError(
                backend="local",
                detail=(
                    "faster-whisper is not installed. Run `make install-models` "
                    "or install the package manually to enable local ASR."
                ),
            ) from exc
        try:
            self._model = WhisperModel(WHISPER_MODEL_ID, device="cpu", compute_type="int8")
        except Exception as exc:
            raise ASRBackendUnavailableError(
                backend="local",
                detail=f"Failed to load {WHISPER_MODEL_ID}: {exc}",
            ) from exc
        return self._model

    def transcribe(self, audio: bytes, *, sample_rate_hz: int) -> ASRResult:
        """Transcribe with the local Whisper-fr model.

        Raises:
            ASRBackendUnavailableError: if faster-whisper or the model
                cache is unavailable.
        """
        model = self._ensure_model()
        # Real conversion of `audio` bytes → float32 numpy array happens
        # inside this branch; we do it lazily to avoid pulling numpy on
        # the import path. The actual decode is deferred until a real
        # transcription is attempted (i.e., the model is loadable).
        try:
            import numpy as np  # type: ignore[import-not-found]  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover — numpy is a faster-whisper dep
            raise ASRBackendUnavailableError(backend="local", detail="numpy missing") from exc

        pcm = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        segments, info = model.transcribe(  # type: ignore[attr-defined]
            pcm,
            language="fr",
            word_timestamps=True,
        )
        tokens, transcript_parts, confidences = _flatten_segments(segments)
        duration_s = len(pcm) / float(sample_rate_hz) if sample_rate_hz else float(info.duration)
        mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return ASRResult(
            transcript=" ".join(transcript_parts).strip(),
            tokens=tuple(tokens),
            mean_confidence=mean_conf,
            language=info.language,
            duration_s=duration_s,
        )


def _flatten_segments(
    segments: object,
) -> tuple[
    list[ASRToken], list[str], list[float]
]:  # pragma: no cover - exercised only with real model
    """Flatten faster-whisper's per-segment word objects into ASRTokens."""
    tokens: list[ASRToken] = []
    transcript_parts: list[str] = []
    confidences: list[float] = []
    for seg in segments:  # type: ignore[attr-defined]
        transcript_parts.append(seg.text)
        for w in seg.words or ():
            # word-level confidence is exp(avg log-prob) per faster-whisper.
            conf = float(getattr(w, "probability", 0.0) or 0.0)
            tokens.append(
                ASRToken(
                    text=w.word.strip(),
                    start_s=float(w.start),
                    end_s=float(w.end),
                    confidence=conf,
                ),
            )
            confidences.append(conf)
    return tokens, transcript_parts, confidences


class CloudLiteLLMASRBackend:
    """Cloud ASR via the LiteLLM gateway (operator opt-in only).

    Constructing this without `TCF_ACCEL_ASR_BACKEND=cloud:litellm`
    raises — ADR-017 makes the cloud path a deliberate per-deploy
    decision, never a per-request one. The capability test
    (`phase5_audit.md §9`) enforces this.
    """

    name: ClassVar[str] = "cloud:litellm"

    def __init__(self) -> None:
        """Refuse construction unless `TCF_ACCEL_ASR_BACKEND=cloud:litellm` (ADR-017)."""
        if os.environ.get(_ENV_VAR) != "cloud:litellm":
            msg = (
                f"{type(self).__name__} can only be constructed when "
                f"{_ENV_VAR}=cloud:litellm is set (ADR-017)."
            )
            raise RuntimeError(msg)

    def transcribe(
        self,
        audio: bytes,
        *,
        sample_rate_hz: int,
    ) -> ASRResult:  # pragma: no cover - opt-in path; covered by integration tests
        """Transcribe via the LiteLLM gateway (Phase 7 finishes the wiring)."""
        try:
            import litellm  # type: ignore[import-not-found]  # noqa: PLC0415
        except ImportError as exc:
            raise ASRBackendUnavailableError(
                backend="cloud:litellm",
                detail="litellm is not installed",
            ) from exc
        # Real call shape: litellm.audio_transcriptions.create(...)
        # — exact mapping lives in `apps/api/.../llm_gateway` (Phase 7
        # finishes the wiring). For Phase 5 we don't exercise this path
        # in CI; the capability test asserts it cannot be constructed
        # without the env var.
        del litellm, audio, sample_rate_hz  # placeholders
        raise ASRBackendUnavailableError(
            backend="cloud:litellm",
            detail="cloud transcription is wired in Phase 7",
        )


# ─── Stub backend (tests) ──────────────────────────────────────


def _stub_transcript(audio: bytes) -> tuple[str, list[ASRToken], float]:
    r"""Build a deterministic stub transcript from `audio` bytes.

    The stub avoids any model dependency: it returns a fixed three-word
    French sentence with a deterministic confidence keyed on the audio
    prefix. Bytes starting with ``\x00\x00`` produce low confidence so
    the insufficient-data gate is testable; anything else is high.
    """
    conf = 0.30 if audio.startswith(b"\x00\x00") else 0.85
    text = "bonjour le monde"
    words = text.split()
    tokens = [
        ASRToken(text=w, start_s=i * 0.4, end_s=(i + 1) * 0.4, confidence=conf)
        for i, w in enumerate(words)
    ]
    return text, tokens, conf


class StubASRBackend:
    """Deterministic, dependency-free ASR for tests."""

    name: ClassVar[str] = "stub"

    def transcribe(self, audio: bytes, *, sample_rate_hz: int) -> ASRResult:
        """Return a fixed three-word French transcript with a deterministic confidence."""
        text, tokens, conf = _stub_transcript(audio)
        # PCM16 mono → bytes / (2 * sample_rate) seconds.
        duration = len(audio) / (2 * max(sample_rate_hz, 1)) if audio else 0.0
        return ASRResult(
            transcript=text,
            tokens=tuple(tokens),
            mean_confidence=conf,
            language="fr",
            duration_s=duration,
        )


__all__ = [
    "WHISPER_MODEL_ID",
    "CloudLiteLLMASRBackend",
    "LocalWhisperBackend",
    "StubASRBackend",
]
