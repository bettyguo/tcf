"""ASR backend tests (Phase 5 step 6).

The stub backend is deterministic; the local backend lazy-loads (we
don't exercise the real weights here). The capability behavior the
ADR-017 / phase5_audit §9 contract relies on: constructing
`CloudLiteLLMASRBackend` without the env var raises.
"""

from __future__ import annotations

import os

import pytest
from tcf_accel.errors import ASRBackendUnavailableError
from tcf_accel_ml.asr import (
    CloudLiteLLMASRBackend,
    LocalWhisperBackend,
    StubASRBackend,
    get_asr_backend,
)
from tcf_accel_ml.asr.backend import EXPECTED_SAMPLE_RATE_HZ

# ─── Stub backend ──────────────────────────────────────────────


def test_stub_backend_is_deterministic() -> None:
    backend = StubASRBackend()
    audio = b"\x10\x20" * 16_000  # 1 s of PCM16 mono at 16 kHz
    a = backend.transcribe(audio, sample_rate_hz=16_000)
    b = backend.transcribe(audio, sample_rate_hz=16_000)
    assert a == b
    assert a.transcript == "bonjour le monde"
    assert a.language == "fr"
    assert a.duration_s == pytest.approx(1.0, abs=1e-3)


def test_stub_backend_high_confidence_for_normal_audio() -> None:
    backend = StubASRBackend()
    result = backend.transcribe(b"\xff\xff" * 16_000, sample_rate_hz=16_000)
    assert result.mean_confidence >= 0.50
    assert len(result.tokens) == 3
    assert all(t.confidence == result.mean_confidence for t in result.tokens)


def test_stub_backend_low_confidence_for_zero_prefix_audio() -> None:
    # Bytes starting with \x00\x00 → low confidence path used by the
    # insufficient-data gate tests downstream.
    backend = StubASRBackend()
    result = backend.transcribe(b"\x00\x00" + b"\xff" * 100, sample_rate_hz=16_000)
    assert result.mean_confidence < 0.50


def test_stub_backend_empty_audio_zero_duration() -> None:
    result = StubASRBackend().transcribe(b"", sample_rate_hz=16_000)
    assert result.duration_s == 0.0


# ─── Local backend lazy behavior ───────────────────────────────


def test_local_backend_constructs_without_model_load() -> None:
    # Construction must not touch the filesystem / network. If it
    # did, this test would fail in a clean venv with no model cache.
    backend = LocalWhisperBackend()
    assert backend.name == "local"
    assert backend._model is None


def test_local_backend_raises_unavailable_when_dependencies_missing() -> None:
    # Without faster-whisper installed (or a model cache), transcribe
    # must raise the typed error the API layer maps to E_ASR_001 (503).
    backend = LocalWhisperBackend()
    with pytest.raises(ASRBackendUnavailableError) as info:
        backend.transcribe(b"\x10\x20" * 100, sample_rate_hz=16_000)
    assert info.value.code == "E_ASR_001"


# ─── Cloud backend: constructible only with the env var ────────


def test_cloud_backend_refuses_without_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TCF_ACCEL_ASR_BACKEND", raising=False)
    with pytest.raises(RuntimeError, match="cloud:litellm"):
        CloudLiteLLMASRBackend()


def test_cloud_backend_constructs_with_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "cloud:litellm")
    backend = CloudLiteLLMASRBackend()
    assert backend.name == "cloud:litellm"


# ─── Dispatch ──────────────────────────────────────────────────


def test_dispatch_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TCF_ACCEL_ASR_BACKEND", raising=False)
    assert get_asr_backend().name == "local"


def test_dispatch_selects_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "stub")
    assert get_asr_backend().name == "stub"


def test_dispatch_unknown_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_ASR_BACKEND", "openai-whisper-3-online")
    with pytest.raises(ValueError, match="Unknown"):
        get_asr_backend()


# ─── Sanity: expected sample rate constant ─────────────────────


def test_expected_sample_rate_is_16khz() -> None:
    assert EXPECTED_SAMPLE_RATE_HZ == 16_000


# ─── Module-level capability check ─────────────────────────────


def test_module_imports_without_heavy_deps() -> None:
    # The package must import in a clean venv (faster-whisper, librosa,
    # mfa are *not* required at import time). Re-importing here is a
    # smoke test against accidental top-level imports.
    import importlib  # noqa: PLC0415

    import tcf_accel_ml.asr  # noqa: PLC0415
    import tcf_accel_ml.asr.backend  # noqa: PLC0415
    import tcf_accel_ml.asr.whisper_fr  # noqa: PLC0415

    importlib.reload(tcf_accel_ml.asr.whisper_fr)
    importlib.reload(tcf_accel_ml.asr)


# ─── Sanity: default env-var value is one of the documented values ──


def test_env_var_default_is_recognized() -> None:
    # If `TCF_ACCEL_ASR_BACKEND` is set in the ambient environment for
    # this test process, it must be one of the documented values; the
    # default (unset) resolves to "local".
    assert os.environ.get("TCF_ACCEL_ASR_BACKEND", "local") in {
        "local",
        "stub",
        "cloud:litellm",
    }
