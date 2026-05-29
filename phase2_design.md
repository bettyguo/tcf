# Phase 2 — DESIGN

> Phase 2 (`02_ARCHITECTURE.md §2`) — the frozen architecture, DB schema,
> Pydantic contracts, API surface, error taxonomy, observability seams, and
> test plan that the rest of the build depends on. After this phase, the
> OpenAPI spec is the law. Date: 2026-05-27.

---

## 0. Reading order

1. §1 service topology — the system at a glance.
2. §2 database schema — what's persisted.
3. §3 Pydantic contracts — what's on the wire / on the bus.
4. §4 API surface — every `/v1/` route, frozen.
5. §5 error taxonomy — every failure mode, with stable codes.
6. §6 observability — logs, metrics, traces, privacy.
7. §7 test plan — what proves the design.
8. §8 ADRs added in this phase — the seven new entries (0011–0017).
9. §9 implementation order — the dependency-ordered CODE checklist.

---

## 1. Service topology

```
                         ┌──────────────────┐
                         │   Web (Next 15)  │
                         │   apps/web       │
                         └────────┬─────────┘
                                  │ HTTPS / JSON
                ┌─────────────────┴──────────────────┐
                ▼                                    ▼
        ┌──────────────┐                    ┌──────────────┐
        │   API        │  ◀─── auth ───▶    │  ML svcs     │
        │   apps/api   │                    │  packages/ml │
        │   FastAPI    │                    │  (Phase 7)   │
        └──┬────────┬──┘                    └──────┬───────┘
           │        │                              │
   reads   │        │ enqueues + reads cache       │ submits jobs
           ▼        ▼                              ▼
        ┌──────────────┐                    ┌──────────────┐
        │  Postgres 16 │ ◀── pgvector ──────│  Redis 7     │
        │  + Alembic   │                    │  cache+queue │
        └──────────────┘                    └──────┬───────┘
                                                   │ Celery broker
                                                   ▼
                                            ┌──────────────┐
                                            │  Worker      │
                                            │  apps/worker │
                                            │  (scheduler, │
                                            │   estimator, │
                                            │   IRT refit) │
                                            └──────────────┘
```

**Service roles:**

| Service | Owner | Phase that fills it in |
|---|---|---|
| `apps/web` | Next.js 15 App Router; thin client over OpenAPI-generated SDK. | Phase 8. |
| `apps/api` | FastAPI; route stubs in Phase 2, handlers in Phases 3–8. | Phase 2 (stubs) + 3–8. |
| `apps/worker` | Celery worker; scheduler + estimator + IRT refit + auto-scorer jobs. | Phase 4 (scheduler), Phase 7 (scorer). |
| `packages/shared` | Pydantic schemas, ids, errors, version. | Phase 1 (Item/Score/error base) + Phase 2 (rubrics, content variants, error subclasses). |
| `packages/sla` | Scheduler + estimator implementations. | Phase 4. |
| `packages/ml` | ASR / TTS / writing / speaking models. | Phase 3 (ASR) + Phase 7 (scorers). |
| `packages/content` | Content pipeline. | Phase 3. |
| `packages/client-ts` | OpenAPI-generated TS SDK. | Phase 2 (generated). |
| `packages/client-py` | OpenAPI-generated Python SDK. | Phase 2 (generated). |
| Postgres 16 + pgvector | Single store for relational + vector. | Phase 2 (schema). |
| Redis 7 | Celery broker + result backend + cache. | Phase 1 (provisioned) + Phase 4 (cache contract). |
| Qdrant 1.10 | Reserved; not consumed in Phase 2. | Phase 4+ if pgvector swaps out. |

**Cross-service rule (Phase 1 anti-criterion 3, re-affirmed):** no service
imports another service's internals. All cross-service data flow goes
through `packages/shared` types over JSON (API) or Pydantic-validated
bytes on Redis (queue).

---

## 2. Database schema (canonical DDL)

All tables target Postgres 16 with the `pgvector` extension. The
migration (`infra/migrations/versions/0001_initial.py`) emits this exact
DDL via Alembic operations.

### 2.1 Identity

```sql
CREATE TABLE users (
  id                    UUID PRIMARY KEY,
  email                 TEXT UNIQUE NOT NULL,
  display_name          TEXT,
  password_hash         TEXT,                       -- argon2id; null until Phase 2 wires auth
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  target_nclc           INT NOT NULL DEFAULT 7
                        CHECK (target_nclc BETWEEN 4 AND 12),
  target_exam_date      DATE,
  daily_minutes_budget  INT NOT NULL DEFAULT 150
                        CHECK (daily_minutes_budget BETWEEN 15 AND 480),
  locale                TEXT NOT NULL DEFAULT 'en'
                        CHECK (locale IN ('en','fr','es','ar','zh')),
  privacy_mode          TEXT NOT NULL DEFAULT 'local_only'
                        CHECK (privacy_mode IN ('local_only','cloud_optin')),
  deleted_at            TIMESTAMPTZ
);
CREATE INDEX users_email_active ON users(email) WHERE deleted_at IS NULL;
```

`deleted_at` is the GDPR-style soft delete; the `DELETE /v1/data`
endpoint sets it + scrubs PII fields atomically. Hard-delete is a
separate scheduled job (Phase 9).

### 2.2 Item bank

```sql
CREATE TABLE items (
  id                    UUID PRIMARY KEY,
  module                TEXT NOT NULL CHECK (module IN ('CO','CE','EE','EO')),
  cefr_level            TEXT NOT NULL CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
  difficulty_irt        DOUBLE PRECISION,                  -- 2PL b; nullable until calibrated
  discrimination_irt    DOUBLE PRECISION DEFAULT 1.0,      -- 2PL a
  content               JSONB NOT NULL,                    -- Pydantic-validated at write
  metadata              JSONB NOT NULL DEFAULT '{}'::jsonb,
  embedding             VECTOR(768),                       -- multilingual MPNet dim
  provenance            JSONB NOT NULL,
  quality_flags         TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  synthetic             BOOLEAN NOT NULL DEFAULT FALSE,
  retired               BOOLEAN NOT NULL DEFAULT FALSE,
  schema_version        TEXT NOT NULL,                     -- pinned to tcf_accel SCHEMA_VERSION at write
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX items_module_level_difficulty
  ON items (module, cefr_level, difficulty_irt) WHERE NOT retired;
CREATE INDEX items_tags_gin
  ON items USING gin ((metadata->'tags'));
CREATE INDEX items_embedding_hnsw
  ON items USING hnsw (embedding vector_cosine_ops);
```

The `embedding` is `VECTOR(768)` (multilingual MPNet output dim,
ADR-0002). The HNSW index is built once; Phase 4 sets the parameters
empirically.

### 2.3 Interactions

```sql
CREATE TABLE interactions (
  id                    BIGSERIAL PRIMARY KEY,
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  item_id               UUID NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
  session_id            UUID NOT NULL,
  module                TEXT NOT NULL CHECK (module IN ('CO','CE','EE','EO')),
  correct               BOOLEAN,                       -- nullable for EE/EO (async grading)
  raw_response          JSONB NOT NULL,
  rt_ms                 INT CHECK (rt_ms IS NULL OR rt_ms >= 0),
  rating                INT CHECK (rating IS NULL OR rating BETWEEN 1 AND 4),
  fsrs_stability        DOUBLE PRECISION,
  fsrs_difficulty       DOUBLE PRECISION,
  graded_score          JSONB,                         -- per-rubric breakdown for EE/EO
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX interactions_user_created
  ON interactions (user_id, created_at DESC);
CREATE INDEX interactions_item_created
  ON interactions (item_id, created_at DESC);
CREATE INDEX interactions_user_session
  ON interactions (user_id, session_id, created_at);
```

Append-only. `ON DELETE CASCADE` on `user_id` because GDPR erasure cascades
through learner history; `ON DELETE RESTRICT` on `item_id` because we never
delete items (only retire them).

### 2.4 Per-skill posterior

```sql
CREATE TABLE skill_estimates (
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill                 TEXT NOT NULL CHECK (skill IN ('CO','CE','EE','EO')),
  posterior_mean        DOUBLE PRECISION NOT NULL,
  posterior_variance    DOUBLE PRECISION NOT NULL CHECK (posterior_variance >= 0),
  n_obs                 INT NOT NULL DEFAULT 0 CHECK (n_obs >= 0),
  last_updated          TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, skill)
);
```

One row per (user, skill). Updated online by the Phase 4 estimator on
session-finish.

### 2.5 Study plans

```sql
CREATE TABLE study_plans (
  id                    UUID PRIMARY KEY,
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  generated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  horizon_days          INT NOT NULL CHECK (horizon_days BETWEEN 1 AND 365),
  daily_blocks          JSONB NOT NULL,
  rationale             TEXT NOT NULL,
  superseded            BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX study_plans_user_active
  ON study_plans (user_id, generated_at DESC) WHERE NOT superseded;
```

A new plan is inserted; the previous active plan is marked `superseded`
(no `UPDATE`, no in-place mutation). Phase 4 owns the regeneration
trigger (posterior delta > threshold).

### 2.6 Mock exams

```sql
CREATE TABLE mock_exams (
  id                    UUID PRIMARY KEY,
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  mode                  TEXT NOT NULL DEFAULT 'canonical'
                        CHECK (mode IN ('canonical','training')),
  started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at           TIMESTAMPTZ,
  per_module_score      JSONB,
  estimated_nclc        JSONB,                      -- per-skill with CI
  raw_log               JSONB
);
CREATE INDEX mock_exams_user_started
  ON mock_exams (user_id, started_at DESC);
```

### 2.7 Submissions (EE / EO async grading)

```sql
CREATE TABLE submissions (
  id                    UUID PRIMARY KEY,
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  item_id               UUID NOT NULL REFERENCES items(id),
  module                TEXT NOT NULL CHECK (module IN ('EE','EO')),
  status                TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','grading','graded','failed')),
  payload_uri           TEXT NOT NULL,             -- s3://, file://, etc.; the artifact lives outside the DB
  payload_bytes         INT NOT NULL CHECK (payload_bytes >= 0),
  payload_sha256        TEXT NOT NULL,
  rubric                JSONB,                     -- WritingRubric or SpeakingRubric when graded
  error                 JSONB,                     -- {code, message, context} when failed
  submitted_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  graded_at             TIMESTAMPTZ
);
CREATE INDEX submissions_user_submitted
  ON submissions (user_id, submitted_at DESC);
CREATE INDEX submissions_status_submitted
  ON submissions (status, submitted_at) WHERE status IN ('pending','grading');
```

Critically: the *artifact* (the writing text, the audio bytes) lives at
`payload_uri`, **not** in the database. `payload_sha256` is the
fingerprint we log; we never log the content itself (master prompt §6.4
+ §6 below).

### 2.8 Diagnostic sessions

```sql
CREATE TABLE diagnostic_sessions (
  id                    UUID PRIMARY KEY,
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at           TIMESTAMPTZ,
  state                 JSONB NOT NULL,           -- adaptive-step pointer, per-skill estimate-in-progress
  final_estimates       JSONB                     -- NCLCEstimate per skill on finish
);
CREATE INDEX diagnostic_sessions_user_started
  ON diagnostic_sessions (user_id, started_at DESC);
```

### 2.9 Practice sessions

```sql
CREATE TABLE sessions (
  id                    UUID PRIMARY KEY,
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  module                TEXT NOT NULL CHECK (module IN ('CO','CE','EE','EO')),
  drill_type            TEXT NOT NULL,            -- 'flashcard'|'cloze'|'shadowing'|... Phase 5 enumerates
  target_minutes        INT NOT NULL CHECK (target_minutes BETWEEN 1 AND 240),
  started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at           TIMESTAMPTZ,
  summary               JSONB                     -- counts, deltas; written on finish
);
CREATE INDEX sessions_user_started
  ON sessions (user_id, started_at DESC);
```

### 2.10 Reference tables (seed-only)

No additional reference tables in Phase 2. CEFR levels and module codes
are `CHECK` constraints (small, frozen, enforced inline). If we need a
"skill catalog" later (Phase 4 may introduce sub-skills), it goes in a
follow-up migration.

### 2.11 Migration ordering

`0001_initial.py` creates everything in this order:

1. Extensions: `CREATE EXTENSION IF NOT EXISTS vector` (also installed by
   `infra/initdb/01-enable-pgvector.sql` for non-Alembic flows).
2. `users` (no FK dependencies).
3. `items` (no FK dependencies).
4. `interactions` (FKs → users, items).
5. `skill_estimates` (FK → users).
6. `study_plans` (FK → users).
7. `mock_exams` (FK → users).
8. `submissions` (FKs → users, items).
9. `diagnostic_sessions` (FK → users).
10. `sessions` (FK → users).
11. All indexes (last, so a partial-restore is still consistent).

`downgrade()` drops in reverse order. Both are tested in Phase 2 audit.

---

## 3. Pydantic schema contracts

Phase 1 shipped a permissive `ItemContent` placeholder. Phase 2 narrows
it to a discriminated union and adds rubric schemas. The narrowing is
**additive**: every valid Phase 1 `Item` continues to validate.

Layout under `packages/shared/src/tcf_accel/schemas/`:

```
schemas/
├── __init__.py          # re-exports
├── common.py            # Phase 1: Provenance, QualityFlag, ItemMetadata, ReviewStatus
├── item.py              # Phase 1: Item; Phase 2: narrowed ItemContent union, supporting types
├── content/             # Phase 2: per-module content models
│   ├── __init__.py
│   ├── co.py            # COContent + Speaker + MCQ
│   ├── ce.py            # CEContent
│   ├── ee.py            # EEContent + ErrorAnnotation
│   └── eo.py            # EOContent
├── scoring.py           # Phase 1: Score, NCLCEstimate; Phase 2: WritingRubric, SpeakingRubric
├── api/                 # Phase 2: request/response models per route
│   ├── __init__.py
│   ├── auth.py          # SignupRequest, LoginRequest, TokenPair
│   ├── me.py            # MeProfile, UpdateMeRequest
│   ├── diagnostic.py    # DiagnosticState, DiagnosticAnswer, DiagnosticReport
│   ├── plan.py          # StudyPlanView, DailyBlock
│   ├── session.py       # SessionStart, SessionItem, SessionAnswer, SessionSummary
│   ├── submission.py    # SubmissionView
│   ├── mock_exam.py     # MockExamState, MockExamReport
│   ├── insights.py      # NCLCTrajectory, WeakPoint, Readiness
│   └── errors.py        # ErrorEnvelope (the on-the-wire error body)
└── version.py           # SCHEMA_VERSION
```

### 3.1 Content variants (`schemas/content/`)

```python
# common discriminated by Item.module
class Speaker(BaseModel):
    label: str                              # e.g. "Speaker A", "Annick"
    accent: Literal["fr-FR","fr-CA","fr-BE","fr-CH","fr-AF","mixed"]

class MCQOption(BaseModel):
    id: str                                 # short slug, e.g. "a", "b"
    text: str

class MCQ(BaseModel):
    id: str
    prompt: str
    options: list[MCQOption]                # ≥2
    correct_option_id: str
    explanation: str | None = None

# CO
class COContent(BaseModel):
    module: Literal["CO"] = "CO"            # discriminator
    transcript: str
    audio_url: AnyHttpUrl | None = None
    audio_local_path: str | None = None     # for cached local audio
    duration_s: float = Field(ge=1, le=600)
    speakers: list[Speaker] = Field(min_length=1)
    accent: Literal["fr-FR","fr-CA","fr-BE","fr-CH","fr-AF","mixed"]
    register: Literal["soutenu","standard","familier"]
    questions: list[MCQ] = Field(min_length=1)

# CE
class CEContent(BaseModel):
    module: Literal["CE"] = "CE"
    passage: str
    genre: Literal["news","ad","letter","admin","academic","narrative"]
    word_count: int = Field(ge=20, le=2000)
    questions: list[MCQ] = Field(min_length=1)

# EE
class ErrorAnnotation(BaseModel):
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)
    error_type: Literal[
        "spelling","agreement","tense","preposition","article","syntax",
        "register","vocabulary","cohesion","other",
    ]
    suggestion: str | None = None
    confidence: float = Field(ge=0, le=1)

class EEContent(BaseModel):
    module: Literal["EE"] = "EE"
    task_number: Literal[1, 2, 3]
    prompt: str
    target_word_count_range: tuple[int, int]    # (min, max)
    required_canadian_context: bool             # True for Task 2 & 3
    rubric_version: str                         # pinned per release

# EO
class EOContent(BaseModel):
    module: Literal["EO"] = "EO"
    task_number: Literal[1, 2, 3]
    examiner_prompts: list[str] = Field(min_length=1)
    candidate_prep_time_s: int = Field(ge=0, le=600)
    target_duration_s: int = Field(ge=30, le=600)
    rubric_version: str

# union
ItemContent = Annotated[
    COContent | CEContent | EEContent | EOContent,
    Field(discriminator="module"),
]
```

The `ItemContent` symbol is re-exported from `schemas/__init__.py`
*replacing* the Phase 1 permissive class. The replacement is additive
because:

- The Phase 1 `ItemContent` had `model_config = ConfigDict(extra="allow")`
  and only required a `module` discriminator.
- Phase 1 round-trip tests passed *any* dict with `{"module": "CE", ...}`;
  Phase 2 round-trip tests pass *any* dict that validates against the new
  union.
- Phase 1 had no fixture data persisted yet (Phase 1 ships only the
  in-memory examples in docstrings), so no migration is required.

### 3.2 Rubric schemas (`schemas/scoring.py`)

```python
class WritingRubric(BaseModel):
    task_completion: int = Field(ge=0, le=5)
    coherence_cohesion: int = Field(ge=0, le=5)
    lexical_range: int = Field(ge=0, le=5)
    grammatical_accuracy: int = Field(ge=0, le=5)
    register_appropriateness: int = Field(ge=0, le=5)
    canadian_context_integration: int | None = Field(default=None, ge=0, le=5)  # Tasks 2 & 3
    total_20: int = Field(ge=0, le=20)
    error_density_per_100w: float = Field(ge=0)
    type_token_ratio: float = Field(ge=0, le=1)
    discourse_marker_count: int = Field(ge=0)
    error_list: list[ErrorAnnotation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _total_invariant(self) -> Self:
        components = [
            self.task_completion, self.coherence_cohesion, self.lexical_range,
            self.grammatical_accuracy, self.register_appropriateness,
        ]
        expected = round(sum(components) * 4 / 5)            # 5 components → 0..25 → scaled to 20
        if abs(self.total_20 - expected) > 1:                # allow off-by-one for the rubric calibrator
            raise ValueError(f"total_20={self.total_20} inconsistent with components={components}")
        return self

class SpeakingRubric(BaseModel):
    task_completion: int = Field(ge=0, le=5)
    fluency_pace: int = Field(ge=0, le=5)
    pronunciation_prosody: int = Field(ge=0, le=5)
    lexical_range: int = Field(ge=0, le=5)
    grammatical_accuracy: int = Field(ge=0, le=5)
    interaction_responsiveness: int = Field(ge=0, le=5)
    total_20: int = Field(ge=0, le=20)
    wpm: float = Field(ge=0)
    pause_ratio: float = Field(ge=0, le=1)
    phoneme_error_rate: float | None = Field(default=None, ge=0, le=1)
```

The `total_20` invariant for `WritingRubric` mirrors the documented rubric
scaling in `00_MASTER_PROMPT.md §2.1.5`; Phase 7 may refine the formula
but the *invariant pattern* (component-derived, off-by-one allowed for
calibration) is the frozen contract.

### 3.3 API request/response models (`schemas/api/`)

One file per route group, each containing the request body, response
body, and any path/query schemas. Names are the wire shape; the handler
implementations land in Phases 3–8.

Phase 2 ships these as **placeholder** Pydantic models with the
canonical fields documented; OpenAPI generation runs against them so
the frozen `openapi.v1.yaml` carries the shape downstream. Subsequent
phases may add fields (additive) without breaking the wire.

### 3.4 Discriminator + version stamp

`Item.schema_version` is set automatically to `SCHEMA_VERSION` at
construction. Phase 2 bumps `SCHEMA_VERSION` to `"0.2.0"` to mark the
additive narrowing.

---

## 4. API surface (frozen `/v1/`)

The full route table is in §4.4. Every route is registered in Phase 2
with a Pydantic request/response model, a `tags=[...]` group, and a
handler that returns:

```python
raise HTTPException(
    status_code=501,
    detail={"code": "E_NOT_IMPLEMENTED", "phase": OWNER_PHASE, "route": REQUEST_PATH},
)
```

…where `OWNER_PHASE` is the phase that owns the eventual implementation,
per the table below.

### 4.1 Versioning policy (ADR-016)

- URL versioning: `/v1/...`.
- Additive changes (new optional fields, new routes) ship under `/v1/`
  with a minor `SCHEMA_VERSION` bump and a `CHANGELOG.md` entry.
- Breaking changes ship a new `/v2/` namespace; `/v1/` is supported for
  ≥ 6 months past `/v2/` GA, then sunset with a `410 Gone` and a
  `Sunset:` header pointing at the migration doc.
- Routes that change shape silently (added required fields, renamed
  fields) are *not allowed* under `/v1/`; PR review enforces this.

### 4.2 Authentication

- `bearerAuth` via JWT (HS256 in dev, RS256 in prod).
- Access token TTL 15 min, refresh 30 days (per `.env.example`).
- Protected routes: everything except `POST /v1/auth/signup`,
  `POST /v1/auth/login`, `GET /healthz`, `GET /v1/health`.

### 4.3 Error envelope

Every non-2xx response carries a JSON body of shape:

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

`phase` is set only on `501 E_NOT_IMPLEMENTED` to indicate which build
phase owns the implementation.

### 4.4 Route table

| Method | Path | Tags | Owner phase | Notes |
|---|---|---|---|---|
| GET  | `/healthz`                          | meta         | (Phase 1) | Liveness; ships from Phase 1. |
| GET  | `/v1/health`                        | meta         | 2 | Same shape as `/healthz`, mounted under `/v1/`. |
| POST | `/v1/auth/signup`                   | auth         | 3 | Body: `SignupRequest`. Resp: `TokenPair`. |
| POST | `/v1/auth/login`                    | auth         | 3 | Body: `LoginRequest`. Resp: `TokenPair`. |
| POST | `/v1/auth/refresh`                  | auth         | 3 | Body: `{refresh_token}`. Resp: `TokenPair`. |
| GET  | `/v1/me`                            | me           | 3 | Resp: `MeProfile`. |
| PATCH| `/v1/me`                            | me           | 3 | Body: `UpdateMeRequest`. Resp: `MeProfile`. |
| POST | `/v1/diagnostic/start`              | diagnostic   | 5 | Resp: `DiagnosticState`. |
| POST | `/v1/diagnostic/{id}/answer`        | diagnostic   | 5 | Body: `DiagnosticAnswer`. |
| POST | `/v1/diagnostic/{id}/finish`        | diagnostic   | 5 | Resp: `DiagnosticReport`. |
| GET  | `/v1/plan`                          | plan         | 4 | Resp: `StudyPlanView`. |
| POST | `/v1/plan/regenerate`               | plan         | 4 | Resp: `StudyPlanView`. |
| GET  | `/v1/plan/today`                    | plan         | 4 | Resp: `list[DailyBlock]`. |
| POST | `/v1/session/start`                 | session      | 5 | Body: `SessionStart`. Resp: `SessionState`. |
| GET  | `/v1/session/{id}/next`             | session      | 5 | Resp: `SessionItem`. |
| POST | `/v1/session/{id}/answer`           | session      | 5 | Body: `SessionAnswer`. |
| POST | `/v1/session/{id}/finish`           | session      | 5 | Resp: `SessionSummary`. |
| POST | `/v1/submission/ee`                 | submission   | 7 | multipart/form-data; Resp: `SubmissionView` (status=pending). |
| POST | `/v1/submission/eo`                 | submission   | 7 | multipart/form-data; Resp: `SubmissionView` (status=pending). |
| GET  | `/v1/submission/{id}`               | submission   | 7 | Resp: `SubmissionView` (graded → `rubric`). |
| POST | `/v1/mock-exam/start`               | mock-exam    | 6 | Resp: `MockExamState`. |
| GET  | `/v1/mock-exam/{id}/state`          | mock-exam    | 6 | Resp: `MockExamState`. |
| POST | `/v1/mock-exam/{id}/submit`         | mock-exam    | 6 | Resp: `MockExamState`. |
| GET  | `/v1/mock-exam/{id}/report`         | mock-exam    | 6 | Resp: `MockExamReport`. |
| GET  | `/v1/insights/nclc-trajectory`      | insights     | 8 | Resp: `NCLCTrajectory`. |
| GET  | `/v1/insights/weak-points`          | insights     | 8 | Resp: `list[WeakPoint]`. |
| GET  | `/v1/insights/readiness`            | insights     | 8 | Resp: `Readiness`. |
| GET  | `/v1/data/export`                   | data         | 9 | Resp: NDJSON stream (`Content-Type: application/x-ndjson`). |
| DELETE | `/v1/data`                        | data         | 9 | Resp: `{deleted: true, scheduled_purge_at}`. |

Total: 1 (Phase 1) + 27 (Phase 2) = **28** routes.

### 4.5 OpenAPI freeze

After the routes are registered, the build runs:

```
uv run python -m tcf_accel_api.scripts.export_openapi \
    --output docs/api/openapi.v1.yaml
```

The output is committed and CI checks that the file on disk equals the
file the running app emits. A drift = a contract change → must be an
intentional PR + a `SCHEMA_VERSION` bump.

Schemathesis (`tests/contract/test_openapi_v1.py`) loads the file and
runs property-based fuzz against every route: every request the spec
permits must produce either a documented response or a `501`.

---

## 5. Error taxonomy

### 5.1 Code shape and stability

Codes are `E_<DOMAIN>_<NNN>`:

| Domain | Range | Examples |
|---|---|---|
| `E_BASE`     | 000      | base class. |
| `E_CONTENT`  | 001..099 | content-bank availability, fixture loading. |
| `E_SCHED`    | 001..099 | scheduler invariants. |
| `E_SCORING`  | 001..099 | ASR / writing / speaking grading. |
| `E_CALIB`    | 001..099 | NCLC estimator. |
| `E_AUTH`     | 001..099 | authn / authz. |
| `E_VALIDATION` | 001..099 | request body validation (mapped from Pydantic). |
| `E_RATE_LIMIT` | 001..099 | quota / abuse. |
| `E_NOT_IMPLEMENTED` | 001 | phase-2 stub. |

Code stability is the ADR-014 promise. Renaming a code is forbidden;
codes are *added* monotonically. A code that becomes unused is *retired*
(documented in `RATIONALE.md`) but never reissued.

### 5.2 Phase 2 error catalog (additive over Phase 1's seed)

| Code | Class | HTTP | Message key |
|---|---|---|---|
| `E_BASE_000`        | `TCFAccelError`              | 500 | base |
| `E_CONTENT_001`     | `ContentNotAvailableError`   | 404 | `content.not_available` |
| `E_CONTENT_002`     | `ItemRetiredError`           | 410 | `content.item_retired` (NEW) |
| `E_SCHED_001`       | `SchedulerError`             | 500 | `scheduler.generic` |
| `E_SCHED_002`       | `SchedulerCacheMissError`    | 503 | `scheduler.cache_miss` (NEW) |
| `E_SCORING_001`     | `ScoringError`               | 500 | `scoring.generic` |
| `E_SCORING_002`     | `ASRConfidenceTooLowError`   | 422 | `scoring.asr_low_confidence` |
| `E_SCORING_003`     | `TextTooShortError`          | 422 | `scoring.text_too_short` |
| `E_SCORING_004`     | `AudioTooShortError`         | 422 | `scoring.audio_too_short` (NEW) |
| `E_SCORING_005`     | `RubricMismatchError`        | 500 | `scoring.rubric_mismatch` (NEW) |
| `E_CALIB_001`       | `CalibrationError`           | 503 | `calibration.generic` |
| `E_CALIB_002`       | `InsufficientObservationsError` | 409 | `calibration.insufficient_obs` |
| `E_AUTH_001`        | `AuthError`                  | 401 | `auth.generic` (NEW) |
| `E_AUTH_002`        | `InvalidCredentialsError`    | 401 | `auth.invalid_credentials` (NEW) |
| `E_AUTH_003`        | `TokenExpiredError`          | 401 | `auth.token_expired` (NEW) |
| `E_AUTH_004`        | `TokenInvalidError`          | 401 | `auth.token_invalid` (NEW) |
| `E_AUTH_005`        | `ForbiddenError`             | 403 | `auth.forbidden` (NEW) |
| `E_VALIDATION_001`  | `RequestValidationError`     | 422 | `validation.request_body` (NEW) |
| `E_RATE_LIMIT_001`  | `RateLimitError`             | 429 | `rate_limit.exceeded` (NEW) |
| `E_NOT_IMPLEMENTED_001` | `NotImplementedRouteError` | 501 | `not_implemented` (NEW; the Phase 2 stub) |

The error module exposes `to_envelope()` for the API layer, returning
the JSON shape in §4.3. The localized `message_localized` field carries
EN + FR strings; the rendered `message` defaults to EN.

### 5.3 EN + FR message catalog

Per master prompt §6.3, learner-facing messages are localized at least
in EN + FR. Other locales (es, ar, zh) are deferred to Phase 8 when the
i18n system is in place; the contract is "the catalog supports adding
keys without code changes."

The catalog lives at
`packages/shared/src/tcf_accel/errors/messages.py`:

```python
# Keyed by message_key (above table); values are dicts of locale → template.
MESSAGES: Final[Mapping[str, Mapping[str, str]]] = {
    "scoring.asr_low_confidence": {
        "en": "We couldn't transcribe the audio confidently (score={score:.2f}). Please re-record in a quieter setting.",
        "fr": "Nous n'avons pas pu transcrire l'audio avec assez de confiance (score={score:.2f}). Veuillez réenregistrer dans un environnement plus calme.",
    },
    "scoring.text_too_short": {
        "en": "Your response is {word_count} words; this task expects at least {minimum}.",
        "fr": "Votre réponse fait {word_count} mots ; cette tâche en attend au moins {minimum}.",
    },
    # …one entry per key in §5.2
}
```

A unit test enforces that every code in §5.2 has a message key and that
every key has both `en` and `fr` templates.

### 5.4 Coverage promise

Phase 2 audit verifies that every `raise <subclass of TCFAccelError>` in
`apps/api` and `packages/*` carries a stable code (no anonymous raises
of the base class). Future phases inherit this check via the same test.

---

## 6. Observability

### 6.1 Logs

- **Library:** `loguru` (Phase 1 dependency).
- **Format:** JSON line per record, with at least: `ts`, `level`,
  `service`, `request_id`, `user_id_hashed`, `route`, `latency_ms`,
  `status`, `error_code`.
- **Sink:** stdout. Containers ship logs to whatever the operator's
  collector ingests (Loki, CloudWatch, etc.).
- **Privacy:** no learner *text*, no learner *audio bytes*, no email
  addresses, no JWTs in logs. User IDs are passed through as UUIDs
  (already non-identifying); when a deeper identifier is required for
  debugging, log the SHA-256 hash. (ADR-017 + master prompt §6.4.)

### 6.2 Metrics

- **Library:** `prometheus_client`.
- **Endpoint:** `/metrics` on the `apps/api` service; scraped by the
  operator's Prometheus.
- **SLO metrics (the four Phase 2 commitments):**
  1. `tcf_api_request_duration_seconds{route, status}` — histogram; p95
     gate set in Phase 9 audit.
  2. `tcf_itembank_hit_rate{module, cefr}` — gauge; computed by the
     content cache; alerts if < 0.95 sustained.
  3. `tcf_scheduler_latency_seconds{phase}` — histogram; gate < 200 ms
     p95 for the cache-fill job.
  4. `tcf_scoring_success_rate{module}` — gauge; alerts if < 0.98
     sustained.
- **Process metrics:** default Prometheus instrumentation
  (`Process*`, `Python*`).
- **Worker metrics:** Celery exposes `celery_*` via a sidecar exporter
  in `infra/docker-compose.yml` (added Phase 2).

### 6.3 Traces

- **Library:** OpenTelemetry SDK (`opentelemetry-instrumentation-fastapi`,
  `opentelemetry-instrumentation-sqlalchemy`,
  `opentelemetry-instrumentation-celery`).
- **Sampling:** 5% in prod, 100% locally (per `.env.example`).
- **Privacy:** same rules as logs. Span attributes carry IDs and sizes,
  never content.
- **Exporter:** OTLP/HTTP to `OTEL_EXPORTER_OTLP_ENDPOINT` (env-driven);
  default unset → in-memory exporter (no leak).

### 6.4 Privacy contract (Phase 2-binding)

Phase 2 audits enforce:

- No code path under `apps/api` or `apps/worker` calls
  `logger.info(...)` with a learner text/audio variable in the format
  string. (A lint rule + a test scanning `**/*.py` for
  `logger.\\w+\\(.*(text|audio|transcript|content)`.)
- All submission payloads are stored at `submissions.payload_uri`; the
  bytes are *not* in the DB.
- Outbound LLM calls obey `users.privacy_mode`; the API gateway refuses
  to call cloud LLMs for `local_only` users. (Phase 7 enforces in the
  scorer; Phase 2 reserves the seam.)

---

## 7. Test plan

### 7.1 Unit tests

- Every schema in `packages/shared/src/tcf_accel/schemas/`:
  - Construction with valid data succeeds.
  - Construction with invalid data raises `ValidationError`.
  - Round-trip: `Model.model_validate(model.model_dump()) == model`.
- Every error class in `tcf_accel.errors`:
  - `code` is set and matches its `E_<DOMAIN>_<NNN>` shape.
  - `http_status` is in `{400, 401, 403, 404, 409, 410, 422, 429, 500,
    501, 503}`.
  - `message_template` renders without `KeyError` given the documented
    context keys.

### 7.2 Property-based tests (Hypothesis)

Phase 2 ships the *scaffolding* for the eventual Phase 4 invariants:

- **`Score` CI invariant**: `ci_low ≤ nclc ≤ ci_high` holds under random
  inputs. (Already in Phase 1; we re-affirm.)
- **`NCLCEstimate` CI invariant**: `ci_low ≤ posterior_mean ≤ ci_high`
  with 0.5-band tolerance.
- **`ItemContent` discrimination**: for any of the four module strings,
  the union picks the right concrete class.
- **Pydantic round-trip** on every model in the contract surface.

Phase 4 will add the *behavioral* invariants (monotonicity, calibration).

### 7.3 Contract tests (Schemathesis)

- Load `docs/api/openapi.v1.yaml`.
- For each route, generate up to 50 schema-conformant requests.
- Assert every response is either a documented 2xx/4xx or a 501 with
  the `E_NOT_IMPLEMENTED_001` envelope.
- Assert response bodies validate against the documented response
  schema (this is what catches "the route exists but returns the wrong
  shape").

### 7.4 Integration tests

- `docker compose -f infra/docker-compose.yml up -d db redis qdrant`
  must reach healthy state.
- `alembic upgrade head` against the live DB.
- A seed script (`scripts/seed_phase2.py`) inserts 50 demo items
  (validated against the Phase 2 union), 1 demo user, 1 demo session.
- A smoke test exercises `/healthz` + `/v1/health` over HTTP.
- `alembic downgrade base` followed by `alembic upgrade head` round-trips
  cleanly.

### 7.5 E2E tests

Phase 2 reserves a single Playwright test that hits the running web app
and confirms the OpenAPI client successfully calls `GET /v1/health`.
Full E2E (a 30-minute synthetic session) lands Phase 8.

### 7.6 Pedagogical regression

`tests/pedagogy/golden_learner.jsonl` carries a hand-curated synthetic
200-interaction trajectory. Phase 2 ships the fixture + a *parser test*
that asserts it deserializes into the contract types. Phase 4 ships the
*behavior* test (the planner output on this trajectory is the golden
output; deviations require an intentional regeneration with a diff
review).

### 7.7 Coverage and CI

- `make test` runs all of the above (Phase 1 dev loop).
- `make phase2-verify` runs `make verify` + the Schemathesis suite +
  Alembic up/down + the integration smoke. Added to `Makefile` in
  Phase 2's CODE stage.
- CI matrix unchanged: `{ubuntu-latest, macos-latest} × py3.12 × node22`.
  Postgres + Redis come from `services:` blocks in `ci.yml` (added
  Phase 2).

---

## 8. ADRs added in this phase

Seven new ADRs land in `docs/adrs/`:

| ADR | Title | Decision |
|---|---|---|
| 0011 | JSONB content vs polymorphic tables | JSONB + Pydantic at the boundary. |
| 0012 | Pre-computed schedule cache vs on-demand | Pre-computed + explicit invalidation + TTL safety net. |
| 0013 | Online Bayesian per-skill update + nightly IRT refit | Two code paths, one for each math shape. |
| 0014 | Error code taxonomy stability promise | Codes are public API; never renamed. |
| 0015 | pgvector first, Qdrant as a swap-in if scale demands | Affirms ADR-0002 with the explicit swap criteria. |
| 0016 | API versioning policy | URL `/v1/`, additive-only, breaking → `/v2/` with ≥ 6 mo overlap. |
| 0017 | Privacy default = `local_only` | No cloud anything until explicit opt-in. |

Each ADR carries a `What would change our mind` section with a concrete
empirical trigger (`phase2_think.md §2`).

---

## 9. Implementation order (CODE checklist)

Phase 2's CODE stage executes this order; each step is unblocked by the
previous one:

1. **Schemas first.** Extend `packages/shared` with the new content
   models, rubric models, and API request/response models. Bump
   `SCHEMA_VERSION` to `0.2.0`. (Phase 1 schemas are untouched except
   for `ItemContent` narrowing, which is additive.)
2. **Error taxonomy.** Add the new error classes (§5.2) and the EN+FR
   message catalog (§5.3). Tests for code uniqueness and message
   coverage.
3. **Alembic migration.** `infra/migrations/versions/0001_initial.py`
   with the DDL in §2. Tests for up/down round-trip.
4. **API stubs.** One module per route group under
   `apps/api/src/tcf_accel_api/routes/`. Each route registered with its
   Pydantic models; each handler raises the 501 envelope.
5. **OpenAPI freeze.** A small `tcf_accel_api.scripts.export_openapi`
   CLI that writes `docs/api/openapi.v1.yaml` from the running app.
   Commit the file.
6. **Generated clients.** `packages/client-ts` (via
   `openapi-typescript`) and `packages/client-py` (via
   `openapi-python-client`). Phase 2 ships the *generation script* and
   the *first generated output*; subsequent phases regenerate as the
   spec evolves additively.
7. **Golden learner fixture.** `tests/pedagogy/golden_learner.jsonl`
   with 200 contract-typed interactions. Parser test.
8. **Test suite.** Schemathesis contract test + property-based
   round-trip + error-taxonomy coverage + integration up/down.
9. **Risk register + CHANGELOG.** Append Phase 2 deltas.
10. **Audit + Evaluate docs.** `phase2_audit.md` + `phase2_evaluate.md`.

---

## 10. Out-of-scope guardrails

A Phase 2 PR is rejected if it introduces:

- Business logic in any `/v1/` handler (must remain 501 in Phase 2).
- Schedulers, estimators, scorers, or rankers (Phases 4 / 7).
- Frontend routes or views (Phase 8).
- Migrations beyond `0001_initial` (any data shape change beyond the
  initial DDL belongs in a separate ADR + a `0002_*` migration in the
  owning phase).
- A new locale beyond EN + FR for error messages (Phase 8).
- Any cloud-only feature path with no `local_only` equivalent (ADR-017).

---

## 11. Hand-off to CODE

The CODE stage executes §9 in order. The AUDIT stage verifies:

- `alembic upgrade head` + `alembic downgrade base` both succeed.
- Pydantic round-trip property test green.
- `make verify` green.
- Schemathesis fuzz returns no contract drift.
- The OpenAPI spec validates against the OpenAPI 3.1 schema.
- Every `raise` in `apps/api` and `packages/*` is a stable-coded
  `TCFAccelError` subclass.
- `phase2_design.md` is self-contained enough for a fresh reviewer to
  recover the architecture in one paragraph (audit self-check).

The EVALUATE stage maps acceptance criteria to evidence, updates the
risk register, and writes the one-page hand-off to Phase 3.
