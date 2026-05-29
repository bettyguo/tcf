"""Error taxonomy for tcf-accel.

Every error class carries:

- `code`: a stable `E_<DOMAIN>_<NNN>` string (ADR-014 — codes are public
  API and never renamed).
- `http_status`: the HTTP status code the API layer should return.
- `message_key`: the key into `tcf_accel.errors.messages.MESSAGES`; the
  rendered EN message becomes `str(error)`, and `to_envelope()` includes
  the EN + FR localized strings.

Phase 1 shipped the seed set. Phase 2 adds: auth, validation,
rate-limit, audio-too-short, rubric-mismatch, item-retired,
scheduler-cache-miss, and the `E_NOT_IMPLEMENTED_001` Phase 2 stub.

Example:
    >>> try:
    ...     raise InsufficientObservationsError(needed=12, have=3)
    ... except InsufficientObservationsError as exc:
    ...     exc.code
    'E_CALIB_002'

Complexity: O(1) construction.
"""

from __future__ import annotations

from typing import Any, ClassVar

from tcf_accel.errors.messages import MESSAGES, render


class TCFAccelError(Exception):
    """Base class for all in-house errors.

    Subclasses MUST override `code`, `http_status`, and `message_key`.
    Direct construction of `TCFAccelError` is allowed for tests but
    discouraged in production code — the audit (`phase2_audit.md §3`)
    enforces stable subclass codes everywhere a raise appears.
    """

    code: ClassVar[str] = "E_BASE_000"
    message_key: ClassVar[str] = "base"
    http_status: ClassVar[int] = 500

    def __init__(self, **context: object) -> None:
        """Build an error with structured context.

        Args:
            **context: keyword arguments referenced in the message template.
        """
        self.context: dict[str, object] = dict(context)
        rendered = render(self.message_key, "en", **context)
        super().__init__(rendered)

    def to_dict(self) -> dict[str, object]:
        """Serialize for structured logging."""
        return {
            "code": self.code,
            "message": str(self),
            "http_status": self.http_status,
            "context": self.context,
        }

    def to_envelope(self, *, locale: str = "en", phase: int | None = None) -> dict[str, Any]:
        """Serialize to the on-the-wire `ErrorEnvelope` shape.

        See `tcf_accel.schemas.api.errors.ErrorEnvelope`. The returned
        dict is suitable for `FastAPI.HTTPException(detail=...)`.

        Args:
            locale: BCP-47 locale to use for the default `message` field.
                Falls back to EN if the locale is missing the key.
            phase: Only set on `E_NOT_IMPLEMENTED_001` to indicate the
                owning build phase.
        """
        return {
            "code": self.code,
            "http_status": self.http_status,
            "message": render(self.message_key, locale, **self.context),
            "message_localized": {
                "en": render(self.message_key, "en", **self.context),
                "fr": render(self.message_key, "fr", **self.context),
            },
            "context": self.context,
            "phase": phase,
        }


# ─── Content domain ────────────────────────────────────────────


class ContentNotAvailableError(TCFAccelError):
    """Item bank cannot satisfy a requested configuration."""

    code: ClassVar[str] = "E_CONTENT_001"
    message_key: ClassVar[str] = "content.not_available"
    http_status: ClassVar[int] = 404


class ItemRetiredError(TCFAccelError):
    """The requested item is retired."""

    code: ClassVar[str] = "E_CONTENT_002"
    message_key: ClassVar[str] = "content.item_retired"
    http_status: ClassVar[int] = 410


class IngestSourceUnavailableError(TCFAccelError):
    """A pipeline source (e.g., RFI RSS, a HuggingFace dataset) is unreachable."""

    code: ClassVar[str] = "E_CONTENT_003"
    message_key: ClassVar[str] = "content.ingest_source_unavailable"
    http_status: ClassVar[int] = 503


class ContentLLMUnreliableError(TCFAccelError):
    """The synthesis or adversarial LLM failed to produce valid output after retries."""

    code: ClassVar[str] = "E_CONTENT_004"
    message_key: ClassVar[str] = "content.llm_unreliable"
    http_status: ClassVar[int] = 502


class CEFRClassifierUnavailableError(TCFAccelError):
    """The CEFR classifier artifact is missing or failed to load."""

    code: ClassVar[str] = "E_CONTENT_005"
    message_key: ClassVar[str] = "content.cefr_unavailable"
    http_status: ClassVar[int] = 503


class BankDistributionViolation(TCFAccelError):
    """The bank's distribution violates a hard quota cell (ADR-0022)."""

    code: ClassVar[str] = "E_CONTENT_006"
    message_key: ClassVar[str] = "content.distribution_violation"
    http_status: ClassVar[int] = 422


class IngestLicenseMissingError(TCFAccelError):
    """An operator-tier cached asset is missing its license.json sidecar."""

    code: ClassVar[str] = "E_CONTENT_007"
    message_key: ClassVar[str] = "content.ingest_license_missing"
    http_status: ClassVar[int] = 422


class IngestLicenseIncompatibleError(TCFAccelError):
    """A source's license is not in the redistribution allowlist (ADR-0010)."""

    code: ClassVar[str] = "E_CONTENT_008"
    message_key: ClassVar[str] = "content.ingest_license_incompatible"
    http_status: ClassVar[int] = 422


# ─── Scheduler domain ──────────────────────────────────────────


class SchedulerError(TCFAccelError):
    """Scheduler invariant violation."""

    code: ClassVar[str] = "E_SCHED_001"
    message_key: ClassVar[str] = "scheduler.generic"
    http_status: ClassVar[int] = 500


class SchedulerCacheMissError(SchedulerError):
    """Cached schedule queue is missing; worker is rebuilding (ADR-0012)."""

    code: ClassVar[str] = "E_SCHED_002"
    message_key: ClassVar[str] = "scheduler.cache_miss"
    http_status: ClassVar[int] = 503


# ─── Scoring domain ────────────────────────────────────────────


class ScoringError(TCFAccelError):
    """Generic scoring failure."""

    code: ClassVar[str] = "E_SCORING_001"
    message_key: ClassVar[str] = "scoring.generic"
    http_status: ClassVar[int] = 500


class ASRConfidenceTooLowError(ScoringError):
    """ASR returned a transcript below the confidence threshold."""

    code: ClassVar[str] = "E_SCORING_002"
    message_key: ClassVar[str] = "scoring.asr_low_confidence"
    http_status: ClassVar[int] = 422


class TextTooShortError(ScoringError):
    """EE submission below the minimum word count."""

    code: ClassVar[str] = "E_SCORING_003"
    message_key: ClassVar[str] = "scoring.text_too_short"
    http_status: ClassVar[int] = 422


class AudioTooShortError(ScoringError):
    """EO submission below the minimum duration."""

    code: ClassVar[str] = "E_SCORING_004"
    message_key: ClassVar[str] = "scoring.audio_too_short"
    http_status: ClassVar[int] = 422


class RubricMismatchError(ScoringError):
    """The submitted item's `rubric_version` does not match the loaded scorer."""

    code: ClassVar[str] = "E_SCORING_005"
    message_key: ClassVar[str] = "scoring.rubric_mismatch"
    http_status: ClassVar[int] = 500


# ─── Calibration / estimator domain ────────────────────────────


class CalibrationError(TCFAccelError):
    """Generic calibration failure."""

    code: ClassVar[str] = "E_CALIB_001"
    message_key: ClassVar[str] = "calibration.generic"
    http_status: ClassVar[int] = 503


class InsufficientObservationsError(CalibrationError):
    """Refuse to predict; not enough data to be honest."""

    code: ClassVar[str] = "E_CALIB_002"
    message_key: ClassVar[str] = "calibration.insufficient_obs"
    http_status: ClassVar[int] = 409


# ─── Auth domain ───────────────────────────────────────────────


class AuthError(TCFAccelError):
    """Generic authentication failure."""

    code: ClassVar[str] = "E_AUTH_001"
    message_key: ClassVar[str] = "auth.generic"
    http_status: ClassVar[int] = 401


class InvalidCredentialsError(AuthError):
    """Wrong email or password."""

    code: ClassVar[str] = "E_AUTH_002"
    message_key: ClassVar[str] = "auth.invalid_credentials"
    http_status: ClassVar[int] = 401


class TokenExpiredError(AuthError):
    """JWT past its `exp` claim."""

    code: ClassVar[str] = "E_AUTH_003"
    message_key: ClassVar[str] = "auth.token_expired"
    http_status: ClassVar[int] = 401


class TokenInvalidError(AuthError):
    """JWT signature or shape invalid."""

    code: ClassVar[str] = "E_AUTH_004"
    message_key: ClassVar[str] = "auth.token_invalid"
    http_status: ClassVar[int] = 401


class ForbiddenError(AuthError):
    """Authenticated but not permitted (e.g., cloud call for local_only user)."""

    code: ClassVar[str] = "E_AUTH_005"
    message_key: ClassVar[str] = "auth.forbidden"
    http_status: ClassVar[int] = 403


# ─── Validation / rate-limit ───────────────────────────────────


class RequestValidationError(TCFAccelError):
    """The request body did not validate against the documented schema."""

    code: ClassVar[str] = "E_VALIDATION_001"
    message_key: ClassVar[str] = "validation.request_body"
    http_status: ClassVar[int] = 422


class RateLimitError(TCFAccelError):
    """The client exceeded the rate quota."""

    code: ClassVar[str] = "E_RATE_LIMIT_001"
    message_key: ClassVar[str] = "rate_limit.exceeded"
    http_status: ClassVar[int] = 429


# ─── Session domain (Phase 5) ──────────────────────────────────


class ExamShapeFloorViolation(TCFAccelError):
    """`POST /v1/session/start` refused: exam-shape floor not met (ADR-028).

    The learner has rolled below the weekly exam-shape minutes floor
    and has not dismissed the floor for the current ISO week. The
    response carries `next_action="exam_shape"` and the suggested
    drill kinds.
    """

    code: ClassVar[str] = "E_SESSION_001"
    message_key: ClassVar[str] = "session.exam_shape_floor"
    http_status: ClassVar[int] = 409


class PauseWindowExpiredError(TCFAccelError):
    """`POST /v1/session/{id}/resume` refused: 24h pause window elapsed."""

    code: ClassVar[str] = "E_SESSION_002"
    message_key: ClassVar[str] = "session.pause_expired"
    http_status: ClassVar[int] = 410


class AccessibilityProfileRequiredError(TCFAccelError):
    """The requested drill needs an accessibility-profile setting the user has not set.

    Example: the planner emitted `co_lexical_alt` for a user whose
    `AccessibilityProfile.co_alternative == "none"`. The API refuses
    rather than silently switching the drill, so the choice is
    explicit (ADR-029).
    """

    code: ClassVar[str] = "E_SESSION_003"
    message_key: ClassVar[str] = "session.accessibility_required"
    http_status: ClassVar[int] = 409


class DrillInputInvalidError(TCFAccelError):
    """Drill-specific input validation failed (e.g., empty EE text, audio too short)."""

    code: ClassVar[str] = "E_SESSION_004"
    message_key: ClassVar[str] = "session.drill_input_invalid"
    http_status: ClassVar[int] = 422


# ─── ASR / Pronunciation / TTS / LLM (Phase 5) ─────────────────


class ASRBackendUnavailableError(TCFAccelError):
    """ASR backend (local Whisper or cloud LiteLLM) failed to load or respond."""

    code: ClassVar[str] = "E_ASR_001"
    message_key: ClassVar[str] = "asr.backend_unavailable"
    http_status: ClassVar[int] = 503


class PronunciationPipelineError(TCFAccelError):
    """Pronunciation pipeline produced no signal; caller proceeds with `pronunciation=null`.

    Soft error: the surrounding response is 200 but carries a
    warning. Used when MFA fails or the canonical reference is
    missing; not raised, returned in the envelope's `warnings` list.
    """

    code: ClassVar[str] = "E_PRON_001"
    message_key: ClassVar[str] = "pronunciation.pipeline_failure"
    http_status: ClassVar[int] = 200


class TTSBackendUnavailableError(TCFAccelError):
    """Examiner TTS (XTTS-v2) failed to load or render."""

    code: ClassVar[str] = "E_TTS_001"
    message_key: ClassVar[str] = "tts.backend_unavailable"
    http_status: ClassVar[int] = 503


class LLMBackendUnavailableError(TCFAccelError):
    """LLM gateway unavailable.

    In default (local-stub) mode this is never raised — the stub is
    deterministic. Only seen when the operator opted into a cloud
    LLM via `TCF_ACCEL_LLM_BACKEND`.
    """

    code: ClassVar[str] = "E_LLM_001"
    message_key: ClassVar[str] = "llm.backend_unavailable"
    http_status: ClassVar[int] = 503


# ─── Mock exam (Phase 6) ────────────────────────────────────────


class MockCadenceExceededError(TCFAccelError):
    """`POST /v1/mock-exam/start` refused: weekly cadence cap reached.

    ADR-033 caps canonical mocks at 1/w (weeks 0..5), 2/w (6..9), 3/w
    (10+). Training mocks are capped at 1/day. The override
    `?force=true` is logged and surfaced by `audit-mocks`.
    """

    code: ClassVar[str] = "E_MOCK_001"
    message_key: ClassVar[str] = "mock.cadence_exceeded"
    http_status: ClassVar[int] = 409


class MockForfeitedError(TCFAccelError):
    """Operation refused: the mock has already been forfeited.

    Canonical mocks forfeit on abnormal exit (tab-blur > 5 s, process
    abort). The state is terminal; the only valid follow-up is to
    start a new mock.
    """

    code: ClassVar[str] = "E_MOCK_002"
    message_key: ClassVar[str] = "mock.forfeited"
    http_status: ClassVar[int] = 409


class MockNotScoredError(TCFAccelError):
    """`GET /v1/mock-exam/{id}/report` called before scoring finished."""

    code: ClassVar[str] = "E_MOCK_003"
    message_key: ClassVar[str] = "mock.not_scored"
    http_status: ClassVar[int] = 404


class MockInvalidTransitionError(TCFAccelError):
    """The requested state transition is illegal for the mock's current state."""

    code: ClassVar[str] = "E_MOCK_004"
    message_key: ClassVar[str] = "mock.invalid_transition"
    http_status: ClassVar[int] = 409


class MockCoSinglePlayViolation(TCFAccelError):
    """The client tried to play a CO audio item twice in the same mock (ADR-029)."""

    code: ClassVar[str] = "E_MOCK_005"
    message_key: ClassVar[str] = "mock.co_single_play"
    http_status: ClassVar[int] = 409


# ─── Phase 2 stub ──────────────────────────────────────────────


class NotImplementedRouteError(TCFAccelError):
    """Returned by every Phase 2 `/v1/` stub.

    The `to_envelope(phase=N)` form sets the envelope's `phase` field so
    clients can branch on "this is a known-not-yet-implemented route in
    phase N" vs a generic 501.
    """

    code: ClassVar[str] = "E_NOT_IMPLEMENTED_001"
    message_key: ClassVar[str] = "not_implemented"
    http_status: ClassVar[int] = 501


__all__ = [
    "MESSAGES",
    "ASRBackendUnavailableError",
    "ASRConfidenceTooLowError",
    "AccessibilityProfileRequiredError",
    "AudioTooShortError",
    "AuthError",
    "BankDistributionViolation",
    "CEFRClassifierUnavailableError",
    "CalibrationError",
    "ContentLLMUnreliableError",
    "ContentNotAvailableError",
    "DrillInputInvalidError",
    "ExamShapeFloorViolation",
    "ForbiddenError",
    "IngestLicenseIncompatibleError",
    "IngestLicenseMissingError",
    "IngestSourceUnavailableError",
    "InsufficientObservationsError",
    "InvalidCredentialsError",
    "ItemRetiredError",
    "LLMBackendUnavailableError",
    "MockCadenceExceededError",
    "MockCoSinglePlayViolation",
    "MockForfeitedError",
    "MockInvalidTransitionError",
    "MockNotScoredError",
    "NotImplementedRouteError",
    "PauseWindowExpiredError",
    "PronunciationPipelineError",
    "RateLimitError",
    "RequestValidationError",
    "RubricMismatchError",
    "SchedulerCacheMissError",
    "SchedulerError",
    "ScoringError",
    "TCFAccelError",
    "TTSBackendUnavailableError",
    "TextTooShortError",
    "TokenExpiredError",
    "TokenInvalidError",
    "render",
]
