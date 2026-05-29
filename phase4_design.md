# Phase 4 — Design

> Companion to `04_LEARNER_MODEL.md §2`. Maps each spec section to the
> shipped module + its public surface.

## 1. Package layout

```
packages/sla/src/tcf_accel_sla/
├── __init__.py           — re-exports the common surface
├── scheduler/
│   ├── __init__.py
│   ├── fsrs.py           — FSRSScheduler, Card, Rating, ReviewLog
│   └── lector.py         — adjust_due_with_lector, cosine_similarity
├── estimator/
│   ├── __init__.py
│   └── nclc.py           — SkillPosterior, update_with_{mcq,rubric}
├── diagnostic/
│   ├── __init__.py
│   └── cat.py            — DiagnosticSession, select_next_item
└── planner/
    ├── __init__.py
    ├── allocator.py      — allocate, SKILL_BETAS, SKILL_FLOOR_MINUTES
    ├── generate_plan.py  — generate_plan, PlannerInputs, simulate_learning
    └── readiness.py      — compute_readiness, probability_meets_target
```

The package is **zero-runtime-dependency** (stdlib `math` only). This
lets `make verify` pass in an empty venv and keeps the swap to vendored
reference implementations a module-level substitution.

## 2. Scheduler — FSRS-6 wrapper

`packages/sla/src/tcf_accel_sla/scheduler/fsrs.py`.

```python
class FSRSScheduler:
    weights: tuple[float, ...] = DEFAULT_WEIGHTS  # length 21
    desired_retention: float = 0.90
    def review(card, rating, now) -> (Card, ReviewLog): ...
    def optimize(history) -> tuple[float, ...]: ...   # no-op in v1, ADR-023
```

The FSRS-6 forgetting curve `R(t, S) = (1 + FACTOR · t / S)^DECAY`
with `DECAY = -0.5, FACTOR = 0.9^(-2) - 1 ≈ 0.2345` so that `R(t=S) = 0.9`.

State transitions on rating:
- First review: `S_0 = w_{rating-1}`, `D_0 = w_4 - (rating - 3) · w_5`.
- Subsequent success: `S' = S · (1 + factor)` where `factor` is the
  FSRS-6 success-stability gain.
- Failure: `S' = w_11 · D^-w_12 · ((S+1)^w_13 - 1) · exp(w_14 · (1 - R))`,
  clipped to the prior stability.

All state is immutable (`@dataclass(frozen=True)`); `review` returns a
new `Card`. Clock-skew is rejected with `ValueError`.

## 3. Scheduler — LECTOR semantic spacing

`packages/sla/src/tcf_accel_sla/scheduler/lector.py`.

```python
def adjust_due_with_lector(
    items_due: list[DueItem],
    recently_reviewed: list[DueItem],
) -> list[DueItem]: ...
```

Quadratic penalty above `SIMILARITY_THRESHOLD = 0.75`, capped at
`MAX_LECTOR_DELAY_DAYS = 2`. **Idempotent** by anchoring shifts to the
most-similar prior's due-date, not the item's own — re-running the
function on its own output yields the same ordering.

## 4. Estimator — Bayesian NCLC

`packages/sla/src/tcf_accel_sla/estimator/nclc.py`.

```python
@dataclass(frozen=True)
class SkillPosterior:
    skill: SkillCode
    mean: float
    variance: float
    n_obs: int
    difficulty_bands_seen: frozenset[int]
    @property def confident(self) -> bool: ...  # the ADR-025 gate
    @property def ci_low(self) -> int: ...
    @property def ci_high(self) -> int: ...

def update_with_mcq(prior, *, item_difficulty, discrimination, correct) -> SkillPosterior:
    """Laplace-approximation update: Newton on log-posterior, var = -1/H."""

def update_with_rubric(prior, *, rubric_total_20, prompt_target_nclc, obs_noise_sigma) -> SkillPosterior:
    """Closed-form Gaussian-Gaussian update; no Newton needed."""
```

Constants:
- `CONFIDENT_MIN_OBS = 40`
- `CONFIDENT_MAX_VARIANCE = 0.4`
- `CONFIDENT_MIN_SPREAD = 3`

`to_nclc_estimate(posterior)` projects onto the `NCLCEstimate` wire schema.

## 5. Diagnostic — CAT

`packages/sla/src/tcf_accel_sla/diagnostic/cat.py`.

```python
@dataclass
class DiagnosticSession:
    user_id: UUID
    skill: SkillCode
    posterior: SkillPosterior
    administered: list[CandidateItem]
    max_items: int = DIAGNOSTIC_MAX_ITEMS         # 15
    stop_variance: float = DIAGNOSTIC_STOP_VARIANCE # 0.3
    def next_item(candidates) -> CandidateItem | None: ...
    def record_mcq(item, *, correct) -> SkillPosterior: ...
    def record_rubric(item, *, rubric_total_20, ...) -> SkillPosterior: ...
```

`select_next_item` picks the item maximizing Fisher information at the
posterior mean, with `SAME_DIFFICULTY_RUN_CAP = 3`.

## 6. Planner — allocator

`packages/sla/src/tcf_accel_sla/planner/allocator.py`.

```python
def allocate(total_minutes: int, posteriors, target_nclc: int) -> dict[SkillCode, int]:
    """Returns minute allocation summing exactly to total_minutes.
    Every skill receives ≥ SKILL_FLOOR_MINUTES = 10.
    Formula: alphas = max(EPSILON, gap²) · β_s; renormalize.
    """
```

Constants: `β_CO=1.0`, `β_CE=0.9`, `β_EE=1.4`, `β_EO=1.5`.

Rounding residual (from int(round(...))) is absorbed into the largest
allocation, tie-broken toward production skills, so the integer sum
always equals `total_minutes` exactly.

## 7. Planner — study-plan generator

`packages/sla/src/tcf_accel_sla/planner/generate_plan.py`.

```python
def generate_plan(inputs: PlannerInputs) -> StudyPlanView:
    """Deterministic given inputs (modulo `generated_at` + `id`)."""
```

`simulate_learning(posteriors, allocation, target)` projects the
posteriors one day forward with a conservative
`LEARNING_RATE_PER_MINUTE = 0.05 / 60` and a diminishing-returns
factor that halves the rate once a skill crosses `target` and falls
linearly to 0 at `NCLC_MAX`. Variance is **never** reduced by
simulation — only by observed evidence.

## 8. Planner — readiness traffic light

`packages/sla/src/tcf_accel_sla/planner/readiness.py`.

```python
def compute_readiness(posteriors, target_nclc, *,
    last_canonical_mock_at, canonical_mock_streak_green) -> Readiness:
```

The decision tree:
- Any skill not `confident` → red, reason="Insufficient data".
- All confident:
  - `min_prob ≥ 0.80` AND mock streak ≥ 2 → green.
  - `min_prob ≥ 0.80` AND mock streak < 2 → yellow ("posteriors say
    green, gate is mock-streak").
  - `0.50 ≤ min_prob < 0.80` → yellow ("borderline").
  - `min_prob < 0.50` → red ("not yet").

## 9. API surface

| Route | Method | Handler |
|---|---|---|
| `/v1/plan` | GET | `routes/plan.py::get_plan` (auto-generates if missing) |
| `/v1/plan/regenerate` | POST | `routes/plan.py::regenerate` |
| `/v1/plan/today` | GET | `routes/plan.py::today` |
| `/v1/diagnostic/start` | POST | `routes/diagnostic.py::start` |
| `/v1/diagnostic/{id}/answer` | POST | `routes/diagnostic.py::answer` |
| `/v1/diagnostic/{id}/finish` | POST | `routes/diagnostic.py::finish` |
| `/v1/insights/readiness` | GET | `routes/insights.py::readiness` |

`/v1/insights/nclc-trajectory` and `/v1/insights/weak-points` remain
Phase 8 stubs.

In-process state lives in `apps/api/src/tcf_accel_api/state.py`:
`UserState` holds `posteriors`, `plan`, `diagnostics`,
`canonical_mock_streak_green`. Phase 5 swaps the registry for a
Postgres-backed store.

## 10. Testing surface

| Path | What it tests |
|---|---|
| `packages/sla/tests/test_fsrs.py` | FSRS-shape invariants (rating monotonicity, AGAIN bounds, etc.) |
| `packages/sla/tests/test_lector.py` | Penalty curve, idempotency, confusable-pair shift |
| `packages/sla/tests/test_nclc_estimator.py` | Update correctness, confidence gate, calibration recovery |
| `packages/sla/tests/test_cat_diagnostic.py` | Stopping rule, same-difficulty-run cap, convergence |
| `packages/sla/tests/test_allocator.py` | Sum invariant, floor, production-skill weighting |
| `packages/sla/tests/test_readiness.py` | All readiness branches + ADR-025 launch-blocker |
| `tests/pedagogy/synthetic_cohorts.py` + `test_synthetic_cohorts.py` | 12 archetypal cohorts |
| `tests/property/test_scheduler_invariants.py` | Hypothesis-driven FSRS invariants |
| `tests/property/test_estimator_calibration.py` | 200-learner synthetic calibration audit |
| `tests/property/test_readiness_invariants.py` | Hypothesis-driven readiness launch-blocker |
| `apps/api/tests/test_plan_routes.py` | API contract for /v1/plan/* |
| `apps/api/tests/test_diagnostic_routes.py` | API contract for /v1/diagnostic/* |
| `apps/api/tests/test_readiness_route.py` | API contract for /v1/insights/readiness |
