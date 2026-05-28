# ADR-0010: MIT for code, CC BY-SA 4.0 for original learning content (and why not GPL)

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer
- **Phase**: 1

## Context

`tcf-accel` ships two distinct artifact classes:

1. **Code** — Python, TypeScript, SQL, infrastructure. The conventional choice for permissively-licensed OSS that wants maximum reuse (commercial and otherwise).
2. **Original learning content** — synthesized items, model essays at NCLC 7/9/11, the rubric prose, the SLA dossier, the Canadian-context primer. These are creative works, not software; they call for a Creative Commons license.

Third-party content (audio clips from RFI/TV5MONDE, FEI sample materials, dataset extracts) keeps its own license and is never relicensed under our umbrella.

Master prompt §6.3 specifies `MIT for code, CC BY-SA 4.0 for original learning content, third-party content remains under its own license`.

## Decision

- **Code**: MIT License. Year 2026, copyright "tcf-accel contributors".
- **Original learning content**: Creative Commons Attribution-ShareAlike 4.0 International (`CC-BY-SA-4.0`). Stored in `CONTENT_LICENSE` at the repo root; every content artifact carries a `provenance.license` field set to `CC-BY-SA-4.0` (or whatever the originating license is for non-original items).
- **Third-party content**: license preserved verbatim in `provenance.license`; the content pipeline rejects items whose license is incompatible with redistribution (e.g., `CC-BY-NC-ND` is *not* re-distributable as derivative; per `03_CONTENT_PIPELINE.md §1.2`, TEDx fr remains "link-only, not derivative").

## Consequences

- **Positive**:
  - Maximum adoption: MIT permits commercial reuse, enabling tutoring services and language schools to embed `tcf-accel`.
  - Content reuse: CC BY-SA encourages community contribution of items (forked banks must also share-alike), preventing private extension and abandonment of public content.
  - Clear separation: an operator can take the code under MIT, ship a private product, and *separately* respect the content license.
- **Negative**:
  - Mixing license families in one repo is a documentation burden; mitigated by per-artifact `provenance.license` and a README clearly delineating "code = MIT, content = CC BY-SA".
  - CC BY-SA is a *copyleft* content license — a closed-source platform that wants to ship our items must comply with share-alike. Some commercial operators may dislike this; we accept the friction because the alternative (CC BY without share-alike) lets a competitor enclose community-built items.
- **Neutral**:
  - GPL / AGPL would close down operator choice. We reject this.

## Alternatives considered

- **GPL-3.0 for code**: rejected because it complicates embedding `tcf-accel` into closed-source institutional deployments (Alliance Française tutor-mode being a v1.1 goal). *Would reconsider*: never; the FSF case for GPL does not outweigh adoption friction for our mission.
- **AGPL-3.0 for code**: rejected, same reasoning, plus the network-use clause adds operational complexity for SaaS operators.
- **Apache-2.0 for code**: viable; we prefer MIT for brevity and the lack of patent grant being acceptable at our project's scale. *Would reconsider*: if we accept a contribution from an entity with significant patent exposure that requires Apache's grant.
- **CC0 for content**: rejected because it removes the share-alike protection; private operators could enclose community contributions.
- **CC BY (no SA) for content**: rejected for the same reason as CC0 in spirit (no copyleft).
- **CC BY-NC-SA**: rejected because non-commercial is hostile to language schools and tutors (a core target user); the SA already prevents the closure we care about.

## What would change our mind

- A documented case where the MIT/CC-BY-SA split actively blocks an adoption we want (e.g., a school can't use the content because they're not willing to share-alike their adaptations). At that point, we'd offer a dual-licensing path for content.
- A change in CC BY-SA 4.0 that materially shifts its semantics.

## References

- [MIT License](https://opensource.org/license/MIT)
- [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- Master prompt §6.3.
- Phase 3 §1.2 (third-party content handling).
