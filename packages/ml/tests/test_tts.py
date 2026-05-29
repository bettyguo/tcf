"""TTS backend tests (Phase 5 step 9).

Stub backend is deterministic; the local XTTS backend lazy-loads (no
weights exercised here). Dispatch via `TCF_ACCEL_TTS_BACKEND`.
"""

from __future__ import annotations

import pytest
from tcf_accel.errors import TTSBackendUnavailableError
from tcf_accel_ml.tts import (
    LocalXTTSBackend,
    StubTTSBackend,
    TTSResult,
    get_tts_backend,
)
from tcf_accel_ml.tts.xtts import TTS_OUTPUT_SAMPLE_RATE_HZ

# ─── Stub backend ──────────────────────────────────────────────


def test_stub_emits_pcm16_silence_for_text() -> None:
    backend = StubTTSBackend()
    out = backend.synthesize("Bonjour, c'est l'examinateur.")
    assert isinstance(out, TTSResult)
    assert out.sample_rate_hz == TTS_OUTPUT_SAMPLE_RATE_HZ
    assert out.duration_s > 0.0
    assert len(out.audio) == int(out.duration_s * out.sample_rate_hz) * 2  # PCM16
    # Silence buffer: all zero bytes.
    assert set(out.audio) == {0}


def test_stub_empty_text_zero_duration() -> None:
    out = StubTTSBackend().synthesize("")
    assert out.duration_s == 0.0
    assert out.audio == b""


def test_stub_cache_key_changes_with_text() -> None:
    a = StubTTSBackend().synthesize("Phrase A")
    b = StubTTSBackend().synthesize("Phrase B")
    assert a.cache_key != b.cache_key


def test_stub_cache_key_changes_with_voice() -> None:
    a = StubTTSBackend().synthesize("Bonjour", voice_id="examiner")
    b = StubTTSBackend().synthesize("Bonjour", voice_id="other")
    assert a.cache_key != b.cache_key


def test_stub_is_deterministic() -> None:
    a = StubTTSBackend().synthesize("Bonjour")
    b = StubTTSBackend().synthesize("Bonjour")
    assert a == b


# ─── Local backend lazy behavior ───────────────────────────────


def test_local_backend_constructs_without_model_load() -> None:
    backend = LocalXTTSBackend()
    assert backend.name == "local"
    assert backend._model is None


def test_local_backend_raises_unavailable_when_deps_missing() -> None:
    # Without the Coqui TTS package installed, synthesize must raise
    # the typed error the API layer maps to E_TTS_001 (503).
    backend = LocalXTTSBackend()
    with pytest.raises(TTSBackendUnavailableError) as info:
        backend.synthesize("test")
    assert info.value.code == "E_TTS_001"


# ─── Dispatch ──────────────────────────────────────────────────


def test_dispatch_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TCF_ACCEL_TTS_BACKEND", raising=False)
    assert get_tts_backend().name == "local"


def test_dispatch_selects_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_TTS_BACKEND", "stub")
    assert get_tts_backend().name == "stub"


def test_dispatch_unknown_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_TTS_BACKEND", "cloud:openai")
    with pytest.raises(ValueError, match="Unknown"):
        get_tts_backend()
