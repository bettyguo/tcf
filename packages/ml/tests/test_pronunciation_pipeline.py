"""Pronunciation pipeline tests (Phase 5 step 7, ADR-031).

Covers:
- `phoneme_error_rate` — Levenshtein over phoneme sequences.
- `display_label_from` — the insufficient-data gate.
- `build_signal` — the factory composing PER + gate + prosody into
  a `PronunciationSignal` carrying the structural contract.
"""

from __future__ import annotations

import pytest
from tcf_accel.schemas.pronunciation import PronunciationProsody, PronunciationSignal
from tcf_accel_ml.alignment import StubMFAAligner
from tcf_accel_ml.asr import StubASRBackend
from tcf_accel_ml.asr.backend import ASRResult
from tcf_accel_ml.pronunciation import (
    DISCLAIMER_VERSION,
    DISPLAY_LABEL_PER_FAIR,
    DISPLAY_LABEL_PER_STRONG,
    INSUFFICIENT_ASR_CONFIDENCE,
    INSUFFICIENT_DURATION_S,
    INSUFFICIENT_PHONEMES,
    build_signal,
    display_label_from,
    phoneme_error_rate,
    reference_phonemes,
)

# ─── Phoneme Error Rate ────────────────────────────────────────


def test_per_identical_sequences_is_zero() -> None:
    assert phoneme_error_rate(["a", "b", "c"], ["a", "b", "c"]) == 0.0


def test_per_one_substitution() -> None:
    # 1 sub / 3 reference phonemes.
    assert phoneme_error_rate(["a", "b", "c"], ["a", "x", "c"]) == pytest.approx(1.0 / 3.0)


def test_per_insertion() -> None:
    # 1 insertion / 2 reference phonemes.
    assert phoneme_error_rate(["a", "b"], ["a", "b", "c"]) == 0.5


def test_per_deletion() -> None:
    # 1 deletion / 3 reference phonemes.
    assert phoneme_error_rate(["a", "b", "c"], ["a", "c"]) == pytest.approx(1.0 / 3.0)


def test_per_empty_reference_with_non_empty_hyp_is_one() -> None:
    assert phoneme_error_rate([], ["a"]) == 1.0


def test_per_both_empty_is_zero() -> None:
    assert phoneme_error_rate([], []) == 0.0


def test_per_completely_different_can_exceed_one() -> None:
    # Hypothesis longer than reference with no overlap: ratio > 1 is valid.
    per = phoneme_error_rate(["a"], ["x", "y", "z"])
    assert per >= 1.0


# ─── insufficient-data gate (display_label_from) ───────────────


def _ok_kwargs(**overrides: object) -> dict[str, object]:
    base = {
        "per": 0.05,
        "asr_mean_confidence": 0.90,
        "duration_s": 10.0,
        "n_phonemes_aligned": 30,
    }
    base.update(overrides)
    return base


def test_label_strong_when_per_under_strong_threshold() -> None:
    assert display_label_from(**_ok_kwargs(per=0.05)) == "strong"  # type: ignore[arg-type]


def test_label_fair_when_per_between_strong_and_fair() -> None:
    assert display_label_from(**_ok_kwargs(per=0.15)) == "fair"  # type: ignore[arg-type]


def test_label_weak_when_per_above_fair_threshold() -> None:
    assert display_label_from(**_ok_kwargs(per=0.30)) == "weak"  # type: ignore[arg-type]


def test_label_insufficient_short_utterance() -> None:
    # Anything below 2.0 s → insufficient, regardless of PER.
    assert display_label_from(**_ok_kwargs(duration_s=1.5)) == "insufficient_data"  # type: ignore[arg-type]


def test_label_insufficient_low_asr_confidence() -> None:
    assert (
        display_label_from(**_ok_kwargs(asr_mean_confidence=0.40))  # type: ignore[arg-type]
        == "insufficient_data"
    )


def test_label_insufficient_too_few_phonemes() -> None:
    assert (
        display_label_from(**_ok_kwargs(n_phonemes_aligned=4))  # type: ignore[arg-type]
        == "insufficient_data"
    )


def test_label_threshold_values_are_loadbearing() -> None:
    # The exact numbers are tunable per release, but the *gate* must
    # exist (ADR-031). Pin the current values so a quiet change to
    # the constants requires this test to be updated explicitly.
    assert INSUFFICIENT_DURATION_S == 2.0
    assert INSUFFICIENT_ASR_CONFIDENCE == 0.50
    assert INSUFFICIENT_PHONEMES == 8
    assert DISPLAY_LABEL_PER_STRONG == 0.10
    assert DISPLAY_LABEL_PER_FAIR == 0.20


# ─── reference_phonemes ────────────────────────────────────────


def test_reference_phonemes_strips_whitespace() -> None:
    assert reference_phonemes("ab cd") == ["a", "b", "c", "d"]


def test_reference_phonemes_keeps_unicode() -> None:
    # The stub reference is the literal characters of the transcript,
    # including accented ones. PER is alphabet-agnostic.
    assert reference_phonemes("été") == ["é", "t", "é"]


# ─── build_signal: composing the pipeline ──────────────────────


def _asr(transcript: str, *, conf: float = 0.85, duration_s: float = 10.0) -> ASRResult:
    return ASRResult(
        transcript=transcript,
        tokens=(),
        mean_confidence=conf,
        language="fr",
        duration_s=duration_s,
    )


def _prosody() -> PronunciationProsody:
    return PronunciationProsody(
        pitch_range_hz=120.0,
        speech_rate_wpm=150.0,
        pause_count=0,
        mean_pause_ms=0.0,
    )


def test_build_signal_perfect_path_is_strong() -> None:
    # The stub-friendly path: ASR transcript matches the reference
    # exactly → PER 0 → score 1.0 → display_label "strong".
    transcript = "bonjour le monde un deux trois"
    asr = _asr(transcript)
    aligns = StubMFAAligner().align(b"\xff" * 32_000, transcript=transcript, sample_rate_hz=16_000)
    sig = build_signal(asr=asr, alignments=aligns, prosody=_prosody())
    assert sig.display_label == "strong"
    assert sig.per == 0.0
    assert sig.score == 1.0


def test_build_signal_short_utterance_is_insufficient() -> None:
    # Identical reference but the utterance is too short — the gate
    # must dominate (`phase5_audit.md §8`: insufficient-data ⇒
    # planner ignores the row's score contribution).
    transcript = "bonjour le monde"
    asr = _asr(transcript, duration_s=1.0)
    sig = build_signal(asr=asr, alignments=[], prosody=_prosody())
    assert sig.display_label == "insufficient_data"


def test_build_signal_low_asr_confidence_is_insufficient() -> None:
    transcript = "bonjour le monde un deux trois"
    asr = _asr(transcript, conf=0.30)
    aligns = StubMFAAligner().align(b"\xff" * 32_000, transcript=transcript, sample_rate_hz=16_000)
    sig = build_signal(asr=asr, alignments=aligns, prosody=_prosody())
    assert sig.display_label == "insufficient_data"


def test_build_signal_carries_required_contract() -> None:
    # The load-bearing assertions from ADR-031: every signal MUST
    # carry `signal_kind="coarse_proxy"` and a non-empty disclaimer.
    asr = _asr("bonjour le monde un deux trois")
    sig = build_signal(asr=asr, alignments=[], prosody=_prosody())
    assert sig.signal_kind == "coarse_proxy"
    assert sig.disclaimer_version
    assert sig.disclaimer_version == DISCLAIMER_VERSION


def test_build_signal_supplied_reference_used_over_stub() -> None:
    # When the caller supplies a reference (production: dictionary
    # lookup), the factory uses it instead of the stub derivation.
    asr = _asr("bonjour le monde un deux trois", conf=0.9)
    # Make the supplied reference DIFFERENT from the transcript so PER>0.
    custom_ref = list("xxxxxxxxxxxxxxxxxxxxxxxxxx")  # 26 chars, no overlap
    sig = build_signal(
        asr=asr,
        alignments=[],
        prosody=_prosody(),
        reference=custom_ref,
    )
    assert sig.per > 0.5  # nearly everything is wrong


def test_build_signal_score_complements_per() -> None:
    asr = _asr("bonjour le monde un deux trois")
    # Mismatched reference produces a non-zero PER.
    sig = build_signal(
        asr=asr,
        alignments=[],
        prosody=_prosody(),
        reference=list("bonjourleMORTun"),  # partial overlap
    )
    # score = max(0, 1 - per); since per>0, score<1.
    assert sig.score == pytest.approx(max(0.0, 1.0 - sig.per))


# ─── Structural contract: cannot be constructed wrongly ────────


def test_signal_rejects_bogus_signal_kind() -> None:
    # The literal "coarse_proxy" is the only permitted value (ADR-031).
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        PronunciationSignal(
            score=0.5,
            signal_kind="evaluative",  # type: ignore[arg-type]
            disclaimer_version="v1.0",
            display_label="fair",
            per=0.2,
            asr_mean_confidence=0.8,
            n_phonemes_aligned=20,
            duration_s=5.0,
            prosody=_prosody(),
        )


def test_signal_rejects_empty_disclaimer() -> None:
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        PronunciationSignal(
            score=0.5,
            disclaimer_version="",
            display_label="fair",
            per=0.2,
            asr_mean_confidence=0.8,
            n_phonemes_aligned=20,
            duration_s=5.0,
            prosody=_prosody(),
        )


# ─── End-to-end with the stub backends ─────────────────────────


def test_end_to_end_stubs_produce_a_valid_signal() -> None:
    audio = b"\xff" * 32_000  # 1 s @ 16 kHz, but we'll fudge duration via ASR
    asr_result = StubASRBackend().transcribe(audio, sample_rate_hz=16_000)
    # The stub ASR reports duration ~ 1 s; bump it via a fresh result
    # for the insufficient-data threshold (2 s).
    asr_bumped = ASRResult(
        transcript=asr_result.transcript,
        tokens=asr_result.tokens,
        mean_confidence=asr_result.mean_confidence,
        language=asr_result.language,
        duration_s=10.0,
    )
    aligns = StubMFAAligner().align(
        audio,
        transcript=asr_bumped.transcript,
        sample_rate_hz=16_000,
    )
    sig = build_signal(asr=asr_bumped, alignments=aligns, prosody=_prosody())
    assert isinstance(sig, PronunciationSignal)
    assert sig.signal_kind == "coarse_proxy"
    # With the stub transcript == stub reference → PER 0 → strong, BUT
    # n_phonemes_aligned must clear the floor (8). "bonjour le monde"
    # has 14 non-space chars, so the gate clears.
    assert sig.n_phonemes_aligned >= INSUFFICIENT_PHONEMES
    assert sig.display_label == "strong"
