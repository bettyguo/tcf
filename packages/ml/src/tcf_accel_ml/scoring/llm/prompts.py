"""Structured-prompt builders for the cloud LLM critic.

The cloud LLM adapter is opt-in; the prompt builders live in the
package so the prompts are versioned alongside the calibration tables.

Prompt invariants (ADR-039):

- Temperature ≤ 0.2.
- Structured output enforcement (JSON schema or `response_format` per
  provider).
- A "refuse-to-inflate" instruction: 5/5 on any dimension requires a
  quoted text span as evidence; otherwise drop to 4/5.
- Few-shot anchors at NCLC 7, 9, 11.
"""

from __future__ import annotations

from typing import Final

EE_STRICT_INSTRUCTION: Final[str] = (
    "You are grading a TCF Canada Expression écrite (EE) Task {task_number} response "
    "against the published 6-dimension rubric. Each dimension is scored 0–5 "
    "(0 = absent, 5 = ceiling NCLC 11+ performance).\n"
    "\n"
    "Strict-grading rule: a 5/5 on any dimension REQUIRES you to quote at "
    "least one specific text span in the submission as evidence. If you "
    "cannot quote evidence, the score is 4/5 maximum.\n"
    "\n"
    "Inflation guard: the auto-scorer's feature pipeline produces an "
    "independent floor estimate of each dimension; gross divergence will "
    "trigger a clamp at score-merge time. Do not pre-clamp.\n"
    "\n"
    "Required Canadian context for this task: {required_canadian_context}.\n"
    "Target word count: {target_word_count_range[0]}–{target_word_count_range[1]}.\n"
    "\n"
    "Return a JSON object with keys: rubric_scores (the 6 dimensions, "
    "integer 0–5; canadian_context_integration MAY be null for Task 1), "
    "justifications (one English sentence per dimension), error_annotations "
    "(span_start, span_end, error_type, suggestion, confidence per error), "
    "suggested_rewrites (up to 3 of the weakest sentences), and confidence "
    "(your overall confidence in [0, 1])."
)

EE_FEWSHOT_ANCHORS: Final[str] = (
    "Anchors (paraphrased; do not echo back):\n"
    "- NCLC 7 (≈14/20): organized paragraphs, simple connectors, "
    "  occasional agreement/tense errors, limited register variation.\n"
    "- NCLC 9 (≈16/20): clear discourse moves, varied connectors, low "
    "  error density, demonstrable Canadian context for Tasks 2 & 3, "
    "  appropriate register.\n"
    "- NCLC 11 (≈18/20): sophisticated lexicon, subjunctive / conditional "
    "  used correctly in context, register fully on-target, no repeated "
    "  agreement errors, all 3 Canadian-context cues integrated naturally."
)

EO_STRICT_INSTRUCTION: Final[str] = (
    "You are grading a TCF Canada Expression orale (EO) Task {task_number} "
    "transcript against the published 6-dimension rubric. The transcript "
    "is the Whisper-fr ASR output; you may also see prosody summaries.\n"
    "\n"
    "Strict-grading rule: same as EE — 5/5 requires quoted evidence.\n"
    "\n"
    "Note: the `pronunciation_prosody` dimension consumes the dedicated "
    "pronunciation pipeline; you should focus on lexical / interactional "
    "evidence and may set `pronunciation_prosody` to null if the "
    "transcript alone is insufficient.\n"
    "\n"
    "Return the same JSON shape as EE."
)


def build_ee_prompt(
    *,
    rubric_version: str,
    task_number: int,
    target_word_count_range: tuple[int, int],
    required_canadian_context: bool,
    prompt: str,
    text: str,
) -> str:
    """Render the full EE prompt string for the cloud critic."""
    return (
        EE_STRICT_INSTRUCTION.format(
            task_number=task_number,
            target_word_count_range=target_word_count_range,
            required_canadian_context=required_canadian_context,
        )
        + "\n\n"
        + EE_FEWSHOT_ANCHORS
        + f"\n\nRubric version: {rubric_version}\n"
        + f"\nTask prompt:\n{prompt}\n\nCandidate response:\n{text}\n"
    )


def build_eo_prompt(
    *,
    rubric_version: str,
    task_number: int,
    duration_s: float,
    prompt: str,
    transcript: str,
) -> str:
    """Render the full EO prompt string for the cloud critic."""
    return (
        EO_STRICT_INSTRUCTION.format(task_number=task_number)
        + f"\n\nRubric version: {rubric_version}\n"
        + f"Duration: {duration_s:.1f}s\n"
        + f"\nTask prompt:\n{prompt}\n\nTranscript:\n{transcript}\n"
    )


__all__ = ["build_ee_prompt", "build_eo_prompt"]
