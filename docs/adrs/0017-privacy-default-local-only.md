# ADR-0017: Privacy default = `local_only`; no cloud anything until explicit opt-in

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Product, Privacy steward
- **Phase**: 2

## Context

Master prompt §6.4 names the project's stance:

> "No cloud telemetry of learner audio by default. The default privacy
> mode is `local_only`; cloud features are opt-in. Learner audio and
> writing artifacts never leave the operator's machine without explicit
> consent."

The Phase 1 `.env.example` already carries `PRIVACY_DEFAULT_MODE=
local_only`. Phase 2 makes the contract architectural: the `users`
table has a `privacy_mode` column, and every cloud-touching code path
must check it.

The forces:

- **Learner audio and writing are sensitive.** A learner practicing
  their writing for an immigration exam is producing data that, if
  leaked, has financial and immigration consequences.
- **Self-hosting is a primary use case** (master prompt §6.4; ADR-0009
  re-affirmed with `litellm` provider configurable). An operator
  running tcf-accel on their own laptop should be able to use the
  full system without any outbound network call beyond NTP and OS
  updates.
- **Cloud features are valuable when the operator wants them**:
  hosted LLM critics, telemetry to improve item bank quality,
  shared-anonymized-cohort calibration. These are *opt-in*, not
  opt-out.

## Decision

The privacy contract:

1. **`users.privacy_mode` defaults to `'local_only'`** for every new
   account, in every environment.
2. **`local_only` semantics** (enforced at the application boundary):
   - No outbound HTTP calls to LLM providers (Anthropic, OpenAI,
     Mistral, etc.). Local models (Ollama, llama.cpp, local Whisper)
     are allowed.
   - No outbound calls to telemetry endpoints (no analytics, no
     crash reporting beyond local logs).
   - Audio bytes and writing text never leave the operator's machine
     except via the explicit `GET /v1/data/export` flow (which the
     learner triggers).
   - The `setup-models` script downloads model weights at install
     time; this is the only "outbound" allowed and is documented in
     `README.md`.
3. **`cloud_optin` semantics**:
   - Cloud LLM critic (`litellm` per ADR-0009) is callable.
   - Cloud-scored EE/EO submissions are allowed; the artifact's
     `payload_uri` may point at a cloud-bucket URI.
   - Cohort telemetry (anonymized, see master prompt §6.4) is allowed
     if the operator has additionally enabled `TELEMETRY_OPT_IN=true`.
4. **Enforcement points**:
   - `apps/api`: a `PrivacyGuard` dependency injected into every route
     that could trigger a cloud call. The guard reads `users.
     privacy_mode` and raises `E_AUTH_005 ForbiddenError` if a
     `local_only` user invokes a cloud-only feature.
   - `apps/worker`: every cloud-touching task checks the user's
     privacy_mode before calling the LLM gateway.
   - `packages/ml`: every scorer reads `privacy_mode` from the task
     payload (not from the DB) so the contract is auditable in
     isolation tests.
5. **Test enforcement**:
   - A property-based test seeds a `local_only` user and asserts no
     route returns 200 if it would have made a cloud call.
   - A linter check (`scripts/check_no_unguarded_cloud_call.py`,
     added Phase 2) scans for unguarded `litellm.completion(...)`
     calls outside of `apps/worker/cloud/` (the only allowed seam).
6. **UI requirement** (Phase 8 honors): cloud opt-in is a deliberate
   step with a written explanation of what data leaves the machine
   and where it goes. Pre-checked checkboxes are forbidden.
7. **Operator override**: an operator running for themselves can set
   `DEFAULT_PRIVACY_MODE=cloud_optin` in their `.env` to flip the
   default for new sign-ups on that instance. This is the only way
   to change the default; it must be a deliberate operator action.

## Consequences

- **Positive**:
  - The default is the most-protective option. A user who does
    nothing pays no privacy cost.
  - Self-hostable end-to-end with no cloud dependencies (master prompt
    differentiator #4).
  - The enforcement is mechanical (PrivacyGuard + linter + test), not
    aspirational.
  - Trust: a learner can audit `git log` and `tests/` and see the
    contract is real.
- **Negative**:
  - Cloud features need a flow for opt-in, which is UX work for
    Phase 8.
  - The LLM critic (Phase 7) must have a *local* implementation path
    that does not degrade so badly that `local_only` becomes
    functionally unusable. Mitigated by: ADR-0007 (local Whisper as
    default ASR); ADR-0008 (local CamemBERT classifier as default
    CEFR scorer); Phase 7 will ship a local Llama-via-Ollama path
    for the rubric scorer alongside the litellm cloud option.
  - Operators who *want* cloud features see an extra opt-in step.
    Acceptable; the privacy default is more important than the
    operator's setup speed.
- **Neutral**:
  - This is consistent with the GDPR/PIPEDA posture; we are
    privacy-by-default not because regulation forces it, but
    because it's the right starting point.

## Alternatives considered

- **`cloud_optin` default with opt-out**: rejected on the master-prompt
  ground that learner audio is sensitive and the default should not
  send it anywhere. Opt-out defaults systematically under-protect
  users who don't read the settings page. *Would reconsider*: never;
  this is a value commitment.
- **`local_only` default with no `cloud_optin` mode at all**: rejected
  because it would force operators who want hosted-LLM features to
  fork the code. The opt-in path keeps the project useful in both
  modes.
- **Per-feature opt-in (rather than a single account-level toggle)**:
  considered but deferred. Phase 8 may add finer-grained controls
  (e.g., "opt in to cloud writing critic but not cloud speaking
  critic"); the Phase 2 contract is account-level for simplicity.
  *Would reconsider*: at Phase 8 UI work if learners express the
  need.

## What would change our mind

- A regulatory shift (e.g., a new Canadian education-privacy law)
  that requires explicit consent at finer granularity than
  account-level. We'd ship per-feature consent in a `/v2/` migration.
- A learner complaint that the `local_only` default is causing them
  to *think* the cloud LLM is being called when it isn't (i.e., a
  UX failure of the indicator). Fix the UX, not the default.

## References

- Master prompt §6.4.
- `02_ARCHITECTURE.md §2.8` ADR-017 entry.
- `phase2_design.md §6.4`.
- ADR-0009 (`litellm` gateway; cloud is gated by this ADR).
- ADR-0010 (MIT + CC-BY-SA; aligned self-hostability stance).
- `.env.example` `PRIVACY_DEFAULT_MODE=local_only`.
- Phase 7 will ship the local Llama-via-Ollama scorer path; tracked
  in `07_AUTO_SCORING_AND_FEEDBACK.md`.
