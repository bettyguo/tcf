"""EE (expression écrite) prompt synthesizer.

Foundation-grade: produces a Pydantic-valid `Item` with `EEContent`
from a typed task specification, with no LLM call. Prompts are selected
deterministically from a small curated pool keyed by
``(task_number, canadian_context, seed)``.

Why a curated pool instead of LLM-authored prompts?

- EE prompts are *stimuli*, not items the learner answers with an MCQ;
  there is no adversarial gate to validate. Quality is a function of
  prompt-task alignment, which is more reliably hand-checked.
- Canadian-context coverage (ADR-0022 + master prompt §1.4) is easier
  to guarantee with a hand-curated pool than with an LLM that may
  drift toward Hexagonal context.
- For testing and foundation auditing, deterministic prompts make the
  bank's distribution audit reproducible.

The Phase 3 follow-up will swap this pool for the LLM-driven
synthesizer (`phase3_design.md §3.3`) using Claude Sonnet 4.6; the
typed `EESynthesisInput` shape is the contract that does not change.

Items are tagged ``synthetic=True`` (ADR-0021): the entire stimulus is
authored — unlike CE, where the *passage* is real and only the question
is synthesized.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from tcf_accel.schemas import (
    EEContent,
    Item,
    ItemMetadata,
    Provenance,
)

from tcf_accel_content._ids import derive_item_id
from tcf_accel_content.cefr import CEFRClassifier, CefrLevel
from tcf_accel_content.types import CandidateItem, SynthesisTrace

SYNTHESIZER_VERSION: str = "ee-fake-v0"
RUBRIC_VERSION: str = "ee.v1"
SOURCE_NAME: str = "foundation_ee_pool"
SOURCE_LICENSE: str = "CC-BY-SA-4.0"

TaskNumber = Literal[1, 2, 3]
CefrTarget = Literal["B2", "C1"]

# FEI canonical word-count ranges (`03_CONTENT_PIPELINE.md §1.1`):
# Tâche 1 = 60w descriptive, Tâche 2 = 120w opinion, Tâche 3 = 180w
# argumentative. We carry ±10w tolerance per task as the operational
# target a scorer rewards.
_WORD_COUNT_RANGES: dict[TaskNumber, tuple[int, int]] = {
    1: (50, 70),
    2: (110, 130),
    3: (170, 190),
}

_PREP_TIME_S_BY_TASK: dict[TaskNumber, int] = {1: 0, 2: 60, 3: 60}

# Curated prompt pool. Each (task_number, canadian_context) bucket has
# multiple variants; the seed picks one. Canadian-flavoured variants
# integrate Canadian referents (immigration, bilinguisme, hivers,
# régions, etc.) as required by ADR-0022 for T2 / T3.
_PROMPT_POOL: dict[tuple[TaskNumber, bool], tuple[str, ...]] = {
    (1, False): (
        "Décrivez à un ami votre routine du matin avant le travail. "
        "Mentionnez vos horaires, votre transport et un détail personnel. "
        "Environ 60 mots.",
        "Rédigez un court message à un voisin pour expliquer comment "
        "vous arroserez ses plantes pendant son absence. "
        "Environ 60 mots.",
    ),
    (1, True): (
        "Envoyez un courriel à un nouveau collègue de votre équipe à "
        "Montréal pour lui souhaiter la bienvenue et lui donner un "
        "conseil pratique pour ses premiers jours. Environ 60 mots.",
    ),
    (2, False): (
        "Donnez votre avis sur l'utilité d'apprendre une langue "
        "étrangère à l'âge adulte. Appuyez votre opinion par deux "
        "raisons concrètes. Environ 120 mots.",
    ),
    (2, True): (
        "Donnez votre avis sur l'importance du bilinguisme français-"
        "anglais pour s'intégrer professionnellement au Canada. "
        "Illustrez par deux exemples. Environ 120 mots.",
        "Selon vous, quels avantages la diversité culturelle apporte-"
        "t-elle aux villes canadiennes comme Toronto ou Montréal ? "
        "Justifiez par deux arguments. Environ 120 mots.",
    ),
    (3, False): (
        "Le télétravail devrait-il devenir la norme dans les bureaux ? "
        "Présentez les avantages, les inconvénients, et défendez une "
        "position argumentée. Environ 180 mots.",
    ),
    (3, True): (
        "La politique d'immigration économique du Canada favorise-t-"
        "elle suffisamment l'intégration linguistique des nouveaux "
        "arrivants ? Présentez les enjeux, les positions en débat, et "
        "défendez votre opinion. Environ 180 mots.",
        "L'enseignement obligatoire du français en dehors du Québec "
        "devrait-il être renforcé ? Présentez les arguments pour et "
        "contre, et défendez une position. Environ 180 mots.",
    ),
}

# Placeholder calibration anchors. Phase 7 replaces these with real
# model responses calibrated against expert raters; the structure is
# already correct so the Phase 7 scorer can consume them.
_ANCHOR_PLACEHOLDER: dict[str, str] = {
    "nclc_7": (
        "[Foundation placeholder - Phase 7 replaces with "
        "calibrated NCLC 7 response.]"
    ),
    "nclc_9": (
        "[Foundation placeholder - Phase 7 replaces with "
        "calibrated NCLC 9 response.]"
    ),
    "nclc_11": (
        "[Foundation placeholder - Phase 7 replaces with "
        "calibrated NCLC 11 response.]"
    ),
}


@dataclass(frozen=True)
class EESynthesisInput:
    """Typed input to `synthesize_ee_prompt`.

    Matches the call shape `phase3_design.md §3.3` documents for the
    real synthesizer.
    """

    task_number: TaskNumber
    canadian_context: bool
    cefr_target: CefrTarget
    seed: int = 0
    ingested_at: datetime = datetime(2026, 5, 28, tzinfo=UTC)


def synthesize_ee_prompt(
    inp: EESynthesisInput,
    *,
    classifier: CEFRClassifier,
) -> CandidateItem:
    """Produce one candidate EE item (no LLM call).

    Args:
        inp: All task + context + seed parameters.
        classifier: Consulted for the `cefr_confidence` metric on the
            prompt text; the item's `cefr_level` is set from
            ``inp.cefr_target`` because short EE prompts classify
            unreliably and the *task* — not the prompt — is what is
            calibrated to a level.

    Returns:
        A `CandidateItem` with `EEContent`, full provenance, and
        placeholder calibration anchors in metadata. The quality gate
        (`run_gate`) treats EE as MCQ-less; only the license check is
        gating for the foundation.

    Complexity: O(|prompt|) for hashing + classifier cost.
    """
    if inp.task_number not in (1, 2, 3):
        raise ValueError(f"task_number must be 1, 2, or 3 (got {inp.task_number!r})")

    canadian_context = _resolve_canadian_context(inp)
    pool = _PROMPT_POOL[(inp.task_number, canadian_context)]
    seed_digest = hashlib.sha256(
        f"ee|task={inp.task_number}|ca={canadian_context}|seed={inp.seed}".encode(),
    ).digest()
    prompt_text = pool[seed_digest[0] % len(pool)]

    cefr_pred = classifier.classify(prompt_text)

    content = EEContent(
        task_number=inp.task_number,
        prompt=prompt_text,
        target_word_count_range=_WORD_COUNT_RANGES[inp.task_number],
        required_canadian_context=canadian_context,
        rubric_version=RUBRIC_VERSION,
    )

    source_id = _source_id(inp.task_number, canadian_context, inp.seed)
    prompt_hash = _prompt_hash(prompt_text, inp.task_number, canadian_context, inp.seed)

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
        tags=["foundation_synth", f"ee_task_{inp.task_number}"],
        seed=inp.seed,
        cefr_confidence=cefr_pred.confidence,
        cefr_distribution=dict(cefr_pred.distribution),
        canadian_context=canadian_context,
        calibration_anchors=dict(_ANCHOR_PLACEHOLDER),
    )

    item = Item(
        id=item_id,
        module="EE",
        cefr_level=_cefr_target_as_level(inp.cefr_target),
        content=content,
        metadata=metadata,
        provenance=provenance,
        synthetic=True,  # whole-stimulus authored; ADR-0021 informational
    )

    trace = SynthesisTrace(
        model="none/foundation",
        prompt_hash=prompt_hash,
        response_hash=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        latency_ms=0.0,
        tokens_in=0,
        tokens_out=0,
        retries=0,
        seed=inp.seed,
    )
    return CandidateItem(item=item, trace=trace)


def _resolve_canadian_context(inp: EESynthesisInput) -> bool:
    """ADR-0022: Tasks 2 & 3 MUST flag Canadian context.

    Task 1 honours the caller's preference. The function refuses to
    produce a non-Canadian Task 2 / 3, because the bank-distribution
    audit would reject the item; failing fast at synthesis is
    cheaper than discovering the violation downstream.
    """
    if inp.task_number in (2, 3) and not inp.canadian_context:
        raise ValueError(
            f"EE task {inp.task_number} requires canadian_context=True "
            "(ADR-0022, master prompt §1.4)",
        )
    return inp.canadian_context


def _cefr_target_as_level(target: CefrTarget) -> CefrLevel:
    """Translate the EE/EO target into a `CefrLevel`.

    EE/EO targets are restricted to B2/C1 because below B2 the FEI EE
    tasks are not coherent (task 3 expects argumentation, an A-level
    skill set cannot produce that).
    """
    return target


def _source_id(task_number: TaskNumber, canadian_context: bool, seed: int) -> str:
    """Stable source id for the foundation pool."""
    return f"task{task_number}-ca{int(canadian_context)}-seed{seed}"


def _prompt_hash(
    prompt: str, task_number: TaskNumber, canadian_context: bool, seed: int,
) -> str:
    """Stable hex digest used as `Provenance.llm_prompt_hash`."""
    payload = (
        f"{SYNTHESIZER_VERSION}|task={task_number}|ca={canadian_context}"
        f"|seed={seed}|{prompt}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "RUBRIC_VERSION",
    "SOURCE_LICENSE",
    "SOURCE_NAME",
    "SYNTHESIZER_VERSION",
    "CefrTarget",
    "EESynthesisInput",
    "TaskNumber",
    "synthesize_ee_prompt",
]
