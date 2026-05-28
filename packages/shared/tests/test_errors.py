"""Tests for the error taxonomy.

The stability promise of error codes is part of the public API (Phase 2
ADR-014). This test pins the seed codes so an accidental rename is caught.
"""

from __future__ import annotations

import pytest

from tcf_accel.errors import (
    ASRConfidenceTooLowError,
    CalibrationError,
    ContentNotAvailableError,
    InsufficientObservationsError,
    SchedulerError,
    ScoringError,
    TCFAccelError,
    TextTooShortError,
)


def test_base_code_and_status() -> None:
    assert TCFAccelError.code == "E_BASE_000"
    assert TCFAccelError.http_status == 500


@pytest.mark.parametrize(
    ("cls", "code", "http_status"),
    [
        (ContentNotAvailableError, "E_CONTENT_001", 404),
        (SchedulerError, "E_SCHED_001", 500),
        (ScoringError, "E_SCORING_001", 500),
        (ASRConfidenceTooLowError, "E_SCORING_002", 422),
        (TextTooShortError, "E_SCORING_003", 422),
        (CalibrationError, "E_CALIB_001", 503),
        (InsufficientObservationsError, "E_CALIB_002", 409),
    ],
)
def test_codes_are_stable(cls: type[TCFAccelError], code: str, http_status: int) -> None:
    assert cls.code == code, f"renaming {cls.__name__}.code breaks the API contract"
    assert cls.http_status == http_status


def test_subclass_chain() -> None:
    assert issubclass(ASRConfidenceTooLowError, ScoringError)
    assert issubclass(InsufficientObservationsError, CalibrationError)
    assert issubclass(ScoringError, TCFAccelError)


def test_template_renders_with_context() -> None:
    err = InsufficientObservationsError(needed=12, have=3)
    assert "12 more" in str(err)
    assert "currently 3" in str(err)
    assert err.context == {"needed": 12, "have": 3}


def test_template_render_failure_is_caught() -> None:
    # Missing placeholder shouldn't blow up the error itself.
    err = InsufficientObservationsError()  # no needed/have
    s = str(err)
    assert "render_error" in s


def test_to_dict_is_serializable() -> None:
    err = TextTooShortError(word_count=20, minimum=60)
    d = err.to_dict()
    assert d["code"] == "E_SCORING_003"
    assert d["http_status"] == 422
    assert d["context"] == {"word_count": 20, "minimum": 60}
