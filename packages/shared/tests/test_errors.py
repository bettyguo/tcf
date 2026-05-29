"""Tests for the error taxonomy.

The stability promise of error codes is part of the public API (ADR-014).
This test pins the codes so an accidental rename is caught and verifies
HTTP statuses, subclass chains, message rendering, code uniqueness, and
that every error class has at least an EN + FR message.
"""

from __future__ import annotations

import re

import pytest
import tcf_accel.errors as errors_mod
from tcf_accel.errors import (
    AccessibilityProfileRequiredError,
    ASRBackendUnavailableError,
    ASRConfidenceTooLowError,
    AudioTooShortError,
    AuthError,
    BankDistributionViolation,
    CalibrationError,
    CEFRClassifierUnavailableError,
    ContentLLMUnreliableError,
    ContentNotAvailableError,
    DrillInputInvalidError,
    ExamShapeFloorViolation,
    ForbiddenError,
    IngestLicenseIncompatibleError,
    IngestLicenseMissingError,
    IngestSourceUnavailableError,
    InsufficientObservationsError,
    InvalidCredentialsError,
    ItemRetiredError,
    LLMBackendUnavailableError,
    NotImplementedRouteError,
    PauseWindowExpiredError,
    PronunciationPipelineError,
    RateLimitError,
    RequestValidationError,
    RubricMismatchError,
    SchedulerCacheMissError,
    SchedulerError,
    ScoringError,
    TCFAccelError,
    TextTooShortError,
    TokenExpiredError,
    TokenInvalidError,
    TTSBackendUnavailableError,
)
from tcf_accel.errors.messages import MESSAGES

_CODE_PATTERN = re.compile(r"^E_[A-Z][A-Z_]*_\d{3}$")
# 502 added in Phase 3 for upstream-LLM failures (E_CONTENT_004).
# 200 added in Phase 5 for the soft-warning E_PRON_001 (pronunciation
# pipeline failure is non-fatal; the surrounding response is 200 with
# `pronunciation=null` and the code surfaced in the warnings list).
_ALLOWED_STATUSES = {200, 400, 401, 403, 404, 409, 410, 422, 429, 500, 501, 502, 503}


def test_base_code_and_status() -> None:
    assert TCFAccelError.code == "E_BASE_000"
    assert TCFAccelError.http_status == 500


@pytest.mark.parametrize(
    ("cls", "code", "http_status"),
    [
        (ContentNotAvailableError, "E_CONTENT_001", 404),
        (ItemRetiredError, "E_CONTENT_002", 410),
        (IngestSourceUnavailableError, "E_CONTENT_003", 503),
        (ContentLLMUnreliableError, "E_CONTENT_004", 502),
        (CEFRClassifierUnavailableError, "E_CONTENT_005", 503),
        (BankDistributionViolation, "E_CONTENT_006", 422),
        (IngestLicenseMissingError, "E_CONTENT_007", 422),
        (IngestLicenseIncompatibleError, "E_CONTENT_008", 422),
        (SchedulerError, "E_SCHED_001", 500),
        (SchedulerCacheMissError, "E_SCHED_002", 503),
        (ScoringError, "E_SCORING_001", 500),
        (ASRConfidenceTooLowError, "E_SCORING_002", 422),
        (TextTooShortError, "E_SCORING_003", 422),
        (AudioTooShortError, "E_SCORING_004", 422),
        (RubricMismatchError, "E_SCORING_005", 500),
        (CalibrationError, "E_CALIB_001", 503),
        (InsufficientObservationsError, "E_CALIB_002", 409),
        (AuthError, "E_AUTH_001", 401),
        (InvalidCredentialsError, "E_AUTH_002", 401),
        (TokenExpiredError, "E_AUTH_003", 401),
        (TokenInvalidError, "E_AUTH_004", 401),
        (ForbiddenError, "E_AUTH_005", 403),
        (RequestValidationError, "E_VALIDATION_001", 422),
        (RateLimitError, "E_RATE_LIMIT_001", 429),
        (ExamShapeFloorViolation, "E_SESSION_001", 409),
        (PauseWindowExpiredError, "E_SESSION_002", 410),
        (AccessibilityProfileRequiredError, "E_SESSION_003", 409),
        (DrillInputInvalidError, "E_SESSION_004", 422),
        (ASRBackendUnavailableError, "E_ASR_001", 503),
        (PronunciationPipelineError, "E_PRON_001", 200),
        (TTSBackendUnavailableError, "E_TTS_001", 503),
        (LLMBackendUnavailableError, "E_LLM_001", 503),
        (NotImplementedRouteError, "E_NOT_IMPLEMENTED_001", 501),
    ],
)
def test_codes_are_stable(cls: type[TCFAccelError], code: str, http_status: int) -> None:
    assert cls.code == code, f"renaming {cls.__name__}.code breaks the API contract"
    assert cls.http_status == http_status


def _all_concrete_subclasses() -> set[type[TCFAccelError]]:
    """Walk the subclass tree from TCFAccelError."""
    seen: set[type[TCFAccelError]] = set()
    stack: list[type[TCFAccelError]] = [TCFAccelError]
    while stack:
        cls = stack.pop()
        seen.add(cls)
        stack.extend(cls.__subclasses__())
    return seen


def test_every_code_matches_pattern() -> None:
    for cls in _all_concrete_subclasses():
        assert _CODE_PATTERN.fullmatch(cls.code), f"{cls.__name__}.code={cls.code!r}"


def test_every_http_status_is_allowed() -> None:
    for cls in _all_concrete_subclasses():
        assert cls.http_status in _ALLOWED_STATUSES, (
            f"{cls.__name__}.http_status={cls.http_status} not in {_ALLOWED_STATUSES}"
        )


def test_codes_are_unique() -> None:
    seen: dict[str, type[TCFAccelError]] = {}
    for cls in _all_concrete_subclasses():
        prev = seen.get(cls.code)
        if prev is not None and prev is not cls:
            pytest.fail(f"duplicate code {cls.code} on {prev.__name__} and {cls.__name__}")
        seen[cls.code] = cls


def test_every_message_key_has_en_and_fr() -> None:
    for cls in _all_concrete_subclasses():
        bundle = MESSAGES.get(cls.message_key)
        assert bundle is not None, f"{cls.__name__}.message_key={cls.message_key!r} not in catalog"
        assert "en" in bundle, f"{cls.message_key!r} missing en"
        assert "fr" in bundle, f"{cls.message_key!r} missing fr"


def test_subclass_chains() -> None:
    assert issubclass(ASRConfidenceTooLowError, ScoringError)
    assert issubclass(InsufficientObservationsError, CalibrationError)
    assert issubclass(SchedulerCacheMissError, SchedulerError)
    assert issubclass(InvalidCredentialsError, AuthError)
    assert issubclass(TokenExpiredError, AuthError)
    assert issubclass(ScoringError, TCFAccelError)


def test_template_renders_with_context() -> None:
    err = InsufficientObservationsError(needed=12, have=3)
    assert "12" in str(err)
    assert "3" in str(err)
    assert err.context == {"needed": 12, "have": 3}


def test_template_render_failure_is_caught() -> None:
    err = InsufficientObservationsError()  # missing placeholders
    assert "render_error" in str(err)


def test_to_dict_is_serializable() -> None:
    err = TextTooShortError(word_count=20, minimum=60)
    d = err.to_dict()
    assert d["code"] == "E_SCORING_003"
    assert d["http_status"] == 422
    assert d["context"] == {"word_count": 20, "minimum": 60}


def test_to_envelope_includes_en_and_fr() -> None:
    err = TextTooShortError(word_count=20, minimum=60)
    env = err.to_envelope(locale="fr")
    assert env["code"] == "E_SCORING_003"
    assert env["http_status"] == 422
    assert "Votre réponse" in env["message"]  # locale=fr renders the FR string
    assert "Your response" in env["message_localized"]["en"]
    assert "Votre réponse" in env["message_localized"]["fr"]
    assert env["context"] == {"word_count": 20, "minimum": 60}
    assert env["phase"] is None


def test_to_envelope_phase_set_on_not_implemented() -> None:
    err = NotImplementedRouteError(phase=5)
    env = err.to_envelope(phase=5)
    assert env["phase"] == 5


def test_module_exports_all_classes_in_all() -> None:
    # The __all__ list shouldn't drift from the actual class definitions.
    for cls in _all_concrete_subclasses():
        assert cls.__name__ in errors_mod.__all__, f"{cls.__name__} missing from __all__"
