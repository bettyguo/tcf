"""Phase 5 schema round-trip + additivity tests (SCHEMA_VERSION 0.4.0).

Covers the new types (`PronunciationSignal`, `PronunciationProsody`,
`AccessibilityProfile`, `DismissalLogEntry`) and the additive
`Interaction` fields (`drill_kind`, `pronunciation`, `audio_path`).

The downgrade-safety test asserts that a Phase 5 `Interaction` written
*without* the new fields parses identically to a Phase-4-era row — i.e.
the bump is additive and a Phase 4 consumer is not broken.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from tcf_accel.schemas import (
    AccessibilityProfile,
    DismissalLogEntry,
    Interaction,
    PronunciationProsody,
    PronunciationSignal,
)
from tcf_accel.schemas.api.plan import DrillKind

_DISPLAY_LABELS = ["weak", "fair", "strong", "insufficient_data"]
# DrillKind is a typing.Literal; its values live in __args__.
_DRILL_KINDS: list[str] = list(DrillKind.__args__)  # type: ignore[attr-defined]
_MODULES = ["CO", "CE", "EE", "EO"]


# ─── PronunciationProsody / PronunciationSignal ────────────────


@st.composite
def _prosody(draw: st.DrawFn) -> PronunciationProsody:
    return PronunciationProsody(
        pitch_range_hz=draw(
            st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False)
        ),
        speech_rate_wpm=draw(
            st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False)
        ),
        pause_count=draw(st.integers(min_value=0, max_value=50)),
        mean_pause_ms=draw(
            st.floats(min_value=0.0, max_value=5000.0, allow_nan=False, allow_infinity=False)
        ),
    )


@st.composite
def _pron_signal(draw: st.DrawFn) -> PronunciationSignal:
    return PronunciationSignal(
        score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        disclaimer_version=draw(st.sampled_from(["v1.0", "v1.1", "v2.0"])),
        display_label=draw(st.sampled_from(_DISPLAY_LABELS)),  # type: ignore[arg-type]
        per=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        asr_mean_confidence=draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        ),
        n_phonemes_aligned=draw(st.integers(min_value=0, max_value=400)),
        duration_s=draw(
            st.floats(min_value=0.0, max_value=600.0, allow_nan=False, allow_infinity=False)
        ),
        prosody=draw(_prosody()),
    )


@given(_pron_signal())
def test_pronunciation_signal_json_roundtrip(sig: PronunciationSignal) -> None:
    reparsed = PronunciationSignal.model_validate_json(sig.model_dump_json())
    assert reparsed == sig


@given(_pron_signal())
def test_pronunciation_signal_always_coarse_proxy(sig: PronunciationSignal) -> None:
    # ADR-031: signal_kind is a load-bearing literal; never anything else.
    assert sig.signal_kind == "coarse_proxy"


def test_pronunciation_signal_rejects_empty_disclaimer() -> None:
    with pytest.raises(ValidationError):
        PronunciationSignal(
            score=0.5,
            disclaimer_version="",  # min_length=1 must reject
            display_label="fair",
            per=0.2,
            asr_mean_confidence=0.8,
            n_phonemes_aligned=20,
            duration_s=5.0,
            prosody=PronunciationProsody(
                pitch_range_hz=100.0,
                speech_rate_wpm=120.0,
                pause_count=0,
                mean_pause_ms=0.0,
            ),
        )


def test_pronunciation_signal_rejects_signal_kind_override() -> None:
    # The only permitted literal is "coarse_proxy"; anything else is rejected.
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
            prosody=PronunciationProsody(
                pitch_range_hz=100.0,
                speech_rate_wpm=120.0,
                pause_count=0,
                mean_pause_ms=0.0,
            ),
        )


def test_pronunciation_signal_is_frozen() -> None:
    sig = PronunciationSignal(
        score=0.5,
        disclaimer_version="v1.0",
        display_label="fair",
        per=0.2,
        asr_mean_confidence=0.8,
        n_phonemes_aligned=20,
        duration_s=5.0,
        prosody=PronunciationProsody(
            pitch_range_hz=100.0,
            speech_rate_wpm=120.0,
            pause_count=0,
            mean_pause_ms=0.0,
        ),
    )
    with pytest.raises(ValidationError):
        sig.score = 0.9  # type: ignore[misc]


# ─── AccessibilityProfile ──────────────────────────────────────


def test_accessibility_profile_defaults_are_none() -> None:
    p = AccessibilityProfile()
    assert p.co_alternative == "none"
    assert p.ee_alternative == "none"
    assert p.eo_alternative == "none"
    assert p.dyslexia_font is False
    assert p.high_contrast is False


def test_accessibility_profile_roundtrip() -> None:
    p = AccessibilityProfile(
        co_alternative="lexical_alt",
        ee_alternative="speech_to_text",
        eo_alternative="text_input",
        dyslexia_font=True,
        high_contrast=True,
    )
    assert AccessibilityProfile.model_validate_json(p.model_dump_json()) == p


# ─── DismissalLogEntry ─────────────────────────────────────────


def test_dismissal_log_entry_roundtrip() -> None:
    e = DismissalLogEntry(
        user_id=uuid4(),
        dismissed_at=datetime(2026, 5, 28, tzinfo=UTC),
        week_iso="2026-W22",
        reason="travelling this week",
    )
    assert DismissalLogEntry.model_validate_json(e.model_dump_json()) == e


# ─── Interaction additive fields ───────────────────────────────


@st.composite
def _interaction(draw: st.DrawFn, *, with_phase5_fields: bool) -> Interaction:
    base = {
        "user_id": uuid4(),
        "item_id": uuid4(),
        "session_id": uuid4(),
        "module": draw(st.sampled_from(_MODULES)),
        "correct": draw(st.one_of(st.none(), st.booleans())),
        "raw_response": {"option_id": "o1"},
        "rt_ms": draw(st.one_of(st.none(), st.integers(min_value=0, max_value=600_000))),
        "rating": draw(st.one_of(st.none(), st.integers(min_value=1, max_value=4))),
        "created_at": datetime(2026, 1, 1, tzinfo=UTC)
        + timedelta(seconds=draw(st.integers(min_value=0, max_value=10_000_000))),
    }
    if with_phase5_fields:
        base["drill_kind"] = draw(st.sampled_from(_DRILL_KINDS))
        base["audio_path"] = draw(st.one_of(st.none(), st.just("audio/abc123.wav")))
        base["pronunciation"] = draw(st.one_of(st.none(), _pron_signal()))
    return Interaction.model_validate(base)


@given(_interaction(with_phase5_fields=True))
def test_interaction_with_phase5_fields_roundtrips(i: Interaction) -> None:
    assert Interaction.model_validate_json(i.model_dump_json()) == i


@given(_interaction(with_phase5_fields=False))
def test_interaction_without_phase5_fields_defaults_none(i: Interaction) -> None:
    # A Phase-4-era row (no new fields) parses with the new fields as None.
    assert i.drill_kind is None
    assert i.pronunciation is None
    assert i.audio_path is None


def test_interaction_downgrade_safe_phase4_consumer() -> None:
    """A Phase 5 Interaction serialized with the new fields set still
    carries the full Phase 4 field set, so a Phase 4 consumer that
    ignores unknown keys reads the legacy fields unchanged."""
    i = Interaction(
        user_id=uuid4(),
        item_id=uuid4(),
        session_id=uuid4(),
        module="CO",
        correct=True,
        raw_response={"option_id": "o2"},
        rt_ms=4200,
        rating=3,
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
        drill_kind="co_mcq",
        audio_path=None,
    )
    dumped = i.model_dump(mode="json")
    # The Phase 4 field set is fully present.
    for legacy_field in (
        "user_id",
        "item_id",
        "session_id",
        "module",
        "correct",
        "raw_response",
        "rt_ms",
        "rating",
        "created_at",
    ):
        assert legacy_field in dumped
    # The new fields are present but null/optional — additive, not breaking.
    assert dumped["drill_kind"] == "co_mcq"
    assert dumped["pronunciation"] is None
    assert dumped["audio_path"] is None


def test_drillkind_has_all_kinds_plus_reserved() -> None:
    # 22 implementable kinds (the §4.5 table's 21 + `eo_text_alt`, the EO
    # accessibility alternative from §7.2) + mock_section + diagnostic_item.
    assert len(_DRILL_KINDS) == 24
    assert len(set(_DRILL_KINDS)) == len(_DRILL_KINDS), "DrillKind values must be unique"
    for required in (
        "co_mcq",
        "co_lexical_alt",  # CO accessibility alt (ADR-029)
        "eo_text_alt",  # EO accessibility alt (§7.2)
        "eo_repair",
        "mock_section",  # reserved for Phase 6
        "diagnostic_item",  # reserved for Phase 4 CAT
    ):
        assert required in _DRILL_KINDS
