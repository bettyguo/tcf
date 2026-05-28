# ADR-0007: `bofenghuang/whisper-large-v3-french` as the primary ASR

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, ML lead
- **Phase**: 1

## Context

ASR is foundational to: shadowing drills (Phase 5), dictation drills (Phase 5), EO recording → transcript for the auto-scorer (Phase 7), and pronunciation feedback via forced alignment (Phase 5 + Phase 7).

Quality target: WER ≤ 9% on Common Voice fr test set (master prompt §8 implicit, Phase 5 audit). Robustness across Hexagonal, Canadian, Belgian, Swiss, and West African French accents (master prompt §1.4, §6.4 — bias avoidance).

Master prompt §8 specifies `bofenghuang/whisper-large-v3-french` as primary, `faster-whisper` for inference, OpenAI Whisper API as an opt-in cloud fallback.

## Decision

`bofenghuang/whisper-large-v3-french` (Hugging Face) as the canonical local model. Inference via `faster-whisper` (CTranslate2 backend) for ~3–4× speedup over the reference HF runtime. Cloud fallback (`openai-whisper-1` or `gpt-4o-mini-transcribe`) is opt-in only, gated by `privacy_mode == 'cloud_optin'` (master prompt §6.4 — privacy default is local-only).

Confidence threshold: ASR output below confidence `0.65` triggers `ASRConfidenceTooLowError` per Phase 2 error taxonomy; the learner is asked to re-record. (Avoids feeding garbage transcripts to the auto-scorer.)

## Consequences

- **Positive**:
  - Best published French-specific WER among open-weight Whisper variants as of 2025.
  - MIT-compatible license; no redistribution constraints.
  - Local inference satisfies the privacy default (no learner audio leaves the device unless explicitly opted in).
- **Negative**:
  - ~3 GB weights; first-run download is bandwidth-heavy. Mitigated by `make setup-models` (one-time pull).
  - Latency on CPU-only is ~1× realtime; acceptable for offline scoring, painful for real-time shadowing feedback. Phase 5 ADR will address GPU acceleration.
- **Neutral**:
  - We abstract the ASR call behind `packages/ml/src/tcf_accel_ml/asr/asr_backend.py` so a future model swap (or cloud fallback) is a config change.

## Alternatives considered

- **`openai/whisper-large-v3`** (generic multilingual): rejected because the French-specific fine-tune materially improves Canadian and African accent WER (per `bofenghuang`'s published evals). *Would reconsider*: if a future generic Whisper release closes that gap.
- **Cloud-only (OpenAI Whisper API, AssemblyAI, Deepgram)**: rejected because it violates the privacy default and adds a recurring cost on the operator. *Would reconsider*: never as a default; cloud remains opt-in.
- **`Wav2Vec2-XLS-R` fine-tuned for French**: viable but inference is slower and the ecosystem (alignment tools, batching) is weaker. *Would reconsider*: if Whisper licensing changes.
- **Locally-trained model**: rejected on cost; we have no training corpus at v1.

## What would change our mind

- Hugging Face removes the model or relicenses to non-permissive terms.
- A 2026+ release closes the French WER gap with materially smaller compute.
- Empirical Phase 5 audit shows accent WER imbalance (e.g., Canadian WER > 1.5× Hexagonal WER) that cannot be mitigated by accent-augmented evaluation.

## References

- [bofenghuang/whisper-large-v3-french on HF](https://huggingface.co/bofenghuang/whisper-large-v3-french)
- Master prompt §8, §6.4.
- Phase 5 §2.6 (pronunciation pipeline).
