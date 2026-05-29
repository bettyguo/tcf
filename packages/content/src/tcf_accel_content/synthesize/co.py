"""CO (compréhension orale) item synthesizer.

Foundation-grade: produces a Pydantic-valid `Item` with `COContent`
from a typed input that carries **a pre-computed transcript** plus
acoustic metadata, with no LLM call and no Whisper invocation. The
MCQ is derived deterministically from sha256(transcript, seed) using
the same length-balanced-pool pattern as CE.

Why "pre-computed transcript" in the foundation impl?

- Master prompt §6.3 invariant: the *authoritative transcript* of CO
  audio is **never** LLM-authored. The Phase 3 follow-up wires
  ``bofenghuang/whisper-large-v3-french`` (ADR-0007) to *derive* the
  transcript from cached audio bytes; once derived, the rest of the
  pipeline is the same as CE.
- The foundation impl accepts the transcript directly so the rest of
  the pipeline (CEFR classify on transcript, synthesize MCQ from
  transcript, attach acoustic metadata, write to bank) can be
  exercised end-to-end without Whisper or Montreal Forced Aligner.
- Operator-side ingest scripts (Common Voice, MLS, Voxpopuli all ship
  ground-truth transcripts) already produce a transcript per
  `phase3_design.md §3.2`; this synth signature matches that path.

The acoustic-CEFR adjustment (`phase3_design.md §4.4`) is *not* applied
in the foundation impl — the Phase 3 follow-up adds the ridge model
that adjusts text-CEFR by 0 or +1 band based on speech rate, lexical
density, etc. The foundation impl records the acoustic features in
`metadata.co_acoustic` so the audit can see them, but the item's
`cefr_level` is just the text-CEFR prediction.

Items are tagged ``synthetic=False`` because the *transcript and
audio* are real (operator-cached or open-license corpus); only the
question is synthesized, matching the CE convention (ADR-0021).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from tcf_accel.schemas import (
    MCQ,
    COContent,
    Item,
    ItemMetadata,
    MCQOption,
    Provenance,
    Speaker,
)

from tcf_accel_content._ids import derive_item_id
from tcf_accel_content.cefr import CEFRClassifier
from tcf_accel_content.types import CandidateItem, SynthesisTrace

SYNTHESIZER_VERSION: str = "co-fake-v0"

Accent = Literal["fr-FR", "fr-CA", "fr-BE", "fr-CH", "fr-AF", "mixed"]
Register = Literal["soutenu", "standard", "familier"]

# CO-specific four-option pool. Distinct from the CE pool to avoid
# false-positive duplicates when both banks are loaded into one writer
# (cosine similarity on near-identical option strings would otherwise
# trigger `POTENTIAL_DUPLICATE`). All four are 8-token French phrases
# so the length-balance check passes.
_OPTION_POOL: tuple[tuple[str, str], ...] = (
    ("a", "ils prennent le train tres tot ce matin la"),
    ("b", "ils partent en voiture vers le sud demain soir"),
    ("c", "ils marchent ensemble dans le parc cet apres-midi tranquille"),
    ("d", "ils restent chez eux et regardent la television longtemps"),
)


@dataclass(frozen=True)
class COSynthesisInput:
    """Typed input to `synthesize_co_item`.

    Matches the shape `phase3_design.md §3.2` documents for the
    LLM-driven follow-up synthesizer, modulo `transcript` being given
    rather than derived from audio. Real Phase 3 will add an
    `audio_path: Path | None` alternative input that triggers Whisper
    transcription internally; this foundation impl is "transcript-
    provided" only.
    """

    transcript: str
    audio_local_path: str
    duration_s: float
    accent: Accent
    register: Register
    source: str
    source_id: str
    license: str
    ingested_at: datetime
    speakers: tuple[Speaker, ...] = field(
        default_factory=lambda: (Speaker(label="Speaker 1", accent="fr-FR"),),
    )
    speech_rate_wpm: float | None = None
    lexical_density: float | None = None
    n_speakers_diarized: int | None = None
    noisiness_proxy: float | None = None
    seed: int = 0


def synthesize_co_item(
    inp: COSynthesisInput,
    *,
    classifier: CEFRClassifier,
) -> CandidateItem:
    """Produce one candidate CO item from a transcript + audio metadata.

    Args:
        inp: All transcript / acoustic / provenance / seed parameters.
        classifier: A `CEFRClassifier` invoked on the *transcript*
            (not the audio); the foundation impl does not apply the
            acoustic adjustment from `phase3_design.md §4.4`.

    Returns:
        A `CandidateItem` whose `item` is Pydantic-valid `COContent`
        with full provenance. The acoustic features (speech rate,
        lexical density, speakers, noisiness) are persisted into
        `metadata.co_acoustic` when provided.

    Raises:
        ValueError: if `duration_s` is outside the schema's [1, 600]
            range — surfaced explicitly so the operator sees the
            wrong-shape audio before the Pydantic error fires.

    Complexity: O(|transcript|) for hashing + classifier cost.
    """
    if not 1.0 <= inp.duration_s <= 600.0:
        raise ValueError(
            f"duration_s={inp.duration_s} outside CO schema range [1, 600]",
        )
    if not inp.transcript.strip():
        raise ValueError("CO transcript must be non-empty (master prompt §6.3)")

    transcript_digest = hashlib.sha256(inp.transcript.encode("utf-8")).digest()
    cefr = classifier.classify(inp.transcript)

    options = _build_options(transcript_digest, inp.seed)
    correct_id = options[transcript_digest[1] % len(options)].id
    question = MCQ(
        id="q1",
        prompt="D'après l'enregistrement, que font les personnes mentionnées ?",
        options=options,
        correct_option_id=correct_id,
        explanation=None,
    )

    content = COContent(
        transcript=inp.transcript,
        audio_local_path=inp.audio_local_path,
        duration_s=inp.duration_s,
        speakers=list(inp.speakers),
        accent=inp.accent,
        register=inp.register,
        questions=[question],
    )

    prompt_hash = _prompt_hash(
        transcript=inp.transcript, accent=inp.accent,
        register=inp.register, seed=inp.seed,
    )
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
        synthesizer_version=SYNTHESIZER_VERSION,
        llm_model="none/foundation",
        llm_prompt_hash=prompt_hash,
        review_status="auto_passed",
    )

    metadata = ItemMetadata(
        tags=["foundation_synth", f"accent_{inp.accent}", f"register_{inp.register}"],
        seed=inp.seed,
        cefr_confidence=cefr.confidence,
        cefr_distribution=dict(cefr.distribution),
        co_acoustic=_build_acoustic(inp),
    )

    item = Item(
        id=item_id,
        module="CO",
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


def _build_options(transcript_digest: bytes, seed: int) -> list[MCQOption]:
    """Permute `_OPTION_POOL` by (digest, seed); ids 'a'..'d' in shuffled order."""
    perm = sorted(
        range(len(_OPTION_POOL)),
        key=lambda i: hashlib.sha256(
            transcript_digest + i.to_bytes(2, "big") + seed.to_bytes(8, "big"),
        ).digest(),
    )
    out: list[MCQOption] = []
    for new_id, original_idx in enumerate(perm):
        _, text = _OPTION_POOL[original_idx]
        out.append(MCQOption(id=chr(ord("a") + new_id), text=text))
    return out


def _prompt_hash(
    *, transcript: str, accent: str, register: str, seed: int,
) -> str:
    """Stable hex digest used as `Provenance.llm_prompt_hash`."""
    payload = f"{SYNTHESIZER_VERSION}|{accent}|{register}|seed={seed}|{transcript}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_acoustic(inp: COSynthesisInput) -> dict[str, float] | None:
    """Return the acoustic-features dict for `metadata.co_acoustic`, or None.

    All four features must be provided together; partial population is
    silently dropped to avoid recording half-truths the audit would
    misread.
    """
    parts = (
        inp.speech_rate_wpm, inp.lexical_density,
        inp.n_speakers_diarized, inp.noisiness_proxy,
    )
    if any(p is None for p in parts):
        return None
    assert inp.speech_rate_wpm is not None
    assert inp.lexical_density is not None
    assert inp.n_speakers_diarized is not None
    assert inp.noisiness_proxy is not None
    return {
        "speech_rate_wpm": float(inp.speech_rate_wpm),
        "lexical_density": float(inp.lexical_density),
        "n_speakers_diarized": float(inp.n_speakers_diarized),
        "noisiness_proxy": float(inp.noisiness_proxy),
    }


__all__ = [
    "SYNTHESIZER_VERSION",
    "Accent",
    "COSynthesisInput",
    "Register",
    "synthesize_co_item",
]
