# packages/shared (`tcf_accel`)

The cross-phase contract surface for tcf-accel. Phase 1 freezes:

- `tcf_accel.ids` — typed NewType wrappers around UUID/int identifiers.
- `tcf_accel.errors` — base error class and the seed error taxonomy. Phase 2
  elaborates with the full set from `02_ARCHITECTURE.md §2.5`.
- `tcf_accel.schemas.version` — the cross-package schema version
  (`SCHEMA_VERSION`); bumped via `CHANGELOG.md`.
- `tcf_accel.schemas.common` — `Provenance`, `QualityFlag`, `ItemMetadata`,
  shared enums.
- `tcf_accel.schemas.item` — `Item` and the placeholder `ItemContent`;
  Phase 2 narrows `ItemContent` to a discriminated union of
  `COContent | CEContent | EEContent | EOContent` (additive).
- `tcf_accel.schemas.scoring` — `Score` (with CI invariants) and the
  Phase 1 skeleton of `NCLCEstimate`.

Changes to anything exported here require an ADR + a `CHANGELOG.md` entry.
Phase 1 commits to additive-only changes; breaking changes require a major
version bump on `SCHEMA_VERSION`.
