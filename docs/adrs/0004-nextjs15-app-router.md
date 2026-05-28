# ADR-0004: Next.js 15 (App Router) over Remix / SvelteKit

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Frontend
- **Phase**: 1 (elaborated in Phase 8 as ADR-041)

## Context

The frontend (Phase 8) is mobile-first, mostly logged-in (server-rendered shells aren't a huge SEO play), with interactive drill loops (heavy client state) and an Insights screen with timeseries visualizations. It must support EN/FR (and later ES/AR/ZH) with sub-2.5 s LCP on 4G (master prompt §8 spec, Phase 8 §2.8 budget).

The candidates are Next.js 15 (App Router + RSC + React 19), Remix, and SvelteKit. Master prompt §8 names Next.js 15.

## Decision

Next.js 15 App Router. React Server Components for static lessons and dashboards; client components for drill interactivity. Tailwind 4 + shadcn/ui for the design system. TanStack Query for server state; Zustand for transient client state.

## Consequences

- **Positive**:
  - RSC reduces shipped JS for the (large) Library section.
  - The shadcn/ui + Tailwind 4 ecosystem is the most mature for the "calm, dense, accessible" aesthetic Phase 8 §1.1 prescribes.
  - Vercel/Cloudflare deploy options are first-class; self-hosters use the standard Node runtime via `next start`.
  - Generated TypeScript clients from the OpenAPI spec drop into `lib/api.ts` cleanly.
- **Negative**:
  - App Router has a steeper learning curve than Pages Router or Remix's nested-routes model.
  - RSC is still maturing; specific patterns (e.g., streaming + Suspense for the Insights screen) have rough edges.
  - Build times scale with the route tree; mitigated by route grouping (Phase 8 design).
- **Neutral**:
  - We use the Edge runtime middleware for locale detection + auth gating; the rest stays on Node.

## Alternatives considered

- **Remix**: nested routes and the loader/action model are elegant. Rejected because the React 19 + RSC story under Next.js 15 is more battle-tested for content-heavy + dashboard hybrid apps, and the shadcn/ui ecosystem leans Next-first. *Would reconsider*: if Remix's React Router v7 rebrand stabilizes with materially better DX for our use case.
- **SvelteKit**: smaller bundles, simpler reactivity. Rejected on ecosystem (TanStack Query, shadcn/ui equivalents are weaker) and contributor pool. *Would reconsider*: only on a green-field rewrite.
- **Pure SPA (Vite + React Router)**: rejected because SSR matters for first-paint of the Today screen on mobile, and the Library section benefits from RSC bundle savings.

## What would change our mind

- Next.js 15 introduces a breaking change that costs more to absorb than the framework's value-add over a quarter.
- RSC ergonomics fail a usability test with three Phase 8 maintainers — at which point we drop RSC and run pure client + SSR.

## References

- Master prompt §8.
- Phase 8 ADR-041 (downstream affirmation).
