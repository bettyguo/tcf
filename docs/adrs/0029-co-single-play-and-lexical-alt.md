# ADR-0029: CO single-play default; lexical alternative emits `module=CE`

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect
- **Phase**: 5 (Practice & Drill Engines)

## Context

The TCF Canada CO module plays each audio clip **once**. A common
preparation failure is letting learners re-listen during practice,
which builds confidence but not exam-aligned skill (`phase5_think.md
§1.1`).

But the single-play contract creates an accessibility tension. WCAG
2.2 SC 1.2.1 requires an equivalent text alternative for auditory
information. A transcript shown *during* the question defeats the
drill (the learner reads instead of listens). A transcript shown only
*after* leaves Deaf / hard-of-hearing learners unable to attempt the
drill at all. The naive "always show the transcript, always allow
replay" re-creates the failure mode the single-play rule exists to
prevent.

The think doc considered three options:

- (a) Hard single-play, no transcript ever, replay locked behind
  submission. Maximally exam-aligned but violates WCAG.
- (b) Soft single-play with transcript always shown. Maximally
  accessible but degrades to a CE drill in disguise.
- (c) Single-play default + accessibility profile that swaps to a
  *lexical* drill which emits a different `Interaction.module` and
  is excluded from the CO posterior update.

## Decision

**(c) Single-play default + accessibility lexical alternative.**

Two structural rules enforce this:

1. **Default CO drills are single-play.** `DrillSpec.single_play =
   True` for `co_mcq`, `co_dictation`, `co_gapfill`. The `<audio>`
   element renders with `controls={false}`, `preload="none"`, and a
   custom React control that does not bind arrow-key seek. The replay
   affordance appears only after `POST /v1/session/{id}/answer`
   returns 200.

2. **Accessibility profile drives a session-time swap.** When the
   learner's `AccessibilityProfile.co_alternative == "lexical_alt"`,
   `POST /v1/session/start` swaps any CO `drill_kind` to
   `co_lexical_alt` before the registry lookup. The
   `COLexicalAltDrill` presents the CO item's transcript *as text*,
   grades the same MCQ as a lexical-comprehension probe, and emits
   `Interaction.module = "CE"` (not CO).

   This means the CO posterior is **never** updated from a learner
   who has the accessibility alternative enabled. The CO estimate
   remains a CO measurement — not a confused mix of "heard once" and
   "read transcript" interactions.

3. **Mandatory UI banner**. The text-alt drill carries
   `payload["accessibility_banner_key"] = "co_lexical_alt"`; the UI
   renders localized copy that says, plainly:

   > This drill does not measure CO and does not contribute to your
   > CO NCLC estimate. See [accommodations] for the official process.

4. **Symmetric EO accessibility**: `eo_text_alt` mirrors this
   exactly — EO text-input alternative declares `module = "EE"`,
   never EO, so the EO posterior stays calibrated against real
   recordings only.

5. **DB-level invariant**: migration
   `0004_phase5_interactions_alter.py` adds a CHECK constraint
   `drill_kind IS DISTINCT FROM 'co_lexical_alt' OR module = 'CE'`
   so a future code path that tries to write the wrong `module`
   fails at the storage layer.

## Consequences

- **Positive**:
  - The CO posterior remains a *measurement* of CO ability, not a
    register-confused average. Refusing to over-predict (the master
    prompt §6.2 commitment) is preserved.
  - Deaf / hard-of-hearing learners are routed to an honestly-labeled
    alternative drill — they're not left out, and the labeling makes
    the limitation explicit.
  - The DB CHECK + the route-side swap + the drill's `DrillSpec.module`
    make this a four-layer structural guarantee, not a single-layer
    policy.
- **Negative**:
  - A Deaf/HoH learner's `Readiness` light is capped at yellow (the
    confidence gate requires all-confident posteriors, and CO without
    real-audio data never reaches confident). The mitigation — an
    operator-level "this learner's CO target is moot for their
    immigration profile" toggle — is Phase 8 work.
- **Neutral**:
  - The lexical alternative is grouped under "Reading & Vocabulary"
    in the UI, not under "Listening". Phase 8 UI categorization
    follows.

## Alternatives considered

- See Context (a) and (b). Both rejected.
- **Lexical alternative still emits `module=CO`** but tagged with a
  flag the posterior update ignores. Rejected because the flag is
  forgettable; the route-side swap is structural.

## What would change our mind

- A WCAG 2.2 audit finds the single-play default fails SC 1.4.2
  (Audio Control) in a way the lexical-alternative route does not
  fix. We'd revisit the per-element implementation; the structural
  invariant stays.
- Deaf/HoH usage data shows the lexical alternative is treated as a
  CO substitute despite the banner ("I'm using your CO drills and
  they work"). We'd escalate the banner to a modal, push harder on
  routing it out of the CO module entirely.

## References

- `phase5_think.md §1.1`, `phase5_design.md §7`.
- `packages/sla/src/tcf_accel_sla/drills/co_mcq.py` (single_play=True).
- `packages/sla/src/tcf_accel_sla/drills/co_lexical_alt.py` (module="CE").
- `packages/sla/src/tcf_accel_sla/drills/eo_text_alt.py` (module="EE").
- `apps/api/src/tcf_accel_api/routes/session.py::start` (the swap).
- `infra/migrations/versions/0004_phase5_interactions_alter.py` (the CHECK).
- `phase5_audit.md §5`, §7, §10.
