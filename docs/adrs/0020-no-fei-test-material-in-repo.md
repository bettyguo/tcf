# ADR-0020: No FEI test material in the repo; sample-link proxy only

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Legal-aware reviewer
- **Phase**: 3

## Context

France Éducation International (FEI) publishes TCF Canada sample items
on its public site (master prompt §1.1 source-of-truth URL). These
samples are valuable as *reference* — they show learners the exact
format, register, and difficulty calibration of real exam items.

They are also **copyrighted by FEI**. Distributing them in a public
repository — even cached for offline use — is a redistribution event
that exceeds fair-dealing arguments for personal study. Master prompt
§6.3 names "official FEI sample items (use only as samples, never as
the question bank)" as the policy; master prompt §11 commits us to
refuse redistribution of FEI test material.

R-006 (copyright complaint from a content source) is L/H and would
be a project-ending event for an open-source repo: a takedown notice
plus a public-reputation hit destroys the trust narrative (master
prompt §9 differentiator 5).

The temptation to relax this rule for convenience ("just one short
clip, for the test suite") is real and recurrent. We pre-empt it
with policy + technical enforcement.

## Decision

**No FEI test material — text, audio, images, or transcripts — enters
the repository under any circumstance.** Three layers of enforcement:

1. **Policy** (this ADR + master prompt §11 + `CONTRIBUTING.md`).
2. **Pipeline boundary**: the source-allowlist test
   (`tests/content/test_no_fei_in_sources.py`,
   `phase3_design.md §12.6`) greps the repo for FEI-domain URLs
   (`france-education-international.fr`, `tcfcanada.gouv.fr`) outside
   `docs/` and `README.md` link contexts; CI fails if any are found
   in source files, fixtures, or test data. The grep also rejects
   common FEI item identifiers if a future leak adopts a different
   URL form.
3. **Sample-link proxy at runtime**: the UI (Phase 8) ships a "FEI
   samples" page that fetches the public FEI sample URLs at *learner
   request time* and renders them in a sandboxed iframe with a clear
   "Source: France Éducation International" attribution and a link
   to the origin. We never cache the fetched content; the proxy is
   a passthrough with appropriate Cache-Control headers.

Learners can practice on FEI samples; they just consume them from FEI
directly, with our UI acting as a thin shim.

## Consequences

- **Positive**:
  - R-006 likelihood drops to L-near-zero for FEI specifically;
    residual risk is operator-side caching of FEI URLs in their
    browser (out of scope).
  - The trust narrative ("ethical content sourcing") survives audit
    scrutiny.
  - The bank's own items are the *only* practice material — there
    is no "FEI vs ours" comparison that could be read as us
    benchmarking against the real exam, which is itself a
    line we should not cross.
- **Negative**:
  - Learners who lose internet access in the middle of a study
    session cannot practice on FEI samples — they fall back to the
    bank. We accept this; the system's value proposition is its own
    bank, not the FEI samples.
  - The UI's FEI sample page must gracefully handle FEI URL changes
    (the FEI site has restructured before; master prompt §1 names
    re-verification at every release). We monitor with a periodic
    URL-liveness check (Phase 9 §2).
- **Neutral**:
  - The decision aligns with the "thin proxy" pattern used elsewhere
    for non-redistributable resources.

## Alternatives considered

- **Bundle a small subset of FEI samples for offline practice**:
  rejected. Even one sample is a redistribution event under FEI's
  copyright. *Would reconsider*: only if FEI publishes a release
  under an explicit re-distribution license. (No evidence this is
  forthcoming.)
- **Cache fetched FEI content server-side** to reduce learner-side
  load times: rejected — server-side caching is a redistribution
  point (the operator's server now hosts FEI content). Origin pull
  + browser caching only.
- **Link to FEI in `docs/` only, no in-product proxy**: weaker UX;
  learners would have to leave the app to access samples. The proxy
  is a passthrough, not a cache, so the legal posture is the same as
  a plain link with the UX of an in-product page.

## What would change our mind

- **FEI publishes its samples under a Creative Commons or other
  permissive license.** We'd bundle and audit just like any other
  CC-licensed source.
- **A contributor or user proposes a fair-dealing argument** for
  caching that a competent IP lawyer reviews and supports. Default
  answer remains no; the ADR + master prompt §11 is the precedent.
  We document the consultation if it happens.
- **The FEI site materially restructures** such that the public
  sample URLs change. We update the sample-link proxy's URL list
  in a follow-up PR; the ADR does not change.

## References

- Master prompt §1.1, §6.3, §11
- `03_CONTENT_PIPELINE.md §1.2` (provenance hierarchy tier 4)
- `phase3_think.md §1.3, §2.3`
- `phase3_design.md §2.3, §12.6, §15`
- R-006 (copyright complaint risk)
- ADR-0010 (MIT code / CC-BY-SA content)
