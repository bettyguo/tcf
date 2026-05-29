"""Mock report — section presence, booking-advice invariants."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from tcf_accel.ids import MockExamId, UserId

from tcf_accel_sla.estimator.nclc import SkillPosterior, bootstrap_posterior
from tcf_accel_sla.mock_exam import (
    MockExamReportFull,
    booking_advice,
    render_html,
    render_markdown,
)
from tcf_accel_sla.mock_exam.report import REPORT_SECTIONS, PerItemRow
from tcf_accel_sla.mock_exam.scorer import MockSkillScore


def _fixture_report(
    *,
    overall_nclc: int | None = 8,
    overall_confident: bool = True,
    light: str = "green",
    canonical_streak_green: int = 2,
    mode: str = "canonical",
) -> MockExamReportFull:
    per_skill = {}
    for skill in ("CO", "CE", "EE", "EO"):
        post = SkillPosterior(
            skill=skill,  # type: ignore[arg-type]
            mean=8.0,
            variance=0.2,
            n_obs=80,
            difficulty_bands_seen=frozenset({6, 7, 8}),
        )
        per_skill[skill] = MockSkillScore(
            skill=skill,  # type: ignore[arg-type]
            raw=30.0,
            max_raw=39.0,
            posterior=post,
            n_items=39,
        )
    return MockExamReportFull(
        mock_id=MockExamId(uuid4()),
        user_id=UserId(uuid4()),
        completed_at=datetime(2026, 5, 28, tzinfo=UTC),
        mode=mode,  # type: ignore[arg-type]
        overall_nclc=overall_nclc,
        overall_confident=overall_confident,
        bottleneck_skill="EE",
        light=light,  # type: ignore[arg-type]
        light_reason="example reason text",
        per_skill=per_skill,
        drill_posteriors={
            s: bootstrap_posterior(skill=s, self_report_nclc=7.5)  # type: ignore[arg-type]
            for s in ("CO", "CE", "EE", "EO")
        },
        per_item_rows={
            "CO": [
                PerItemRow(
                    item_id_short="abcdef12",
                    module="CO",
                    cefr="B2",
                    difficulty=8.0,
                    correct=True,
                    rt_ms=12000,
                ),
            ],
            "EE": [
                PerItemRow(
                    item_id_short="11112222",
                    module="EE",
                    cefr="B2",
                    difficulty=8.0,
                    correct=None,
                    rubric_total_20=14.0,
                    task_number=1,
                ),
            ],
            "EO": [
                PerItemRow(
                    item_id_short="33334444",
                    module="EO",
                    cefr="B2",
                    difficulty=8.0,
                    correct=None,
                    rubric_total_20=15.0,
                    task_number=2,
                ),
            ],
        },
        canonical_streak_green=canonical_streak_green,
    )


def test_markdown_contains_all_seven_sections() -> None:
    rendered = render_markdown(_fixture_report())
    for section in REPORT_SECTIONS:
        assert section.lower() in rendered.lower(), f"missing section {section}"


def test_html_contains_all_seven_sections() -> None:
    rendered = render_html(_fixture_report())
    for section in REPORT_SECTIONS:
        assert section.lower() in rendered.lower(), f"missing section {section}"


def test_markdown_traffic_light_emoji_present() -> None:
    rendered = render_markdown(_fixture_report(light="green"))
    assert "🟢" in rendered


def test_html_is_standalone_document() -> None:
    rendered = render_html(_fixture_report())
    assert rendered.startswith("<!doctype html>")
    assert "</html>" in rendered


@pytest.mark.parametrize("streak", [0, 1])
def test_single_green_mock_never_recommends_booking(streak: int) -> None:
    """Anti-criterion: booking advice never escalates with < 2 consecutive greens."""
    advice = booking_advice(
        light="green",
        canonical_streak_green=streak,
        mode="canonical",
    )
    assert "reasonable" not in advice.lower()
    assert "another" in advice.lower() or "do not" in advice.lower()


def test_two_consecutive_canonical_greens_unlocks_booking() -> None:
    advice = booking_advice(
        light="green", canonical_streak_green=2, mode="canonical",
    )
    assert "reasonable" in advice.lower()


def test_yellow_never_recommends_booking() -> None:
    advice = booking_advice(
        light="yellow", canonical_streak_green=5, mode="canonical",
    )
    assert "do not book" in advice.lower() or "not yet" in advice.lower()


def test_red_never_recommends_booking() -> None:
    advice = booking_advice(
        light="red", canonical_streak_green=5, mode="canonical",
    )
    assert "do not book" in advice.lower() or "not yet" in advice.lower()


def test_training_mode_never_recommends_booking() -> None:
    advice = booking_advice(
        light="green", canonical_streak_green=5, mode="training",
    )
    assert "reasonable" not in advice.lower()
    assert "training" in advice.lower() or "canonical" in advice.lower()


def test_report_with_insufficient_evidence_does_not_show_overall_nclc() -> None:
    report = _fixture_report(overall_nclc=None, overall_confident=False)
    rendered = render_markdown(report)
    assert "Insufficient evidence" in rendered
