# Phase 6 — DESIGN

> Inputs: `phase6_think.md`, ADR-032 through ADR-035.
> Output of this doc: a build-ready specification for the mock-exam
> engine — the package surface, the state machine, the scoring rules,
> the API wire, and the test strategy.

---

## 1. Module layout

```
packages/sla/src/tcf_accel_sla/mock_exam/
├── __init__.py          # re-exports
├── spec.py              # exam shape constants (FEI structure, breaks)
├── state.py             # MockState enum + transition rules + journal
├── cadence.py           # week-aware cooldown (1/w → 2/w → 3/w)
├── selector.py          # constraint-guided greedy item picker
├── scorer.py            # CO/CE/EE/EO → posterior, divergence alert
├── report.py            # Markdown + HTML mock-report renderer
└── candidate.py         # scripted candidate (integration test driver)

apps/api/src/tcf_accel_api/
├── mock_exam_pool.py    # bank fixture (≥ 200 CO + 200 CE + 30 EE + 30 EO items)
├── mock_exam_state.py   # in-process MockExam store + journal log
└── routes/mock_exam.py  # /v1/mock-exam/* handlers

apps/worker/src/tcf_accel_worker/tasks/
└── score_mock.py        # celery task: takes a submitted mock id, scores it
```

---

## 2. Constants (`mock_exam/spec.py`)

```python
EXAM_SHAPE: dict[Module, int] = {"CO": 39, "CE": 39, "EE": 3, "EO": 3}
MODULE_DURATION_S: dict[Module, int] = {
    "CO": 35 * 60,   # 2100 s
    "CE": 60 * 60,   # 3600 s
    "EE": 60 * 60,   # 3600 s
    "EO": 12 * 60,   #  720 s
}
BREAK_DURATION_S: dict[str, int] = {
    "BREAK_1": 5 * 60,   # after CO
    "BREAK_2": 5 * 60,   # after CE
    "BREAK_3": 15 * 60,  # after EE
}
TOTAL_DURATION_S: int = (
    sum(MODULE_DURATION_S.values()) + sum(BREAK_DURATION_S.values())
)  # = 2100 + 300 + 3600 + 300 + 3600 + 900 + 720 = 11520 s = 3:12:00
# Note: the master prompt's "2h47" target reflects active-test time only
# (modules, no breaks). Audit asserts active = 35+60+60+12 = 167 min.
ACTIVE_DURATION_S: int = sum(MODULE_DURATION_S.values())  # 10020 s = 2:47:00

# Per-module ordering of CEFR difficulty per FEI's "progressive
# difficulty" doctrine: within each module, items are sorted ascending.
FEI_SPREAD: dict[CefrLevel, float] = {
    "A1": 0.10, "A2": 0.15,
    "B1": 0.20, "B2": 0.25,
    "C1": 0.20, "C2": 0.10,
}

# Tab-blur grace window before a forfeit in canonical mode (s).
CANONICAL_TAB_BLUR_GRACE_S: int = 5
```

---

## 3. State machine (`mock_exam/state.py`)

### 3.1 The states

```
SCHEDULED → STARTED → CO_ACTIVE → CO_DONE → BREAK_1
                                                ↓
                                            CE_ACTIVE → CE_DONE → BREAK_2
                                                                       ↓
                                                                  EE_ACTIVE → EE_DONE → BREAK_3
                                                                                          ↓
                                                                                      EO_ACTIVE → EO_DONE → FINISHED → SCORED

(any abnormal exit during canonical) → FORFEITED  (terminal)
```

### 3.2 Transition table

| From          | Event              | To           | Notes                                   |
|---------------|--------------------|--------------|-----------------------------------------|
| SCHEDULED     | start              | CO_ACTIVE    | sets `started_at`                       |
| CO_ACTIVE     | module-time-expired | CO_DONE     | auto-advance                            |
| CO_ACTIVE     | learner-submits-module | CO_DONE  | early-submit allowed                    |
| CO_DONE       | break-clock-tick   | BREAK_1      | enters break                            |
| BREAK_1       | break-time-expired | CE_ACTIVE    | learner can also resume early           |
| CE_ACTIVE     | …                  | CE_DONE      | symmetric                               |
| CE_DONE       | …                  | BREAK_2      |                                         |
| BREAK_2       | …                  | EE_ACTIVE    |                                         |
| EE_ACTIVE     | …                  | EE_DONE      |                                         |
| EE_DONE       | …                  | BREAK_3      |                                         |
| BREAK_3       | …                  | EO_ACTIVE    |                                         |
| EO_ACTIVE     | learner-submits-final | FINISHED  | triggers scoring                        |
| FINISHED      | scorer-completes   | SCORED       | scoring result attached                 |
| any non-terminal | canonical-abnormal-exit | FORFEITED | one-way; no scoring               |

### 3.3 The journal

Every transition writes an audit row:

```python
@dataclass(frozen=True)
class MockJournalEntry:
    mock_id: MockExamId
    at: datetime         # UTC
    from_state: MockState
    to_state: MockState
    reason: str          # "start", "module_time_expired", "submit", "tab_blur", …
    elapsed_s_in_state: float
```

In Phase 6 the journal lives in-memory next to the `MockExam` record;
Phase 9 swaps it for a Postgres table without changing the record
shape.

### 3.4 Transition function signature

```python
def transition(
    current: MockState,
    event: MockEvent,
    *,
    mode: MockExamMode,
    now: datetime,
    started_at: datetime,
) -> MockState
```

Raises `InvalidMockTransition` for impossible event sequences (caught
in tests; the API returns 409).

---

## 4. Cadence (`mock_exam/cadence.py`)

```python
def mocks_allowed_per_iso_week(week_index: int) -> int:
    """Return the canonical-mock cap for week index since first-mock.

    week_index 0..5  → 1
    week_index 6..9  → 2
    week_index 10+   → 3
    """
def can_start_canonical(
    history: list[MockExamSummary],
    *,
    now: datetime,
    first_mock_at: datetime | None,
) -> tuple[bool, str]:
    """Return (allowed, reason). Reason is a human-readable explanation."""

def can_start_training(history: ...) -> tuple[bool, str]:
    """Training mode has a much looser cap: 1/day."""
```

Used by `POST /v1/mock-exam/start` to return 409 with
`next_action="cooldown"`.

---

## 5. Selector (`mock_exam/selector.py`)

### 5.1 Public surface

```python
@dataclass(frozen=True)
class SelectorInputs:
    user_id: UserId
    iso_week: str
    bank: Sequence[PooledMockItem]   # the full bank for a module
    seen_within_30d: set[ItemId]
    seen_ever: set[ItemId]
    rng_seed: int                    # derived: hash(user_id, iso_week)

@dataclass(frozen=True)
class SelectorResult:
    module: Module
    items: list[PooledMockItem]      # exactly EXAM_SHAPE[module] items
    warnings: list[str]              # bucket backoff notes; empty in the happy path

def select_for_module(
    inputs: SelectorInputs, module: Module,
) -> SelectorResult: ...

def select_full_mock(
    user_id: UserId,
    iso_week: str,
    bank: Mapping[Module, Sequence[PooledMockItem]],
    seen_within_30d: set[ItemId],
    seen_ever: set[ItemId],
) -> dict[Module, SelectorResult]: ...
```

### 5.2 The algorithm (greedy + seeded RNG)

```python
def select_for_module(inputs, module):
    target = EXAM_SHAPE[module]
    rng = random.Random(inputs.rng_seed ^ hash(module))

    # 1) hard filters: recency, retired, quality.
    pool = [
        i for i in inputs.bank
        if i.item.id not in inputs.seen_within_30d
        and not i.item.retired
    ]

    # 2) for EE/EO: bucket by task_number ∈ {1,2,3}; target 1 per bucket.
    # for CO/CE: bucket by CEFR; target = ceil(FEI_SPREAD[band] * 39).
    buckets = bucket_by(module, pool)
    targets = bucket_targets(module)

    # 3) enforce ≥20% never-seen by drawing from never-seen pool first.
    never_seen = [i for i in pool if i.item.id not in inputs.seen_ever]
    novel_budget = max(0, round(0.2 * target))

    chosen: list[PooledMockItem] = []
    # Phase A: novelty budget
    for _ in range(novel_budget):
        if not never_seen:
            break
        idx = rng.randrange(len(never_seen))
        chosen.append(never_seen.pop(idx))

    # Phase B: bucket-filling
    for band, target_count in targets.items():
        already = sum(1 for c in chosen if bucket_key(c) == band)
        need = max(0, target_count - already)
        bucket = [b for b in buckets.get(band, []) if b not in chosen]
        rng.shuffle(bucket)
        chosen.extend(bucket[:need])

    # Phase C: if short, fill from any remaining
    if len(chosen) < target:
        rest = [p for p in pool if p not in chosen]
        rng.shuffle(rest)
        chosen.extend(rest[: target - len(chosen)])

    # 4) trim to exactly target (in case novelty over-filled)
    chosen = chosen[:target]

    # 5) sort ascending by IRT difficulty
    chosen.sort(key=lambda p: p.difficulty)
    return SelectorResult(module=module, items=chosen, warnings=[])
```

The seed makes the selector deterministic per (user, week).
A different week or a different user yields a different draw. The
audit's diversity metric runs the selector 100× across simulated
weeks, not the same week (which would correctly return the same draw).

### 5.3 EE/EO task-number constraint

For EE and EO, EXAM_SHAPE is 3 and the FEI requirement is exactly one
each of task numbers 1, 2, 3. The selector uses task_number as the
bucket key (instead of CEFR), and the targets are `{1: 1, 2: 1, 3: 1}`.

---

## 6. Scorer (`mock_exam/scorer.py`)

### 6.1 Per-skill scoring

```python
@dataclass(frozen=True)
class ItemOutcome:
    item_id: ItemId
    module: Module
    difficulty: float
    correct: bool
    rt_ms: int

@dataclass(frozen=True)
class RubricOutcome:
    item_id: ItemId
    module: Module          # "EE" or "EO"
    task_number: int
    prompt_target_nclc: float
    rubric_total_20: float

@dataclass(frozen=True)
class MockSkillScore:
    skill: SkillCode
    raw: float              # CO/CE: # correct; EE/EO: mean rubric total 0..20
    max_raw: float
    posterior: SkillPosterior  # the posterior built from THIS mock's evidence

def score_mock(
    co: list[ItemOutcome],
    ce: list[ItemOutcome],
    ee: list[RubricOutcome],
    eo: list[RubricOutcome],
) -> dict[SkillCode, MockSkillScore]: ...
```

The mock-posterior is built from a *fresh* `bootstrap_posterior` (not
the user's running drill posterior) and folded with the mock's items
via `update_with_mcq` / `update_with_rubric`. This makes the mock
posterior independent of drill history — the whole point.

### 6.2 Drill–mock divergence

```python
def divergence_alert(
    drill: SkillPosterior,
    mock: SkillPosterior,
    *,
    threshold: float = 2.0,
) -> str | None:
    if abs(drill.mean - mock.mean) >= threshold:
        return (
            f"Drill {drill.skill} = {drill.mean:.1f}, "
            f"Mock {mock.skill} = {mock.mean:.1f}; "
            f"divergence {abs(drill.mean - mock.mean):.1f}."
        )
    return None
```

The alert text is included in the report `divergence_alerts` field.

### 6.3 Composite NCLC (the headline)

The composite is the *minimum* of the four per-skill posterior means,
floored to integer band — matching the TCF Canada "bottleneck"
equivalence. The `bottleneck_skill` field on the report carries the
identity.

The composite is *suppressed* (set to `null` and `overall_confident=False`)
if **any** per-skill posterior has `confident=False`. This is the
"never over-predict" guarantee.

---

## 7. Report (`mock_exam/report.py`)

### 7.1 The seven sections (matching `06_MOCK_EXAM_ENGINE.md §2.5`)

1. **Headline** — overall NCLC ± CI, bottleneck, traffic light.
2. **Module breakdown** — per-skill score, # correct / max, rubric
   tables for EE/EO.
3. **EE report** — per-task rubric scores, model improvements.
4. **EO report** — per-task rubric, transcript stub, pronunciation drill suggestion.
5. **Trajectory** — this mock's per-skill NCLC compared against the
   drill posterior. (Long-running trajectory overlay is Phase 8.)
6. **Actionable plan** — top 3 next-week recommendations, derived
   from the bottleneck skill + the rubric subscores.
7. **Booking advice** — strictly gated by the 2-consecutive-🟢-canonical
   rule.

### 7.2 Renderers

```python
def render_markdown(report: MockExamReportFull) -> str: ...
def render_html(report: MockExamReportFull) -> str: ...
```

`MockExamReportFull` is an internal record richer than the
`MockExamReport` wire schema — it carries all sections. The wire
schema is the summary; the full report is fetched from
`item_log_uri` (a file URI in Phase 6, an S3-style URI in production).

### 7.3 Booking-advice gate

```python
def booking_advice(
    *,
    canonical_streak_green: int,
    light: ReadinessLight,
    last_canonical_at: datetime | None,
) -> str:
    if light != "green":
        return "Do not book yet — keep working the plan."
    if canonical_streak_green < 2:
        return (
            f"You hit green on this mock; the system requires "
            f"≥ 2 consecutive canonical greens before recommending a "
            f"booking. Sit another canonical mock in 7 days."
        )
    return "Booking the exam in 2–4 weeks is reasonable."
```

The anti-criterion is asserted in `tests/test_booking_advice_invariant.py`.

---

## 8. Bank fixture (`apps/api/.../mock_exam_pool.py`)

Phase 6 needs a bank large enough for the diversity audit but small
enough to keep fixtures bearable. We synthesize:

- **CO**: 200 items spread across 6 CEFR bands × ~33 items each, with
  3 accents (`fr-FR`, `fr-CA`, `fr-BE`) and 3 registers.
- **CE**: 200 items spread similarly, across 6 genres.
- **EE**: 30 items: 10 per task-number, spread across CEFR.
- **EO**: 30 items: 10 per task-number, spread across CEFR.

Item ids are deterministic (sha-256 of `"mock::{module}::{band}::{idx}"`),
so two test runs return identical banks. The pool is built at module
import time and cached.

---

## 9. State store (`apps/api/.../mock_exam_state.py`)

In-process, mirroring `session_state.py`. The store keys mocks by
`MockExamId` and indexes by user. The journal lives in-memory; the
forfeit detection (tab blur) is the API's responsibility — the store
just records the transition once the API decides it.

```python
@dataclass
class MockExam:
    id: MockExamId
    user_id: UserId
    mode: MockExamMode
    state: MockState
    started_at: datetime
    finished_at: datetime | None
    items_by_module: dict[Module, list[PooledMockItem]]
    outcomes: dict[ItemId, ItemOutcome | RubricOutcome]
    co_plays: dict[ItemId, int]  # max 1 per item per session
    current_module: Module | None
    seconds_remaining_in_module: int
    journal: list[MockJournalEntry]
    skill_scores: dict[SkillCode, MockSkillScore] | None  # set on SCORED
    overall_nclc: int | None                              # set on SCORED
    overall_confident: bool                               # set on SCORED
```

---

## 10. API surface (`apps/api/.../routes/mock_exam.py`)

Phase 2 froze the wire shape (`MockExamState`, `MockExamReport`).
Phase 6 fills the handlers. Routes:

| Method | Path                                | Behavior                                       |
|--------|-------------------------------------|------------------------------------------------|
| POST   | `/v1/mock-exam/start`               | enforce cadence; build a mock; return state   |
| GET    | `/v1/mock-exam/{id}/state`          | return current state (NEVER reveals answers) |
| POST   | `/v1/mock-exam/{id}/advance`        | transition to the next state (new)            |
| GET    | `/v1/mock-exam/{id}/items/{mid}`    | get module's items (no correct_option_id)     |
| POST   | `/v1/mock-exam/{id}/answer`         | record an MCQ answer or rubric outcome        |
| POST   | `/v1/mock-exam/{id}/co-play`        | record a CO audio play (server-tracked)       |
| POST   | `/v1/mock-exam/{id}/tab-blur`       | report a tab-blur event (→ forfeit if > 5s)   |
| POST   | `/v1/mock-exam/{id}/submit`         | finalize → enqueue score_mock task           |
| GET    | `/v1/mock-exam/{id}/report`         | return the report (404 until SCORED)          |

The `advance` and module-items-fetch endpoints are *additive* per
ADR-016 (additive-only). The frozen `MockExamState` and
`MockExamReport` schemas remain unchanged.

### 10.1 The leak-prevention wrapper

Every response that returns `Item` objects passes them through
`redact_item_for_mock(item)` which:

- Drops `MCQ.correct_option_id` and `MCQ.explanation`.
- Drops `EEContent.rubric_version` and any `model_answer` field.
- Leaves `EEContent.prompt`, `target_word_count_range`,
  `required_canadian_context`.

The Pydantic model used at the wire is `RedactedItem`, a sibling of
`Item` with the answer fields excluded. The audit walks the response
body and asserts none of `("correct_option_id", "explanation",
"correct", "answer_key")` appears.

### 10.2 Cadence enforcement

`POST /v1/mock-exam/start` consults `cadence.can_start_canonical`
against the user's stored `mock_history` and returns:

```json
{
  "code": "E_MOCK_001",
  "http_status": 409,
  "message": "You have reached this week's canonical-mock cap (1).",
  "context": {"reason": "weekly_cap", "next_eligible_at": "2026-06-04T00:00:00Z"}
}
```

The override `?force=true` is accepted but logged at WARN level.

### 10.3 Forfeit on tab-blur

`POST /v1/mock-exam/{id}/tab-blur` accepts `{"duration_ms": int}`.
If `duration_ms > 5000` and `mode == "canonical"`, transition to
`FORFEITED` and 200 with the new state. Otherwise no-op.

### 10.4 Submit + worker dispatch

`POST /v1/mock-exam/{id}/submit` flips the state to FINISHED and
enqueues `score_mock` (Celery task). In tests we run with
`task_always_eager=True` so the result is immediate. The task writes
back the scored fields onto the in-process record (Phase 9 replaces
with Postgres + Redis pub-sub).

---

## 11. Errors

Three new `TCFAccelError` subclasses, codes follow the existing
`E_<DOMAIN>_NNN` pattern (ADR-014).

```python
class MockCadenceExceededError(TCFAccelError):
    code = "E_MOCK_001"
    http_status = 409
    message_key = "mock.cadence_exceeded"

class MockForfeitedError(TCFAccelError):
    code = "E_MOCK_002"
    http_status = 409
    message_key = "mock.forfeited"

class MockNotScoredError(TCFAccelError):
    code = "E_MOCK_003"
    http_status = 404
    message_key = "mock.not_scored"

class MockInvalidTransitionError(TCFAccelError):
    code = "E_MOCK_004"
    http_status = 409
    message_key = "mock.invalid_transition"
```

Localized messages added to `errors/messages.py` (EN + FR per ADR-014).

---

## 12. Worker (`apps/worker/.../tasks/score_mock.py`)

```python
@celery_app.task(name="tcf_accel.score_mock")
def score_mock(payload: dict[str, Any]) -> dict[str, Any]:
    """Score a submitted mock.

    Payload shape:
        {
            "mock_id": "uuid",
            "co_outcomes": [...],
            "ce_outcomes": [...],
            "ee_outcomes": [...],
            "eo_outcomes": [...],
            "drill_posteriors": {"CO": {...}, ...},  # for divergence
        }

    Returns:
        Full scored payload with per-skill scores, divergence alerts,
        overall_nclc, and the rendered report.
    """
```

Idempotent: replaying with the same payload returns the same result.
Phase 6 ships with the scoring inline; Phase 9 moves it under Celery's
queue when Redis is wired.

---

## 13. Scripted candidate (`mock_exam/candidate.py`)

```python
@dataclass(frozen=True)
class CandidateProfile:
    co_p_correct_by_band: dict[CefrLevel, float]
    ce_p_correct_by_band: dict[CefrLevel, float]
    ee_target_total_20_by_task: dict[int, int]
    eo_target_total_20_by_task: dict[int, int]
    timing_jitter_ms: int = 1000  # per-item timing noise (s.d.)

def run_full_mock(
    client: TestClient,
    profile: CandidateProfile,
    *,
    mode: MockExamMode = "canonical",
    rng_seed: int = 42,
) -> dict:
    """Walk the full state machine; return the scored report payload."""
```

The candidate runner is used in two places:

- `apps/api/tests/test_mock_exam_routes.py` runs it as an integration
  test and asserts the wire-shape invariants.
- `phase6_audit.md`'s diversity audit calls it 100× with different
  profile seeds and accumulates the union of selected items.

---

## 14. Test plan

| Test                                              | What it asserts                                              |
|---------------------------------------------------|--------------------------------------------------------------|
| `test_mock_spec_shape.py`                         | EXAM_SHAPE counts, durations, breaks; sum = 2:47 active.    |
| `test_mock_state_transitions.py`                  | Every legal transition fires; illegal ones raise.           |
| `test_mock_cadence.py`                            | 1/w in weeks 0..5; 2/w 6..9; 3/w 10+; training looser.     |
| `test_mock_selector.py`                           | Exactly 39/39/3/3 picked; ascending difficulty; no recent. |
| `test_mock_selector_diversity.py`                 | Union across 100 weeks ≥ 60% of bank.                       |
| `test_mock_scorer.py`                             | Score consistency: posterior mean ± 0.5 of expected over 50 runs at known p. |
| `test_mock_report_sections.py`                    | All 7 sections present in Markdown + HTML.                  |
| `test_mock_report_booking_invariant.py`           | Booking advice never escalates with <2 consecutive greens. |
| `test_mock_exam_routes.py`                        | Start → walk → submit → report happy path (scripted cand). |
| `test_mock_exam_no_leak.py`                       | State response body has no `correct_option_id` substring. |
| `test_mock_exam_forfeit.py`                       | Tab-blur > 5s in canonical → FORFEITED.                     |
| `test_mock_exam_cadence_route.py`                 | 409 on second mock in same week.                            |
| `test_mock_exam_co_single_play.py`                | Second co-play request → 409.                               |
| `test_score_mock_task.py`                         | Celery task is deterministic; same input → same output.   |
| `tests/contract/test_openapi_v1.py`               | Updated to include the new mock-exam additive routes.      |

The `test_v1_stubs.py` table is updated to remove the four mock-exam
rows (they're no longer 501).

---

## 15. ADRs

- ADR-032 — Canonical vs training mock modes.
- ADR-033 — Mock cadence cap (1/w → 2/w → 3/w).
- ADR-034 — Drill / mock posterior divergence alert.
- ADR-035 — Greedy randomized selector (rejection of OR-Tools).

---

## 16. Hand-off

`docs/sample_mock_report.html` and `docs/sample_mock_report.md`: a
sample report for a synthetic candidate, illustrating each section.
The audit step renders these and the build asserts they are non-empty
and contain the 7 section headings.
