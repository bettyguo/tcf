"""Version-related sanity checks."""

from __future__ import annotations

import re

from tcf_accel.schemas.version import SCHEMA_VERSION


def test_schema_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+].+)?", SCHEMA_VERSION), SCHEMA_VERSION


def test_schema_version_is_phase5_baseline() -> None:
    # Phase 1: 0.1.0. Phase 2: 0.2.0 (additive narrowing of ItemContent +
    # rubric/API schemas). Phase 3: 0.3.0 (additive QualityFlag values,
    # documented ItemMetadata Phase 3 surfaces, new E_CONTENT_003..008
    # subclasses, new confusable_pairs table). Phase 5: 0.4.0 (additive
    # Interaction fields, PronunciationSignal contract per ADR-031,
    # DrillType extension, AccessibilityProfile, DismissalLogEntry,
    # E_SESSION/E_ASR/E_PRON/E_TTS/E_LLM error codes). Any further bump
    # requires an ADR + CHANGELOG entry.
    assert SCHEMA_VERSION == "0.4.0"
