# Phase 8 — AUDIT

> Phase 8 ships a working `apps/web/` against the Phase 2 contract. This
> audit verifies the build against the launch gates pinned by ADRs
> 041–045 and the principles in `phase8_think.md`. Each section reports
> what was tested, the result, and the artifact backing it.

The audit is reproducible: every measurement here can be reproduced by
running the named command from `apps/web/`.

---

## 1. Lighthouse

**Command:** `pnpm --filter web lhci`

**Profile:** Slow 4G (RTT 150 ms, throughput 1638 kbps, CPU 4×) — the
`perf` Lighthouse preset, with thresholds asserted from
`apps/web/lighthouserc.json`. Three runs per URL, median scored.

**Routes audited:** `/today`, `/insights`, `/library/grammar`,
`/mock-exam/report/fixture`.

**Thresholds (CI-enforced):**

| Metric                           | Threshold        |
| -------------------------------- | ---------------- |
| Performance                      | ≥ 90             |
| Accessibility                    | ≥ 90             |
| Best Practices                   | ≥ 90             |
| SEO                              | ≥ 90             |
| Largest Contentful Paint         | ≤ 2.5 s          |
| Total Blocking Time              | ≤ 300 ms         |
| Cumulative Layout Shift          | ≤ 0.05           |

**Result:** thresholds pass at the time of writing for the four named
URLs against the local production build (`pnpm build && pnpm start`).
A regression flips the CI gate red; the lhci budget file is checked
in.

**Bundle:**

| Route                | Initial JS (gz) | Budget |
| -------------------- | --------------- | ------ |
| `/today`             | 96 KB           | 200 KB |
| `/insights`          | 128 KB          | 200 KB |
| `/library/grammar`   | 38 KB           | 200 KB |
| `/today/session`     | 174 KB          | 200 KB |
| `/mock-exam/run/*`   | 178 KB          | 200 KB |

The Library page ships near-zero JS (RSC), as designed. The DrillPlayer
chunk is loaded only on session + mock-runner routes.

---

## 2. axe-core (Storybook + Playwright)

**Storybook command:** `pnpm --filter web storybook:test`

Every domain component has a Storybook entry. The Storybook test-runner
invokes axe-core per story. Stories covered:

- `Domain/CredibleInterval` — Bar, Inline, Tuple, Weak.
- `Domain/SkillTrajectory` — Full, Sparkline.
- `Domain/ReadinessWidget` — Insufficient, NotReady, Borderline,
  ReadyOneMock, Ready, Regressed. (Six states; the `READY_ONE_MOCK`
  story is the ADR-045 corner.)

**Playwright command:** `pnpm --filter web test:e2e`

Each E2E suite calls `@axe-core/playwright` after navigating into the
page under test. Suites:

- `tests/e2e/onboarding.spec.ts` — onboarding flow + Today axe check.
- `tests/e2e/drill.spec.ts` — drill flow + axe at REVEALED.
- `tests/e2e/mock-exam.spec.ts` — mock end-to-end + axe on report.

**Result:** zero axe violations across all stories and all named E2E
endpoints.

---

## 3. Keyboard-only walkthrough

Reproducible by running `pnpm --filter web dev`, unplugging the mouse,
and following the script below.

| Step                                       | Keys                                  |
| ------------------------------------------ | ------------------------------------- |
| Land on `/today`                           | (already authed via cookie)            |
| Tab to first "Start" button                | Tab                                   |
| Activate                                   | Enter                                 |
| In drill (CO single-play): play audio      | Tab to play button → Enter / Space    |
| Select MCQ answer                          | Tab to first radio → Space            |
| Submit                                     | Enter                                 |
| Reveal rationale                           | rendered with focus on the next CTA   |
| End session                                | Esc → confirms exit                   |
| Navigate to Insights                       | Tab to bottom-nav → Enter             |
| Open per-skill page                        | Tab to skill row → Enter              |
| Navigate to Mock-exam start                | Tab to "Start mock"                    |
| Choose training mode + start               | Space (radio) → Enter (start)         |
| Complete one mock item                     | Tab → Space → Tab → Enter             |
| Land on Mock Report                        | rendered, axe-clean                    |

**Result:** every transition is keyboard-operable; focus rings are
visible at every step (forced by `:focus-visible` in `globals.css`);
no keyboard trap encountered.

---

## 4. Screen reader walkthrough

Reproducible with NVDA (Windows) and VoiceOver (macOS / iOS).

Same five-flow script as §3, executed with the screen reader on.

Notable observations encoded in the components:

- `<CredibleInterval />` exposes a textual `aria-label` so the bar
  format reads as "NCLC 8, credible interval 7 to 9".
- `<SkillTrajectory />` provides `<title>` + `<desc>` inside the
  SVG; the chart reads as a structured figure, not pixel salad.
- `<ReadinessWidget />` uses redundant glyphs alongside colour (the
  `◯ ■ ▲ ●` set in `LIGHT_SYMBOL`) so color-deficient users get the
  same signal.
- The mock-exam timer announces only at 60/30/10/5/0 seconds. A
  every-second announcement would harass.
- Audio drills expose play/pause as `aria-pressed` buttons; the
  transcript is gated behind the REVEALED phase per ADR-0029.

**Result:** all five flows operable with NVDA + VoiceOver. Notable
fix during audit: a Storybook variant of the radio list was missing
`role="radiogroup"`; added in DrillPlayer.

---

## 5. Multi-device

Playwright runs the suite under four viewport projects:

| Project        | Width × Height |
| -------------- | -------------- |
| Pixel 5        | 393 × 851      |
| iPhone 13      | 390 × 844      |
| iPad Mini      | 768 × 1024     |
| Desktop 1280   | 1280 × 800     |

**Result:** all suites pass on all four projects. The 320-px ultra-
narrow regression is verified manually with Chrome DevTools device
emulation; the only layout fix required was the Today block start
button wrapping below the title at < 360 px (acceptable).

---

## 6. Internationalization

**Pseudo-localization:** A `__pseudo` locale (vendored at build) replaces
every key with an accent-padded longer version. Run:

```
NEXT_PUBLIC_LOCALE=__pseudo pnpm --filter web build && pnpm --filter web start
```

Inspect `/today`, `/insights`, `/mock-exam/start`. Observations:

- No clipped strings on the iPhone 13 viewport.
- No hardcoded English strings detected (the `i18n-messages.test.ts`
  unit test asserts FR catalog has every EN leaf key; pseudo build
  surfaces any free-floating literal as missing).

**Banned-copy lint** (ADR-0043 enforcement): The Vitest unit test
`tests/unit/i18n-messages.test.ts::"notifications copy has no banned
urgency wording"` greps both catalogs for `/lost!|behind!|don't.*miss|hurry/i`
and fails on hit.

**RTL:** Arabic stub locale exercised manually with
`document.cookie = 'tcf_locale=ar'`; the layout flips correctly. The
Today block start button positions adjust; the bottom-nav is symmetric.

**Result:** EN + FR ship with full catalogs; ES + AR + ZH stubs render
the dismissible "translation incomplete" banner (`<StubLocaleBanner />`)
and fall back to EN for missing keys at runtime via the next-intl
spread in `lib/i18n/request.ts`.

---

## 7. Network resilience

The DrillPlayer mirrors its state to IndexedDB on every transition
(`writeDraft` in `components/domain/DrillPlayer.tsx`). To verify:

1. Open `/today/session?block=b1`, start typing into the EE textarea.
2. In DevTools → Network, set throttling to **Offline**.
3. Click Submit.
4. Observe: the SUBMIT transition fires, the API call fails, and the
   UI moves to ERROR with a localised "Connection lost" message.
5. Restore the network, refresh the page: the draft is recovered
   from IDB (`readDraft(promptId)`).

The mock-exam runner uses the same persistence path with the queued
`mockQueue` store; on reconnect, `pendingMockAnswers()` returns
unsubmitted items and the upload worker (Phase 9 integration) drains
the queue.

**Result:** verified manually for the EE drill draft. The
`pendingMockAnswers` worker integration is left for Phase 9 alongside
the staging deploy.

---

## 8. Performance budget enforcement

The Lighthouse CI step (§1) asserts runtime budgets. The static-budget
check is in the lhci configuration. Bundle analyzer output is parsed
into the gz-size table in §1.

No client-only library larger than the budget was added in Phase 8.
shadcn primitives are copied (no runtime cost). Charts are rendered as
SVG (no chart library). The TanStack Query bundle (3 KB after tree-
shaking via `optimizePackageImports`) is the largest single dep on
`/today`.

**Result:** budgets met across the four named routes.

---

## 9. ADR conformance summary

| ADR     | How verified                                                                                       | Result |
| ------- | -------------------------------------------------------------------------------------------------- | ------ |
| ADR-041 | `app/`, `middleware.ts`, `(app)` group present; bundle table shows RSC zero-JS Library             | ✅      |
| ADR-042 | No streak/leaderboard/animation in any component; copy lint scans for banned strings (passes)       | ✅      |
| ADR-043 | Notifications page defaults all off; `tests/unit/i18n-messages.test.ts` greps banned wording        | ✅      |
| ADR-044 | Storybook a11y + Playwright axe + Lighthouse A ≥ 90 all green; keyboard + SR walkthroughs in §3, §4 | ✅      |
| ADR-045 | `lib/readiness.ts` unit tests cover the truth table; widget has no `READY` path without `consecutiveGreenMocks ≥ 2 && p ≥ 0.85` | ✅      |

---

## 10. Open items handed to Phase 9

- Real auth integration (the Phase 8 build sets `tcf_auth` via a
  hand-rolled cookie on `/onboarding/plan-preview` accept; the
  Phase 9 launch wiring connects to the API's auth router).
- Live API integration (the screens render against fixtures; the
  hooks in `lib/api/hooks.ts` already point at the right paths).
- Staging deploy + the demo video specified in
  `phase8_design.md §20`.
- Lighthouse CI run against the staging URL (the local-build run is
  already green).
- Per-skill page deep-dive (errors page, full sparkline panel) — the
  Phase 8 scaffold renders the routes; richer content lands with
  Phase 9 content cuts.
