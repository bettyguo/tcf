# PHASE 8 — Frontend UX, Study Planner, Dashboards, Accessibility

> Goal: a Next.js 15 application that turns the backend into a daily learning experience. Mobile-first, accessible, calm, and information-dense without being overwhelming.

---

## 1. THINK (produce `phase8_think.md`)

### 1.1 Three Design Principles

1. **Calm over gamification.** TCF Canada candidates are typically adults preparing for an immigration milestone, often under significant pressure. Streak fire emojis, leaderboards, and intrusive notifications are anti-patterns here. The product is a tool, not entertainment.
2. **Honesty over engagement.** When the model is uncertain, the UI shows uncertainty. When the learner is not ready, the UI says so. We optimize for *outcome at exam*, not for daily active users.
3. **Information density without overwhelm.** Adults reading on a commute can absorb more than Duolingo's UI assumes. Show structured information (CI bars, weak-pattern lists, drill rationales) without dumbing it down.

### 1.2 The Three Surfaces

1. **Today screen** (the default after login): what to do *right now*.
2. **Insights screen**: where am I, where am I going, am I ready?
3. **Library screen**: explore drills, content, the bank, reference material.

The information architecture is deliberately shallow. Everything important is reachable in two taps.

### 1.3 Mobile-First Because of Use Patterns

Most learners are squeezing study into commutes, lunch breaks, and pre-bed slots. The Today screen must work one-handed on a phone, including audio playback for CO drills with auto-resume after lock-screen.

### 1.4 Accessibility Is Foundational, Not a Layer

- All audio has transcripts toggleable post-answer.
- All interactions navigable by keyboard with visible focus rings.
- All actionable elements ≥ 44×44 px touch target.
- ARIA live regions for timers and score reveals.
- Reduced-motion mode respected.
- Dyslexia-friendly font (OpenDyslexic) toggleable.
- High-contrast theme + dark mode (auto + manual).
- Screen reader–tested with NVDA and VoiceOver.
- WCAG 2.2 AA across the app; AAA where feasible.

### 1.5 The "Booking Decision" UX

The Insights screen contains the traffic-light readiness widget. This is the most consequential UI element in the product. Its design constraints:

- Must show CI bars, not point estimates.
- Must require ≥ 2 consecutive 🟢 mocks before showing 🟢.
- Must show the *bottleneck skill* prominently (the immigration-rule floor).
- Must NOT use a celebratory animation when 🟢 — that nudges premature booking.
- MUST link to "what to do next" regardless of state.

### 1.6 Internationalization

UI in EN + FR (the FR audience is non-trivial: existing francophones improving for higher NCLC). Add ES + AR + ZH at lower priority — common L1s of TCF Canada candidates per IRCC stats. i18next or next-intl.

---

## 2. DESIGN (produce `phase8_design.md`)

### 2.1 Screen Inventory

```
/onboarding
  /goals          set target NCLC + exam date + daily budget
  /diagnostic     CO → CE → EE → EO CAT (Phase 4)
  /plan-preview   show the 12-week plan + accept

/today           drill blocks for today + start-now CTA
/today/session   the active drill flow (Phase 5 drills hosted)

/mock-exam
  /start         confirmation + canonical vs training toggle
  /run/[id]      full-screen player
  /report/[id]   detailed report (Phase 6)

/insights
  /                trajectory + traffic light + bottleneck skill
  /skills/[skill]  per-skill deep-dive: posterior, weak patterns, drill history
  /errors          recurrent error patterns across history
  /readiness       the booking decision + checklist

/library
  /grammar         lessons indexed by NCLC level + linked drills
  /vocab           word lists, FLELex-derived, with audio
  /writing         model essays at NCLC 7/9/11 with annotations
  /speaking        model recordings with rubric scores
  /culture         Canadian-context primer (institutions, idioms, news topics)

/settings
  /account
  /privacy         local-only vs cloud toggles, export, delete
  /accessibility
  /notifications   minimal — see §2.5
  /api-keys        for self-hosters configuring LLM/ASR backends
```

### 2.2 Today Screen — The Default Surface

Layout (mobile):

```
┌──────────────────────────────────────┐
│ Bonjour, Aïcha.                      │
│ Day 23 of 84 • 1h 42m remaining today│
├──────────────────────────────────────┤
│ Block 1 • 30 min • EE (priority)     │
│ Task 2 timed write — Canadian housing│
│ [Start]                              │
├──────────────────────────────────────┤
│ Block 2 • 20 min • EO                │
│ Picture description × 5              │
│ [Start]                              │
├──────────────────────────────────────┤
│ Block 3 • 25 min • CE                │
│ Mixed-difficulty drills              │
│ [Start]                              │
├──────────────────────────────────────┤
│ Block 4 • 10 min • CO shadowing      │
│ [Start]                              │
└──────────────────────────────────────┘

  ▾ Why this plan today?
   "EE is your bottleneck (NCLC 6, target 9).
   EO close behind. CO and CE are on track."
```

### 2.3 Insights Screen — The Booking Decision

```
┌──────────────────────────────────────┐
│ Readiness   🟡 BORDERLINE            │
│                                      │
│ Min skill: EE = NCLC 8 (CI 7–9)      │
│ Target: NCLC 9                       │
│ P(min ≥ target) = 0.62               │
│                                      │
│ Recommendation:                      │
│ Run another mock in 7 days.          │
│ Book the exam only after 2           │
│ consecutive 🟢 mocks.                │
├──────────────────────────────────────┤
│ Per-skill trajectory ───────────     │
│                                      │
│ CO  ▓▓▓▓▓▓▓▓▓░░  NCLC 9 (8–10)       │
│ CE  ▓▓▓▓▓▓▓▓▓░░  NCLC 9 (8–10)       │
│ EE  ▓▓▓▓▓▓▓░░░  NCLC 8 (7–9)  ← floor│
│ EO  ▓▓▓▓▓▓▓▓░░  NCLC 8 (8–9)         │
│                                      │
│ [Sparkline of last 6 weeks]          │
└──────────────────────────────────────┘
```

### 2.4 Notifications — Minimal by Design

Default: zero push notifications. Opt-in for:
- Daily reminder at user-chosen time (single, dismissible).
- Mock-exam scheduled reminder.
- Streak-protection ping if user hasn't logged in for 3 days **and explicitly enabled** — never as a default.

No notification ever uses urgency language or fear-based copy.

### 2.5 State Management

- TanStack Query for server state, with `staleTime: 60s` for plan/insights, `0` for active session state.
- Zustand for transient client state (current drill question, audio playback position).
- IndexedDB for offline draft of EE submissions and queued mock items (so a CO drill can be initiated offline using pre-fetched audio).

### 2.6 Component System

shadcn/ui base, augmented by:

- A `<SkillTrajectory />` component (posterior mean ± CI bar + sparkline).
- A `<MockReport />` component (the 7-section report from Phase 6).
- A `<DrillPlayer />` component (the universal drill state machine UI).
- A `<RubricCard />` component (per-rubric score with feedback).
- A `<ReadinessWidget />` component (traffic-light + bottleneck + recommendation).

Visual identity: muted palette, no gradients, generous whitespace, monospace for numerics (so CI ranges align visually). Reference: Bret Victor / Edward Tufte over Figma-trend gradients.

### 2.7 Routing & Auth

- Next.js App Router.
- Auth: bearer JWTs from the API, refresh-on-401 in a fetch interceptor.
- Server components for static lessons; client components for interactive drills.
- Edge-runtime middleware for locale detection and auth gating.

### 2.8 Performance Budget

- LCP ≤ 2.5 s on a 4G connection.
- TTI ≤ 4 s.
- Audio prefetch for the next 3 CO items in a session (avoid drill-time stalls).
- Bundle size: initial JS ≤ 200 KB gzipped.

### 2.9 ADRs

- ADR-041: Next.js 15 App Router + RSC for static, CSC for drills.
- ADR-042: No gamification (no streaks-as-default, no leaderboards).
- ADR-043: Notifications opt-in, never default.
- ADR-044: WCAG 2.2 AA across the app.
- ADR-045: Readiness widget never shows 🟢 without 2 consecutive canonical mocks at 🟢.

---

## 3. CODE

- `apps/web/` complete:
  - `app/` directory for the route tree above.
  - `components/` for the design-system pieces.
  - `lib/api.ts` consumes the generated client from Phase 2.
  - `lib/i18n.ts` for EN/FR (ES/AR/ZH stubbed).
  - `tests/e2e/` Playwright suites for onboarding, drill, mock-exam happy paths.
- Storybook for the design system.
- An accessibility CI step (`axe-core` + `pa11y-ci`) on PR.

---

## 4. AUDIT (produce `phase8_audit.md`)

- **Lighthouse:** ≥ 90 in Performance, Accessibility, Best Practices, SEO on Today, Insights, Library, Mock Report.
- **axe-core:** 0 violations on every page.
- **Keyboard-only walkthrough:** complete a CO drill + EE drill + EO drill + finish a mock + read the report, using only keyboard. Document.
- **Screen reader walkthrough:** same set, with NVDA + VoiceOver.
- **Multi-device:** 320 px, 768 px, 1280 px verified.
- **Internationalization:** all strings externalized; pseudo-localization run shows no clipped strings or hardcoded English.
- **Network resilience:** kill the network during a drill — the app surfaces a clear retry path; in-progress drill saves to IDB.
- **Performance budget met.**

---

## 5. EVALUATE (produce `phase8_evaluate.md`)

Acceptance criteria:

- ✅ All audit metrics pass.
- ✅ Three representative users (or maintainers, in their absence) complete a 60-min session end-to-end without external help, measured with a think-aloud.
- ✅ The Insights screen surfaces CI bars correctly across all confidence states.
- ✅ The Today screen renders correct allocations from the planner.
- ✅ ADRs ADR-041 through ADR-045 accepted.

Anti-criteria:

- ❌ Any UI that shows an NCLC point estimate without its CI.
- ❌ Any "Start exam!" CTA visible when readiness is 🔴 or ⚪.
- ❌ Any notification path that is enabled by default.
- ❌ Any drill the screen reader cannot operate.
- ❌ Any leaderboard, streak-flame, or "your friends are ahead" element.

Hand-off: a deployed staging URL + a short demo video walking through one realistic 30-minute session per device size.
