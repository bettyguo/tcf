"""Error taxonomy for tcf-accel.

Every error class carries:

- `code`: a stable `E_DOMAIN_NNN` string. Stability is part of the public API
  contract (Phase 2 ADR-014). Tests check this; never edit a code in-place.
- `http_status`: the HTTP status code the API layer should return.
- `message_template`: a learner-facing message template with `{placeholder}`
  fields. Filled at construction via keyword arguments.

Phase 1 ships the seed set. Phase 2's `02_ARCHITECTURE.md §2.5` enumerates the
full taxonomy; subsequent phases add domain-specific subclasses.

Example:
    >>> try:
    ...     raise InsufficientObservationsError(needed=12, have=3)
    ... except InsufficientObservationsError as exc:
    ...     exc.code
    'E_CALIB_002'

Complexity: O(1) construction.
"""

from __future__ import annotations

from typing import ClassVar


class TCFAccelError(Exception):
    """Base class for all in-house errors."""

    code: ClassVar[str] = "E_BASE_000"
    message_template: ClassVar[str] = "tcf-accel error"
    http_status: ClassVar[int] = 500

    def __init__(self, **context: object) -> None:
        """Build an error with structured context.

        Args:
            **context: keyword arguments referenced in `message_template`.
        """
        try:
            rendered = self.message_template.format(**context)
        except (IndexError, KeyError) as exc:
            rendered = f"{self.message_template} [render_error={exc!s}]"
        super().__init__(rendered)
        self.context: dict[str, object] = dict(context)

    def to_dict(self) -> dict[str, object]:
        """Serialize for structured logging / API response bodies."""
        return {
            "code": self.code,
            "message": str(self),
            "http_status": self.http_status,
            "context": self.context,
        }


# ─── Content domain ────────────────────────────────────────────


class ContentNotAvailableError(TCFAccelError):
    """Item bank cannot satisfy a requested configuration."""

    code: ClassVar[str] = "E_CONTENT_001"
    message_template: ClassVar[str] = "No items match constraints: {constraints}"
    http_status: ClassVar[int] = 404


# ─── Scheduler / planner domain ────────────────────────────────


class SchedulerError(TCFAccelError):
    """Scheduler invariant violation."""

    code: ClassVar[str] = "E_SCHED_001"
    message_template: ClassVar[str] = "Scheduler error: {detail}"
    http_status: ClassVar[int] = 500


# ─── Scoring domain ────────────────────────────────────────────


class ScoringError(TCFAccelError):
    """Generic scoring failure."""

    code: ClassVar[str] = "E_SCORING_001"
    message_template: ClassVar[str] = "Scoring failed: {detail}"
    http_status: ClassVar[int] = 500


class ASRConfidenceTooLowError(ScoringError):
    """ASR returned a transcript below the confidence threshold."""

    code: ClassVar[str] = "E_SCORING_002"
    message_template: ClassVar[str] = (
        "We couldn't transcribe the audio confidently (score={score:.2f}, "
        "threshold={threshold:.2f}). Please re-record in a quieter setting."
    )
    http_status: ClassVar[int] = 422


class TextTooShortError(ScoringError):
    """EE submission below the minimum word count."""

    code: ClassVar[str] = "E_SCORING_003"
    message_template: ClassVar[str] = (
        "Your response is {word_count} words; this task expects at least {minimum}."
    )
    http_status: ClassVar[int] = 422


# ─── Calibration / estimator domain ────────────────────────────


class CalibrationError(TCFAccelError):
    """Generic calibration failure."""

    code: ClassVar[str] = "E_CALIB_001"
    message_template: ClassVar[str] = "Calibration failed: {detail}"
    http_status: ClassVar[int] = 503


class InsufficientObservationsError(CalibrationError):
    """Refuse to predict; not enough data to be honest."""

    code: ClassVar[str] = "E_CALIB_002"
    message_template: ClassVar[str] = (
        "Not enough data yet to estimate confidently — complete {needed} more "
        "items (currently {have})."
    )
    http_status: ClassVar[int] = 409


__all__ = [
    "ASRConfidenceTooLowError",
    "CalibrationError",
    "ContentNotAvailableError",
    "InsufficientObservationsError",
    "SchedulerError",
    "ScoringError",
    "TCFAccelError",
    "TextTooShortError",
]
