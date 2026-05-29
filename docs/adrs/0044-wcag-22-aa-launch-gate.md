# ADR-0044: WCAG 2.2 AA is a launch gate across the app

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, UX lead
- **Phase**: 8 (Frontend UX)

## Context

Accessibility is often treated as a v2 backlog item, which then
calcifies as the codebase grows. Our target user includes older
candidates with declining near vision, dyslexic learners (≈10% of
the general population, higher among self-selected language-prep
cohorts), candidates studying on small Android screens, and
candidates eligible for the TCF Canada hearing-accommodation
modality.

Treating a11y as a launch gate (not a v2 feature) makes the cost
small if paid upfront, large if deferred.

## Decision

The Phase 8 launch is gated on WCAG 2.2 AA conformance across the
following surfaces:

- All authed screens: Today, Today/session, Insights (overview, per-
  skill, errors, readiness), Library (all sub-pages), Settings (all
  sub-pages), Mock-Exam (start, run, report).
- Unauthed screens: Onboarding (goals, diagnostic, plan-preview).

Concrete requirements:

- Every interactive element has ≥ 44×44 px tap target.
- Every page passes axe-core with zero violations (asserted in
  Storybook tests and Playwright E2E).
- Lighthouse Accessibility ≥ 90 on `/today`, `/insights`, `/library/grammar`,
  `/mock-exam/report/fixture` under the CI throttling profile.
- Keyboard-only completion of one of each drill type (CO single-
  play, CO shadowing, CE skim, EE timed write, EO picture) is
  demonstrated in audit.
- Screen reader smoke-test with NVDA + VoiceOver on the same drill
  set demonstrated in audit.
- ARIA live regions for timer (announces at 60/30/10/5/0s) and
  score reveals.
- Reduced-motion respected throughout (no animation that violates
  `prefers-reduced-motion: reduce`).
- High-contrast theme + dark mode, switchable.
- Dyslexia-friendly font (OpenDyslexic) toggleable.
- All audio post-answer transcripts available (`AudioPlayer.transcript`).
- UI reading-level targets CEFR B1 in both English and French.

AAA is pursued where it does not impose a trade-off; specifically,
the high-contrast theme meets AAA contrast.

## Consequences

- Every PR runs axe-core, pa11y-ci, and Lighthouse CI; a regression
  fails the build.
- Every new domain component requires a Storybook entry exercising
  axe-core.
- Initial development is 10–15% slower than an a11y-deferred
  approach; total cost is lower because we avoid the v2 retrofit.
- Reversing this would require new audit infrastructure per release
  and would re-open the equity argument with our user base. High
  reversal cost.

## Related

- ADR-0042, ADR-0043, ADR-0045
- `phase8_think.md §5`, `phase8_design.md §3.3, §4.5, §16`, `phase8_audit.md §1–§6`
