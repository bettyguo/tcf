"""End-to-end EE and EO scorer tests (Phase 7).

Covers the orchestrators (`EEScorer`, `EOScorer`), the worker adapters,
the rubric-shape invariants, the under-length flag, and the
pronunciation-signal pass-through.
"""

from __future__ import annotations

from tcf_accel.schemas.pronunciation import PronunciationProsody, PronunciationSignal
from tcf_accel.schemas.scoring import SpeakingRubric, WritingRubric

from tcf_accel_ml.scoring.ee.score import EEScorer, EEWorkerScorer
from tcf_accel_ml.scoring.eo.score import EOScorer, EOWorkerScorer
from tcf_accel_ml.scoring.feedback import render_feedback
from tcf_accel_ml.scoring.llm.stub import LLMCriticStub
from tcf_accel_ml.scoring.rubric_table import nclc_from_total_20

_SAMPLE_PROMPT = (
    "Vous écrivez un message à votre voisin pour vous plaindre du bruit. "
    "Expliquez la situation et proposez une solution."
)

_PLAUSIBLE_RESPONSE = (
    "Cher voisin, je vous écris à propos du bruit nocturne qui me dérange "
    "depuis plusieurs semaines. Par ailleurs, je travaille tôt le matin et "
    "j'ai besoin de me reposer. Cependant, je comprends que la vie en ville "
    "à Montréal n'est pas toujours simple. Je propose donc que nous "
    "trouvions ensemble une solution amiable, par exemple en limitant la "
    "musique forte après vingt-deux heures. En conclusion, j'espère que "
    "nous pourrons résoudre cette situation rapidement et cordialement. "
    "Cordialement, votre voisin."
)


# ─── EE ────────────────────────────────────────────────────────


def test_ee_scorer_returns_valid_writing_rubric() -> None:
    scorer = EEScorer()
    result = scorer.score(
        text=_PLAUSIBLE_RESPONSE,
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        target_word_count_range=(120, 150),
        required_canadian_context=True,
    )
    assert isinstance(result.rubric, WritingRubric)
    assert 0 <= result.rubric.total_20 <= 20
    assert result.rubric.canadian_context_integration is not None
    # The dimension scores are int 0..5; total_20 invariant is enforced by
    # the schema's model_validator.
    assert all(0 <= v <= 5 for v in (
        result.rubric.task_completion,
        result.rubric.coherence_cohesion,
        result.rubric.lexical_range,
        result.rubric.grammatical_accuracy,
        result.rubric.register_appropriateness,
    ))


def test_ee_scorer_flags_under_length() -> None:
    scorer = EEScorer()
    result = scorer.score(
        text="Bonjour.",
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        target_word_count_range=(120, 150),
        required_canadian_context=True,
    )
    assert result.under_length is True
    assert result.needs_human_review is True


def test_ee_scorer_null_canadian_when_not_required() -> None:
    scorer = EEScorer()
    result = scorer.score(
        text=_PLAUSIBLE_RESPONSE,
        prompt=_SAMPLE_PROMPT,
        task_number=1,  # Task 1: no canadian context required
        target_word_count_range=(60, 120),
        required_canadian_context=False,
    )
    assert result.rubric.canadian_context_integration is None


def test_ee_scorer_inflation_guard_engages_for_forced_inflated_llm() -> None:
    critic = LLMCriticStub(force_scores={
        "task_completion": 5,
        "coherence_cohesion": 5,
        "lexical_range": 5,
        "grammatical_accuracy": 5,
        "register_appropriateness": 5,
        "canadian_context_integration": 5,
    })
    scorer = EEScorer(critic=critic)
    # Tiny essay → feature floor low → forced 5/5 should clamp.
    result = scorer.score(
        text="Bonjour. Voilà.",
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        target_word_count_range=(120, 150),
        required_canadian_context=True,
    )
    assert result.inflation_guard.needs_human_review is True
    assert result.inflation_guard.clamped_dimensions


def test_ee_scorer_emits_feedback_blocks() -> None:
    scorer = EEScorer()
    result = scorer.score(
        text=_PLAUSIBLE_RESPONSE,
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        target_word_count_range=(120, 150),
        required_canadian_context=True,
    )
    assert result.feedback_blocks
    # The disclaimer block is always present.
    assert any(b.kind == "disclaimer" for b in result.feedback_blocks)


def test_ee_scorer_deterministic_on_repeat() -> None:
    scorer = EEScorer()
    kwargs = {
        "text": _PLAUSIBLE_RESPONSE,
        "prompt": _SAMPLE_PROMPT,
        "task_number": 2,
        "target_word_count_range": (120, 150),
        "required_canadian_context": True,
    }
    a = scorer.score(**kwargs)
    b = scorer.score(**kwargs)
    assert a.rubric.total_20 == b.rubric.total_20
    assert a.rubric.model_dump() == b.rubric.model_dump()


def test_ee_worker_scorer_payload_round_trip() -> None:
    payload = {
        "text": _PLAUSIBLE_RESPONSE,
        "prompt": _SAMPLE_PROMPT,
        "task_number": 2,
        "target_word_count_range": [120, 150],
        "required_canadian_context": True,
        "rubric_version": "ee.v1",
        "drill_kind": "ee_task",
    }
    graded = EEWorkerScorer().score_ee(payload)
    assert graded["phase7_status"] == "graded"
    assert graded["rubric_version"] == "ee.v1"
    assert "rubric" in graded
    assert "feedback_blocks" in graded
    assert graded["nclc_band"] == nclc_from_total_20(graded["rubric"]["total_20"])


# ─── EO ────────────────────────────────────────────────────────


def _make_signal(label: str = "fair", per: float = 0.15) -> PronunciationSignal:
    return PronunciationSignal(
        score=1.0 - per,
        disclaimer_version="v1.0",
        display_label=label,  # type: ignore[arg-type]
        per=per,
        asr_mean_confidence=0.85,
        n_phonemes_aligned=42,
        duration_s=10.0,
        prosody=PronunciationProsody(
            pitch_range_hz=180.0,
            speech_rate_wpm=140.0,
            pause_count=2,
            mean_pause_ms=240.0,
        ),
    )


def test_eo_scorer_returns_valid_speaking_rubric() -> None:
    scorer = EOScorer()
    result = scorer.score(
        transcript=_PLAUSIBLE_RESPONSE,
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        duration_s=30.0,
        asr_mean_confidence=0.85,
        pronunciation_signal=_make_signal(label="fair", per=0.15),
    )
    assert isinstance(result.rubric, SpeakingRubric)
    assert 0 <= result.rubric.total_20 <= 20
    assert result.pronunciation_display_label == "fair"


def test_eo_scorer_insufficient_data_flags_human_review() -> None:
    scorer = EOScorer()
    result = scorer.score(
        transcript="Bonjour le monde",
        prompt="say hello",
        task_number=1,
        duration_s=1.0,
        asr_mean_confidence=0.3,
        pronunciation_signal=None,
    )
    assert result.pronunciation_display_label == "insufficient_data"
    assert result.needs_human_review is True


def test_eo_scorer_pronunciation_signal_overrides_llm() -> None:
    """A strong PronunciationSignal pushes the pronunciation rubric high
    regardless of what the LLM stub would have returned.
    """
    strong = _make_signal(label="strong", per=0.05)
    weak = _make_signal(label="weak", per=0.40)
    scorer = EOScorer()
    r_strong = scorer.score(
        transcript=_PLAUSIBLE_RESPONSE,
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        duration_s=30.0,
        asr_mean_confidence=0.9,
        pronunciation_signal=strong,
    )
    r_weak = scorer.score(
        transcript=_PLAUSIBLE_RESPONSE,
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        duration_s=30.0,
        asr_mean_confidence=0.9,
        pronunciation_signal=weak,
    )
    assert r_strong.rubric.pronunciation_prosody > r_weak.rubric.pronunciation_prosody


def test_eo_worker_scorer_payload_round_trip() -> None:
    payload = {
        "transcript": _PLAUSIBLE_RESPONSE,
        "prompt": _SAMPLE_PROMPT,
        "task_number": 2,
        "duration_s": 30.0,
        "asr_mean_confidence": 0.85,
        "rubric_version": "eo.v1",
        "drill_kind": "eo_task",
        "pronunciation_signal": _make_signal(label="fair", per=0.15).model_dump(),
    }
    graded = EOWorkerScorer().score_eo(payload)
    assert graded["phase7_status"] == "graded"
    assert "rubric" in graded
    assert graded["pronunciation_display_label"] == "fair"


def test_eo_worker_scorer_with_partial_pronunciation_payload() -> None:
    payload = {
        "transcript": _PLAUSIBLE_RESPONSE,
        "prompt": _SAMPLE_PROMPT,
        "task_number": 2,
        "duration_s": 30.0,
        "asr_mean_confidence": 0.85,
        "rubric_version": "eo.v1",
        "pronunciation_display_label": "fair",
        "phoneme_error_rate": 0.15,
        "prosody": {
            "pitch_range_hz": 180.0,
            "speech_rate_wpm": 140.0,
            "pause_count": 2,
            "mean_pause_ms": 240.0,
        },
        "n_phonemes_aligned": 42,
    }
    graded = EOWorkerScorer().score_eo(payload)
    assert graded["pronunciation_display_label"] == "fair"


# ─── Feedback render ────────────────────────────────────────────


def test_feedback_render_keeps_learner_quote_separate() -> None:
    """ADR-040 anti-criterion: learner text never inlined into detail."""
    scorer = EEScorer()
    result = scorer.score(
        text="Si j'aurais le choix, j'irais à Montréal demain.",
        prompt=_SAMPLE_PROMPT,
        task_number=2,
        target_word_count_range=(60, 120),
        required_canadian_context=True,
    )
    for block in result.feedback_blocks:
        if block.learner_quote is not None:
            # The fragment must not be inlined into detail prose.
            assert block.learner_quote not in block.detail


def test_feedback_render_disclaimer_always_present() -> None:
    from tcf_accel_ml.scoring.features.writing import extract_writing_features

    blocks = render_feedback(
        rubric=WritingRubric(
            task_completion=3,
            coherence_cohesion=3,
            lexical_range=3,
            grammatical_accuracy=3,
            register_appropriateness=3,
            canadian_context_integration=3,
            total_20=12,
            error_density_per_100w=0.0,
            type_token_ratio=0.5,
            discourse_marker_count=2,
        ),
        features=extract_writing_features(_PLAUSIBLE_RESPONSE),
        text=_PLAUSIBLE_RESPONSE,
        errors=[],
        target_nclc=9,
    )
    assert any(b.kind == "disclaimer" for b in blocks)
    # The context block is always present.
    assert any(b.kind == "context" for b in blocks)
