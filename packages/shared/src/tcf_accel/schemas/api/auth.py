"""Auth route schemas — `/v1/auth/{signup,login,refresh}`.

Phase 3 implements; Phase 2 freezes the wire shape.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    display_name: str | None = Field(default=None, max_length=80)
    locale: str = Field(default="en", pattern=r"^(en|fr|es|ar|zh)$")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    """JWT pair. `access_token` is short-lived; `refresh_token` is long-lived."""

    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = Field(default="Bearer")
    access_ttl_s: int = Field(ge=60, le=3600, description="Seconds until access_token expires.")
    refresh_ttl_s: int = Field(ge=3600, description="Seconds until refresh_token expires.")


__all__ = ["LoginRequest", "RefreshRequest", "SignupRequest", "TokenPair"]
