"""Property tests for the `PronunciationSignal` contract (ADR-031).

These are the structural guarantees the audit gate
(`phase5_audit.md §8`) relies on:

1. Every `PronunciationSignal` constructed via the factory carries
   `signal_kind="coarse_proxy"` and a non-empty `disclaimer_version`.
2. `display_label="insufficient_data"` implies the score is, in
   spirit, ignorable — the property holds when any of the gate's
   three predicates is violated.
3. The score field complements PER (clipped at 0).
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from tcf_accel.schemas.pronunciation import (
    PronunciationDisplayLabel,
    PronunciationProsody,
    PronunciationSignal,
)
from tcf_accel_ml.asr.backend import ASRResult
from tcf_accel_ml.pronunciation import (
    INSUFFICIENT_ASR_CONFIDENCE,
    INSUFFICIENT_DURATION_S,
    INSUFFICIENT_PHONEMES,
    build_signal,
    display_label_from,
)


def _prosody() -> PronunciationProsody:
    return PronunciationProsody(
        pitch_range_hz=100.0,
        speech_rate_wpm=120.0,
        pause_count=0,
        mean_pause_ms=0.0,
    )


@st.composite
def _asr_result(draw: st.DrawFn) -> ASRResult:
    return ASRResult(
        transcript=draw(st.text(min_size=1, max_size=80)),
        tokens=(),
        mean_confidence=draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        ),
        language="fr",
        duration_s=draw(
            st.floats(min_value=0.0, max_value=120.0, allow_nan=False, allow_infinity=False),
        ),
    )


@given(_asr_result())
def test_every_factory_signal_is_coarse_proxy(asr: ASRResult) -> None:
    """Property: the factory NEVER emits a signal whose kind isn't 'coarse_proxy'."""
    sig = build_signal(asr=asr, alignments=[], prosody=_prosody())
    assert sig.signal_kind == "coarse_proxy"
    assert sig.disclaimer_version  # non-empty


@given(_asr_result())
def test_display_label_is_in_documented_set(asr: ASRResult) -> None:
    """Property: `display_label` is one of the four documented values."""
    sig = build_signal(asr=asr, alignments=[], prosody=_prosody())
    assert sig.display_label in {"weak", "fair", "strong", "insufficient_data"}


@given(_asr_result())
def test_insufficient_data_when_any_predicate_fails(asr: ASRResult) -> None:
    """Property: the gate routes to 'insufficient_data' whenever ANY predicate fails.

    The factory derives `n_phonemes_aligned` from the reference when
    alignments are absent; we use a transcript whose length we know to
    test the duration/confidence predicates explicitly.
    """
    sig = build_signal(asr=asr, alignments=[], prosody=_prosody())
    too_short = sig.duration_s < INSUFFICIENT_DURATION_S
    low_conf = sig.asr_mean_confidence < INSUFFICIENT_ASR_CONFIDENCE
    few_phon = sig.n_phonemes_aligned < INSUFFICIENT_PHONEMES
    if too_short or low_conf or few_phon:
        assert sig.display_label == "insufficient_data"


@given(_asr_result())
def test_score_is_clipped_one_minus_per(asr: ASRResult) -> None:
    """Property: `score = max(0, 1 - per)`. The score never goes negative."""
    sig = build_signal(asr=asr, alignments=[], prosody=_prosody())
    assert 0.0 <= sig.score <= 1.0
    expected = max(0.0, 1.0 - sig.per)
    assert abs(sig.score - expected) < 1e-9


@given(
    per=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    conf=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    dur=st.floats(min_value=0.0, max_value=120.0, allow_nan=False, allow_infinity=False),
    n_phon=st.integers(min_value=0, max_value=300),
)
def test_gate_pure_function_property(
    per: float, conf: float, dur: float, n_phon: int,
) -> None:
    """Property: the gate is a pure mapping from the four signals."""
    label: PronunciationDisplayLabel = display_label_from(
        per=per,
        asr_mean_confidence=conf,
        duration_s=dur,
        n_phonemes_aligned=n_phon,
    )
    assert label in {"weak", "fair", "strong", "insufficient_data"}
    # The gate is monotone in PER over the "sufficient" regime.
    if (
        dur >= INSUFFICIENT_DURATION_S
        and conf >= INSUFFICIENT_ASR_CONFIDENCE
        and n_phon >= INSUFFICIENT_PHONEMES
    ):
        # Strong → PER < 0.10; weak → PER ≥ 0.20.
        if label == "strong":
            assert per < 0.10
        if label == "weak":
            assert per >= 0.20


def test_signal_kind_literal_is_load_bearing() -> None:
    """Removing or changing `signal_kind="coarse_proxy"` breaks the contract."""
    import pytest  # noqa: PLC0415
    from pydantic import ValidationError  # noqa: PLC0415

    # The literal type is enforced at validation time. Any value other
    # than the exact string "coarse_proxy" is rejected.
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


def test_disclaimer_version_required() -> None:
    """An empty disclaimer must fail validation (ADR-031)."""
    import pytest  # noqa: PLC0415
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        PronunciationSignal(
            score=0.5,
            disclaimer_version="",  # min_length=1
            display_label="fair",
            per=0.2,
            asr_mean_confidence=0.8,
            n_phonemes_aligned=20,
            duration_s=5.0,
            prosody=_prosody(),
        )
