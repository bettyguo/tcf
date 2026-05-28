# ADR-0009: `litellm` as the LLM gateway, Claude Sonnet 4.6 (`claude-sonnet-4-6`) as default

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, ML lead
- **Phase**: 1

## Context

The system makes LLM calls in three places: synthetic-item authoring (Phase 3), EE auto-scoring critic (Phase 7), and EO follow-up generation (Phase 5). Each calling site needs: provider portability (operator may choose Claude / GPT / Mistral / local), prompt caching, structured-output enforcement, retries, and observability.

Master prompt §8 specifies `litellm` as the gateway and Claude Sonnet 4.6 (`claude-sonnet-4-6`) as the default model.

## Decision

`litellm` as the single LLM client wrapper. Configurable model id via `LLM_MODEL` env var. Default: `claude-sonnet-4-6`. Supported alternatives at v1: `gpt-4o-2024-08`, `mistral-large-latest`, local Mistral via Ollama.

LLM calls are mediated by `packages/ml/src/tcf_accel_ml/llm/client.py`, which:
- Enforces structured-output (Pydantic schema validation on the response; retries with a stronger prompt if invalid).
- Records the prompt hash and the model id in `Provenance.llm_model` / `Provenance.llm_prompt_hash` (Phase 1 schema) so every synthetic item is auditable.
- Caches deterministic prompts (the EE scoring rubric prompt is identical across submissions; the per-essay text is the variable). Phase 7 ADR-040 elaborates the cache key strategy.
- Tests use seeded fixtures + recorded responses (VCR-style) per master prompt §6.5 — no live LLM in CI.

## Consequences

- **Positive**:
  - Single integration point for OpenAI-compatible providers.
  - Operator chooses their preferred model; no hard dependency on a paid vendor at install time.
  - Prompt-caching reduces cost on stable rubric prompts (Phase 7 design relies on this).
- **Negative**:
  - `litellm`'s abstraction can lag behind individual provider features (e.g., Anthropic prompt-caching parameter coverage). Mitigated by directly calling the provider SDK for any feature `litellm` doesn't yet expose, hidden behind the same wrapper.
- **Neutral**:
  - We choose Claude Sonnet 4.6 as default on (a) instruction-following on structured outputs, (b) French-language quality, (c) cost vs Claude Opus, (d) familiarity with prompt caching for our use case. Updates to a newer model (Claude Opus 4.7 / Claude Sonnet 4.7 when released) are a config-only change.

## Alternatives considered

- **Direct Anthropic SDK only**: rejected because lock-in to one vendor contradicts the open-source / self-hostable mandate.
- **`langchain` LLM wrappers**: rejected on abstraction cost; we want a thin gateway, not a framework.
- **Per-call provider SDKs (no gateway)**: rejected — boilerplate × 3 providers × N call sites = unmaintainable.

## What would change our mind

- `litellm` becomes unmaintained or pivots in a way that breaks our patterns.
- A specific provider feature (e.g., a much-better French-aware structured-output API) materially improves item-quality and `litellm` cannot expose it for > 1 quarter.

## References

- [litellm docs](https://docs.litellm.ai/)
- Master prompt §8, §6.5.
- Phase 7 ADR-040.
