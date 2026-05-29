"""Cross-package schema version.

Bumped on every breaking change to the schemas under `tcf_accel.schemas`.

- 0.1.0 — Phase 1 baseline. `Item` with permissive `ItemContent` placeholder;
  `Score`, `NCLCEstimate`, `Provenance`, `QualityFlag`, `ItemMetadata`,
  error taxonomy seed.
- 0.2.0 — Phase 2. Additive:
  * `ItemContent` narrowed into a discriminated union of
    `COContent | CEContent | EEContent | EOContent` (every Phase 1 instance
    that carried a valid `module` discriminator still validates).
  * Added `WritingRubric`, `SpeakingRubric`, `ErrorAnnotation`, `Speaker`,
    `MCQ`, `MCQOption` schemas.
  * Added `tcf_accel.schemas.api.*` request/response models for the
    frozen `/v1/` surface.
  * Added error subclasses for auth, validation, rate-limit, audio-short,
    rubric-mismatch, content-retired, scheduler-cache-miss, and the
    `E_NOT_IMPLEMENTED_001` envelope for Phase 2 stubs.
- 0.3.0 — Phase 3 (this version). Strictly additive:
  * New `QualityFlag` values `CEFR_HUMAN_OVERRIDDEN` and
    `TOPIC_OVER_CAPPED` (existing values unchanged).
  * `ItemMetadata` documents previously-undocumented optional fields
    used by the content pipeline (`cefr_confidence`,
    `cefr_distribution`, `canadian_context`, `co_acoustic`,
    `calibration_anchors`, `synthesis_trace_uri`); the model remains
    `extra="allow"` so the additions are non-breaking.
  * New `E_CONTENT_003..008` error subclasses
    (`IngestSourceUnavailableError`, `ContentLLMUnreliableError`,
    `CEFRClassifierUnavailableError`, `BankDistributionViolation`,
    `IngestLicenseMissingError`, `IngestLicenseIncompatibleError`).
  * New `confusable_pairs` table via Alembic migration
    `0002_confusable_pairs.py` — Phase 3 creates the table; Phase 4
    consumes it for LECTOR.
  Every Phase 2 round-trip test must continue to pass.
- 0.4.0 — Phase 5 (this version). Strictly additive:
  * `Interaction` gains optional `drill_kind` (Literal of the 21 Phase 5
    drill kinds plus `mock_section` and `diagnostic_item`),
    `pronunciation` (`PronunciationSignal | None`), and `audio_path`
    (local-only relative path under `data/` if the operator opted into
    audio retention; `None` by default per ADR-017).
  * New `PronunciationSignal` and `PronunciationProsody` models
    (ADR-031): coarse-proxy contract with `score`, `signal_kind`,
    `disclaimer_version`, `display_label`.
  * `DrillType` literal in `tcf_accel.schemas.api.plan` extends from
    9 to 26 values; legacy names remain valid.
  * New `AccessibilityProfile` model in `tcf_accel.schemas.api.me`
    (CO/EE/EO alternatives + dyslexia font + high contrast).
  * New `DismissalLogEntry` model in `tcf_accel.schemas.api.session`
    (local-only record of exam-shape floor dismissals; ADR-028).
  * New `E_SESSION_001..004`, `E_ASR_001`, `E_PRON_001`, `E_TTS_001`,
    `E_LLM_001` error subclasses.
  * Two new Alembic migrations: `0003_phase5_sessions_alter.py`
    (adds `paused_at`, `items_seen`, `items_correct`, `exam_shape`
    columns) and `0004_phase5_interactions_alter.py` (adds
    `drill_kind`, `pronunciation_signal`, `audio_path` columns).
  Phase 1–4 round-trip tests must continue to pass; a Phase 4
  consumer parsing a Phase 5 row sees `null` in the new optional
  fields (downgrade-safe).
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final[str] = "0.4.0"

__all__ = ["SCHEMA_VERSION"]
