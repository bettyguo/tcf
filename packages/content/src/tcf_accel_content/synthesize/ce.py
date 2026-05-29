"""CE (compréhension écrite) item synthesizer.

This module ships the **foundation-grade** CE synthesizer: it produces
a valid `Item` (CE-discriminated) from a passage with no LLM call —
the MCQ shape is derived deterministically from sha256(passage, seed)
and four register-appropriate generic options whose lengths are
balanced so the foundation gate passes.

This is *not* the production synthesizer. The Phase 3 follow-up
(`phase3_design.md §3.1`) plugs in `claude-sonnet-4-6` via litellm,
the FLELex vocabulary constraint, and the adversarial validator. The
foundation version exists so the end-to-end pipeline (source → CEFR →
synth → gate → loader) can be exercised, audited, and tested *now*
without external dependencies — and so the loader's idempotency
contract (deterministic `Item.id` per `phase3_design.md §1.2`) is
already in force when the real synthesizer lands.

Why a hardcoded MCQ pool instead of literally random text?

- The four options are length-balanced so the foundation
  length-balance check passes, exercising the gate composer end-to-end.
- The options are register-coherent French (not gibberish), so a human
  reviewer eyeballing the bank sees plausible-shaped distractors.
- The "correct" option is hash-derived, so different passages produce
  different correct keys and the gate cannot trivially solve them.

The synthesizer marks every output with `Provenance.synthesizer_version
= "ce-fake-v0"` and `Item.metadata.tags = ["foundation_synth"]` so the
audit can identify and retire foundation-synth items once the real
synthesizer lands.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from tcf_accel.schemas import (
    MCQ,
    CEContent,
    Item,
    ItemMetadata,
    MCQOption,
    Provenance,
)

from tcf_accel_content._ids import derive_item_id
from tcf_accel_content.cefr import CEFRClassifier
from tcf_accel_content.types import CandidateItem, SynthesisTrace

SYNTHESIZER_VERSION: str = "ce-fake-v0"

Genre = Literal["news", "ad", "letter", "admin", "academic", "narrative"]

# Four length-balanced, register-coherent generic distractors. The
# correct answer is selected by hash; the order is shuffled by hash so
# the "correct option is always at index 0" tell does not exist.
_OPTION_POOL: tuple[tuple[str, str], ...] = (
    ("a", "le matin tres tot avant le travail"),
    ("b", "le soir tard apres une longue journee"),
    ("c", "le week-end ensemble avec sa famille proche"),
    ("d", "pendant la pause de midi au bureau"),
)


@dataclass(frozen=True)
class CESynthesisInput:
    """Typed input to `synthesize_ce_item`.

    Matches the shape `phase3_design.md §3.1` documents for the real
    synthesizer, so the call site does not have to change when the
    foundation impl is swapped out.
    """

    passage: str
    genre: Genre
    source: str
    source_id: str
    license: str
    ingested_at: datetime
    seed: int = 0


def synthesize_ce_item(
    inp: CESynthesisInput,
    *,
    classifier: CEFRClassifier,
) -> CandidateItem:
    """Produce one candidate CE item from a passage (no LLM call).

    The CEFR level is determined by classifying the passage; the MCQ is
    derived deterministically from the passage hash and the seed.

    Args:
        inp: All passage + provenance + seed parameters.
        classifier: A `CEFRClassifier`-conforming instance. Pass a
            `FakeCEFRClassifier()` for tests; the production caller
            passes `load_classifier()`.

    Returns:
        A `CandidateItem` whose `item` is Pydantic-valid and whose
        `trace` carries the synth-call metadata. The quality gate
        (`tcf_accel_content.quality.gate.run_gate`) must still be run
        before the item enters the bank.

    Complexity: O(|passage|) for hashing + the classifier's cost.
    """
    word_count = _word_count_clamped(inp.passage)
    passage_digest = hashlib.sha256(inp.passage.encode("utf-8")).digest()

    cefr = classifier.classify(inp.passage)

    options = _build_options(passage_digest, inp.seed)
    correct_id = options[passage_digest[1] % len(options)].id
    question = MCQ(
        id="q1",
        prompt="Selon le texte, quand l'action principale se déroule-t-elle ?",
        options=options,
        correct_option_id=correct_id,
        explanation=None,
    )

    content = CEContent(
        passage=inp.passage,
        genre=inp.genre,
        word_count=word_count,
        questions=[question],
    )

    prompt_hash = _prompt_hash(passage=inp.passage, genre=inp.genre, seed=inp.seed)

    item_id = derive_item_id(
        source=inp.source,
        source_id=inp.source_id,
        synthesizer_version=SYNTHESIZER_VERSION,
        prompt_hash=prompt_hash,
        seed=inp.seed,
    )

    provenance = Provenance(
        source=inp.source,
        source_id=inp.source_id,
        license=inp.license,
        ingested_at=inp.ingested_at,
        fetcher_version=None,
        synthesizer_version=SYNTHESIZER_VERSION,
        llm_model="none/foundation",
        llm_prompt_hash=prompt_hash,
        review_status="auto_passed",
    )

    metadata = ItemMetadata(
        tags=["foundation_synth"],
        seed=inp.seed,
        cefr_confidence=cefr.confidence,
        cefr_distribution=dict(cefr.distribution),
    )

    item = Item(
        id=item_id,
        module="CE",
        cefr_level=cefr.level,
        content=content,
        metadata=metadata,
        provenance=provenance,
    )

    trace = SynthesisTrace(
        model="none/foundation",
        prompt_hash=prompt_hash,
        response_hash=hashlib.sha256(
            question.model_dump_json().encode("utf-8"),
        ).hexdigest(),
        latency_ms=0.0,
        tokens_in=0,
        tokens_out=0,
        retries=0,
        seed=inp.seed,
    )
    return CandidateItem(item=item, trace=trace, passage_provenance=provenance)


def _word_count_clamped(passage: str) -> int:
    """Whitespace word count clamped to CEContent's [20, 2000] range.

    Foundation-grade approximation; the real synthesizer uses the
    CamemBERT tokenizer.
    """
    raw = len(passage.split())
    return max(20, min(raw, 2000))


def _build_options(passage_digest: bytes, seed: int) -> list[MCQOption]:
    """Permute `_OPTION_POOL` by (digest, seed) and return as MCQOptions.

    Order is deterministic per (passage, seed); different passages or
    seeds permute the pool differently, so the gate cannot rely on
    positional priors.
    """
    perm = sorted(
        range(len(_OPTION_POOL)),
        key=lambda i: hashlib.sha256(
            passage_digest + i.to_bytes(2, "big") + seed.to_bytes(8, "big"),
        ).digest(),
    )
    out: list[MCQOption] = []
    for new_id, original_idx in enumerate(perm):
        _, text = _OPTION_POOL[original_idx]
        out.append(MCQOption(id=chr(ord("a") + new_id), text=text))
    return out


def _prompt_hash(*, passage: str, genre: str, seed: int) -> str:
    """Stable hex digest of the "synthesis prompt"; identifies the call."""
    payload = f"{SYNTHESIZER_VERSION}|{genre}|seed={seed}|{passage}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "SYNTHESIZER_VERSION",
    "CESynthesisInput",
    "Genre",
    "synthesize_ce_item",
]
