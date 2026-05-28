"""Pull ML models referenced by the system.

Phase 1: stub. Prints the planned downloads and exits 0.
Phase 3+: actually pulls the CEFR classifier weights, Whisper-fr, the MPNet
embedding model, and the MFA French acoustic model.

Usage:
    uv run python scripts/download_models.py
    uv run python scripts/download_models.py --check   # report what's already downloaded
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

PHASE: int = 1


@dataclass(frozen=True)
class Model:
    name: str
    hf_id: str | None
    size_mb: int
    license: str
    introduced_in_phase: int
    rationale: str


MODELS: tuple[Model, ...] = (
    Model(
        name="CEFR classifier (CamemBERT-derived)",
        hf_id="JonathanStefanov/CEFR_Classifier_French",
        size_mb=445,
        license="MIT",
        introduced_in_phase=3,
        rationale="ADR-0008: primary CEFR classifier for text + audio-transcript items.",
    ),
    Model(
        name="Whisper-large-v3-french",
        hf_id="bofenghuang/whisper-large-v3-french",
        size_mb=3094,
        license="MIT",
        introduced_in_phase=3,
        rationale="ADR-0007: primary ASR for shadowing/dictation/EO transcription.",
    ),
    Model(
        name="Multilingual MPNet embeddings",
        hf_id="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        size_mb=1110,
        license="Apache-2.0",
        introduced_in_phase=3,
        rationale="LECTOR semantic-confusable detection + item-cluster topic quotas.",
    ),
    Model(
        name="Montreal Forced Aligner — French",
        hf_id=None,
        size_mb=180,
        license="MIT",
        introduced_in_phase=5,
        rationale="Phoneme-level alignment for pronunciation feedback (Phase 5 §2.6).",
    ),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Just print what would be pulled.")
    args = parser.parse_args(argv)

    print(f"download_models.py — Phase {PHASE} stub. Planned models:\n")
    total_mb = 0
    for m in MODELS:
        active = "✓" if m.introduced_in_phase <= PHASE else "·"
        ident = m.hf_id or "(non-HF source)"
        print(f"  [{active}] {m.name}  —  {m.size_mb:>5} MB  —  {m.license}  —  Phase {m.introduced_in_phase}")
        print(f"        id: {ident}")
        print(f"        why: {m.rationale}")
        total_mb += m.size_mb
    print(f"\nTotal: {total_mb} MB ({total_mb / 1024:.1f} GB)")

    if args.check:
        return 0

    if PHASE < 3:
        print("\nNo actual downloads in Phase 1. Re-run after Phase 3 ships.")
        return 0

    # Phase 3+ implements the actual pull.
    raise NotImplementedError("Phase 3+ implements the download pipeline.")


if __name__ == "__main__":
    sys.exit(main())
