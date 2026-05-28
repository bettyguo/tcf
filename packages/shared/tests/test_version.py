"""Version-related sanity checks."""

from __future__ import annotations

import re

from tcf_accel.schemas.version import SCHEMA_VERSION


def test_schema_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+].+)?", SCHEMA_VERSION), SCHEMA_VERSION


def test_schema_version_is_phase1_baseline() -> None:
    # Phase 1 freezes at 0.1.0. A bump requires an ADR + CHANGELOG entry.
    assert SCHEMA_VERSION == "0.1.0"
