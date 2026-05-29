# LEARNER_GUIDE

> The 12-week journey, week by week, with the system's expectations
> at each step. Pair with `LIMITATIONS.md` (what the system won't
> do) and the in-app `/today` view (what you do today).

---

## 0. Before you start

Read `LIMITATIONS.md`. If any of it is a blocker for you, use a
different path. If not, continue.

Confirm you're at B1 (independent user). If you're not sure, the
diagnostic in Week 1 will tell you. If the diagnostic puts you
below B1, the system will suggest a foundation course first; don't
fight the recommendation.

### Time budget

The default plan assumes **2.5 h/day, 6 d/week** for 12 weeks
(~210 h total). If you have less time, the planner adjusts and
the readiness window narrows accordingly. The minimum useful
budget is 60 min/day; below that, the system warns you that
NCLC 7 in 12 weeks is unrealistic.

### What you need

- A working microphone (for EO drills + the mock exam).
- A quiet 60-min slot for the canonical mock exam (one per
  week from Week 6 onward).
- Pen and paper for the EE (writing) sections — typing is
  allowed in drills, but you'll write by hand in the real
  exam.

---

## 1. Week 1 — Diagnostic and orientation

**Goal:** the system learns where you actually are.

You'll run:

1. The **diagnostic CAT** (~45 min). Adaptive MCQ across CO + CE
   + a short EE prompt + a short EO recording. Output: a 4-skill
   posterior.
2. The **planner setup** (~5 min). You confirm your target NCLC
   (7, 8, or 9), your exam date (within 12 weeks), and your
   daily budget. The planner generates a 12-week trajectory.
3. **2-3 days of low-pressure drills** to let the posterior
   tighten before the plan over-commits.

What you'll see:

- An NCLC posterior per skill, with a confidence flag (⚪ → 🟡
  → 🟢). Don't be surprised if you're ⚪ across the board on
  Day 1 — the confidence gate (40+ items, 3+ difficulty bands)
  is intentionally strict.
- A daily plan with explicit minutes per skill. The plan
  over-weights your bottleneck.

What to avoid:

- Don't take the diagnostic twice "to get a better number." The
  system uses the diagnostic to *initialise* the posterior; you
  rebuild trust through drills, not through re-tests.

---

## 2. Week 2 — Build the daily rhythm

**Goal:** establish a sustainable cadence.

You'll do, every day:

- ~10 min CO **shadowing** (ADR-030 reserves this). It's
  pre-decided; don't skip.
- Per-skill drill blocks per the plan. The mix varies daily —
  the planner rotates across drill types so you don't burn out
  on one format.
- **One review session** of yesterday's flashcards (FSRS-6
  scheduled).

What you'll see:

- Your posterior tightening; the confidence flag moving from
  ⚪ → 🟡 on at least 1–2 skills.
- Per-skill mean nudging upward (slowly — we use a conservative
  learning rate; under-promising is the right error direction).

What to avoid:

- Marathon sessions to "catch up." If you miss a day, just
  resume; the planner adapts.
- Skipping the production-skill blocks because they're hard.
  EE and EO are *exactly* where the system's bottleneck
  weighting is doing its work.

---

## 3. Weeks 3–4 — Production-skill push

**Goal:** start producing in volume; let the EE/EO drills do
their work.

The planner increases production-skill minutes (β_EE = 1.4,
β_EO = 1.5 per ADR-027). You'll see more writing drills, more
speaking drills, fewer pure-reception flashcard sessions.

What to do:

- **Book a conversation partner.** HelloTalk, Tandem, italki,
  Alliance Française — any of them work. Aim for one 30-min
  conversation per week, scaling to two by Week 8. The system
  cannot replicate this, and your EO posterior will plateau
  without it (this is honest; we say so in the readiness widget
  if it happens).
- Run your **first mid-arc mock** in Week 4 (training mode —
  the planner schedules it). This is a no-pressure shape-check,
  not a readiness mock.

What you'll see:

- Auto-scored EE rubrics: per-criterion scores, error
  annotations, register feedback. Treat them as the system's
  opinion (κ ≈ 0.65–0.75) — useful, not gospel.
- A "pronunciation" sub-score on EO with the **coarse proxy**
  label. Use it for individual phoneme issues; ignore it for
  prosody (use a human for prosody).

---

## 4. Weeks 5–6 — Calibration and gap-narrowing

**Goal:** all four posteriors at `confident=True` (🟢 flag).

By the end of Week 6:

- All four skills should clear the confidence gate (n_obs ≥ 40,
  variance ≤ 0.4, ≥ 3 difficulty bands).
- The Insights page shows per-skill posteriors with credible
  intervals.
- The first **canonical mock** lands at the end of Week 6 — this
  one *is* a readiness mock, and the planner reschedules around
  the result.

If a skill remains ⚪ or 🟡 after Week 6, the planner adds
diagnostic-style probe items to that skill until the confidence
gate clears. This is honest: we'd rather take another week than
ship a confident-but-wrong projection.

---

## 5. Weeks 7–9 — Mock cadence ramps up

**Goal:** two consecutive 🟢 canonical mocks.

The mock cadence (ADR-033, ADR-034):

- Weeks 7–8: one canonical mock per week.
- Week 9: two canonical mocks (Mon + Fri).
- Weeks 10–11: 3 mocks/week if you're chasing 🟢 readiness.

What you'll see:

- A `MockSectionScore` per section, with calibration confidence.
- A drill-mock posterior-divergence alert (ADR-034) if your
  drill posterior and your mock posterior disagree by > 1 NCLC.
  This is a *signal*, not a failure — it tells you your
  practice doesn't match exam conditions, and the planner
  rebalances.

What to avoid:

- Don't book the real exam until two consecutive canonical mocks
  are 🟢 AND all four skills are 🟢. The readiness widget
  (ADR-045) refuses to show the booking CTA otherwise.

---

## 6. Weeks 10–11 — Pre-exam discipline

**Goal:** stabilise; don't over-train.

By now you should be:

- 🟢 on all four skills.
- 🟢 on at least two consecutive canonical mocks.
- Booking the exam.

What to do:

- **Reduce volume by ~20%** in the final week. Cramming the day
  before is a false economy.
- **Sleep**. Boring advice. True advice.
- Do **light shadowing + light vocab review** the day before;
  no new prompts, no new rubrics.

What to avoid:

- A "Hail Mary" extra mock the day before the exam. If you
  haven't built it by now, you won't build it tonight.

---

## 7. Week 12 — Exam week

**Goal:** show up.

The day of:

- Eat. Hydrate. Bring two pens.
- The CO section uses the venue's audio. If it's bad, raise
  your hand; FEI knows this can happen.
- For EE: handwritten. You've been typing in drills, but the
  exam is on paper. Practise once with paper in Week 11 if you
  haven't.
- For EO: the examiner is a human. Make eye contact. Speak in
  full sentences. The cohort that says "I felt like I bombed
  it" often scores fine; cohort that says "I had a great
  conversation" sometimes scores middle. Test-day perception is
  unreliable.

The day after:

- Walk away from the system for a day. Come back to log how it
  went (the system has a `/post-exam` survey; the data feeds
  into the planner's calibration for future learners).

---

## 8. The CE/EE/EO-only path (Deaf and HoH candidates)

If you're using the system without CO:

- The diagnostic skips CO; the planner re-weights the three
  remaining skills (the allocator behaves the same as the "CO
  already at target" case).
- Mock exams skip CO; the readiness widget gates on two
  consecutive CE/EE/EO mocks 🟢.
- The Library page links to IRCC's accommodations and to
  Canadian Deaf-advocacy organisations — those processes are
  outside this system.

The structural reality: the TCF Canada CO section is audio-only
by FEI design. This system cannot make the exam itself
accessible. `LIMITATIONS.md §3` is the long form.

---

## 9. After v1.0 — where to go next

If you got the NCLC band you needed: congratulations.

If you need to push further (NCLC 10+, DELF C1, DALF C2):

- **DELF C1 prep**: Alliance Française has structured courses.
  This system does not cover DELF.
- **DALF C2 prep**: even more structured. Multi-month commitment.
- **Conversation maintenance**: Lingoda, italki, HelloTalk —
  keep speaking. NCLC degrades without practice.

If you're a self-hoster and you'd like to contribute back:
`CONTRIBUTING.md` describes the dev loop. We particularly need
expert raters for the κ gold-set acquisition (R-010).

---

## 10. The honest closing note

This system is not magic. It is a 12-week scaffolded course that
has been audited for honesty: it won't lie to you about what
you can do in 12 weeks, what an auto-scored rubric tells you,
or what a Deaf candidate can expect from the CO section.

If you do the work — 2.5 h/day, 6 d/week, on-plan — and the
diagnostic placed you at a real B1, you have a realistic shot
at NCLC 7–9 in 12 weeks. That's the deal. Read
`LIMITATIONS.md` if you haven't.

Bonne chance.
