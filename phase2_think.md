# Phase 2 — THINK

> Phase 2 (`02_ARCHITECTURE.md §1`) — the architectural decisions that, once
> taken, the rest of the build pivots on. Three load-bearing questions; for
> each, the option space, the chosen path, and the empirical signal that
> would flip the decision. Date: 2026-05-27.

---

## 0. Frame

Phase 1 froze the *contracts*: `Item`, `Score`, `NCLCEstimate`, the error
base, `SCHEMA_VERSION="0.1.0"`. Phase 2's job is to freeze the *system* that
carries those contracts: the database schema, the API surface, the error
taxonomy, the observability seams. After this phase, Phases 3–8 implement
*behind* a frozen wall. Contract churn after this phase is a tax on every
subsequent phase. So the bar for "decide it now, decide it once" is high.

The three questions below are the ones that, if revisited later, would force
the largest rewrite. Everything else is downstream of these three.

---

## 1. The three hardest architectural questions

### 1.1 Where does the learner model live?

The learner model — FSRS scheduler state, per-skill posterior, IRT-driven
item selection — runs on *bursty* compute: at the end of a 30-minute
session, ~50 cards get re-rated, the per-skill posterior moves, and the
study plan may need regeneration. The naive request-bound implementation
would block the API thread for hundreds of milliseconds at a moment when
the learner is staring at a "submitting…" spinner.

**Options:**

| Option | Topology | Cost |
|---|---|---|
| **(a)** In-process inside the API | `apps/api` owns scheduler + estimator; reads/writes Postgres directly. | Scheduler computations sit on request threads; p95 blows up on session-finish. No isolation between "API health" and "scheduler bug". |
| **(b)** Dedicated `sla-service` consumed via gRPC | `packages/sla` becomes its own process; API gRPC-calls it. | Extra deploy unit, extra network hop, extra failure mode. Over-engineered for v1 traffic (≤ 10k users). |
| **(c)** API consumes pre-computed schedules from a cache; Celery workers compute | Workers re-compute on `session.finished` events; API reads from Redis + Postgres. | Cache-invalidation complexity. But: the API never blocks on scheduler math. |

**Pick (c).** The decisive consideration is the *coupling shape*. Option (a)
lets a slow scheduler regression degrade the API; option (b) buys isolation
at the price of an operational surface we cannot staff in v1; option (c)
keeps the API thin and lets the heavy work happen on a queue the user
doesn't watch. The cost — cache invalidation — is a known, tractable problem
(invalidate-on-write, TTL fallback, version key on the cached payload).

This decision is *not* "run a workflow engine"; it's just "the API reads,
the worker computes, Redis is the seam." Phase 1 already shipped
`apps/worker` with Celery + Redis (ADR-0005), so the seam exists.

**Concrete consequence:** every endpoint that *consumes* scheduler state
(`GET /v1/session/{id}/next`, `GET /v1/plan/today`, `POST
/v1/session/{id}/finish`) must be able to *degrade gracefully* if the cache
is empty or stale — e.g., compute synchronously with a published-latency
SLO, or return `409 Conflict` with `Retry-After`. We accept the
graceful-degradation work as the price of decoupling.

### 1.2 How do we represent items across four modules with different shapes?

CO items carry audio. CE items carry passages. EE items carry writing
prompts with rubric versions. EO items carry speaking prompts and
preparation times. The four shapes are *related* (every item has CEFR
level, difficulty, provenance) but their `content` fields share nothing.

**Options:**

| Option | Storage | Cost |
|---|---|---|
| **(a)** One `items` table with a JSONB `content` column | Single physical table; Pydantic discriminated-union validates on write; queryable fields (`module`, `cefr_level`, `difficulty_irt`, `tags`) live as real columns. | JSONB does not enforce shape at the DB layer; we own that invariant in app code. |
| **(b)** Four tables (`co_items`, `ce_items`, `ee_items`, `eo_items`) | DB-level shape guarantees per module. | Cross-module queries (mock-exam composition, recommender) become unions; the recommender's vector index would need to be either four indices or a denormalized view. ORM mapping is 4× the surface. |
| **(c)** Polymorphic SQLAlchemy with a base `Item` and four subclasses | Mixed: one row in `items`, additional rows in per-module tables. | Inherits both costs — the JOIN cost of multi-table reads *and* the ORM complexity of polymorphic loading. SQLAlchemy polymorphism is a known footgun for async sessions. |

**Pick (a) with strict Pydantic validation at the boundary.** Three
load-bearing reasons:

1. **Cross-module queries are constant**: every mock exam, every adaptive
   session, every recommender call queries across modules.
2. **The query columns are stable**: `module`, `cefr_level`,
   `difficulty_irt`, `tags`, `retired`. We index those as real columns; the
   JSONB is "the payload" not "the queryable surface".
3. **Pydantic-v2 discriminated unions are mature**: validation cost is
   sub-millisecond; the discriminator (`module`) is enforced both at
   `Item.__post_init__` and at the JSONB write path.

The cost — losing DB-side shape enforcement — is mitigated by:

- A `CHECK` constraint on `module ∈ {'CO','CE','EE','EO'}`.
- A `CHECK` constraint on `cefr_level ∈ {'A1'..'C2'}`.
- A Pydantic-validated write path (`ItemRepository.create` calls
  `Item.model_validate(...)` before INSERT).
- A nightly audit job (Phase 9 §2.3) that scans the JSONB and reports any
  row that fails current-schema validation. Drift is *detectable*.

### 1.3 How do we keep the NCLC estimator from going stale?

The posterior NCLC estimate is the system's central honesty claim (master
prompt §6.2; R-004). It must be updated *fast enough* that the learner sees
their progress, and *infrequently enough* that we are not redoing expensive
math on every keypress.

The compute decomposes into two layers:

- **Per-skill posterior** (per user, per module): a closed-form Bayesian
  update (Beta-Binomial-ish; Phase 4 makes this precise). Cheap. Online.
- **Per-item IRT difficulty** (per item, across all users): a 2PL fit
  across the interaction matrix. Expensive. Bulk.

**Options:**

| Option | Update cadence | Cost |
|---|---|---|
| **(a)** Recompute everything on every interaction | Online for posterior + online for IRT | IRT fit is O(items × users); not feasible per interaction. |
| **(b)** Recompute everything on session-end + nightly batch | Batch for posterior + nightly for IRT | Posterior estimate stale during long sessions; learner asking "am I improving?" mid-session sees yesterday's number. |
| **(c)** Online streaming Bayesian update for per-skill posterior; nightly batch IRT refit | Posterior online; IRT once per day | Two code paths. But each path uses the right algorithm for its shape. |

**Pick (c).** The two layers have genuinely different math:

- The per-skill posterior with a conjugate prior has a closed-form update;
  it would be silly *not* to do it online.
- The IRT refit is a non-trivial optimization (gradient descent over the
  full item × user matrix). Doing it nightly is correct.

The two paths share zero code, so the "two code paths" cost is illusory —
they were always going to be two paths.

**Concrete consequence:** the `skill_estimates` table is *write-on-every-
interaction-finish* (single row per (user, skill); no append-only history).
The `items.difficulty_irt` / `items.discrimination_irt` columns are
*write-on-nightly-job*. The nightly job is owned by Phase 4; Phase 2
reserves the columns and ships the schema.

---

## 2. What would change our mind

These are the empirical signals that, if observed, would warrant
revisiting the decisions above. They are deliberately concrete; vague
triggers ("if it's slow") don't count.

### 2.1 On the learner-model placement (1.1)

- **Worker queue backlog > 30 s at p95** on `session.finished` events.
  This means the API-blocking approach (option a) would have been roughly
  comparable in user-visible latency. We'd reconsider folding the
  scheduler back into the API.
- **Cache invalidation bugs exceed three incidents in a quarter**. If
  cache staleness is causing user-facing wrong-queue bugs more often than
  the option (a) latency would, the trade-off has shifted.
- **The worker pool's `simulate_learning` or IRT refit jobs starve
  scheduler computation**. We'd split workers into dedicated pools (still
  option c) before considering (b).

### 2.2 On JSONB item content (1.2)

- **pgvector or the JSONB extraction becomes the query bottleneck**: p95
  `GET /v1/session/next` > 300 ms attributable to item-table scans. We'd
  consider a materialized view per module before splitting to option (b).
- **A schema-drift incident** where the nightly audit (Phase 9 §2.3)
  reports > 0.1% of items failing current-schema validation. This
  indicates we're losing the JSONB invariant; we'd consider option (b).
- **Item bank exceeds ~10M items**: pgvector's HNSW index and the JSONB
  GIN index both degrade. ADR-0002 / ADR-015 already names Qdrant as the
  swap-in for vectors; we'd revisit the items table at the same time.

### 2.3 On the streaming Bayesian + nightly IRT split (1.3)

- **Per-skill posterior shows oscillation** on the synthetic-cohort
  trajectory (Phase 4 audit). Online updates are mathematically
  well-behaved for our prior, but a bug in the update rule would show
  here. We'd switch to "recompute on session-end" before going fully batch.
- **Nightly IRT refit takes > 4 hours**. We'd add a streaming variational
  IRT (e.g., online-2PL) before resorting to weekly refits, which would
  let item difficulty stay stale longer than acceptable for new items.
- **A cohort calibration audit shows the posterior is mis-calibrated**
  by more than 1 NCLC band on average. This is a learner-harm signal
  (R-004), not just a math signal. We'd halt online updates and re-fit
  from a holdout set.

---

## 3. Adjacent decisions deferred to design (`phase2_design.md`)

Decisions that are *not* among the three hardest but are still worth
recording explicitly so the design doc can lock them down without
re-deriving:

- **API versioning**: URL-based `/v1/`, additive-only. Breaking → `/v2/`.
  (ADR-016.)
- **Privacy default**: `local_only` for every new user. Cloud features
  opt-in. (ADR-017; master prompt §6.4 + ADR-0010.)
- **Error code stability**: codes are part of the public API; never
  renamed once shipped. (ADR-014.)
- **Vector store**: pgvector first, Qdrant as a swap-in if scale demands.
  (ADR-015 affirms ADR-0002.)
- **Cache eviction policy**: Redis with TTL + explicit invalidation on
  `Interaction` insert affecting the cached user/skill. The TTL is a
  safety net; the explicit invalidation is the contract. (Detailed in
  `phase2_design.md §2.6`.)
- **Observability privacy**: no learner text or audio in logs or traces —
  only IDs and sizes. (Detailed in `phase2_design.md §2.6`.)

---

## 4. Out of scope for Phase 2

The phase plan (`02_ARCHITECTURE.md §3`) ships *stubs* for the `/v1/`
routes; the handlers return `501 Not Implemented` with a structured
`{"phase": N}` marker indicating which phase owns the implementation.
That is the contract Phase 3+ inherits.

Phase 2 does **not**:

- Implement business logic for any `/v1/` route (Phases 3–8).
- Implement the FSRS scheduler, the IRT estimator, the Bayesian posterior
  update, or the LECTOR retrieval (Phase 4).
- Implement the ASR / writing / speaking auto-scorers (Phase 7).
- Build the diagnostic flow logic or the mock-exam composer (Phases 5/6).
- Author the actual frontend pages (Phase 8); only the API surface that
  the frontend will consume is frozen here.

Anything that smells like business logic in this phase is a contract bug.

---

## 5. Phase 2 invariants going into design

1. **The OpenAPI spec is the law.** After Phase 2 audit, `docs/api/openapi.v1.yaml`
   is the single source of truth for the API surface. Generated clients
   (`packages/client-ts`, `packages/client-py`) are derived from it.
2. **The schema is the law.** `infra/migrations/0001_initial.py` is the
   single source of truth for the DB shape. `alembic upgrade head` +
   `alembic downgrade base` both pass on a fresh DB; tests prove it.
3. **Every error has a stable code.** `E_<DOMAIN>_<NNN>`. Tests enforce
   code uniqueness; ADR-014 promises code stability.
4. **Every schema has Pydantic validation.** No raw `dict` returns from
   API handlers; no untyped JSONB writes from the repository layer.
5. **Every `/v1/` route exists and returns 501** in Phase 2 — the surface
   is *frozen*, not implemented.
6. **Privacy default is `local_only`.** Every new user, every new test
   fixture, every new demo. Cloud is opt-in. (ADR-017.)
7. **Schema additive promise.** Phase 1's `SCHEMA_VERSION="0.1.0"`
   bumps to `0.2.0` to mark the additive narrowing of `ItemContent` into
   a discriminated union and the addition of rubric schemas. No Phase 1
   round-trip test should fail.

---

## 6. Hand-off to DESIGN

`phase2_design.md` takes these decisions and turns them into:

- The service topology diagram.
- The full SQL schema in DDL.
- The Pydantic discriminated-union for `ItemContent`.
- The Pydantic rubric schemas for `WritingRubric` and `SpeakingRubric`.
- The OpenAPI sketch for `/v1/` routes.
- The error taxonomy module shape.
- The observability stack choices.
- The test plan (unit + property + contract + integration + E2E +
  pedagogical regression).
- The seven new ADRs (0011 through 0017).
