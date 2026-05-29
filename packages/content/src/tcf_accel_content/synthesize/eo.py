"""EO (expression orale) examiner-script synthesizer.

Foundation-grade: produces a Pydantic-valid `Item` with `EOContent`
from a typed task specification, with no LLM call. Examiner prompts
are selected deterministically from a curated pool keyed by
``(task_number, seed)``.

EO differs from EE in two ways:

- The "content" is a list of *examiner prompts* (Phase 5's TTS renders
  them; the candidate hears them, not reads them).
- Each task has a documented prep time and target duration
  (`03_CONTENT_PIPELINE.md §1.1`, master prompt §1.1): Task 1 is no
  prep + ~3 min Q&A; Tasks 2/3 are ~2 min prep + ~3.5 min.

Unlike EE, the `EOContent` schema does not carry a
``required_canadian_context`` field — the design records Canadian
context as a soft signal in the prompt text only.

Items are tagged ``synthetic=True`` for the same reason as EE: the
whole stimulus is authored.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from tcf_accel.schemas import (
    EOContent,
    Item,
    ItemMetadata,
    Provenance,
)

from tcf_accel_content._ids import derive_item_id
from tcf_accel_content.cefr import CEFRClassifier, CefrLevel
from tcf_accel_content.types import CandidateItem, SynthesisTrace

SYNTHESIZER_VERSION: str = "eo-fake-v0"
RUBRIC_VERSION: str = "eo.v1"
SOURCE_NAME: str = "foundation_eo_pool"
SOURCE_LICENSE: str = "CC-BY-SA-4.0"

TaskNumber = Literal[1, 2, 3]
CefrTarget = Literal["B2", "C1"]

# Per master prompt §1.1: EO total 12 min including 2 min prep.
# Task 1 has no prep; Tasks 2/3 each get the prep budget.
_PREP_TIME_S: dict[TaskNumber, int] = {1: 0, 2: 60, 3: 60}
_TARGET_DURATION_S: dict[TaskNumber, int] = {1: 180, 2: 210, 3: 210}

# Curated examiner-prompt pool. Each variant is a list of utterances
# the examiner reads in order — Phase 5's TTS pipeline plays them with
# inter-prompt pauses. The pool is small but covers Canadian and
# generic contexts; the seed picks one variant per call.
_PROMPT_POOL: dict[TaskNumber, tuple[tuple[str, ...], ...]] = {
    1: (
        (
            "Bonjour. Pouvez-vous vous présenter en quelques phrases ?",
            "Pourquoi avez-vous décidé de passer le TCF Canada ?",
            "Que faites-vous pendant votre temps libre ?",
        ),
        (
            "Bonjour. Pouvez-vous parler de votre famille et de l'endroit où vous habitez ?",
            "Quel est votre travail actuel, ou que comptez-vous faire au Canada ?",
            "Quelles sont vos passions ou centres d'intérêt principaux ?",
        ),
    ),
    2: (
        (
            "Comparez la vie dans une grande ville et la vie en région rurale au Canada.",
            "Selon vous, lequel des deux modes de vie convient mieux à un nouvel "
            "arrivant, et pourquoi ?",
        ),
        (
            "Comparez les avantages d'apprendre le français en immersion "
            "et en classe traditionnelle.",
            "Quelle approche recommanderiez-vous à un ami qui prépare le TCF, et pourquoi ?",
        ),
    ),
    3: (
        (
            "Certains affirment que le télétravail devrait devenir la norme dans les "
            "entreprises canadiennes. D'autres pensent qu'il nuit à l'intégration "
            "des nouveaux arrivants.",
            "Quelle est votre position sur cette question, et comment la "
            "défendez-vous ?",
            "Comment répondriez-vous à quelqu'un qui défend la position opposée ?",
        ),
        (
            "Le gouvernement du Canada envisage de renforcer les exigences "
            "linguistiques en français pour l'immigration économique.",
            "Êtes-vous favorable ou opposé à cette politique, et pourquoi ?",
            "Que répondriez-vous à un partisan de la position contraire ?",
        ),
    ),
}

_ANCHOR_PLACEHOLDER: dict[str, str] = {
    "nclc_7": (
        "[Foundation placeholder - Phase 7 replaces with "
        "calibrated NCLC 7 spoken response.]"
    ),
    "nclc_9": (
        "[Foundation placeholder - Phase 7 replaces with "
        "calibrated NCLC 9 spoken response.]"
    ),
    "nclc_11": (
        "[Foundation placeholder - Phase 7 replaces with "
        "calibrated NCLC 11 spoken response.]"
    ),
}


@dataclass(frozen=True)
class EOSynthesisInput:
    """Typed input to `synthesize_eo_prompt`.

    Matches the shape `phase3_design.md §3.4` documents for the
    LLM-driven follow-up synthesizer.
    """

    task_number: TaskNumber
    cefr_target: CefrTarget
    seed: int = 0
    ingested_at: datetime = datetime(2026, 5, 28, tzinfo=UTC)


def synthesize_eo_prompt(
    inp: EOSynthesisInput,
    *,
    classifier: CEFRClassifier,
) -> CandidateItem:
    """Produce one candidate EO item (no LLM call).

    Args:
        inp: All task + seed parameters.
        classifier: Consulted for the `cefr_confidence` metric on the
            concatenated examiner prompts; the item's `cefr_level` is
            set from ``inp.cefr_target`` (see EE rationale).

    Returns:
        A `CandidateItem` with `EOContent`, full provenance, and
        placeholder calibration anchors. The quality gate treats EO as
        MCQ-less; the license check is the foundation gate.

    Complexity: O(|concatenated prompts|) + classifier cost.
    """
    if inp.task_number not in (1, 2, 3):
        raise ValueError(f"task_number must be 1, 2, or 3 (got {inp.task_number!r})")

    pool = _PROMPT_POOL[inp.task_number]
    seed_digest = hashlib.sha256(
        f"eo|task={inp.task_number}|seed={inp.seed}".encode(),
    ).digest()
    examiner_prompts = pool[seed_digest[0] % len(pool)]

    joined = " ".join(examiner_prompts)
    cefr_pred = classifier.classify(joined)

    content = EOContent(
        task_number=inp.task_number,
        examiner_prompts=list(examiner_prompts),
        candidate_prep_time_s=_PREP_TIME_S[inp.task_number],
        target_duration_s=_TARGET_DURATION_S[inp.task_number],
        rubric_version=RUBRIC_VERSION,
    )

    source_id = _source_id(inp.task_number, inp.seed)
    prompt_hash = _prompt_hash(joined, inp.task_number, inp.seed)

    item_id = derive_item_id(
        source=SOURCE_NAME,
        source_id=source_id,
        synthesizer_version=SYNTHESIZER_VERSION,
        prompt_hash=prompt_hash,
        seed=inp.seed,
    )

    provenance = Provenance(
        source=SOURCE_NAME,
        source_id=source_id,
        license=SOURCE_LICENSE,
        ingested_at=inp.ingested_at,
        synthesizer_version=SYNTHESIZER_VERSION,
        llm_model="none/foundation",
        llm_prompt_hash=prompt_hash,
        review_status="auto_passed",
    )

    metadata = ItemMetadata(
        tags=["foundation_synth", f"eo_task_{inp.task_number}"],
        seed=inp.seed,
        cefr_confidence=cefr_pred.confidence,
        cefr_distribution=dict(cefr_pred.distribution),
        calibration_anchors=dict(_ANCHOR_PLACEHOLDER),
    )

    item = Item(
        id=item_id,
        module="EO",
        cefr_level=_cefr_target_as_level(inp.cefr_target),
        content=content,
        metadata=metadata,
        provenance=provenance,
        synthetic=True,
    )

    trace = SynthesisTrace(
        model="none/foundation",
        prompt_hash=prompt_hash,
        response_hash=hashlib.sha256(joined.encode("utf-8")).hexdigest(),
        latency_ms=0.0,
        tokens_in=0,
        tokens_out=0,
        retries=0,
        seed=inp.seed,
    )
    return CandidateItem(item=item, trace=trace)


def _cefr_target_as_level(target: CefrTarget) -> CefrLevel:
    """EE/EO target ∈ {B2, C1} maps directly to the schema's CefrLevel."""
    return target


def _source_id(task_number: TaskNumber, seed: int) -> str:
    """Stable source id for the foundation pool."""
    return f"task{task_number}-seed{seed}"


def _prompt_hash(joined_prompts: str, task_number: TaskNumber, seed: int) -> str:
    """Stable hex digest used as `Provenance.llm_prompt_hash`."""
    payload = (
        f"{SYNTHESIZER_VERSION}|task={task_number}|seed={seed}|{joined_prompts}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "RUBRIC_VERSION",
    "SOURCE_LICENSE",
    "SOURCE_NAME",
    "SYNTHESIZER_VERSION",
    "CefrTarget",
    "EOSynthesisInput",
    "TaskNumber",
    "synthesize_eo_prompt",
]
