"""Unit + perfect-agent tests for the pure-text CO supplementary drills.

Covers dictation (WER), gap-fill (per-gap exact match), and the
accessibility lexical alternative (ADR-029 routing invariant). The
shadowing and accent drills depend on the ML stack / 2-clip item
content and land in later §17 steps.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from tcf_accel.schemas.common import Provenance
from tcf_accel.schemas.content import MCQ, COContent, MCQOption, Speaker
from tcf_accel.schemas.item import Item
from tcf_accel_sla.drills import (
    CODictationDrill,
    COGapFillDrill,
    COLexicalAltDrill,
    get_drill,
)
from tcf_accel_sla.drills._text import word_error_rate

_TRANSCRIPT = "Le chat noir dort sur le tapis du salon."


def _co_item(transcript: str = _TRANSCRIPT) -> Item:
    return Item(
        id=uuid4(),
        module="CO",
        cefr_level="B1",
        content=COContent(
            transcript=transcript,
            duration_s=8.0,
            speakers=[Speaker(label="A", accent="fr-CA")],
            accent="fr-CA",
            register="standard",
            questions=[
                MCQ(
                    id="q1",
                    prompt="Qui est l'animal ?",
                    options=[
                        MCQOption(id="a", text="un chat"),
                        MCQOption(id="b", text="un chien"),
                        MCQOption(id="c", text="un oiseau"),
                        MCQOption(id="d", text="un poisson"),
                    ],
                    correct_option_id="a",
                ),
            ],
        ),
        provenance=Provenance(
            source="test",
            source_id="t",
            license="CC-BY-SA-4.0",
            ingested_at=datetime(2026, 5, 28, tzinfo=UTC),
            review_status="auto_passed",
        ),
    )


# ─── WER helper ────────────────────────────────────────────────


def test_wer_identical_strings_is_zero() -> None:
    assert word_error_rate("le chat dort", "le chat dort") == 0.0


def test_wer_accent_and_case_insensitive() -> None:
    # "Élève" vs "eleve" must not count as an error.
    assert word_error_rate("Élève attentif", "eleve attentif") == 0.0


def test_wer_one_substitution_in_three_words() -> None:
    # 1 sub / 3 reference words = 1/3.
    assert abs(word_error_rate("le chat dort", "le chien dort") - 1.0 / 3.0) < 1e-9


def test_wer_empty_reference_with_non_empty_hyp_is_one() -> None:
    assert word_error_rate("", "extra") == 1.0


# ─── co_dictation ──────────────────────────────────────────────


def test_dictation_perfect_transcription_is_correct() -> None:
    drill = CODictationDrill()
    item = _co_item()
    result = drill.grade(item, {"transcription": _TRANSCRIPT})
    assert result.correct is True
    assert result.raw_response["wer"] == 0.0
    assert result.partial_credit == 1.0


def test_dictation_one_word_off_still_correct_within_threshold() -> None:
    drill = CODictationDrill()
    item = _co_item()
    # Replace one word out of 9 → WER ≈ 0.111, under the 0.15 threshold.
    result = drill.grade(item, {"transcription": "Le chien noir dort sur le tapis du salon."})
    assert result.correct is True
    assert (
        "spelling" in result.raw_response["error_classes"]
        or "missing" in result.raw_response["error_classes"]
    )


def test_dictation_many_errors_fails() -> None:
    drill = CODictationDrill()
    item = _co_item()
    result = drill.grade(item, {"transcription": "le chien blanc joue dans la rue"})
    assert result.correct is False
    assert result.raw_response["wer"] > 0.15


def test_dictation_present_carries_reference_length() -> None:
    drill = CODictationDrill()
    item = _co_item()
    step = drill.present(item)
    assert step.single_play is True
    assert step.payload["n_reference_words"] == 9  # 9 words in _TRANSCRIPT


# ─── co_gapfill ────────────────────────────────────────────────


def test_gapfill_perfect_agent_all_gaps_correct() -> None:
    drill = COGapFillDrill()
    item = _co_item()
    step = drill.present(item)
    n_gaps = step.payload["n_gaps"]
    assert n_gaps >= 1

    # Derive the answer key by looking at the masked transcript:
    # the drill's _key picks every 3rd token. Reuse it to build a
    # perfect-agent response.
    answers, _ = drill._key(item)  # type: ignore[attr-defined]
    result = drill.grade(item, {"answers": answers})
    assert result.correct is True
    assert all(result.raw_response["per_gap_correct"])
    assert result.partial_credit == 1.0


def test_gapfill_partial_credit_for_some_correct() -> None:
    drill = COGapFillDrill()
    item = _co_item()
    answers, _ = drill._key(item)  # type: ignore[attr-defined]
    # Get exactly one wrong.
    wrong = answers[:]
    wrong[0] = "WRONG"
    result = drill.grade(item, {"answers": wrong})
    assert result.correct is False
    assert 0.0 < (result.partial_credit or 0.0) < 1.0


def test_gapfill_accent_insensitive() -> None:
    drill = COGapFillDrill()
    item = _co_item()
    answers, _ = drill._key(item)  # type: ignore[attr-defined]
    # Strip accents — must still grade as correct.
    relaxed = [a.replace("é", "e").replace("è", "e") for a in answers]
    result = drill.grade(item, {"answers": relaxed})
    assert result.correct is True


# ─── co_lexical_alt — ADR-029 routing invariant ────────────────


def test_lexical_alt_declares_module_ce() -> None:
    # The structural ADR-029 guarantee: the drill is a CO accessibility
    # alternative but its declared posterior module is CE.
    assert COLexicalAltDrill().spec.module == "CE"
    assert COLexicalAltDrill().spec.drill_kind == "co_lexical_alt"


def test_lexical_alt_present_includes_transcript_and_banner_key() -> None:
    drill = COLexicalAltDrill()
    step = drill.present(_co_item())
    # The transcript IS in the payload here (unlike co_mcq where it's
    # withheld pre-answer) — the lexical alt presents it AS text.
    assert step.payload["transcript"] == _TRANSCRIPT
    assert step.payload["accessibility_banner_key"] == "co_lexical_alt"
    assert step.single_play is False


def test_lexical_alt_interaction_writes_module_ce() -> None:
    drill = COLexicalAltDrill()
    item = _co_item()
    user, session = uuid4(), uuid4()
    result = drill.grade(item, {"option_id": "a"})
    assert result.raw_response["drill_origin"] == "co_lexical_alt"
    interaction = drill.to_interaction(
        user_id=user,
        session_id=session,
        item=item,
        result=result,
        rt_ms=20000,
        rating=3,
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    # The load-bearing assertion: the row's module is CE, never CO,
    # even though the underlying item is a CO item. This is what keeps
    # the CO posterior calibrated (ADR-029, phase5_audit §7).
    assert interaction.module == "CE"
    assert interaction.drill_kind == "co_lexical_alt"


def test_registry_resolves_new_drills() -> None:
    assert get_drill("co_dictation").spec.drill_kind == "co_dictation"
    assert get_drill("co_gapfill").spec.drill_kind == "co_gapfill"
    assert get_drill("co_lexical_alt").spec.module == "CE"
