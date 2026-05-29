"""`/v1/me` — user profile read/update.

Phase 5 (ADR-029) adds `AccessibilityProfile`, served at
`GET/PATCH /v1/me/accessibility`. The profile is local-only per
ADR-017; the operator's pod stores the row, never the cloud.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from tcf_accel.ids import UserId

PrivacyMode = Literal["local_only", "cloud_optin"]
Locale = Literal["en", "fr", "es", "ar", "zh"]

COAccessibilityAlt = Literal["none", "lexical_alt"]
EEAccessibilityAlt = Literal["none", "speech_to_text"]
EOAccessibilityAlt = Literal["none", "text_input"]


class AccessibilityProfile(BaseModel):
    """Per-learner accessibility preferences (Phase 5, ADR-029).

    Setting `co_alternative="lexical_alt"` reroutes any CO drill the
    planner emits to `co_lexical_alt`, which writes `Interaction.module
    = "CE"` and does *not* contribute to the CO posterior. The UX
    banner is mandatory; see `phase5_design.md §7.3`.

    `ee_alternative="speech_to_text"` plugs STT at the EE drill's input
    layer; the rubric still scores the resulting text. `eo_alternative
    = "text_input"` swaps the EO drill for a text-input variant that
    emits `module="EE"` with a banner-disclaimed "does not measure
    real EO" caveat.

    `dyslexia_font` and `high_contrast` are UI-only signals consumed
    by the Phase 8 frontend.
    """

    model_config = ConfigDict(extra="forbid")

    co_alternative: COAccessibilityAlt = "none"
    ee_alternative: EEAccessibilityAlt = "none"
    eo_alternative: EOAccessibilityAlt = "none"
    dyslexia_font: bool = False
    high_contrast: bool = False


class MeProfile(BaseModel):
    """The authenticated user's full profile."""

    model_config = ConfigDict(extra="forbid")

    id: UserId
    email: EmailStr
    display_name: str | None
    target_nclc: int = Field(ge=4, le=12)
    target_exam_date: date | None
    daily_minutes_budget: int = Field(ge=15, le=480)
    locale: Locale
    privacy_mode: PrivacyMode = Field(
        description="Default 'local_only' per ADR-0017; flipping to 'cloud_optin' requires explicit opt-in.",
    )
    created_at: datetime


class UpdateMeRequest(BaseModel):
    """Partial update of the profile. Only the supplied fields are changed.

    Sending an empty body is a no-op (returns the unchanged profile).
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=80)
    target_nclc: int | None = Field(default=None, ge=4, le=12)
    target_exam_date: date | None = None
    daily_minutes_budget: int | None = Field(default=None, ge=15, le=480)
    locale: Locale | None = None
    privacy_mode: PrivacyMode | None = None


__all__ = [
    "AccessibilityProfile",
    "COAccessibilityAlt",
    "EEAccessibilityAlt",
    "EOAccessibilityAlt",
    "Locale",
    "MeProfile",
    "PrivacyMode",
    "UpdateMeRequest",
]
