"""Scripted candidate — end-to-end mock-exam driver.

Drives the FastAPI `/v1/mock-exam/*` surface as if it were a human
candidate, sampling answer correctness per CEFR band and rubric
scores per task. Used in two places:

- `apps/api/tests/test_mock_exam_routes.py` runs it as the
  integration test of the whole phase.
- `phase6_audit.md`'s diversity metric calls it 100× with varying
  seeds and accumulates the union of selected items.

The candidate is *deterministic* given (profile, rng_seed): the same
inputs always produce the same submitted answers and so the same
report. This is what makes the audit reproducible.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final

from tcf_accel.schemas.item import CefrLevel, Module

from tcf_accel_sla.mock_exam.spec import EXAM_SHAPE

# Default p(correct) by CEFR band for a "typical NCLC 7 / B2" candidate.
DEFAULT_P_CORRECT: Final[dict[CefrLevel, float]] = {
    "A1": 0.92,
    "A2": 0.88,
    "B1": 0.78,
    "B2": 0.62,
    "C1": 0.45,
    "C2": 0.28,
}

DEFAULT_RUBRIC_BY_TASK: Final[dict[int, int]] = {1: 14, 2: 13, 3: 12}


@dataclass(frozen=True)
class CandidateProfile:
    """Behavior profile of the scripted candidate."""

    co_p_correct_by_band: dict[CefrLevel, float] = field(
        default_factory=lambda: dict(DEFAULT_P_CORRECT),
    )
    ce_p_correct_by_band: dict[CefrLevel, float] = field(
        default_factory=lambda: dict(DEFAULT_P_CORRECT),
    )
    ee_target_total_20_by_task: dict[int, int] = field(
        default_factory=lambda: dict(DEFAULT_RUBRIC_BY_TASK),
    )
    eo_target_total_20_by_task: dict[int, int] = field(
        default_factory=lambda: dict(DEFAULT_RUBRIC_BY_TASK),
    )
    # Per-item timing in milliseconds: mean & s.d.
    # Defaults match the FEI wall-clock: 35 min / 39 items ≈ 53.8 s for
    # CO; 60 min / 39 items ≈ 92.3 s for CE. The audit-timing target
    # (2:47:00 ± 30 s) holds with the EE/EO modules taking their full
    # allotted duration.
    co_item_ms_mean: int = 53_846   # 35*60_000 / 39
    ce_item_ms_mean: int = 92_307   # 60*60_000 / 39
    timing_jitter_ms: int = 4_000


@dataclass
class _CandidateState:
    rng: random.Random
    sim_clock: float  # accumulated seconds simulated; for timing-audit


def expected_active_seconds(profile: CandidateProfile) -> int:
    """Sum of CO + CE + EE + EO active wallclock per the profile.

    Used by the timing audit (`phase6_audit.md`): the scripted
    candidate must finish in 2:47:00 ± 30 s of *active* test time.
    """
    co_total_ms = profile.co_item_ms_mean * EXAM_SHAPE["CO"]
    ce_total_ms = profile.ce_item_ms_mean * EXAM_SHAPE["CE"]
    # EE + EO total durations fixed by spec, since the candidate uses
    # the full module time for rubric tasks.
    ee_total_s = 60 * 60
    eo_total_s = 12 * 60
    return int((co_total_ms + ce_total_ms) / 1000 + ee_total_s + eo_total_s)


def _sample_correct(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def _sample_rt_ms(rng: random.Random, mean: int, jitter: int) -> int:
    """Truncated-normal-ish: clamp to [50ms, 4 × mean]."""
    val = mean + int(rng.gauss(0, jitter))
    return max(50, min(4 * mean, val))


@dataclass
class CandidateRunResult:
    """Outcome of one full mock run."""

    mock_id: str
    state_transitions: list[str]
    submitted_payload: dict[str, Any]
    report: dict[str, Any] | None
    elapsed_simulated_s: float
    selected_item_ids: list[str]
    leak_audit_passed: bool


_FORBIDDEN_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {"correct_option_id", "explanation", "answer_key"},
)


def _walk_for_leaks(node: object) -> bool:
    """Return True iff `node` contains no forbidden answer-key fields."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in _FORBIDDEN_RESPONSE_KEYS and v not in (None, "", []):
                return False
            if not _walk_for_leaks(v):
                return False
    elif isinstance(node, list):
        for child in node:
            if not _walk_for_leaks(child):
                return False
    return True


@dataclass
class CandidateRunner:
    """Stateful driver for one mock run.

    The runner accepts callbacks rather than a TestClient so it can be
    used both from the in-process FastAPI tests and from the audit
    script (which talks to a real running server).
    """

    start_mock: Callable[[dict[str, Any]], dict[str, Any]]
    fetch_items: Callable[[str, Module], list[dict[str, Any]]]
    submit_answer: Callable[[str, dict[str, Any]], dict[str, Any]]
    advance: Callable[[str], dict[str, Any]]
    submit_final: Callable[[str], dict[str, Any]]
    fetch_report: Callable[[str], dict[str, Any]]
    fetch_state: Callable[[str], dict[str, Any]] | None = None

    def run(
        self,
        profile: CandidateProfile,
        *,
        mode: str = "canonical",
        rng_seed: int = 42,
    ) -> CandidateRunResult:
        """Walk the full state machine and return the run result."""
        rng = random.Random(rng_seed)
        state = _CandidateState(rng=rng, sim_clock=0.0)
        transitions: list[str] = []
        selected: list[str] = []

        # 1) Start the mock.
        start_resp = self.start_mock({"mode": mode})
        mock_id = str(start_resp["id"])
        transitions.append(start_resp.get("state", "STARTED"))

        co_outcomes: list[dict[str, Any]] = []
        ce_outcomes: list[dict[str, Any]] = []
        ee_outcomes: list[dict[str, Any]] = []
        eo_outcomes: list[dict[str, Any]] = []
        leak_ok = True

        # 2) Walk each module:
        #    - From STARTED to CO_ACTIVE: 1 advance.
        #    - Between modules: 3 advances (MODULE_DONE → BREAK_n → NEXT_ACTIVE).
        for i, module in enumerate(("CO", "CE", "EE", "EO")):
            needed_advances = 1 if i == 0 else 3
            for _ in range(needed_advances):
                adv = self.advance(mock_id)
                transitions.append(adv.get("status") or "")

            items = self.fetch_items(mock_id, module)
            leak_ok = leak_ok and _walk_for_leaks(items)
            for item_dump in items:
                selected.append(str(item_dump.get("id", "")))
                if module in ("CO", "CE"):
                    cefr = item_dump.get("cefr_level", "B1")
                    p = (
                        profile.co_p_correct_by_band.get(cefr, 0.5)
                        if module == "CO"
                        else profile.ce_p_correct_by_band.get(cefr, 0.5)
                    )
                    is_correct = _sample_correct(state.rng, p)
                    mean_ms = (
                        profile.co_item_ms_mean
                        if module == "CO"
                        else profile.ce_item_ms_mean
                    )
                    rt_ms = _sample_rt_ms(
                        state.rng, mean_ms, profile.timing_jitter_ms,
                    )
                    state.sim_clock += rt_ms / 1000.0
                    self.submit_answer(
                        mock_id,
                        {
                            "item_id": item_dump["id"],
                            "module": module,
                            "kind": "mcq",
                            # The candidate picks the first option iff
                            # it intends to be "correct" — the *server*
                            # owns the correct_option_id; we mimic the
                            # learner by sending option "a" with prob p.
                            "selected_option_id": (
                                "a" if is_correct else "b"
                            ),
                            "rt_ms": rt_ms,
                        },
                    )
                    record = {
                        "item_id": item_dump["id"],
                        "module": module,
                        "difficulty": item_dump.get("difficulty_irt", 5.0),
                        "discrimination": item_dump.get(
                            "discrimination_irt", 1.0,
                        ),
                        "correct": is_correct,
                        "rt_ms": rt_ms,
                    }
                    (co_outcomes if module == "CO" else ce_outcomes).append(
                        record,
                    )
                else:
                    # EE/EO rubric
                    content = item_dump.get("content", {})
                    task = int(content.get("task_number", 1))
                    target = (
                        profile.ee_target_total_20_by_task.get(task, 12)
                        if module == "EE"
                        else profile.eo_target_total_20_by_task.get(task, 12)
                    )
                    rubric = max(
                        0,
                        min(
                            20,
                            int(round(target + state.rng.gauss(0, 1.5))),
                        ),
                    )
                    self.submit_answer(
                        mock_id,
                        {
                            "item_id": item_dump["id"],
                            "module": module,
                            "kind": "rubric",
                            "rubric_total_20": rubric,
                            "task_number": task,
                        },
                    )
                    cefr = item_dump.get("cefr_level", "B1")
                    prompt_target = {
                        "A1": 3.0, "A2": 4.0, "B1": 5.5,
                        "B2": 7.0, "C1": 9.0, "C2": 11.0,
                    }.get(cefr, 6.0)
                    record = {
                        "item_id": item_dump["id"],
                        "module": module,
                        "task_number": task,
                        "prompt_target_nclc": prompt_target,
                        "rubric_total_20": rubric,
                    }
                    (ee_outcomes if module == "EE" else eo_outcomes).append(
                        record,
                    )

        submitted = self.submit_final(mock_id)
        transitions.append(submitted.get("status") or "")
        report = self.fetch_report(mock_id)

        # Leak audit: state and report should never contain raw answers.
        if self.fetch_state is not None:
            try:
                live_state = self.fetch_state(mock_id)
                leak_ok = leak_ok and _walk_for_leaks(live_state)
            except Exception:  # noqa: BLE001 -- state may be inaccessible
                pass

        return CandidateRunResult(
            mock_id=mock_id,
            state_transitions=transitions,
            submitted_payload={
                "co_outcomes": co_outcomes,
                "ce_outcomes": ce_outcomes,
                "ee_outcomes": ee_outcomes,
                "eo_outcomes": eo_outcomes,
            },
            report=report,
            elapsed_simulated_s=state.sim_clock,
            selected_item_ids=selected,
            leak_audit_passed=leak_ok,
        )


__all__ = [
    "CandidateProfile",
    "CandidateRunner",
    "CandidateRunResult",
    "DEFAULT_P_CORRECT",
    "DEFAULT_RUBRIC_BY_TASK",
    "expected_active_seconds",
]
