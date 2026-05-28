# packages/content

Content pipeline. Phase 3 (`03_CONTENT_PIPELINE.md`) fills in:

- `sources/` — one module per source (common_voice, voxpopuli, librispeech, …).
- `synthesize/` — `ce.py`, `co.py`, `ee.py`, `eo.py` synthesizers.
- `quality/` — distractor adversarial check, length-balance, PII scan, license check.
- `cefr/` — fine-tuned CamemBERT classifier wrapper + CLI.
- `embedding/` — embedding + HDBSCAN clustering for topic-quota enforcement.

Phase 1 ships only the package skeleton.
