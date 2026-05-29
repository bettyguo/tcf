# ADR-0041: Next.js 15 App Router with RSC for static, CSC for interactive

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, UX lead
- **Phase**: 8 (Frontend UX)

## Context

Phase 8 elaborates the Phase 1 hello-page into a Today / Insights /
Library / Mock-Exam application. The framework was tentatively pinned
in `ADR-0004` (Next.js 15 App Router). Phase 8 now exercises the
RSC/CSC boundary across screens with very different requirements:

- The **Library** is read-mostly, statically rendered, and benefits
  from RSC (zero JS on initial paint).
- The **DrillPlayer** is a stateful FSM that must own the viewport
  during a session.
- The **Mock-Exam** runner suppresses chrome and runs in canonical
  mode without nav, audio rationales, or transcripts.
- The **Insights** screen streams a posterior-driven SVG chart that
  benefits from Server Components rendering the chrome and a
  Suspense boundary delivering the chart.

We needed a concrete contract for which screens render server-side
and which hydrate, because the bundle budget (200 KB initial gzipped)
does not survive every screen being client-rendered.

Alternatives considered:

1. **Remix.** Nested routing analog, but smaller ecosystem for our
   pinned libs (next-intl, shadcn/ui) and we'd lose the App Router
   RSC bundle wins on the Library.
2. **Bare React + Vite + react-router.** Simpler at small scale but
   loses RSC entirely, so the Library ships a non-trivial bundle for
   what is fundamentally HTML.
3. **Pages Router (Next.js 14 style).** No RSC. We would pay the
   client-bundle cost for every page even when the page is static.

## Decision

We adopt Next.js 15 App Router with the following split:

- **RSC for static, mostly-read surfaces:** Library (all five sub-
  pages), Plan-Preview, the Today greeting + plan summary, the Mock
  Report shell.
- **CSC for interactive surfaces:** the DrillPlayer and per-drill
  renderers, the Today block start buttons, the Onboarding goals
  form, the Mock-Exam runner.
- **Edge middleware** (`app/middleware.ts`) for (a) locale
  negotiation against the `tcf_locale` cookie and `Accept-Language`,
  (b) auth gate, (c) onboarding-completion redirect, (d) maintenance
  switch.
- **Suspense boundaries** around the Insights trajectory chart so
  the bottleneck callout paints before the chart hydrates.

Route groups:

- `(app)/` for the authed shell (header + bottom-tab nav).
- `onboarding/` and `mock-exam/` outside the shell so they own the
  viewport without nesting overrides.

## Consequences

- The Library bundle is near-zero JS (the only client islands are
  "Drill this" buttons and audio play buttons on vocab).
- DrillPlayer and the Zustand drill store load only on session and
  mock-runner routes.
- Streaming the Insights chart improves perceived performance on
  Slow 4G — the bottleneck callout (the most actionable data point)
  appears before the SVG hydrates.
- The middleware's auth gate replaces a per-route `redirect()` and
  means an unauthed user never sees the (app) chrome flicker.
- Migrating to Remix or a different framework is now a meaningful
  cost (medium reversal). The internals worth preserving — the FSM,
  the readiness function, the message catalogs — are framework-
  independent and easy to lift.

## Related

- ADR-0004 (initial framework selection)
- ADR-0042, ADR-0043, ADR-0044, ADR-0045
- `phase8_think.md §9`, `phase8_design.md §1–§2, §11–§12`
