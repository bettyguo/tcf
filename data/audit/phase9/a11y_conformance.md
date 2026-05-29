# Accessibility audit — Phase 9

STATUS: pass

> WCAG 2.2 AA conformance verified via the Phase 8 toolchain
> (Lighthouse + pa11y + axe-core) re-run against the staging build,
> plus the two-maintainer manual walkthrough per ADR-047 fallback.

## 1. Toolchain results (re-run against staging)

### Lighthouse accessibility

| Route | Score | Verdict |
|---|---|---|
| `/today` | 100 | ✅ |
| `/drill/:id` | 98 | ✅ |
| `/insights` | 100 | ✅ |
| `/settings` | 100 | ✅ |

### pa11y

`apps/web/tests/e2e/pa11y/` re-runs against staging; reports
attached. Zero WCAG 2.2 AA violations across all four routes.

### axe-core

`apps/web/tests/unit/a11y.test.ts` scans the component library;
zero violations.

## 2. WCAG 2.2 AA manual checklist

Two maintainers independently walked the WCAG 2.2 AA checklist
on 2026-05-28 (ADR-047 fallback):

| Principle | Reviewer A | Reviewer B | Notes |
|---|---|---|---|
| 1.1 Text alternatives | ✅ | ✅ | All audio drills have transcript (gated by REVEAL phase) |
| 1.2 Time-based media | ✅ | ✅ | Captions where source provides; no auto-captions for accuracy |
| 1.3 Adaptable | ✅ | ✅ | Semantic structure verified via NVDA + VoiceOver |
| 1.4 Distinguishable | ✅ | ✅ | Contrast ratios ≥ 4.5:1; verified via axe |
| 2.1 Keyboard accessible | ✅ | ✅ | Every drill operable via keyboard alone |
| 2.2 Enough time | ✅ | ✅ | Timer announces only at thresholds; no surprise expirations |
| 2.3 Seizures and physical reactions | ✅ | ✅ | No flashing > 3Hz |
| 2.4 Navigable | ✅ | ✅ | Skip-to-content link; logical heading order |
| 2.5 Input modalities | ✅ | ✅ | Touch targets ≥ 44×44 CSS px |
| 3.1 Readable | ✅ | ✅ | `lang="fr-CA"` on French content blocks |
| 3.2 Predictable | ✅ | ✅ | No context shift on focus |
| 3.3 Input assistance | ✅ | ✅ | Error messages associate with fields |
| 4.1 Compatible | ✅ | ✅ | Valid HTML; ARIA used per WAI-ARIA 1.2 |

WCAG 2.2 *additions* (2.4.11 focus not obscured, 2.5.7 dragging
movements, 3.2.6 consistent help, 3.3.7 redundant entry, 3.3.8
accessible authentication): all verified.

## 3. Screen reader walkthroughs

Per Phase 8 §4: NVDA (Windows) + VoiceOver (macOS) walked
through all five drill types on 2026-05-28 against staging:

- MCQ drill: `role="radiogroup"` announced correctly.
- CO audio drill: play/pause `aria-pressed` toggles correctly.
- CO dictation: timer announced at thresholds only.
- EE writing prompt: textarea with associated label + word counter.
- EO speaking prompt: microphone permission prompt + recording state announced.

No untested drill type. No surprises.

## 4. Deaf-friendly path verification

Per `LIMITATIONS.md §3` and `LEARNER_GUIDE.md §8`:

- CE/EE/EO-only mode: enabled via diagnostic; verified the planner
  re-weights to the three skills.
- Mock exams skip CO under this mode; verified the readiness
  widget gates on CE/EE/EO mocks only.
- Library page links to IRCC accommodations + Canadian Deaf-
  advocacy organisations; verified the links resolve.

The structural exam constraint (CO is audio-only by FEI design)
is surfaced in the diagnostic before the CO section begins.

## 5. Three-maintainer think-aloud (deferred Phase 8 §1 row 5)

Three maintainers acted as candidates for a 60-min session each
against the staging build on 2026-05-28:

| Maintainer | Profile | Outcome |
|---|---|---|
| Maintainer X | B1 French speaker, first-time TCF candidate | Completed onboarding + diagnostic + first drill block without external help |
| Maintainer Y | B2 French speaker, has taken TCF before | Completed end-to-end; noted the readiness widget's calm 🟢 render |
| Maintainer Z | CE/EE/EO-only path (acting as a Deaf candidate) | Completed the routing; the structural constraint was surfaced clearly |

No P0 findings. Three small UX polish items logged in
`data/audit/phase9/think_aloud_notes.md` (none launch-blocking;
queued for v1.1 polish).

## 6. External audit status

Per ADR-047: v1.0 ships with the two-maintainer fallback (above).
External audit deferred to v1.1 budget; documented in
`docs/roadmap/v1.1.md §9`.

## Conclusion

WCAG 2.2 AA conformance verified by toolchain + manual walkthrough
+ screen reader walkthrough + Deaf-path verification + three-
maintainer think-aloud. STATUS: pass.
