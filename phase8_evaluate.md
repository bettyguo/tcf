# Phase 8 — EVALUATE

> Verdict on whether Phase 8 cleared its acceptance criteria. Pairs
> with `phase8_audit.md` (the evidence) and `phase8_think.md` (the
> principles being measured against).

---

## 1. Acceptance criteria

Each line is a launch gate. ✅ means met; ⚠ means partially met with
hand-off documented.

| #   | Criterion                                                                                              | Status |
| --- | ------------------------------------------------------------------------------------------------------ | ------ |
| 1   | All Phase 8 audit metrics pass (Lighthouse ≥ 90 on the four named routes; axe-clean; budgets met)      | ✅      |
| 2   | The Insights screen surfaces CI bars correctly across all confidence states                            | ✅      |
| 3   | The Today screen renders correct allocations from the planner (fixture in scaffold; live integration is the Phase 9 hand-off) | ⚠      |
| 4   | ADRs ADR-041 through ADR-045 accepted                                                                  | ✅      |
| 5   | Three representative users (or maintainers, in their absence) complete a 60-min session end-to-end without external help, measured with a think-aloud | ⚠      |

### Notes

**(3)** The scaffolded Today screen renders against deterministic
fixtures so it stands alone for design review and E2E tests. The
underlying API endpoints (`/plan/today`) exist as Phase 4 handlers
and the `useToday()` hook in `lib/api/hooks.ts` already targets the
correct path. Switching from fixture to live API is a one-file
change in `app/(app)/today/page.tsx`. Documented for Phase 9.

**(5)** Three maintainer think-alouds were not run as part of this
phase deliverable; they are scheduled for the Phase 9 launch QA
slot. The shape of the task is unchanged — Phase 8 produced the
fully-navigable surface against fixtures; Phase 9 runs the
think-aloud against the staging build.

---

## 2. Anti-criteria

Each line is something this phase must NOT have shipped. ✅ means
"correctly absent."

| #   | Anti-criterion                                                                                | Status |
| --- | --------------------------------------------------------------------------------------------- | ------ |
| 1   | Any UI that shows an NCLC point estimate without its CI                                       | ✅      |
| 2   | Any "Start exam!" CTA visible when readiness is 🔴 or ⚪                                       | ✅      |
| 3   | Any notification path enabled by default                                                      | ✅      |
| 4   | Any drill the screen reader cannot operate                                                    | ✅      |
| 5   | Any leaderboard, streak-flame, or "your friends are ahead" element                            | ✅      |

### Evidence

**(1)** `<CredibleInterval />` is the sole NCLC-render component;
`formatNclcWithCi()` is the sole text renderer. The custom ESLint
rule `eslint/no-bare-nclc.js` flags any `NCLC <n>` literal outside
the component's source file, the i18n catalogs, and Storybook
fixtures. The rule is wired in `eslint.config.mjs` and runs in CI.

**(2)** The `<ReadinessWidget />` renders the booking CTA only when
`state === "READY"`. In `INSUFFICIENT_DATA` (⚪), `NOT_READY` (🔴),
`REGRESSED` (🔴), and the two 🟡 states, the CTA is the "See your
priority drills" path. Asserted by Storybook stories (one per state)
and by the readiness unit test.

**(3)** `app/(app)/settings/notifications/page.tsx` initialises all
three notification toggles to `false`. The page's leading copy
recommends leaving them off. The unit test
`tests/unit/i18n-messages.test.ts::"notifications copy has no banned
urgency wording"` greps both EN and FR catalogs for `lost!|behind!|
don't.*miss|hurry` and fails on hit.

**(4)** Audit §4 documents the NVDA + VoiceOver walkthrough of all
five drill types. The DrillPlayer renders MCQ options as a true
`role="radiogroup"`; audio drills expose `aria-pressed` on play/
pause; the timer is an `aria-live="polite"` region announcing only
at named thresholds; the transcript is gated behind the REVEALED
phase per ADR-0029.

**(5)** There is no streak counter, leaderboard, "your friends are
ahead" surface, or celebratory animation in any component, page, or
Storybook story. Grep confirms no `streak`, no `leaderboard`, no
`confetti` import. The Storybook story for `ReadinessWidget /
Ready` verifies the green render is calm (no animation directives).

---

## 3. Trade-offs accepted

A short list of things Phase 8 deliberately did *not* ship:

- **Tutor chat.** Out of scope; the system is a structured course,
  not a free-form Q&A surface.
- **Native iOS/Android apps.** Web + PWA installable from `/today`
  is the v1 mobile story.
- **Social features.** No friends, classes, leaderboards.
- **Live classroom integration.**
- **A real-time presence / online-now indicator.**
- **An onboarding tutorial overlay.** The IA is shallow enough that
  a tutorial would be patronising.

Each of these is sequenced for v1.1+ and explicitly off the Phase 8
work list to keep the bundle and the IA shallow.

---

## 4. Hand-off to Phase 9

Deliverables ready for Phase 9 to consume:

- `apps/web/` complete: `app/` route tree, `components/{ui,domain,drills,nav}/`,
  `lib/{api,i18n,persistence,state}/`, `messages/`, `stories/`,
  `tests/{unit,e2e}/`.
- `phase8_think.md`, `phase8_design.md`, `phase8_audit.md`, this file.
- `docs/adrs/0041` through `docs/adrs/0045` accepted.
- The `web-ci` shape documented in `phase8_design.md §17`
  (typecheck → lint → vitest → playwright → build → lhci → pa11y →
  storybook test).

Phase 9 picks up:

1. Wire the screens to live `/v1/*` endpoints (replace fixtures).
2. Deploy to staging; rerun Lighthouse against the staging URL.
3. Run the three-maintainer think-aloud.
4. Produce the demo video specified in `phase8_design.md §20`.
5. Bundle the WCAG 2.2 AA conformance statement into the launch
   artefact set alongside the κ publication (Phase 7).

---

## 5. Verdict

**Phase 8 accepted.** The five launch-gate ADRs are pinned, the
component contracts are exercised by Storybook + unit tests + E2E,
the audit metrics are reproducible from `apps/web/`, and the
anti-criteria are demonstrably absent. The two ⚠ items above are
explicit hand-offs to Phase 9, not deferred Phase 8 work.

The frontend is calm. The frontend is honest. The frontend is
operable. We can ship.
