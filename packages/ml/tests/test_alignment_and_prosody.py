"""MFA + prosody tests (Phase 5 step 6).

The stub MFA aligner is deterministic — slices the audio uniformly
across the transcript characters. The prosody analyzers (`pause`,
`pitch`, `analyze`) consume those outputs and produce a typed
`PronunciationProsody`. The real Whisper + MFA paths are deferred to
the §17 step 14 quality gates with `make install-models`.
"""

from __future__ import annotations

import pytest
from tcf_accel.errors import ASRBackendUnavailableError
from tcf_accel.schemas.pronunciation import PronunciationProsody
from tcf_accel_ml.alignment import LocalMFAAligner, StubMFAAligner, get_mfa_aligner
from tcf_accel_ml.alignment.mfa import PhonemeAlignment
from tcf_accel_ml.asr import StubASRBackend
from tcf_accel_ml.prosody import (
    analyze_prosody,
    detect_pauses,
    pitch_range_hz,
    speech_rate_wpm,
    summarize_pauses,
)
from tcf_accel_ml.prosody.pause import PAUSE_THRESHOLD_S, Pause

# ─── Stub MFA aligner ──────────────────────────────────────────


def test_stub_aligner_emits_one_alignment_per_non_space_char() -> None:
    aligner = StubMFAAligner()
    out = aligner.align(b"\xff" * 32_000, transcript="ab cd", sample_rate_hz=16_000)
    assert [a.phoneme for a in out] == ["a", "b", "c", "d"]


def test_stub_aligner_uniform_time_slicing() -> None:
    aligner = StubMFAAligner()
    # 1 second of audio, transcript "abcd" → 0.25 s per phoneme.
    out = aligner.align(b"\xff" * 32_000, transcript="abcd", sample_rate_hz=16_000)
    assert out[0].start_s == pytest.approx(0.0)
    assert out[0].end_s == pytest.approx(0.25, abs=1e-3)
    assert out[-1].end_s == pytest.approx(1.0, abs=1e-3)


def test_stub_aligner_low_confidence_for_zero_prefix() -> None:
    aligner = StubMFAAligner()
    out = aligner.align(b"\x00\x00" + b"\xff" * 100, transcript="abc", sample_rate_hz=16_000)
    assert all(a.confidence < 0.60 for a in out)


def test_stub_aligner_empty_transcript_returns_empty() -> None:
    assert StubMFAAligner().align(b"\xff" * 100, transcript="   ", sample_rate_hz=16_000) == []


# ─── Local MFA aligner refuses cleanly without the binary ──────


def test_local_aligner_raises_when_mfa_missing() -> None:
    aligner = LocalMFAAligner()
    with pytest.raises(ASRBackendUnavailableError) as info:
        aligner.align(b"\xff" * 100, transcript="abc", sample_rate_hz=16_000)
    assert info.value.code == "E_ASR_001"


def test_aligner_dispatch_default_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TCF_ACCEL_MFA_BACKEND", raising=False)
    assert get_mfa_aligner().name == "local"


def test_aligner_dispatch_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "stub")
    assert get_mfa_aligner().name == "stub"


def test_aligner_dispatch_unknown_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TCF_ACCEL_MFA_BACKEND", "kaldi-online")
    with pytest.raises(ValueError, match="Unknown"):
        get_mfa_aligner()


# ─── Pause detection ───────────────────────────────────────────


def _a(p: str, start: float, end: float, conf: float = 0.95) -> PhonemeAlignment:
    return PhonemeAlignment(phoneme=p, start_s=start, end_s=end, confidence=conf)


def test_detect_pauses_finds_gap_above_threshold() -> None:
    aligns = [_a("a", 0.0, 0.5), _a("b", 0.8, 1.0)]  # 0.3 s gap
    pauses = detect_pauses(aligns)
    assert len(pauses) == 1
    assert pauses[0].duration_s == pytest.approx(0.3, abs=1e-9)


def test_detect_pauses_ignores_sub_threshold_gaps() -> None:
    aligns = [_a("a", 0.0, 0.5), _a("b", 0.6, 1.0)]  # 0.1 s gap, under 0.2 s
    assert detect_pauses(aligns) == []


def test_detect_pauses_no_pauses_on_contiguous_alignment() -> None:
    aligns = [_a("a", 0.0, 0.5), _a("b", 0.5, 1.0), _a("c", 1.0, 1.5)]
    assert detect_pauses(aligns) == []


def test_pause_threshold_is_200ms() -> None:
    assert pytest.approx(0.200) == PAUSE_THRESHOLD_S


def test_summarize_pauses_returns_zero_for_empty() -> None:
    assert summarize_pauses([]) == (0, 0.0)


def test_summarize_pauses_mean_in_ms() -> None:
    pauses = [Pause(0.0, 0.3), Pause(1.0, 1.5)]  # 300 ms, 500 ms → mean 400 ms
    count, mean_ms = summarize_pauses(pauses)
    assert count == 2
    assert mean_ms == pytest.approx(400.0)


# ─── speech_rate_wpm ───────────────────────────────────────────


def test_speech_rate_three_words_per_second_is_180_wpm() -> None:
    assert speech_rate_wpm("bonjour le monde", 1.0) == pytest.approx(180.0)


def test_speech_rate_zero_duration_returns_zero() -> None:
    assert speech_rate_wpm("anything", 0.0) == 0.0


def test_speech_rate_empty_transcript_returns_zero() -> None:
    assert speech_rate_wpm("", 1.0) == 0.0


# ─── pitch_range_hz: graceful zero without librosa ─────────────


def test_pitch_returns_zero_when_librosa_unavailable() -> None:
    # In a clean test venv librosa is absent → must return 0.0
    # rather than raise. The PronunciationSignal gate handles the rest.
    assert pitch_range_hz(b"\xff" * 1000, sample_rate_hz=16_000) == 0.0


def test_pitch_returns_zero_for_empty_audio() -> None:
    assert pitch_range_hz(b"", sample_rate_hz=16_000) == 0.0


# ─── End-to-end (stubs): analyze_prosody composes cleanly ──────


def test_analyze_prosody_with_stub_backends() -> None:
    asr = StubASRBackend().transcribe(b"\xff" * 32_000, sample_rate_hz=16_000)
    aligns = StubMFAAligner().align(
        b"\xff" * 32_000,
        transcript=asr.transcript,
        sample_rate_hz=16_000,
    )
    prosody = analyze_prosody(
        audio=b"\xff" * 32_000,
        sample_rate_hz=16_000,
        asr=asr,
        alignments=aligns,
    )
    assert isinstance(prosody, PronunciationProsody)
    assert prosody.speech_rate_wpm > 0.0  # 3 words / 1 s → 180 wpm
    assert prosody.pause_count == 0  # uniform alignment has no gaps
    assert prosody.pitch_range_hz == 0.0  # librosa unavailable in CI
    assert prosody.mean_pause_ms == 0.0


def test_analyze_prosody_detects_pauses_when_alignments_have_gaps() -> None:
    asr = StubASRBackend().transcribe(b"\xff" * 32_000, sample_rate_hz=16_000)
    # Hand-craft alignments with a 300 ms gap between phonemes.
    aligns = [
        PhonemeAlignment(phoneme="a", start_s=0.0, end_s=0.4, confidence=0.9),
        PhonemeAlignment(phoneme="b", start_s=0.7, end_s=1.0, confidence=0.9),
    ]
    prosody = analyze_prosody(
        audio=b"\xff" * 32_000,
        sample_rate_hz=16_000,
        asr=asr,
        alignments=aligns,
    )
    assert prosody.pause_count == 1
    assert prosody.mean_pause_ms == pytest.approx(300.0, abs=1e-6)
