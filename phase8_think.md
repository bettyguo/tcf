# Phase 8 — THINK

> The backend has, by the end of Phase 7, become a credible exam-prep
> system: it ingests aligned content, models the learner, generates
> drills, runs mock exams, scores them honestly, and tells the user
> whether they're ready to book. None of that matters if the surface
> the user touches is loud, dishonest, or unusable on a phone at 6 a.m.
> Phase 8 is where the *product* either earns the engineering or
> squanders it.

This is the load-bearing reasoning for the frontend. The design and the
code that follow inherit it.

---

## 1. Who the user actually is

The TCF Canada candidate is, statistically, not a teenager learning
French for fun. The dominant cohort is:

- 28–42 years old.
- Working full-time (often in a non-French-speaking environment).
- Studying in 20–45 minute slots: morning commute, lunch break,
  pre-bed.
- Preparing for *Express Entry* — a points-based immigration system
  in which NCLC 7 vs. NCLC 9 vs. NCLC 10 is a difference of tens of
  thousands of CAD in their ability to settle in Canada, and often the
  difference between an invitation to apply and indefinite waiting.
- Anxious, time-constrained, and skeptical of language apps that
  optimize for retention metrics.

A secondary cohort is francophone or partially francophone (Maghreb,
Sub-Saharan Africa, Haiti) candidates who already speak French
conversationally but need to score higher on the *Expression écrite*
formal-register dimensions specifically.

Both cohorts share one trait: **they will quit at the first sign that
the product wastes their time.** They will not be won by streaks,
character mascots, or a celebratory "you did it!" toast. They will be
won by a tool that tells them, today, the next 90 minutes that will
most move their NCLC floor.

This is the design brief.

---

## 2. Three design principles, ranked

### 2.1 Calm over gamification

Gamification works for Duolingo because Duolingo's users *do not need
to learn the language by Tuesday*. Streak loss aversion, leaderboards,
and notification spam are aligned with retention-metric optimization,
not exam-outcome optimization. They are also actively harmful for the
TCF Canada cohort because:

- Streaks weaponize the user's already-elevated anxiety against them.
- Leaderboards create social comparison among strangers studying for
  the same scarce immigration slots.
- Daily-active-user (DAU) chasing pushes the product into pushing
  the user to study when they should be sleeping, working, or
  recovering — all of which raise exam-day performance more than a
  marginal drill block.

We will therefore have:

- No streak-flame. (`ADR-042`.)
- No leaderboard. (`ADR-042`.)
- No "you fell behind!" notifications. (`ADR-043`.)
- No default push notifications at all. (`ADR-043`.)
- No celebratory animations on green-light readiness, because that
  is exactly the moment a user is most prone to *premature booking*
  (`ADR-045`).

This is a hard constraint, not a style preference. Reviewers will be
looking for the temptation to "just one little streak — for engagement"
and we will refuse it.

### 2.2 Honesty over engagement

Every numeric estimate in this product has uncertainty. The learner
model produces posteriors with credible intervals; the mock-exam
scorer publishes its own κ; the readiness widget emits a probability.

Engagement-optimized UIs hide all of that behind a single shiny
number. We will not.

- NCLC estimates ALWAYS show a credible interval (`ADR-025` from
  Phase 4 — confidence-flag-launch-blocking). A point estimate
  without a CI is treated by the linter as a defect.
- The booking-decision widget shows the *probability* that the
  bottleneck skill clears the target — not a single recommendation
  pretending to be deterministic.
- When a mock-exam dimension has been *clamped by the inflation
  guard* (`ADR-040`), the UI says so visibly. Silent clamping would
  be a credibility leak.
- When a recommendation depends on a model the user can dispute
  ("EE is your weakest skill"), the rationale is one tap away. The
  user is an adult; do not hide the reasoning.

A consequence: this UI is more *information-dense* than language-app
peers. That is fine. The target user reads NYT and can absorb a CI
bar. We do not need to dumb anything down.

### 2.3 Information density without overwhelm

Density without overwhelm comes from *typographic hierarchy* and
*shallow information architecture*, not from removing information.

- Type hierarchy: large numerics (the NCLC numbers, the minutes
  remaining) in a *monospace* face so columns of numbers visually
  align. Narrative copy in a humanist sans. Reference: Tufte, Ben
  Fry, Bret Victor — not contemporary Figma trends.
- IA: every important screen is at most two taps from the home
  screen. There is no nested settings hierarchy. There is no
  "tutorial" the user clicks through before reaching the actual
  work.
- One screen, one job: Today tells you what to do *now*. Insights
  tells you *where you are*. Library is for *exploration*. We do
  not collapse these into a single dashboard with twelve cards.

---

## 3. The three surfaces (mental model, not just routes)

We do not think of the frontend as "a list of screens." We think of
it as three *modes of relating to the system*:

1. **Today (act):** "I have 30–60 minutes. Tell me what to do."
   The Today screen is the default after login, because answering
   that question is the product's first promise.
2. **Insights (reflect):** "Where am I? Am I ready? What is my
   bottleneck?" The Insights screen is the second-most-visited
   surface for an engaged user — usually after a mock exam.
3. **Library (explore):** "I want to look up a grammar point, read
   a model essay, browse vocab." The Library is shallow, indexed,
   and crucially *linked to drills* — every grammar lesson has a
   "drill this" button.

There are administrative surfaces (Onboarding, Settings, Mock-Exam
runner) but they are *not* navigation peers. They are entered from a
specific context and exited back to it.

### 3.1 The implicit fourth surface: Mock Exam

The mock-exam runner is a *modal full-screen experience*. It is
deliberately not a navigation peer because once started it must look
and feel like the real TCF — minimal chrome, no notifications, no
visible navigation. We trade IA consistency for fidelity. Phase 6
already established the canonical-vs-training distinction; the UI
honours it (no scaffolding in canonical mode).

---

## 4. Mobile-first because of when learning happens

Web analytics from comparable adult-learner products consistently
show **60–75% of session starts on mobile**, even when the user has
a laptop available. The reason is when the sessions happen: commute,
lunch, bedside. The desktop sessions tend to be longer (mock exams,
EE writing) but rarer.

Implications:

- **Today** must work *one-handed on a phone in portrait, with the
  phone in the dominant hand and the thumb reaching the start
  button.* That is a real ergonomic constraint, not a slogan.
- **CO (compréhension orale) audio** must auto-resume after a
  lock-screen interruption. A train going through a tunnel must not
  reset the drill.
- **Audio prefetch** for the next three items, so a brief connection
  drop does not stall the session.
- **EE submissions** save locally to IndexedDB on every keystroke,
  so a tab-kill or background-process-kill loses ≤ 1 typed word.
- **Tap targets ≥ 44×44 px** with adequate spacing — yes, even when
  it forces fewer answer options per visible viewport. We accept
  the trade.
- **Desktop is a courtesy**, not an afterthought: the mock-exam
  runner is best on tablet/desktop because that's where most users
  actually sit a 90-minute exam. The Insights screen is best on
  desktop because the trajectory chart benefits from width. The
  Today screen is best on mobile.

---

## 5. Accessibility is foundational, not a layer

The TCF Canada cohort includes:

- Older candidates (45+) with declining near vision.
- Candidates with dyslexia (≈10% of the population; higher in
  self-selected language-learning cohorts).
- Candidates with hearing impairment using the visual-only
  accommodation (TCF Canada offers accessibility accommodations;
  our prep must too).
- Candidates studying on a 5-year-old Android phone with a small
  screen.

We will therefore commit, as a launch gate (not a v2 wish list):

- **WCAG 2.2 AA** across the entire app (`ADR-044`). AAA where
  achievable without a significant trade-off.
- **All audio has a post-answer transcript toggle** — never visible
  *before* the answer (else the listening drill is trivial), always
  available after.
- **Keyboard navigation** for every drill, including CO replay,
  with visible focus rings. We will demonstrate this in the audit
  by completing one of each drill type with the mouse unplugged.
- **ARIA live regions** for the mock-exam timer, score reveals,
  drill rationales — screen readers must announce, not be left to
  poll.
- **Reduced-motion** preferences respected (no smooth-scroll, no
  parallax, no `prefers-reduced-motion: reduce` violations).
- **Dyslexia-friendly font** (OpenDyslexic) as an opt-in. We do not
  default to it (it has legibility costs for non-dyslexic readers)
  but it is one toggle away.
- **High-contrast theme** + **dark mode** (auto-detect + manual
  override). Dark mode is not a vanity feature — it materially
  reduces eye strain for late-night study, which is when this
  cohort studies.
- **Screen reader smoke-tested with NVDA + VoiceOver** before
  every release tag (`phase8_audit.md §3`).
- **Reading-level**: UI copy targets CEFR B1 in English and B1 in
  French, so the *meta-language* of the app does not exceed the
  level the user is studying for.

A11y is not a separate ticket queue. It is the definition of
"working." A drill that the screen reader cannot operate is not
shipped.

---

## 6. The booking-decision UX (the most consequential screen)

The Insights screen contains a readiness widget that says, in
effect: *should you book the exam yet?*

This is the single highest-stakes UI element in the product, because:

- A premature booking burns the user's exam fee (CAD ~340, plus
  travel) and their next 6–8 weeks of demoralized re-prep.
- A delayed booking pushes their Express Entry profile out of an
  invitation window — direct financial harm.

Design constraints we will not relax:

- **CI bars, not point estimates.** The number under "EE = NCLC
  8" is "NCLC 8 (CI 7–9)" or rendered as a visual bar.
- **Two consecutive 🟢 mocks before 🟢 is shown** (`ADR-045`). One
  green mock is variance, not evidence.
- **The bottleneck skill is named prominently.** Per IRCC rules,
  Express Entry points are awarded against the *minimum* of the
  four skill levels. A user who reads "average NCLC = 8" and books
  the exam, only to find their EE was 6, has been failed by the UI.
- **No celebration on 🟢.** A "✨ You're ready!" toast at the moment
  the user sees 🟢 nudges them to book immediately, which we have
  just argued is the failure mode. The 🟢 state shows confidently
  but soberly, and the call-to-action is "book the exam" — not a
  victory.
- **Always link to what to do next.** Even in 🔴, the screen has a
  "see your priority drills" path. The user is never told "you're
  not ready" without a "and here is how to get ready."

This widget will get a Storybook entry covering every state
(⚪ insufficient data, 🔴 not ready, 🟡 borderline, 🟢-after-one-mock
which still renders as 🟡, 🟢-after-two-mocks, and the rare
🔴-after-a-green case where the most recent mock regressed).

---

## 7. Internationalization: what we ship, what we stub

The UI launches in **EN + FR**.

Why FR is non-optional, not a nicety: the secondary cohort of partially
francophone candidates is large, and a French UI is also useful for the
EN cohort to *practice in the target language*. Many users will toggle
the UI to FR as their NCLC rises — an organic difficulty knob.

Stubbed (extraction infrastructure in place, translations deferred to
v1.1): **ES, AR, ZH**. These are, by IRCC-published L1 statistics, the
next three largest L1s among TCF Canada candidates after EN/FR. AR
in particular requires RTL layout support, which we wire from day one
even though the translations are stubs — so the v1.1 translation
rollout is a content update, not a rebuild.

We use `next-intl` over `i18next` because (a) App Router native, (b)
type-safety on message catalogs, (c) the smaller bundle matters for
our 200 KB initial JS budget.

---

## 8. State management: where data lives

The frontend's state cleanly partitions into three regions:

- **Server state** (the truth): per-user plan, posteriors, drill
  bank, mock-exam history, library content. Cached in **TanStack
  Query**. `staleTime: 60s` for plan/insights (they change slowly),
  `0` for active session state (every answer matters). Mutations
  optimistically update where safe (drill-block check-off).
- **Transient client state**: the in-progress drill question, audio
  playback position, the currently-typed-but-unsubmitted essay.
  Held in **Zustand** (small, no provider hell, plays well with
  RSC). The Zustand store is the *single source of truth for drill
  flow*, so the DrillPlayer state machine has one home.
- **Local-persisted state**: offline drafts of EE submissions,
  queued mock items, prefetched CO audio blobs. In **IndexedDB**
  via `idb-keyval`. This is what makes a 4G train-tunnel survivable.

Why not just one of these? Because they have *fundamentally different
invariants*:

- Server state must be invalidated on mutations and refetched.
- Transient state is allowed to be lost on reload (we re-fetch the
  drill).
- Local-persisted state must survive reload AND be reconciled with
  the server on next connect (drafts).

A single store would force the invariants of the strictest into the
others, which is how SPAs accumulate latency.

---

## 9. Why Next.js 15 App Router (not Remix, not bare React)

This was decided in Phase 1 (`ADR-0004`) but it earns a Phase 8 paragraph
because the choice now becomes load-bearing.

App Router gives us:

- **Server components** for static lessons (Library, model essays,
  Canadian-context primer). These ship zero JS for the read-only
  surface, which is most of the library — a meaningful bundle win.
- **Client components** for interactive drills, scoped per route
  segment. The Today screen is RSC for the header + plan summary
  and CSC for the start buttons + active drill.
- **Edge middleware** for locale detection (`Accept-Language` →
  default), auth gating (redirect unauth → onboarding), and
  redirect of `/` → `/today` for authenticated users.
- **Streaming** for the Insights screen: the trajectory chart can
  render with `<Suspense>` boundaries so the bottleneck-skill
  callout appears before the chart is hydrated. Time-to-content
  for the screen the user most wants on a slow connection.

Remix's nested-routing model would also have worked. App Router won
on (a) RSC bundle savings, (b) the Next team's larger ecosystem for
the libraries we depend on (shadcn/ui, next-intl), and (c) the lead
maintainer's existing fluency.

---

## 10. The performance budget, and why it is non-negotiable

A 4G connection in a moving train in suburban Montréal delivers
~1.5 Mbps with frequent dropouts. A user opening Today on that
connection should see Block 1 within 2.5 seconds (LCP) or they will
not study at all that morning.

Therefore:

- **LCP ≤ 2.5s** on a simulated Slow 4G + Moto G4 profile.
- **TTI ≤ 4s** on the same profile.
- **Initial JS bundle ≤ 200 KB gzipped.** This is the budget that
  forces us to scope dependencies. shadcn/ui (copy-pasted, not a
  runtime dep) and Recharts-or-equivalent fit; a full charting
  library does not.
- **Audio prefetch** for the next 3 CO items in a session, gated on
  `navigator.connection.effectiveType` — we don't burn 2 MB on a
  saved-data user.

The audit measures these on real network throttling, not just
Lighthouse defaults.

---

## 11. The notifications stance

Default: **zero push notifications**. Period.

Opt-in surfaces:

- Daily reminder at a user-chosen time. Single, dismissible.
- Mock-exam scheduled reminder.
- Streak-protection ping if the user has not opened the app for 3
  days AND has explicitly opted in. Never as a default.

No notification ever uses urgency language ("you'll lose!"),
fear ("don't fall behind!"), or social pressure ("your friends
are ahead!"). Copy is reviewed against `00_MASTER_PROMPT.md` and the
calm-over-gamification principle.

This is `ADR-043`. The temptation to relax it for "engagement
metrics" is exactly the temptation we are pre-committing against.

---

## 12. Privacy posture in the UI

Inherited from Phase 4's `ADR-017` (privacy-default-local-only):
the Settings → Privacy screen exposes the local-only ↔ cloud toggle
prominently, *not* buried three taps deep.

- The default state is communicated honestly: "Your drill data is
  stored only on this device unless you turn on cloud sync."
- Cloud sync, if enabled, lists *what* syncs (posteriors, plan,
  mock results) and *what does not* (raw EE drafts, audio
  recordings — those leave only for scoring and are deleted post-
  scoring per Phase 7).
- "Export my data" returns a JSON dump. "Delete my account" is a
  red button, two-tap-confirm, and actually deletes. Both are
  reachable from the same screen.

We will not hide these behind a "more" menu.

---

## 13. The five ADRs Phase 8 will pin

| ADR     | Statement                                                                                       |
| ------- | ----------------------------------------------------------------------------------------------- |
| ADR-041 | Next.js 15 App Router with RSC for static, CSC for interactive drills, edge mw for locale+auth. |
| ADR-042 | No gamification: no streak-flames, no leaderboards, no DAU-chasing UI patterns.                 |
| ADR-043 | Notifications are opt-in with zero defaults; copy reviewed against the calm principle.          |
| ADR-044 | WCAG 2.2 AA across the app as a launch gate; AAA where feasible without trade-off.              |
| ADR-045 | Readiness widget never shows 🟢 without ≥ 2 consecutive canonical-mode mocks at 🟢.             |

Each is irrevocable in the same sense as the Phase 4/6/7 ADRs: an
"ADR-grade change" to reverse, with a documented review of
consequences.

---

## 14. What success looks like

The acceptance test that summarises everything above:

> A first-time user opens the app on a Moto G4 simulating Slow 4G,
> completes onboarding + a diagnostic CAT + accepts a 12-week plan,
> studies one 30-minute block today, returns the next day and
> finishes a second block, runs their first training-mode mock the
> following weekend, reviews the report, and reaches the Insights
> screen — all without touching the documentation, all keyboard-
> and screen-reader-operable, and at no point sees a streak fire,
> a leaderboard, an urgency notification, or an NCLC point estimate
> without its CI.

That is the bar.
