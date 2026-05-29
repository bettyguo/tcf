# FEI source-of-truth check — Phase 9

STATUS: verified

> The master prompt §1.1 anchors the TCF Canada exam specification
> to the published FEI page. This file records the re-verification
> at the moment of the v1.0.0 launch tag.

## Re-verification

| Field | Source | Verified value | Date | Auditor |
|---|---|---|---|---|
| FEI canonical URL | `00_MASTER_PROMPT.md §1.1` | https://www.france-education-international.fr/test/tcf-canada | 2026-05-28 | maintainer A |
| Section structure | FEI page | CO + CE + EE + EO unchanged | 2026-05-28 | maintainer A |
| CO item count + duration | FEI page | 39 items, ~35 min | 2026-05-28 | maintainer A |
| CE item count + duration | FEI page | 39 items, 60 min | 2026-05-28 | maintainer A |
| EE prompt count + duration | FEI page | 3 prompts, 60 min | 2026-05-28 | maintainer A |
| EO prompt count + duration | FEI page | 3 prompts, 12 min | 2026-05-28 | maintainer A |
| NCLC mapping table | FEI + IRCC pages | NCLC 1–12 unchanged | 2026-05-28 | maintainer A |
| Adaptive-listening 29-question variant (R-001) | FEI page | not present (rumoured variant has not shipped); R-001 remains mitigated | 2026-05-28 | maintainer A |

## Diff against the spec embedded in the codebase

`packages/shared/src/tcf_accel/schemas/exam_format.py` carries the
versioned exam format. The Phase 9 check verifies the on-disk
schema matches the FEI page:

- Section counts: match.
- Per-section durations: match.
- Per-section item counts: match.
- NCLC band mapping: match.

No drift detected at the source-of-truth check.

## What we'll do if the FEI page changes post-v1.0

Per R-001 mitigation + ADR (Phase 1 design):

1. Bump `exam_format.py` to a new versioned record (no in-place
   edits to a released version).
2. Issue a patch release (`v1.0.1`) if the change is
   non-breaking for learners mid-arc.
3. Issue a minor release (`v1.1.0`) if the change requires bank
   re-leveling or mock structure changes.
4. Re-run the Phase 9 audit suite against the new schema.

## Conclusion

FEI source-of-truth verified against the live FEI page on
2026-05-28. STATUS: verified.
