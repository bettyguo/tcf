# packages/ml

ML services. Phase 3+ fills in:

- `cefr/` — fine-tuned CamemBERT CEFR classifier (ADR-0008).
- `asr/` — Whisper-large-v3-french wrapper (ADR-0007) + faster-whisper inference.
- `alignment/` — Montreal Forced Aligner glue (Phase 5 §2.6).
- `prosody/` — pitch / stress / pause analysis (Phase 5).
- `scoring/ee/` — EE rubric scorer (Phase 7).
- `scoring/eo/` — EO rubric scorer (Phase 7).
- `llm/` — litellm-backed gateway (ADR-0009) with structured-output enforcement and prompt caching.

Phase 1 ships only the package skeleton.
