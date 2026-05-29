"""Content pipeline package.

Phase 3 foundation: subpackage skeletons + typed protocols. The heavy
implementation (Whisper transcription, MFA alignment, CamemBERT
fine-tune, LLM synthesizers, HDBSCAN clustering) lands in follow-up
PRs scoped per subpackage; see `phase3_design.md §14` for the
implementation order.

Subpackages:
- `sources`: per-source ingestion modules (Common Voice, Voxpopuli, …).
- `cefr`: text + acoustic CEFR classifier.
- `synthesize`: per-module item synthesizers (CO, CE, EE, EO).
- `quality`: the quality gate and its individual checks.
- `embedding`: embed + HDBSCAN cluster.

Refer to `03_CONTENT_PIPELINE.md` for the design and ADRs 0018-0022
for the locked decisions.
"""

from __future__ import annotations

__version__ = "0.3.0"
