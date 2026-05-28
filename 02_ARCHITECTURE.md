# PHASE 2 — System Architecture, Data Model & API Contracts

> Goal: a frozen architecture that lets Phases 3–8 proceed in parallel without contract churn. After this phase, the OpenAPI spec is the law.

---

## 1. THINK (produce `phase2_think.md`)

### 1.1 The Three Hardest Architectural Questions

1. **Where does the learner model live?** Options:
   - (a) Inside the API service. Simplest. Cost: scheduler computations block request threads.
   - (b) In a dedicated `sla-service` consumed via gRPC. Clean. Cost: extra deploy unit, latency.
   - (c) In Celery workers, with the API consuming pre-computed schedules from a cache. Decoupled. Cost: cache invalidation complexity.
   - **Pick (c).** Reason: scheduling on review is bursty (1000s of cards re-rated at end of session); we don't want the user waiting for the API to recompute the whole queue. Pre-compute, cache, invalidate.

2. **How do we represent items across four modules with different shapes?** Options:
   - (a) One `items` table with a JSONB `content` column.
   - (b) Four tables, one per module.
   - (c) Polymorphic SQLAlchemy with a base `Item` and four subclasses.
   - **Pick (a) with strict Pydantic validation at the boundary.** Reason: querying across modules (mock exams, recommender) is constant; the JSONB is validated on write and indexed on the queryable fields (`module`, `cefr_level`, `difficulty_irt`, `tags`). Polymorphism adds ORM complexity without query benefit.

3. **How do we keep the NCLC estimator from going stale?** Options:
   - (a) Recompute on every interaction.
   - (b) Recompute on session-end + nightly batch.
   - (c) Streaming Bayesian update (online).
   - **Pick (c) for per-skill posterior + (b) for the IRT item-difficulty re-fit.** Reason: per-skill is cheap (closed-form conjugate update); item difficulty fit is expensive and only needs daily refresh.

### 1.2 What Would Change Our Mind

- If pgvector becomes a query bottleneck above ~10M embeddings: swap to Qdrant (the schemas are designed to be vector-DB-agnostic).
- If learner cohorts exceed 10k: split the API into read/write services and add a queue between.
- If LLM costs dominate: cache canonical EE/EO feedback by error-signature + add a cheaper local fallback.

---

## 2. DESIGN (produce `phase2_design.md`)

### 2.1 Service Topology

```
                       ┌────────────────┐
                       │   Web (Next)   │
                       └───────┬────────┘
                               │ HTTPS
            ┌──────────────────┼───────────────────┐
            ▼                  ▼                   ▼
        ┌─────────┐       ┌─────────┐         ┌──────────┐
        │  API    │◀────▶│  Redis   │◀───────▶│  Worker  │
        │ FastAPI │       │  cache   │         │  Celery  │
        └────┬────┘       │  +queue  │         └────┬─────┘
             │            └─────────┘               │
             │                                       │
       ┌─────▼─────┐                           ┌─────▼──────┐
       │ Postgres  │◀── pgvector ──────────────▶  ML svcs   │
       │  +Alembic │                           │  (ASR/TTS/ │
       └───────────┘                           │   scorer)  │
                                               └────────────┘
```

### 2.2 Database Schema (canonical tables)

```sql
-- Identity
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE,
  display_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  target_nclc INT NOT NULL CHECK (target_nclc BETWEEN 4 AND 12),
  target_exam_date DATE,
  daily_minutes_budget INT NOT NULL DEFAULT 150,
  locale TEXT NOT NULL DEFAULT 'en',
  privacy_mode TEXT NOT NULL DEFAULT 'local_only'
    CHECK (privacy_mode IN ('local_only','cloud_optin'))
);

-- Items (CO/CE/EE/EO) — single table, JSONB content
CREATE TABLE items (
  id UUID PRIMARY KEY,
  module TEXT NOT NULL CHECK (module IN ('CO','CE','EE','EO')),
  cefr_level TEXT NOT NULL CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
  difficulty_irt DOUBLE PRECISION,            -- IRT b-parameter, set in Phase 4
  discrimination_irt DOUBLE PRECISION DEFAULT 1.0,  -- 2PL a-parameter
  content JSONB NOT NULL,                     -- validated by Pydantic at write
  metadata JSONB NOT NULL DEFAULT '{}',
  embedding VECTOR(768),                       -- for LECTOR + retrieval
  provenance JSONB NOT NULL,                  -- source, license, ingested_at
  quality_flags TEXT[] NOT NULL DEFAULT '{}',
  synthetic BOOLEAN NOT NULL DEFAULT false,
  retired BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX items_module_level_difficulty ON items(module, cefr_level, difficulty_irt) WHERE NOT retired;
CREATE INDEX items_embedding_hnsw ON items USING hnsw (embedding vector_cosine_ops);

-- Interactions (every review/answer)
CREATE TABLE interactions (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  item_id UUID NOT NULL REFERENCES items(id),
  session_id UUID NOT NULL,
  module TEXT NOT NULL,
  correct BOOLEAN,                            -- nullable for EE/EO (graded async)
  raw_response JSONB NOT NULL,
  rt_ms INT,                                  -- response time
  rating INT,                                 -- FSRS 1..4
  fsrs_stability DOUBLE PRECISION,            -- post-state
  fsrs_difficulty DOUBLE PRECISION,
  graded_score JSONB,                         -- per-rubric breakdown for EE/EO
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX interactions_user_created ON interactions(user_id, created_at DESC);

-- Per-skill posterior NCLC estimate
CREATE TABLE skill_estimates (
  user_id UUID,
  skill TEXT,                                 -- CO/CE/EE/EO
  posterior_mean DOUBLE PRECISION,            -- on NCLC 1..12 scale, continuous
  posterior_variance DOUBLE PRECISION,
  n_obs INT,
  last_updated TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, skill)
);

-- Study plan (rolling, regenerated when posterior shifts > threshold)
CREATE TABLE study_plans (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  generated_at TIMESTAMPTZ DEFAULT now(),
  horizon_days INT NOT NULL,
  daily_blocks JSONB NOT NULL,                -- [{date, blocks: [{skill, mins, drill_type}]}]
  rationale TEXT NOT NULL,                    -- human-readable why
  superseded BOOLEAN DEFAULT false
);

-- Mock exam sessions
CREATE TABLE mock_exams (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  started_at TIMESTAMPTZ DEFAULT now(),
  finished_at TIMESTAMPTZ,
  per_module_score JSONB,
  estimated_nclc JSONB,                       -- per-skill with CI
  raw_log JSONB                               -- full timing log
);
```

### 2.3 Pydantic Schema Contracts

`packages/shared/src/tcf_accel/schemas/` contains:

```python
# item.py
class COContent(BaseModel):
    transcript: str
    audio_url: AnyHttpUrl | None
    audio_local_path: str | None  # for cached local audio
    duration_s: float
    speakers: list[Speaker]                # for multi-turn dialogues
    accent: Literal["fr-FR","fr-CA","fr-BE","fr-CH","fr-AF","mixed"]
    register: Literal["soutenu","standard","familier"]
    questions: list[MCQ]                   # ≥1 question

class CEContent(BaseModel):
    passage: str
    genre: Literal["news","ad","letter","admin","academic","narrative"]
    word_count: int
    questions: list[MCQ]

class EEContent(BaseModel):
    task_number: Literal[1,2,3]
    prompt: str
    target_word_count_range: tuple[int,int]
    required_canadian_context: bool        # True for Task 2 & 3
    rubric_version: str                    # pinned per release

class EOContent(BaseModel):
    task_number: Literal[1,2,3]
    examiner_prompts: list[str]
    candidate_prep_time_s: int             # only nonzero for Task 1 in some versions
    target_duration_s: int
    rubric_version: str

ItemContent = COContent | CEContent | EEContent | EOContent  # discriminated by module

# scoring.py
class NCLCEstimate(BaseModel):
    skill: Literal["CO","CE","EE","EO"]
    posterior_mean: float = Field(ge=1, le=12)
    ci_low: int
    ci_high: int
    confident: bool
    n_observations: int

class WritingRubric(BaseModel):
    task_completion: int = Field(ge=0, le=5)
    coherence_cohesion: int = Field(ge=0, le=5)
    lexical_range: int = Field(ge=0, le=5)
    grammatical_accuracy: int = Field(ge=0, le=5)
    register_appropriateness: int = Field(ge=0, le=5)
    canadian_context_integration: int | None = Field(default=None, ge=0, le=5)  # Tasks 2&3
    total_20: int = Field(ge=0, le=20)
    error_density_per_100w: float
    type_token_ratio: float
    discourse_marker_count: int
    error_list: list[ErrorAnnotation]

class SpeakingRubric(BaseModel):
    task_completion: int = Field(ge=0, le=5)
    fluency_pace: int = Field(ge=0, le=5)
    pronunciation_prosody: int = Field(ge=0, le=5)
    lexical_range: int = Field(ge=0, le=5)
    grammatical_accuracy: int = Field(ge=0, le=5)
    interaction_responsiveness: int = Field(ge=0, le=5)
    total_20: int = Field(ge=0, le=20)
    wpm: float
    pause_ratio: float
    phoneme_error_rate: float | None
```

### 2.4 API Surface (OpenAPI sketch)

```yaml
paths:
  # Identity & onboarding
  POST /v1/auth/signup
  POST /v1/auth/login
  GET  /v1/me
  PATCH /v1/me                       # set target_nclc, exam_date, daily budget

  # Diagnostic
  POST /v1/diagnostic/start
  POST /v1/diagnostic/{id}/answer
  POST /v1/diagnostic/{id}/finish    # returns NCLCEstimate per skill + plan

  # Study plan
  GET  /v1/plan                      # rolling plan
  POST /v1/plan/regenerate
  GET  /v1/plan/today                # today's blocks only

  # Practice
  POST /v1/session/start             # body: {module, drill_type, target_minutes}
  GET  /v1/session/{id}/next         # next item per scheduler
  POST /v1/session/{id}/answer
  POST /v1/session/{id}/finish       # commits FSRS state, returns summary

  # Writing & Speaking submission
  POST /v1/submission/ee             # multipart: text + task_id
  POST /v1/submission/eo             # multipart: audio + task_id
  GET  /v1/submission/{id}           # returns WritingRubric or SpeakingRubric

  # Mock exam
  POST /v1/mock-exam/start           # creates full 2h47 session, locks shape
  GET  /v1/mock-exam/{id}/state
  POST /v1/mock-exam/{id}/submit     # finalize
  GET  /v1/mock-exam/{id}/report     # detailed item-by-item

  # Insights
  GET  /v1/insights/nclc-trajectory  # historical estimate + forecast
  GET  /v1/insights/weak-points      # top error patterns by skill
  GET  /v1/insights/readiness        # "are you ready to book the exam?" → traffic-light

  # Data ownership
  GET  /v1/data/export               # full JSONL of user's interactions
  DELETE /v1/data                    # GDPR-style erasure

components:
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer }
```

### 2.5 Error Taxonomy

```python
class TCFAccelError(Exception): ...
class ContentNotAvailableError(TCFAccelError): ...  # bank too thin for requested config
class SchedulerError(TCFAccelError): ...
class ScoringError(TCFAccelError):
    class ASRConfidenceTooLowError(ScoringError): ...    # ask learner to re-record
    class TextTooShortError(ScoringError): ...           # below minimum word count
class CalibrationError(TCFAccelError):
    class InsufficientObservationsError(CalibrationError): ...  # refuse to predict
```

Every error has a stable code (`E_SCORING_001` etc.), an HTTP status, and a learner-facing message in EN + FR.

### 2.6 Observability

- Structured JSON logs (loguru → stdout → Loki-compatible).
- Metrics: Prometheus client; the four key SLO metrics: API p95, item-bank hit-rate, scheduler latency, scoring success rate.
- Traces: OpenTelemetry; sampling 5% in prod, 100% locally.
- Privacy: no learner text or audio in logs or traces, only IDs + sizes.

### 2.7 Test Plan

- **Unit:** every schema; every error path; every scheduler primitive (Phase 4 carries these forward).
- **Property-based (Hypothesis):** NCLC estimator invariants (monotonic, bounded, calibrated).
- **Contract:** Schemathesis fuzzing the OpenAPI spec.
- **Integration:** docker-compose stack + a realistic 100-item bank seeded.
- **E2E:** Playwright running a 30-minute synthetic session.
- **Pedagogical regression:** a fixed `golden_learner` JSONL trajectory; if the plan output changes shape, fail with a diff.

### 2.8 ADRs added in this phase

- ADR-011: JSONB content vs polymorphic tables (decided: JSONB).
- ADR-012: Pre-computed schedule cache vs on-demand (decided: pre-computed + invalidate).
- ADR-013: Online Bayesian per-skill update + nightly IRT refit.
- ADR-014: Error code taxonomy stability promise.
- ADR-015: pgvector first, Qdrant as a swap-in if scale demands.
- ADR-016: API versioning policy (URL `/v1/`, additive-only; breaking → `/v2/`).
- ADR-017: Privacy default = `local_only` (no cloud anything until explicit opt-in).

---

## 3. CODE

- Alembic migration `0001_initial.py` with the schema above.
- Pydantic schemas in `packages/shared`.
- Empty FastAPI handlers for every `/v1/` route returning `501 Not Implemented` with a structured "phase: N" marker — Phase 3+ fills them in.
- OpenAPI spec generated from the empty handlers + frozen as `docs/api/openapi.v1.yaml`.
- Schemathesis test that loads `openapi.v1.yaml` and confirms every route returns either its implemented response or `501`.
- The `golden_learner.jsonl` fixture (a hand-curated 200-interaction synthetic trajectory).
- Error taxonomy module with EN+FR messages.

---

## 4. AUDIT (produce `phase2_audit.md`)

- Alembic `upgrade head` and `downgrade base` both succeed on a fresh DB.
- Pydantic round-trip property test: random JSON → parse → re-serialize → equal.
- `make verify` still green.
- Schemathesis fuzz returns no contract drift.
- The OpenAPI spec validates against the OpenAPI 3.1 schema.
- Error taxonomy covers every `raise` in `apps/api`.
- A "fresh-clone reviewer" can read `phase2_design.md` and explain back the system architecture in one paragraph — verified by self-review against the description.

---

## 5. EVALUATE (produce `phase2_evaluate.md`)

Acceptance criteria:

- ✅ DB schema migrated and tested
- ✅ OpenAPI v1 frozen and committed
- ✅ All seventeen ADRs through ADR-017 written and reviewed
- ✅ Property-based + contract tests passing
- ✅ Risk register updated; new risks logged

Anti-criteria:

- ❌ Any schema field without a Pydantic validator
- ❌ Any API route without an OpenAPI annotation
- ❌ Any error raised without a stable error code
- ❌ Any TODO referencing post-Phase-2 work without a tracking issue

Hand-off: a frozen `openapi.v1.yaml` and a generated API client SDK published to `packages/client-ts` + `packages/client-py`. Subsequent phases consume these clients rather than re-typing routes.
