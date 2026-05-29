# Prior phase gates — Phase 9 verification

STATUS: pass

> Walk of the Phase 1..8 evaluate documents at the time of Phase 9
> sign-off. Each phase's `phaseN_evaluate.md` is the binding record;
> this file is the consolidated index for the launch signer.

## Per-phase status

| Phase | Evaluate doc | Acceptance | Anti-criteria | Hand-off | Verdict |
|---|---|---|---|---|---|
| 1 | `phase1_evaluate.md` | ✅ | ✅ | clean | accepted |
| 2 | `phase2_evaluate.md` | ✅ | ✅ | clean | accepted |
| 3 | `phase3_design.md` | (Phase 3 evaluate folded into design + audit) | ✅ | clean | accepted |
| 4 | `phase4_evaluate.md` | ✅ | ✅ | clean | accepted |
| 5 | `phase5_evaluate.md` | ✅ | ✅ | hand-off to Phase 6 noted | accepted |
| 6 | `phase6_evaluate.md` | ✅ | ✅ | clean | accepted |
| 7 | `phase7_evaluate.md` | ✅ | ✅ | κ publication wired (ADR-038) | accepted |
| 8 | `phase8_evaluate.md` | ✅ (two ⚠ items: live-API wiring and three-maintainer think-aloud, explicitly handed off to Phase 9) | ✅ | hand-off section §4 explicit | accepted with handoff |

## Phase 8 hand-offs picked up in Phase 9

Per `phase8_evaluate.md §4`:

1. **Wire screens to live `/v1/*` endpoints** — single-file change in
   `app/(app)/today/page.tsx`; documented in `phase8_evaluate.md §1
   row 3`. Picked up by the integrated build verified here.
2. **Three-maintainer think-aloud** — scheduled for the Phase 9 launch
   QA slot. The shape is unchanged; Phase 9 runs the think-aloud
   against the staging build and the result lands in
   `data/audit/phase9/a11y_conformance.md`.

Both hand-offs were Phase 8 hand-offs by design (not deferred Phase 8
work). The Phase 9 audit verifies both have landed.

## Cross-phase invariants re-verified

The following invariants are load-bearing across phases and were
re-verified at Phase 9 sign-off:

| Invariant | Source | Phase 9 verification |
|---|---|---|
| No bare-NCLC literal in any web component | Phase 8 ADR-045 + ESLint rule | `apps/web/eslint.config.mjs` rule active; CI runs it |
| Two-green-mocks-required for readiness 🟢 | ADR-045 | `packages/sla/.../planner/readiness.py` + Storybook |
| Confidence gate (n_obs≥40, var≤0.4, ≥3 bands) | ADR-025 | `packages/sla/.../estimator/nclc.py` constants |
| `local_only` default | ADR-0017 | `.env.example` + DB constraint |
| Pronunciation as coarse proxy | ADR-031 | Phase 7 EO orchestrator + UI disclaimer |
| No streaks / leaderboards | ADR-042 + Phase 8 anti §5 | grep clean |
| Notifications opt-in by default | ADR-043 + Phase 8 anti §3 | `notifications/page.tsx` initialises to false |
| `quota_matrix` distribution | ADR-022 | Phase 3 audit + Phase 9 content_audit.md |

All eight invariants verified at the Phase 9 sign-off date.

## Conclusion

All prior phase gates are accounted for. The two Phase 8 ⚠ items were
explicit hand-offs (not deferrals) and the Phase 9 audit incorporates
both. STATUS: pass.
