# PHASE 4 — Learner Model: FSRS + LECTOR Scheduler, Bayesian NCLC Estimator, Diagnostic

> Goal: a calibrated learner model that (a) schedules every learnable item via FSRS-6 + LECTOR semantic spacing, (b) maintains a per-skill Bayesian posterior over NCLC level, (c) drives a diagnostic test that bootstraps the model in ≤ 60 minutes of learner time, and (d) refuses to over-predict.

---

## 1. THINK (produce `phase4_think.md`)

### 1.1 Three Sub-Models, Three Roles

| Sub-model | Role | Updates | Source |
|---|---|---|---|
| FSRS-6 | When to re-show each item (memory stability + difficulty + retrievability) | After each review | open-spaced-repetition/free-spaced-repetition-scheduler |
| LECTOR-style semantic spacer | Push confusable items apart in time | After each review involving a confusable family | arxiv 2508.03275 (LECTOR, 2025) |
| Bayesian NCLC posterior | Estimate per-skill NCLC level with calibrated uncertainty | After each scored interaction | IRT-style with conjugate Beta-Binomial for MCQ + Gaussian for rubric-scored |

These are **complementary**, not substitutes:

- FSRS optimizes retention of individual items.
- LECTOR avoids the failure mode where FSRS schedules `amener` and `emmener` on the same day, creating interference.
- The NCLC posterior is the **planning** signal: it tells the scheduler which skill to over-allocate time to, and tells the learner what NCLC they would likely get if they sat the exam today.

### 1.2 The Calibration Question

A critical reviewer asks: "What evidence supports your NCLC point estimate?" The honest answer: it's a *prediction*, not a measurement. Therefore:

- Always report a credible interval, not a point estimate.
- The "confident" flag is set only when:
  - n_obs ≥ 40 per skill (heuristic from IRT minimums for 1PL fit), AND
  - posterior variance ≤ 0.4 NCLC units (≈ ±1 NCLC band), AND
  - the learner's interaction history spans ≥ 3 difficulty bands (so we're not extrapolating).
- If `confident=False`, the UI is *forbidden* from showing the estimate as a final number; it must show "still learning your level — please complete N more items."

This is non-negotiable. Over-prediction is a financial harm.

### 1.3 The Diagnostic — Computer-Adaptive Testing (CAT)

For each skill, a CAT routine:

1. Start at item difficulty corresponding to the learner's self-reported level (default: B1 = NCLC 5).
2. Update posterior after each item.
3. Select next item maximizing **expected information gain** (Fisher information at the posterior mean) — but cap consecutive same-difficulty items to avoid frustration.
4. Stop when: posterior variance ≤ threshold OR 15 items administered OR 10 minutes elapsed.

For EE/EO: short writing+speaking prompts at three target levels (B1/B2/C1), scored with the Phase 7 auto-scorer, used to set the prior for the production-skill posterior.

Total diagnostic time: ~50 min CO+CE+EE+EO with breaks. Output: 4 NCLC posteriors + initial study plan + recommended 12-week schedule.

### 1.4 Why Bayesian, Not Just IRT?

Classical IRT gives a maximum-likelihood theta estimate but doesn't naturally express "we don't know enough yet." A Bayesian formulation:

- Prior: skill-level Gaussian centered on the learner's self-report, σ=1.2 (broad).
- Likelihood: 2-parameter IRT for MCQ items; rubric score modeled as Normal given true level for EE/EO.
- Posterior: numerical (Laplace approximation suffices; HMC if we need it later).
- Predictive: P(score ≥ target_nclc on real exam) directly from posterior → drives the "readiness traffic light."

### 1.5 Alternatives Considered

- **Pure FSRS**: misses confusable interference; doesn't drive planning. Rejected.
- **Pure CAT/IRT without FSRS**: doesn't tell us when to re-review; learner forgets. Rejected.
- **Frequentist MLE for NCLC**: doesn't represent uncertainty. Rejected.
- **A single end-to-end deep model that predicts everything**: black-box, hard to debug, hard to calibrate. Rejected for v1; reconsider when we have > 10k users of training data.

---

## 2. DESIGN (produce `phase4_design.md`)

### 2.1 FSRS Integration

Use `fsrs` Python package (the reference implementation from open-spaced-repetition).

```python
# packages/sla/src/scheduler/fsrs.py
from fsrs import FSRS, Card, Rating

class FSRSScheduler:
    def __init__(self, parameters: list[float] | None = None):
        self.fsrs = FSRS(parameters=parameters)  # default = FSRS-6 weights

    def review(self, card: Card, rating: Rating, now: datetime) -> Card:
        card, _ = self.fsrs.review_card(card, rating, now)
        return card  # contains updated stability, difficulty, due

    def optimize(self, history: list[ReviewLog]) -> list[float]:
        """Re-fit FSRS parameters on the user's own history; nightly job."""
        ...
```

The per-user FSRS parameter optimization runs nightly when the user has ≥ 100 reviews. Until then, defaults are used.

### 2.2 LECTOR Semantic Spacing

LECTOR's contribution: when two items are semantically confusable, their reviews should be temporally separated.

```python
# packages/sla/src/scheduler/lector.py
def lector_spacing_penalty(item_a: Item, item_b: Item, embeddings: np.ndarray) -> float:
    sim = cosine_similarity(embeddings[item_a.id], embeddings[item_b.id])
    if sim < 0.75:
        return 0.0  # not confusable; no spacing requirement
    # higher similarity → larger penalty for proximity
    return (sim - 0.75) ** 2 * MAX_PENALTY_DAYS

def adjust_due_with_lector(items_due_today: list[Item], recent_reviews: list[Review]) -> list[Item]:
    """Reorder/shift today's queue to maximize aggregate semantic distance."""
    ...
```

LECTOR runs *after* FSRS decides what's due, only to reorder/shift within the day's queue. It never delays an item by more than 2 days from FSRS's recommendation (to preserve FSRS's retention guarantees).

### 2.3 Bayesian NCLC Estimator

Per skill (CO, CE, EE, EO):

```python
# packages/sla/src/estimator/nclc.py
@dataclass
class SkillPosterior:
    mean: float                # in [1, 12]
    variance: float            # on same scale
    n_obs: int
    history_difficulty_spread: float  # # of distinct difficulty bands observed

    @property
    def ci_low(self) -> int: return int(max(1, self.mean - 1.96 * sqrt(self.variance)))
    @property
    def ci_high(self) -> int: return int(min(12, self.mean + 1.96 * sqrt(self.variance)))
    @property
    def confident(self) -> bool:
        return (self.n_obs >= 40
                and self.variance <= 0.4
                and self.history_difficulty_spread >= 3)

def update_posterior(prior: SkillPosterior, observation: Interaction, item: Item) -> SkillPosterior:
    """
    For MCQ: 2PL IRT likelihood
        P(correct | theta) = 1 / (1 + exp(-a * (theta - b)))
    For rubric: Gaussian likelihood with item-specific noise
    Update is Laplace approximation: find posterior mode, second derivative at mode = -1/var.
    """
    ...
```

### 2.4 The Diagnostic (CAT)

```python
# packages/sla/src/diagnostic/cat.py
class DiagnosticSession:
    def __init__(self, user_id: UUID, skill: Literal["CO","CE","EE","EO"]):
        self.posterior = SkillPosterior(mean=5.0, variance=1.44, n_obs=0, ...)  # B1 prior
        self.administered: list[Item] = []

    def next_item(self) -> Item | None:
        if self._should_stop(): return None
        target_b = self.posterior.mean
        return self._select_max_info(target_b, self.administered)

    def record(self, item: Item, interaction: Interaction):
        self.posterior = update_posterior(self.posterior, interaction, item)
        self.administered.append(item)

    def _should_stop(self) -> bool:
        return self.posterior.variance <= 0.3 or len(self.administered) >= 15
```

The diagnostic for EE/EO uses a single calibrated prompt per skill at each of three difficulty levels; the auto-scorer (Phase 7) produces the rubric score; the posterior is updated.

### 2.5 The Bottleneck-Driven Time Allocator

Translates §2.3 of the master prompt into code:

```python
# packages/sla/src/planner/allocator.py
def allocate(today_minutes: int, posteriors: dict[Skill, SkillPosterior], target: int) -> dict[Skill, int]:
    BETAS = {"CO": 1.0, "CE": 0.9, "EE": 1.4, "EO": 1.5}
    alphas = {s: max(0.01, (target - p.mean)) ** 2 * BETAS[s] for s, p in posteriors.items()}
    Z = sum(alphas.values())
    raw = {s: int(round(today_minutes * a / Z)) for s, a in alphas.items()}
    # enforce a floor of 10 min/skill to avoid neglect
    return enforce_floor(raw, floor=10, total=today_minutes)
```

The allocator is the *planner's* engine. Tested against synthetic cohorts (`tests/pedagogy/synthetic_cohorts.py`): a learner with CO=B2/CE=B2/EE=B1/EO=A2 targeting NCLC 9 must spend ≥ 50% of their daily minutes on EE+EO.

### 2.6 The Study Plan Generator

```python
def generate_plan(user: User, posteriors: dict, horizon_days: int = 84) -> StudyPlan:
    plan = []
    current_posteriors = deepcopy(posteriors)
    for day in range(horizon_days):
        minutes = user.daily_minutes_budget
        alloc = allocate(minutes, current_posteriors, user.target_nclc)
        blocks = []
        for skill, mins in alloc.items():
            blocks.append(select_drill_block(skill, mins, current_posteriors[skill], day))
        plan.append(DayPlan(date=user.start_date + timedelta(days=day), blocks=blocks))
        # simulate expected improvement to keep the projection honest
        current_posteriors = simulate_learning(current_posteriors, alloc)
    rationale = render_rationale(user, posteriors, plan)
    return StudyPlan(daily_blocks=plan, rationale=rationale, horizon_days=horizon_days)
```

`simulate_learning` is a conservative model: ~0.05 NCLC/hour of focused practice for the weakest skill, declining as the skill approaches the target (diminishing returns). Calibrated to land at ~70% probability of hitting target at target date; if it doesn't, the plan refuses to generate and warns the user.

### 2.7 The Readiness Traffic Light

`GET /v1/insights/readiness` returns one of:

- 🟢 **Likely ready** (P(min_skill ≥ target_NCLC) ≥ 0.80, n_obs sufficient)
- 🟡 **Borderline** (0.50 ≤ P < 0.80)
- 🔴 **Not yet** (P < 0.50)
- ⚪ **Insufficient data** (any skill not confident)

The estimator is *forbidden* from showing 🟢 without all four `confident` flags = True. This is the booking-decision interface; it is the single most consequential output of the whole system.

### 2.8 ADRs

- ADR-023: FSRS-6 default weights initially; per-user optimization at ≥ 100 reviews.
- ADR-024: LECTOR spacing penalty bounded so as not to overrule FSRS.
- ADR-025: Posterior reporting requires CI; confidence flag is launch-blocking.
- ADR-026: Diagnostic is CAT for CO/CE; rubric-scored prompts for EE/EO.
- ADR-027: Allocator over-weights production skills (β=1.4–1.5).

---

## 3. CODE

- `packages/sla/src/scheduler/{fsrs,lector}.py`
- `packages/sla/src/estimator/nclc.py` with the Laplace-approximation update
- `packages/sla/src/diagnostic/cat.py`
- `packages/sla/src/planner/{allocator,generate_plan,readiness}.py`
- `apps/api/routes/diagnostic.py`, `routes/plan.py`, `routes/insights.py`
- `tests/pedagogy/synthetic_cohorts.py` — 12 archetypal learners
- `tests/property/scheduler_invariants.py` — Hypothesis-driven FSRS invariants

---

## 4. AUDIT (produce `phase4_audit.md`)

- **FSRS conformance:** running 10,000 random review sequences through our wrapper and through the reference `fsrs` package produces bit-identical card states.
- **LECTOR effect:** in a synthetic confusable-pair scenario, our scheduler delays the second of the pair vs the FSRS baseline by ≥ 1 day on average.
- **Estimator calibration on synthetic data:** generate 1000 synthetic learners with known true NCLC; the 95% CI from the estimator contains the truth ≥ 92% of the time (allowing some miscalibration).
- **Estimator MAE on synthetic data:** ≤ 0.6 NCLC units once `confident=True`.
- **Allocator behavior:** runs the 12 archetypal cohorts, checks bottleneck allocation matches expectations.
- **Plan realism:** generated plans for the 12 cohorts don't promise the impossible (no plan claims NCLC 11 in 12 weeks from NCLC 4).
- **Refuse-to-predict:** for a fresh user with 5 interactions, `readiness` returns ⚪ and the UI hides numeric estimates.

---

## 5. EVALUATE (produce `phase4_evaluate.md`)

Acceptance criteria:

- ✅ All audit metrics pass.
- ✅ All ADRs ADR-023 through ADR-027 accepted.
- ✅ Diagnostic completes in ≤ 60 min for an average learner (measured against a scripted test agent that takes 30 s/CO item, 60 s/CE item, ~5 min/EE prompt, ~4 min/EO prompt).
- ✅ Allocator + planner integrate with API endpoints from Phase 2.

Anti-criteria:

- ❌ Any code path that reports an NCLC point estimate without an accompanying CI.
- ❌ Any path that returns 🟢 readiness while `confident=False` on any skill.
- ❌ Any allocator output that violates the production-skill floor when the bottleneck is EE or EO.

Hand-off: a synthetic-cohort report showing the estimator on each archetype; the planner-output rationale samples; FSRS+LECTOR integration verified.
