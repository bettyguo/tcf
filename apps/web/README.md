# apps/web

Next.js 15 (App Router, React 19) frontend for tcf-accel — the surface
through which all backend Phase 3–7 capabilities reach the learner.

## Run

```bash
pnpm --filter web dev          # http://localhost:3000
pnpm --filter web storybook    # http://localhost:6006
```

## Test

```bash
pnpm --filter web typecheck
pnpm --filter web lint
pnpm --filter web test         # vitest (unit + component)
pnpm --filter web test:e2e     # Playwright (4 viewports)
pnpm --filter web storybook:test  # axe-core per story
pnpm --filter web lhci         # Lighthouse CI (Slow 4G profile)
pnpm --filter web pa11y        # pa11y-ci across built routes
```

## Structure

```
app/                        # App Router (RSC + CSC)
  (app)/                    # Authed shell (header + bottom nav)
    today/                  # default after login
    insights/               # readiness widget, per-skill trajectories
    library/                # grammar, vocab, writing, speaking, culture
    settings/               # account, privacy, accessibility, notifications
  onboarding/               # goals → diagnostic → plan-preview
  mock-exam/                # full-screen runner (chrome suppressed)
components/
  ui/                       # shadcn primitives (copied, not deps)
  domain/                   # CredibleInterval, SkillTrajectory,
                            # ReadinessWidget, MockReport, RubricCard
  drills/                   # DrillPlayer renderers + shared (Timer, Audio)
  nav/                      # Header, BottomNav, StubLocaleBanner
lib/
  api/                      # client + typed query hooks + keys
  i18n/                     # next-intl config + request handler
  persistence/              # IndexedDB wrappers (idb-keyval)
  state/                    # Zustand: drill FSM + UI preferences
  readiness.ts              # ADR-045 enforcement (pure)
  format.ts                 # NCLC formatters (ADR-025)
messages/                   # en, fr (full); es, ar, zh (stubs)
stories/                    # Storybook stories — every domain component state
tests/
  unit/                     # Vitest
  e2e/                      # Playwright + @axe-core/playwright
```

## ADRs

- ADR-041 Next.js 15 App Router (RSC for static, CSC for interactive).
- ADR-042 No gamification.
- ADR-043 Notifications opt-in.
- ADR-044 WCAG 2.2 AA gate.
- ADR-045 Readiness never green without ≥ 2 consecutive canonical greens.
