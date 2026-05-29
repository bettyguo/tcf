"""Mock-exam report renderer — Markdown + HTML.

Produces the seven-section report from `phase6_design.md §7`:

1. Headline (overall NCLC ± CI, bottleneck, traffic light).
2. Module breakdown (per-skill score table + per-item rows).
3. EE report (per-task rubric).
4. EO report (per-task rubric + suggested pronunciation drill).
5. Trajectory (mock vs drill posterior).
6. Actionable plan (top 3 next-week tasks).
7. Booking advice (strictly gated: 2 consecutive 🟢 canonical mocks).

The renderer is *pure*: it takes a `MockExamReportFull` value and
returns a string. No I/O. The caller writes to disk or wire.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final, Literal

from tcf_accel.ids import MockExamId, UserId
from tcf_accel.schemas.api.insights import ReadinessLight
from tcf_accel.schemas.item import Module
from tcf_accel.schemas.scoring import SkillCode

from tcf_accel_sla.estimator.nclc import SkillPosterior
from tcf_accel_sla.mock_exam.scorer import MockSkillScore

REPORT_SECTIONS: Final[tuple[str, ...]] = (
    "Headline",
    "Module breakdown",
    "EE report",
    "EO report",
    "Trajectory",
    "Actionable plan",
    "Booking advice",
)

_LIGHT_EMOJI: Final[Mapping[ReadinessLight, str]] = {
    "red": "🔴",
    "yellow": "🟡",
    "green": "🟢",
}


@dataclass(frozen=True)
class PerItemRow:
    """One row in the per-module breakdown section."""

    item_id_short: str       # last 8 chars of the UUID
    module: Module
    cefr: str
    difficulty: float
    correct: bool | None     # None for EE/EO (rubric, not boolean)
    rt_ms: int = 0
    rubric_total_20: float | None = None
    task_number: int | None = None


@dataclass(frozen=True)
class WeakPatternHint:
    """One weak-pattern hint surfaced in the actionable plan."""

    skill: SkillCode
    pattern: str
    suggestion: str


@dataclass(frozen=True)
class MockExamReportFull:
    """The complete renderable report record."""

    mock_id: MockExamId
    user_id: UserId
    completed_at: datetime
    mode: Literal["canonical", "training"]
    overall_nclc: int | None
    overall_confident: bool
    bottleneck_skill: SkillCode
    light: ReadinessLight
    light_reason: str
    per_skill: dict[SkillCode, MockSkillScore]
    drill_posteriors: dict[SkillCode, SkillPosterior]
    per_item_rows: dict[Module, list[PerItemRow]]
    divergence_alerts: list[str] = field(default_factory=list)
    weak_patterns: list[WeakPatternHint] = field(default_factory=list)
    canonical_streak_green: int = 0
    last_canonical_at: datetime | None = None


def booking_advice(
    *,
    light: ReadinessLight,
    canonical_streak_green: int,
    mode: Literal["canonical", "training"],
) -> str:
    """The booking-advice text. Never escalates to "ready" without ≥ 2 🟢 canonical.

    Anti-criterion enforced here: a single green mock NEVER suggests
    booking. The Phase 6 acceptance test asserts this in two places —
    here, and against the report sample.
    """
    if mode == "training":
        return (
            "Training mode mocks do not count toward your readiness streak. "
            "Sit a canonical mock to update your booking advice."
        )
    if light != "green":
        if light == "yellow":
            return (
                "Borderline — keep working the plan and sit another canonical "
                "mock in 7 days. Do not book the exam yet."
            )
        return (
            "Not yet — your bottleneck skill is still well below target. "
            "Do not book the exam; continue the plan."
        )
    if canonical_streak_green < 2:
        return (
            f"You hit green on this canonical mock, but the system requires "
            f"≥ 2 consecutive canonical greens before recommending a booking. "
            f"Current streak: {canonical_streak_green}. Sit another canonical "
            f"mock in 7 days."
        )
    return (
        "You have sustained green for ≥ 2 canonical mocks — booking the exam "
        "in 2–4 weeks is reasonable."
    )


def _format_ci(p: SkillPosterior) -> str:
    return f"NCLC {p.mean:.1f} (CI {p.ci_low}–{p.ci_high}, n={p.n_obs})"


def _format_overall(report: MockExamReportFull) -> str:
    if not report.overall_confident or report.overall_nclc is None:
        return (
            "Insufficient evidence to assign an overall NCLC band yet. "
            "Per-skill posteriors below are shown individually."
        )
    return (
        f"Overall NCLC **{report.overall_nclc}**, bottleneck "
        f"**{report.bottleneck_skill}**."
    )


def render_markdown(report: MockExamReportFull) -> str:
    """Render the report as Markdown — the human-facing form."""
    lines: list[str] = []
    lines.append(f"# Mock exam report — {report.mock_id}")
    lines.append("")
    lines.append(
        f"*Completed {report.completed_at.isoformat()} — mode: "
        f"`{report.mode}` — user: `{report.user_id}`*",
    )
    lines.append("")

    # 1. Headline
    lines.append("## 1. Headline")
    lines.append("")
    lines.append(f"{_LIGHT_EMOJI[report.light]} **{report.light.upper()}**.")
    lines.append("")
    lines.append(_format_overall(report))
    lines.append("")
    lines.append(f"> _{report.light_reason}_")
    lines.append("")

    if report.divergence_alerts:
        lines.append("### Divergence alerts")
        for alert in report.divergence_alerts:
            lines.append(f"- ⚠️  {alert}")
        lines.append("")

    # 2. Module breakdown
    lines.append("## 2. Module breakdown")
    lines.append("")
    lines.append("| Skill | Raw | Posterior |")
    lines.append("|-------|-----|-----------|")
    for skill in ("CO", "CE", "EE", "EO"):
        s = report.per_skill[skill]
        raw_str = (
            f"{int(s.raw)}/{int(s.max_raw)}"
            if skill in ("CO", "CE")
            else f"{s.raw:.1f}/{s.max_raw:.0f}"
        )
        lines.append(f"| {skill} | {raw_str} | {_format_ci(s.posterior)} |")
    lines.append("")

    for module in ("CO", "CE"):
        rows = report.per_item_rows.get(module, [])
        if not rows:
            continue
        lines.append(f"### {module} per-item")
        lines.append("")
        lines.append("| Item | CEFR | Difficulty | Correct | RT (ms) |")
        lines.append("|------|------|------------|---------|---------|")
        for row in rows:
            mark = "✓" if row.correct else "✗"
            lines.append(
                f"| `{row.item_id_short}` | {row.cefr} | "
                f"{row.difficulty:.2f} | {mark} | {row.rt_ms} |",
            )
        lines.append("")

    # 3. EE report
    lines.append("## 3. EE report")
    lines.append("")
    ee_rows = report.per_item_rows.get("EE", [])
    if ee_rows:
        lines.append("| Task | Rubric / 20 | Difficulty |")
        lines.append("|------|-------------|------------|")
        for row in ee_rows:
            rubric_str = (
                f"{row.rubric_total_20:.1f}" if row.rubric_total_20 is not None else "—"
            )
            lines.append(
                f"| Task {row.task_number} | {rubric_str} | {row.difficulty:.2f} |",
            )
        lines.append("")
    lines.append(
        "Model improvements per task are surfaced in the writing-feedback UI "
        "(Phase 7 + Phase 8). The current rubric scorer is the Phase 5 stub; "
        "Phase 7 wires the calibrated scorer.",
    )
    lines.append("")

    # 4. EO report
    lines.append("## 4. EO report")
    lines.append("")
    eo_rows = report.per_item_rows.get("EO", [])
    if eo_rows:
        lines.append("| Task | Rubric / 20 | Difficulty |")
        lines.append("|------|-------------|------------|")
        for row in eo_rows:
            rubric_str = (
                f"{row.rubric_total_20:.1f}" if row.rubric_total_20 is not None else "—"
            )
            lines.append(
                f"| Task {row.task_number} | {rubric_str} | {row.difficulty:.2f} |",
            )
        lines.append("")
    lines.append(
        "Suggested next-step pronunciation drill: `eo_picture` at the "
        "bottleneck CEFR band (Phase 8 surfaces the audio player + spectrogram).",
    )
    lines.append("")

    # 5. Trajectory
    lines.append("## 5. Trajectory")
    lines.append("")
    lines.append("| Skill | Drill | Mock | Δ |")
    lines.append("|-------|-------|------|---|")
    for skill in ("CO", "CE", "EE", "EO"):
        drill = report.drill_posteriors.get(skill)
        mock = report.per_skill[skill].posterior
        if drill is None:
            lines.append(f"| {skill} | — | {mock.mean:.1f} | — |")
        else:
            delta = mock.mean - drill.mean
            lines.append(
                f"| {skill} | {drill.mean:.1f} | {mock.mean:.1f} | {delta:+.1f} |",
            )
    lines.append("")

    # 6. Actionable plan
    lines.append("## 6. Actionable plan (top 3)")
    lines.append("")
    if not report.weak_patterns:
        lines.append(
            f"1. Focus on **{report.bottleneck_skill}** drills at your current "
            f"CEFR band for 30 min/day.",
        )
        lines.append(
            "2. Add one exam-shape session per week to maintain timing fidelity.",
        )
        lines.append("3. Schedule the next canonical mock in 7 days.")
    else:
        for i, w in enumerate(report.weak_patterns[:3], start=1):
            lines.append(f"{i}. **{w.skill}** — {w.pattern}. {w.suggestion}")
    lines.append("")

    # 7. Booking advice
    lines.append("## 7. Booking advice")
    lines.append("")
    lines.append(
        booking_advice(
            light=report.light,
            canonical_streak_green=report.canonical_streak_green,
            mode=report.mode,
        ),
    )
    lines.append("")

    return "\n".join(lines)


def render_html(report: MockExamReportFull) -> str:
    """Render the report as standalone HTML.

    Embeds CSS inline so the report renders the same in a browser, a
    PDF print job, and an emailed copy. No external assets.
    """
    md_str = render_markdown(report)
    # Heuristic Markdown → HTML pass; we do not pull a real markdown
    # library to keep deps minimal. Phase 8 (frontend) handles rich
    # rendering for the interactive UI; this string is for the
    # standalone artifact (operator + email).
    body = html.escape(md_str)
    # Minimal block-level handling: turn lines starting with # into <h*>.
    rendered_lines: list[str] = []
    in_table = False
    for raw in body.splitlines():
        line = raw.rstrip()
        if line.startswith("####"):
            rendered_lines.append(f"<h4>{line.lstrip('#').strip()}</h4>")
        elif line.startswith("###"):
            rendered_lines.append(f"<h3>{line.lstrip('#').strip()}</h3>")
        elif line.startswith("##"):
            rendered_lines.append(f"<h2>{line.lstrip('#').strip()}</h2>")
        elif line.startswith("#"):
            rendered_lines.append(f"<h1>{line.lstrip('#').strip()}</h1>")
        elif line.startswith("|"):
            if not in_table:
                rendered_lines.append("<table>")
                in_table = True
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Skip Markdown's separator rows ("|---|---|").
            if all(set(c) <= set("-: ") for c in cells if c):
                continue
            row = "".join(f"<td>{c}</td>" for c in cells)
            rendered_lines.append(f"<tr>{row}</tr>")
        elif line.startswith("- "):
            rendered_lines.append(f"<li>{line[2:]}</li>")
        elif line.startswith("&gt; "):
            rendered_lines.append(f"<blockquote>{line[5:]}</blockquote>")
        else:
            if in_table:
                rendered_lines.append("</table>")
                in_table = False
            if line:
                rendered_lines.append(f"<p>{line}</p>")
    if in_table:
        rendered_lines.append("</table>")

    return (
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'>"
        f"<title>Mock exam {report.mock_id}</title>"
        "<style>"
        "body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2em auto; }"
        "h1 { border-bottom: 2px solid #333; }"
        "h2 { color: #1a4d8c; margin-top: 1.6em; }"
        "table { border-collapse: collapse; margin: 1em 0; }"
        "td { border: 1px solid #ccc; padding: 0.3em 0.6em; }"
        "blockquote { color: #555; border-left: 3px solid #999; padding-left: 0.8em; }"
        "</style></head><body>\n"
        + "\n".join(rendered_lines)
        + "\n</body></html>\n"
    )


__all__ = [
    "MockExamReportFull",
    "PerItemRow",
    "REPORT_SECTIONS",
    "WeakPatternHint",
    "booking_advice",
    "render_html",
    "render_markdown",
]
