"""On-the-wire error envelope.

The shape every non-2xx response carries:

```json
{
  "code": "E_SCORING_002",
  "http_status": 422,
  "message": "We couldn't transcribe the audio confidently…",
  "message_localized": {"en": "...", "fr": "Nous n'avons pas pu…"},
  "context": {"score": 0.41, "threshold": 0.65},
  "phase": null
}
```

`phase` is set only on `501 E_NOT_IMPLEMENTED_001` to indicate which
build phase owns the eventual implementation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ErrorEnvelope(BaseModel):
    """JSON shape returned by every non-2xx response."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        pattern=r"^E_[A-Z][A-Z_]*_\d{3}$",
        description="Stable error code (ADR-014). Format: E_<DOMAIN>_<NNN>; DOMAIN may contain underscores (e.g. E_NOT_IMPLEMENTED_001).",
    )
    http_status: int = Field(ge=400, le=599)
    message: str = Field(min_length=1, description="Default-locale rendered message (EN).")
    message_localized: dict[str, str] = Field(
        default_factory=dict,
        description="Locale → rendered message. Keys are BCP-47 codes (e.g. 'en', 'fr').",
    )
    context: dict[str, object] = Field(
        default_factory=dict,
        description="Structured context for the error. Keys are stable per code (ADR-014 point 6).",
    )
    phase: int | None = Field(
        default=None,
        description="Set only on 501 E_NOT_IMPLEMENTED_001 to indicate the owning build phase.",
    )


__all__ = ["ErrorEnvelope"]
