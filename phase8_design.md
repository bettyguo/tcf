# Phase 8 — DESIGN

> This document is the build-spec for `apps/web/`. It is informed by
> `phase8_think.md` and constrained by ADRs 041–045. It is opinionated
> about file layout, component contracts, state boundaries, and
> testability — those decisions are easier to revisit early than to
> retrofit.

---

## 1. The repository slice we own

```
apps/web/
├── app/                          # Next.js App Router root
│   ├── (marketing)/              # Unauthed marketing/landing
│   ├── (app)/                    # Authed shell
│   │   ├── layout.tsx
│   │   ├── today/
│   │   ├── mock-exam/
│   │   ├── insights/
│   │   ├── library/
│   │   └── settings/
│   ├── onboarding/               # Outside the (app) chrome
│   ├── api/                      # BFF-style edge handlers (rare)
│   ├── globals.css
│   ├── layout.tsx
│   ├── middleware.ts             # locale + auth gate
│   └── providers.tsx             # Query/Zustand/i18n providers
├── components/
│   ├── ui/                       # shadcn primitives (copied, not deps)
│   ├── domain/                   # SkillTrajectory, ReadinessWidget, ...
│   ├── drills/                   # DrillPlayer + per-drill renderers
│   └── nav/                      # bottom-tab + sidebar shells
├── lib/
│   ├── api/                      # generated client + typed hooks
│   ├── auth/                     # token store, refresh interceptor
│   ├── i18n/                     # next-intl setup, message catalogs
│   ├── persistence/              # IndexedDB wrappers
│   ├── state/                    # Zustand stores
│   ├── format/                   # NCLC formatters, CI pretty-printers
│   └── a11y/                     # focus utils, ARIA helpers
├── messages/
│   ├── en.json
│   ├── fr.json
│   ├── es.json                   # stub (English fallback)
│   ├── ar.json                   # stub
│   └── zh.json                   # stub
├── tests/
│   ├── unit/
│   ├── component/                # Vitest + Testing Library
│   └── e2e/                      # Playwright
├── .storybook/
├── stories/
├── next.config.mjs
├── package.json
├── tsconfig.json
├── playwright.config.ts
└── vitest.config.ts
```

The `(app)` route group exists so the authed shell (bottom nav,
header, locale switcher) is shared without leaking into onboarding
or the mock-exam runner — both of which deliberately suppress chrome.

---

## 2. Routing & navigation

### 2.1 Route table

| Path                          | Render mode | Auth   | Notes                                                       |
| ----------------------------- | ----------- | ------ | ----------------------------------------------------------- |
| `/`                           | edge        | any    | Redirects: `/today` if authed, `/onboarding/goals` if not.  |
| `/onboarding/goals`           | csc         | guest  | Target NCLC + exam date + daily budget.                     |
| `/onboarding/diagnostic`      | csc         | guest+ | Hosts the Phase 4 CAT through the DrillPlayer.              |
| `/onboarding/plan-preview`    | rsc+csc     | guest+ | Shows the generated plan; accept persists + redirects.      |
| `/today`                      | rsc+csc     | authed | Plan summary (RSC) + start buttons (CSC).                   |
| `/today/session`              | csc         | authed | Active drill block; modal-style.                            |
| `/mock-exam/start`            | csc         | authed | Confirmation + canonical/training toggle.                   |
| `/mock-exam/run/[id]`         | csc         | authed | Full-screen runner; chrome suppressed.                      |
| `/mock-exam/report/[id]`      | rsc+csc     | authed | The 7-section report from Phase 6.                          |
| `/insights`                   | rsc+csc     | authed | Trajectory + ReadinessWidget + bottleneck.                  |
| `/insights/skills/[skill]`    | rsc+csc     | authed | Per-skill deep-dive.                                        |
| `/insights/errors`            | rsc         | authed | Aggregated error patterns.                                  |
| `/insights/readiness`         | rsc+csc     | authed | The booking-decision view + checklist.                      |
| `/library/grammar`            | rsc         | authed | Indexed by NCLC; "Drill this" buttons are CSC islands.      |
| `/library/vocab`              | rsc         | authed | FLELex-derived word lists, with audio.                      |
| `/library/writing`            | rsc         | authed | Model essays NCLC 7/9/11 + annotations.                     |
| `/library/speaking`           | rsc         | authed | Model recordings + rubric scores.                           |
| `/library/culture`            | rsc         | authed | Canadian-context primer.                                    |
| `/settings/account`           | csc         | authed | Email, password, sign-out.                                  |
| `/settings/privacy`           | csc         | authed | Local-only ↔ cloud toggle, export, delete.                  |
| `/settings/accessibility`     | csc         | authed | Font, contrast, motion, language.                           |
| `/settings/notifications`     | csc         | authed | Opt-in only — see §6.                                       |
| `/settings/api-keys`          | csc         | authed | Self-host LLM/ASR config (gated by env flag).               |

### 2.2 Middleware (`app/middleware.ts`)

Runs at edge. Order:

1. **Locale detection.** If path lacks a locale prefix and
   `Accept-Language` indicates fr/es/ar/zh, internally rewrite. (We
   do not put the locale in the URL for the v1 surface — the cookie
   tracks it. The cookie wins over `Accept-Language`.)
2. **Auth gate.** Read `tcf_auth` cookie. If absent and path is
   under `(app)`, redirect to `/onboarding/goals`. If present and
   path is `/onboarding/*` *after* completion, redirect to `/today`.
3. **Maintenance.** If `TCF_MAINTENANCE=1`, render a maintenance
   page (server-rendered, no JS).

### 2.3 Bottom-tab navigation (mobile) / sidebar (desktop ≥ 1024 px)

Three tabs only: **Today**, **Insights**, **Library**. Settings is a
top-right cog icon, not a tab. Mock-Exam is reached from Today (a
"Start mock" button shown when the plan recommends one).

Bottom-tab heights honor 56px + iOS safe-area inset. Active tab
indicated by an underline + 600-weight label (not color alone, for
contrast-deficient users).

---

## 3. Component system

### 3.1 The shadcn/ui layer (`components/ui/`)

We use the shadcn convention of *copying* primitives into our repo
rather than depending on a UI runtime. That keeps:

- Bundle size predictable (no upstream bloat).
- Tokens centralized in our Tailwind config.
- Component code editable when accessibility audits surface fixes.

Primitives we ship in v1: `Button`, `Input`, `Textarea`, `Select`,
`Checkbox`, `Switch`, `Slider`, `Dialog`, `Sheet`, `Tabs`, `Toast`,
`Tooltip`, `Popover`, `RadioGroup`, `Progress`, `Skeleton`,
`ScrollArea`, `AlertDialog`, `Label`, `Form`, `Separator`,
`Avatar`, `Badge`, `Card`, `DropdownMenu`. (Not the entire shadcn
catalogue — we don't yet need DataTable, Calendar, etc.)

### 3.2 Domain components (`components/domain/`)

The five named in the brief, plus a sixth (`<CredibleInterval />`)
that all of them depend on.

#### `<CredibleInterval />`

```ts
type CIProps = {
  mean: number;        // e.g., NCLC 8.3
  lower: number;       // e.g., 7.0
  upper: number;       // e.g., 9.4
  domain?: [number, number];   // default: [1, 12] for NCLC
  unit?: "NCLC" | "score" | "raw";
  format?: "bar" | "inline" | "tuple";
  status?: "ok" | "weak" | "strong";  // colour mapping
};
```

Renders as a horizontal bar with a mark for the mean. `format="inline"`
returns the textual form (e.g., "NCLC 8 (CI 7–9)") for use in copy.
`format="tuple"` returns just the (lower, upper) tuple for compact
tables.

This component is *the* enforcement point for ADR-025: there is no
other supported way to render an NCLC number in the app. The linter
rule (custom ESLint) flags free-floating `NCLC \d+` strings outside
this component.

#### `<SkillTrajectory />`

```ts
type SkillTrajectoryProps = {
  skill: "CO" | "CE" | "EE" | "EO";
  history: SkillSnapshot[];   // posterior at each timestamp
  target: number;             // target NCLC
  width?: number;
};
```

Shows the posterior mean with CI shading over time + a horizontal
line at `target`. Last point gets a `<CredibleInterval />` callout
on its right. Sparkline mode (`width ≤ 200`) for embedding in the
Insights summary; full mode for the per-skill page.

Renders via SVG, no chart library. Bundle savings + a11y wins
(SVG is screen-reader-traversable with `<title>` + `<desc>`).

#### `<ReadinessWidget />`

The most-tested component in the codebase. States:

| State                         | Light    | Condition                                                                                  |
| ----------------------------- | -------- | ------------------------------------------------------------------------------------------ |
| `INSUFFICIENT_DATA`           | ⚪       | No mock exams completed yet.                                                              |
| `NOT_READY`                   | 🔴       | Posterior min skill mean < target − 1.                                                     |
| `BORDERLINE`                  | 🟡       | Mean within ±1 of target, or P(min ≥ target) ∈ [0.5, 0.85].                                |
| `READY_ONE_MOCK`              | 🟡       | One canonical mock at green, but ADR-045 floors display to 🟡.                             |
| `READY`                       | 🟢       | Two consecutive canonical mocks at green AND P(min ≥ target) ≥ 0.85.                       |
| `REGRESSED`                   | 🔴       | Previously READY, then a mock below target. UI says so explicitly.                         |

The state mapping lives in `lib/readiness.ts` (pure function) so the
unit test owns the truth table without a render. The component
renders `state + bottleneckSkill + probability + recommendation`.

`recommendation` is *always* present. Even in 🔴 it says "Your top
priority is EE — start today's block." Never a dead end.

The component does **not** render a celebratory animation on 🟢
(ADR-045). It renders a calm green badge and a "Book your exam"
CTA. Period.

#### `<DrillPlayer />`

The universal state machine for every drill type defined in Phase 5:

- CO single-play, CO shadowing
- CE skim-then-detail, CE click-the-distractor
- EE timed write (Tasks 1/2/3)
- EO picture description, EO compare-contrast, EO express-opinion

Sub-components per drill type live in `components/drills/`:

```
DrillPlayer.tsx                 # the orchestrator
drills/
  COSinglePlay.tsx
  COShadowing.tsx
  CESkim.tsx
  CEClickDistractor.tsx
  EETimedWrite.tsx
  EOPicture.tsx
  EOCompareContrast.tsx
  EOExpressOpinion.tsx
  shared/
    AudioPlayer.tsx             # transcript-toggle behind state
    RationaleSheet.tsx          # post-answer rationale
    KeyboardHints.tsx
```

Drill flow (FSM, see §4.3):

```
PRESENTED → ANSWERING → SUBMITTED → REVEALED → (NEXT | END)
```

The DrillPlayer accepts an array of items + a callback for
submission. It is responsible for *flow*, *timing*, *focus
management*, and *persistence to IDB*. It is **not** responsible for
generating items (that's the API) or for grading (that's Phase 7).

#### `<MockReport />`

Renders the Phase 6 mock-exam report. Sections:

1. Headline: overall NCLC + per-skill min.
2. Per-skill cards (`<SkillCard />`) with rubric breakdowns.
3. Inflation-guard banner if any dimension was clamped (ADR-040).
4. Span-annotated essay rendering for EE.
5. Audio-with-transcript playback for EO with rubric overlays.
6. Top 3 actionable next-step drills (linked to Today).
7. Confidence footer: model κ, last calibration date.

#### `<RubricCard />`

```ts
type RubricCardProps = {
  rubric: "EE" | "EO";
  task: 1 | 2 | 3;
  dimensions: RubricDimension[];
  clamped?: string[];   // dimensions clamped by inflation guard
};
```

Each dimension shows a 0–5 score, a short rationale, a "what
this means" tooltip with the rubric definition, and a `[Drill →]`
link to a relevant drill. Clamped dimensions get a small `⚠` icon
with `aria-label="Inflation-guard clamp — see Insights"`.

### 3.3 Component testing budget

Every domain component has:

- A Vitest unit test covering its render permutations.
- A Storybook entry covering every state in the type union.
- An axe-core assertion in Storybook test-runner.

The Storybook is the source of truth for visual states. The audit
will exercise it.

---

## 4. The drill flow in detail

### 4.1 Why a state machine

Drills involve audio, timers, keyboard, IDB persistence, screen
readers, and the post-answer rationale. Modelling that with a chain
of `useEffect` + booleans is how SPAs grow bugs. We use a typed
finite-state machine.

### 4.2 The store (`lib/state/drill-store.ts`)

Zustand store keyed by `sessionId`:

```ts
type DrillState =
  | { phase: "IDLE" }
  | { phase: "LOADING_ITEM"; itemId: string }
  | { phase: "PRESENTED"; item: DrillItem; startedAt: number }
  | { phase: "ANSWERING"; item: DrillItem; answer: Answer; startedAt: number }
  | { phase: "SUBMITTING"; item: DrillItem; answer: Answer }
  | { phase: "REVEALED"; item: DrillItem; answer: Answer; result: GradeResult }
  | { phase: "ERROR"; item: DrillItem; error: ErrorEnvelope };
```

Transitions are pure functions exported next to the store and unit-
tested. Side effects (audio play, IDB save, API call) are dispatched
by middleware that observes the state transition, not embedded in
the components.

### 4.3 The FSM transitions

```
IDLE
  → LOAD(itemId) → LOADING_ITEM
                    → loaded(item) → PRESENTED
                    → failed(err)  → ERROR

PRESENTED
  → startAnswering() → ANSWERING

ANSWERING
  → updateAnswer(a) → ANSWERING (same)
  → submit()        → SUBMITTING

SUBMITTING
  → graded(result) → REVEALED
  → failed(err)    → ERROR

REVEALED
  → next() → IDLE (and the parent dispatches LOAD)
  → end()  → IDLE
```

The DrillPlayer renders the active phase. Audio playback,
keyboard listeners, and IDB writes are scoped to specific phases:

- Audio loads on PRESENTED, plays on ANSWERING for CO drills.
- IDB save runs on every ANSWERING `updateAnswer`.
- Rationale-sheet opens on REVEALED.

### 4.4 Offline resilience

`SUBMITTING → ERROR` with network failure does **not** lose the
answer. The Zustand state is mirrored to IDB on every transition;
on reload, the store rehydrates from IDB and the user resumes from
exactly the last phase. EE drafts auto-save every 1 s as well as on
blur.

### 4.5 Accessibility within the drill

- Focus enters the drill question on PRESENTED (focus-ring on the
  question's container, not jumping to a button).
- Audio play/pause has a button with `aria-pressed`.
- The timer is an `aria-live="polite"` region that announces at
  60/30/10/5/0 seconds (not every second — that would harass).
- Keyboard shortcuts: `Space` to play/pause audio, `Enter` to
  submit, `R` to replay (CO only, single-play drills suppress this
  per ADR-029), `Esc` to escape to the session summary (with
  confirm dialog).
- All shortcuts shown in a discoverable `?` overlay.

---

## 5. State management contracts

### 5.1 TanStack Query keys

A typed query-key factory in `lib/api/keys.ts`:

```ts
export const qk = {
  me: () => ["me"] as const,
  plan: () => ["plan"] as const,
  todayBlocks: () => ["plan", "today"] as const,
  insights: () => ["insights"] as const,
  skill: (s: Skill) => ["insights", "skill", s] as const,
  errors: () => ["insights", "errors"] as const,
  readiness: () => ["insights", "readiness"] as const,
  mockHistory: () => ["mock-exam", "history"] as const,
  mockReport: (id: string) => ["mock-exam", "report", id] as const,
  libraryGrammar: () => ["library", "grammar"] as const,
  // ...
} as const;
```

`staleTime`: 60 s default, 0 s for in-session drill data, ∞ for the
library content (revalidated on app version change).

### 5.2 Mutation contracts

Optimistic where safe:

- Submitting a drill answer → optimistic check-off of the block;
  rollback on server error with a toast.
- Accepting a plan → no optimism, navigation gated on success.
- Toggling cloud sync → no optimism, settings page shows a
  loading state.

### 5.3 Auth & token handling

- Token stored in an `HttpOnly` cookie issued by the API; the
  frontend never reads it directly. (Defense in depth against XSS
  exfiltration.)
- Token refresh: a fetch interceptor in `lib/api/fetch.ts` catches
  401, calls `/v1/auth/refresh`, retries once. If refresh fails,
  it clears the in-memory user and redirects to `/`.
- CSRF: double-submit cookie pattern for state-changing requests.

### 5.4 Zustand stores

Two narrow stores, not one monolith:

- `drillStore` — the FSM from §4.
- `uiStore` — bottom-sheet open states, locale, accessibility
  toggles. Persisted to `localStorage` via `zustand/middleware`.

Nothing else lives in Zustand. Server data is in Query; persisted
draft data is in IDB.

### 5.5 IndexedDB schema

```
db: tcf-accel
  store: drafts        # EE submission drafts keyed by promptId
  store: mockQueue     # mock-exam answers awaiting upload
  store: audioCache    # prefetched CO audio blobs, LRU-bounded 50 MB
  store: prefs         # accessibility prefs (mirror of uiStore for early read)
```

LRU eviction for `audioCache` runs on app start when the cache exceeds
budget. `mockQueue` items have a `submittedAt | null`; the upload
worker drains the queue on reconnect.

---

## 6. Notifications — implementation contract

Web push only (no SMS, no email-marketing). All paths default OFF.

| Surface                | Default | UI location              |
| ---------------------- | ------- | ------------------------ |
| Daily reminder         | off     | Settings → Notifications |
| Mock-exam reminder     | off     | Settings → Notifications |
| Streak-protection ping | off     | Settings → Notifications, gated behind a "are you sure?" dialog because we strongly recommend leaving it off |

The page copy:

> Notifications are off by default. Most users do best with no
> reminders at all — your plan is here when you open the app.
> Enable only if you've found you forget to open the app for
> multiple days at a time.

No notification ever uses urgency or fear-based copy. The copy table
lives in `messages/{locale}.json` under the `notifications.*` key
and is reviewed in CI by a lint rule that forbids strings matching
`/lost!|behind!|don't.*miss/i`.

---

## 7. Internationalization

### 7.1 next-intl setup

- `next-intl/middleware` runs in `middleware.ts` for locale
  detection.
- Messages loaded server-side from `messages/{locale}.json` and
  passed to the client provider.
- Date/time/number formatting via `Intl.*` with locale propagation.

### 7.2 Locale fallback chain

`zh → en`, `ar → en` (until v1.1 translations land). The UI shows
a banner at top of page: "This translation is incomplete. English
shown where missing." The banner is dismissible per session.

### 7.3 RTL handling

`<html dir="rtl">` set in the root layout for `ar`. Tailwind's
`rtl:` variants used throughout. Mock-exam runner audited
specifically because audio scrubber + timer placement flip.

### 7.4 Pseudo-localization

A `__pseudo` locale (vendored at build time) replaces every string
with an accent-padded longer version (`Hello → [Ḧéĺĺöö-Ẅöŕĺď]`).
Used in CI to catch hardcoded English and clipped layouts.

### 7.5 Reading-level

UI copy is reviewed against B1 (CEFR) targets for EN and FR.
Marketing-style English ("Crush your exam!") is forbidden. A
`docs/copy-style.md` doc lives in repo for contributor reference.

---

## 8. Visual identity

### 8.1 Tokens (Tailwind 4 + CSS variables)

```
--color-bg: oklch(0.99 0 0)            light
--color-bg: oklch(0.18 0.01 250)       dark
--color-fg: oklch(0.20 0 0)            light
--color-fg: oklch(0.95 0 0)            dark
--color-muted: oklch(0.5 0 0)
--color-accent: oklch(0.55 0.12 220)   muted blue
--color-danger: oklch(0.55 0.18 25)    muted red
--color-success: oklch(0.55 0.12 145)  muted green
--color-warning: oklch(0.7 0.13 80)    muted amber
--font-sans: "Inter Variable", system-ui, sans-serif
--font-mono: "JetBrains Mono Variable", ui-monospace, monospace
--font-dyslexic: "OpenDyslexic", var(--font-sans)
--radius-sm: 6px
--radius-md: 10px
--radius-lg: 16px
```

No gradients. No drop-shadow stacks. One shadow token per elevation
(`--shadow-1`, `--shadow-2`).

### 8.2 Type scale

| Token      | Size                | Use                                |
| ---------- | ------------------- | ---------------------------------- |
| `text-2xs` | 11px / 1.3          | timestamps, very-secondary meta    |
| `text-xs`  | 12px / 1.4          | secondary meta                     |
| `text-sm`  | 14px / 1.5          | body                               |
| `text-base`| 16px / 1.6          | reading body                       |
| `text-lg`  | 18px / 1.5          | sub-headings                       |
| `text-xl`  | 22px / 1.4          | screen headings                    |
| `text-2xl` | 28px / 1.3          | the Today greeting, screen titles  |
| `text-3xl` | 36px / 1.2          | the readiness label                |
| `text-num` | 32px mono / 1.0     | the big NCLC numbers               |

Headings use the sans face; all numerics use the mono face.

### 8.3 Light / dark / high-contrast

Three themes, switchable via `data-theme` attribute on `<html>`:

- `light` (default, auto-detected)
- `dark` (auto-detected via `prefers-color-scheme`)
- `hc` (high-contrast; user opt-in; raises contrast to AAA)

The Insights traffic light uses *both* color AND a redundant symbol
(○ ● 🔺 🚦 — replace with semantic shapes in code) so red/green
colorblind users get the same signal.

---

## 9. Performance budget — enforcement

### 9.1 Static budgets (CI gate)

`next.config.mjs` enables `bundleAnalyzer` in CI; a Make target
parses the output and fails if:

- Initial JS > 200 KB gzipped (route `/today`).
- Any single client component bundle > 80 KB gzipped.
- Total CSS > 30 KB gzipped.

### 9.2 Runtime budgets (Lighthouse CI)

Lighthouse CI runs on PR against a Docker-served build under Slow
4G + Moto G4 throttling. Budgets:

- LCP ≤ 2.5 s on `/today`, `/insights`, `/library/grammar`.
- TTI ≤ 4 s on the same.
- CLS ≤ 0.05.
- Lighthouse score ≥ 90 in Performance, Accessibility, Best
  Practices, SEO.

### 9.3 Audio prefetch

`AudioPlayer` consults `navigator.connection.effectiveType`:

- `4g`, `unknown`: prefetch next 3 items.
- `3g`: prefetch next 1.
- `2g`, `slow-2g`, or saveData: prefetch nothing; show a
  "preload audio?" button.

### 9.4 Code splitting

- Each top-level route is its own chunk via App Router defaults.
- DrillPlayer + drill renderers are loaded only on `/today/session`
  and `/mock-exam/run/[id]`.
- Storybook, MSW handlers, Chromatic config never end up in the
  app bundle (verified by `import-cost` lint rule).

---

## 10. The mock-exam runner

### 10.1 Modal full-screen

`/mock-exam/run/[id]` renders a layout that suppresses bottom-nav,
header, locale switcher. It owns the viewport.

### 10.2 Canonical vs training

Toggle on `/mock-exam/start`. Canonical mode:

- No transcripts, no rationales, no "skip" buttons.
- The timer is large and red in the last 5 minutes.
- The user cannot exit without confirming abandonment.
- The submitted score counts toward the ADR-045 "2 consecutive
  greens" requirement.

Training mode:

- Transcripts available post-answer.
- Per-item rationale viewable.
- Score does NOT count toward ADR-045.

The two modes are visually distinct (a `🟦 CANONICAL` badge vs a
`🟧 TRAINING` badge) so users cannot mistake one for the other.

### 10.3 Auto-save and resume

Every answer is queued to IDB and uploaded as soon as connection
permits. A connection drop in the middle of CO does not lose the
mock. On reconnect, the upload worker drains the queue; on a fresh
load mid-exam, the runner rehydrates from `/v1/mock-exam/{id}/state`.

---

## 11. The Today screen — implementation notes

### 11.1 The data flow

`/today` page = RSC that:

1. Resolves `me` from the auth cookie (server-side fetch).
2. Fetches `plan/today` blocks (server-side, suspended).
3. Renders the greeting + block list as RSC.
4. Hydrates the `[Start]` buttons as a small client component.

This gives a sub-1 s First Contentful Paint on a warm cache: the
plan summary is HTML on first byte, the start buttons hydrate as JS
streams in.

### 11.2 The "Why this plan today?" disclosure

A `<details>` element (server-rendered, no JS) that reveals the
plan rationale. The rationale string is computed by the planner
(Phase 4) and ships in the `/plan/today` payload.

### 11.3 "Resume" state

If a session is in progress (IDB has a non-empty `drillStore`
mirror), the top of `/today` shows a "Resume your session" card
above the block list. Clicking restores the exact phase from IDB.

---

## 12. The Insights screen — implementation notes

### 12.1 Layout

Mobile (≤ 640 px):

```
ReadinessWidget (full bleed)
Per-skill rows, vertical stack
Sparkline at bottom
```

Desktop (≥ 1024 px):

```
[ ReadinessWidget          ] [ Bottleneck callout    ]
[ Per-skill trajectory chart (full width SVG)         ]
[ Recent mock history table                            ]
```

### 12.2 The per-skill page

Each skill page shows:

- Posterior with CI history (full `<SkillTrajectory />`).
- Top 5 weak patterns (from `/insights/errors`).
- Recent drill performance log.
- "Drill this skill now" CTA.

### 12.3 The readiness page

`/insights/readiness`:

- Top: the widget at large size.
- Body: a checklist of the ADR-045 preconditions.
  - [x] Diagnostic complete
  - [x] Mock 1 at green (yyyy-mm-dd)
  - [ ] Mock 2 at green — required for booking recommendation
- Bottom: "When you book, here's what to bring" — a static
  checklist (ID, exam fee receipt, etc.). This is genuinely
  useful content; the user will not get it from IRCC.

---

## 13. Library — implementation notes

Library pages are almost entirely RSC. Each page is a server-
rendered list of cards linking to a per-item RSC. The only client
islands are:

- "Drill this lesson" buttons.
- The vocab page's "Play audio" buttons.

This keeps the Library bundle near-zero JS, which is correct: it's
a reading surface, not an interactive one.

---

## 14. Settings — implementation notes

### 14.1 Privacy (the headline)

`/settings/privacy`:

```
┌──────────────────────────────────────┐
│ Where your data lives                │
│                                      │
│ ◉ This device only (recommended)     │
│ ○ Cloud sync                         │
│                                      │
│ When cloud sync is on, we sync:      │
│   - your plan and progress           │
│   - your mock-exam scores            │
│ We never sync:                       │
│   - raw EE drafts                    │
│   - audio recordings                 │
│                                      │
│ [Export my data]   [Delete account]  │
└──────────────────────────────────────┘
```

The "Delete account" button is destructive-styled, two-tap-confirm,
and actually deletes. The "Export" button returns a JSON blob via
`/v1/data/export`.

### 14.2 Accessibility

`/settings/accessibility`:

- Text size: `S | M | L | XL`.
- Contrast: `Auto | Light | Dark | High-contrast`.
- Font: `System | OpenDyslexic`.
- Reduce motion: `Auto (system) | Always | Never`.
- Captions/transcripts default: `Off | On`.
- Language: `English | Français | Español | عربى | 中文`.

Every toggle persists to `uiStore` (localStorage) and mirrors to
IDB for early read.

### 14.3 Notifications

Per §6 above. The default is everything OFF and the page leads with
that fact.

### 14.4 API keys (self-hosters)

Behind `NEXT_PUBLIC_SELF_HOST=1`. Forms for:

- LLM gateway URL + API key.
- ASR backend (Whisper) URL.
- Custom model overrides (rarely used).

Keys are sent to the API, which stores them encrypted server-side.
The form never echoes the secret on reload.

---

## 15. Onboarding flow

`/onboarding/goals` → `/onboarding/diagnostic` → `/onboarding/plan-preview`.

Form on goals page (all optional except target NCLC):

- Target NCLC (required, default 9).
- Exam date (optional; influences plan length).
- Daily budget (15–120 min slider; default 30).
- L1 (used for tailored idiom hints; not for ML).

Diagnostic runs the Phase 4 CAT through the DrillPlayer. The
diagnostic state is server-side; an abandoned diagnostic can resume
from the same item.

Plan preview shows the 12-week plan (configurable to exam date) +
a "Looks good" CTA. Accepting persists the plan and redirects to
`/today`.

---

## 16. Testing strategy

### 16.1 Unit (Vitest, jsdom)

- Pure-function tests: `lib/readiness.ts` (truth table), formatters,
  i18n message-key tests (no missing keys per locale).
- Drill FSM transition tests: every transition + every illegal
  transition rejected.
- Auth interceptor: 401 → refresh → retry.

### 16.2 Component (Vitest + Testing Library)

- Each domain component, every Storybook state.
- Each drill renderer covers PRESENTED → REVEALED.
- axe-core invocation per component test asserts 0 violations.

### 16.3 E2E (Playwright)

Three priority flows, exercised under multiple viewports
(`Pixel 5`, `iPhone 13`, `iPad Mini`, `1280x800`):

1. **Onboarding → first block.** Sign up, finish diagnostic,
   accept plan, complete Block 1.
2. **Drill happy path** for each drill type (CO/CE/EE/EO),
   parameterized.
3. **Mock exam end-to-end.** Training mode, full 90 minutes
   collapsed via a `--fast-timer` debug flag.

Plus an a11y suite that runs each flow keyboard-only and screen-
reader-readable (`@axe-core/playwright`).

### 16.4 Visual regression

Storybook + Chromatic on PR for the design-system components.

### 16.5 Mock the API

We use MSW (`msw`) with handlers generated from the same OpenAPI
spec as the client SDK. Tests run against deterministic fixtures
in `tests/fixtures/`.

---

## 17. CI on PR

`make web-ci` runs:

1. `pnpm install --frozen-lockfile`
2. `pnpm typecheck`
3. `pnpm lint`
4. `pnpm test` (Vitest)
5. `pnpm test:e2e` (Playwright, headless)
6. `pnpm build` (Next build + bundle analyzer)
7. `pnpm lhci autorun` (Lighthouse CI; budgets from §9.2)
8. `pnpm pa11y-ci` (against built routes)
9. `pnpm storybook:test` (axe + visual)

All must pass for green. Bundle size and Lighthouse budgets are
hard gates, not warnings.

---

## 18. ADRs locked by Phase 8

| ADR     | Decision                                                                                       | Reversal cost |
| ------- | ---------------------------------------------------------------------------------------------- | ------------- |
| ADR-041 | Next.js 15 App Router; RSC for static, CSC for interactive; edge middleware for locale + auth. | Medium — would imply Remix or bare React migration. |
| ADR-042 | No gamification: no streak-flames, no leaderboards, no DAU-chasing patterns.                  | High — re-introducing them re-opens the calm-vs-engagement debate. |
| ADR-043 | Notifications opt-in, zero defaults; copy reviewed against the calm-principle lint rule.       | High — defaults that opt users in are a trust violation. |
| ADR-044 | WCAG 2.2 AA across the app as a launch gate.                                                  | High — would require new audit pass per release. |
| ADR-045 | Readiness widget never shows 🟢 without ≥ 2 consecutive canonical-mode mocks at 🟢.            | Medium — would re-open the booking-decision-failure mode. |

---

## 19. What we are explicitly NOT building in Phase 8

- Tutor chat ("ask the AI a question"). Out of scope; the system is
  a structured course, not a Q&A surface.
- Native mobile apps (iOS/Android). PWA installable from the web is
  the v1 mobile story.
- Social features of any kind (friends, classes, leaderboards).
- A live-classroom integration.
- Anything Storybook-Composition-based with external design teams.

These are sequenced for v1.1+ and explicitly off the Phase 8 work
list to keep the bundle and the IA shallow.

---

## 20. Hand-off

End of Phase 8 deliverables:

- `apps/web/` complete with the route tree above.
- All 5 ADRs accepted and lint-rules enforcing where applicable.
- `phase8_audit.md` populated with the Lighthouse + axe + keyboard
  + screen-reader + multi-device + pseudo-loc + network-resilience
  results.
- `phase8_evaluate.md` populated with the acceptance verdict.
- A deployed staging URL.
- A short demo video walking through one realistic 30-minute
  session on each device size.

Phase 9 then takes the staging build through launch QA + the
publish-κ + the data-governance audit.
