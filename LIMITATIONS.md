# LIMITATIONS

> **Read this before you read the README's "What it is" section.** A
> system that's honest about what it doesn't do is worth more than a
> system that over-promises. This page is the load-bearing honest
> page for `tcf-accel`.

If you are a candidate considering whether to use this system for
your TCF Canada preparation, read this whole document. If it tells
you something the system can't do for *you*, that is a feature, not
a bug — choose another path.

---

## 1. We do not guarantee a score

The TCF Canada is administered by France Éducation International
(FEI). The exam itself, the prompt set you draw on test day, the
quality of the audio in your test room, your sleep the night
before, your anxiety in the booth — none of these are under our
control. No prep system can credibly guarantee a score on this
exam, including this one.

What we *do* promise:

- A 12-week study plan grounded in the published Common European
  Framework guided-learning-hour estimates (we don't invent
  better-than-published gains).
- A readiness signal that **refuses to say you're ready** until
  two consecutive canonical-mock 🟢 sessions and all four skills
  reach posterior confidence.
- A clear-eyed credible interval on every NCLC estimate.

What we will not say, anywhere:

- "Pass guaranteed."
- "Score X or your money back."
- "9/10 of our users pass." (We are pre-pilot at v1.0; we don't
  have that data.)

---

## 2. We do not promise C2 (NCLC 11+) in 12 weeks from B1

The Common European Framework's guided-learning-hour estimates for
B1 → C2 cluster around 600–800 hours. 12 weeks × 2.5 h/day is 210
hours. The arithmetic doesn't work.

The system's *honest target band* is **NCLC 7 floor / NCLC 9
ceiling** for a learner starting at solid B1 in 12 weeks. We
verify this every release via the Phase 9 pedagogy audit
(`tests/pedagogy/launch_audit.py`); the `aggressive_B1_target_C2`
cohort is intentionally allowed to fail in our simulator, and the
planner is required to **honestly refuse** to project success for
it.

If you need C2-level skills for a specific reason (academic
admission to a French-language program; senior bilingual roles in
Canada), use this system for the NCLC 7–9 window and then move to
a more advanced path. We link some options in `LEARNER_GUIDE.md
§9`.

---

## 3. We can route a Deaf or hard-of-hearing candidate, but the TCF Canada CO is audio-only by FEI design

The Compréhension orale (CO) section of the TCF Canada is audio-
only. We cannot make the exam itself accessible — only FEI / IRCC
can.

What we *do* support:

- A "CE/EE/EO only" mode that hides CO from the diagnostic, the
  planner, and the mock exams. The readiness signal then gates
  on those three skills only.
- The Library page links to IRCC's accommodations process and to
  Canadian Deaf-advocacy organisations.
- The diagnostic UI surfaces the structural exam constraint
  before a CO drill begins (`LEARNER_GUIDE.md §8`).

What we *don't* do:

- We don't claim our system is "accessible to Deaf candidates"
  in a way that papers over the exam's structural constraint.
  This is a *structural exam issue*, not a system gap, and we
  say so. The honest framing belongs in your decision-making.

R-007 in `RISK_REGISTER.md` documents this.

---

## 4. Auto-scoring is not perfect

Our published Cohen's quadratic-weighted κ on EE writing
(against an LLM critic with a sample-of-30 expert spot-check) is
≥ 0.65. The published auto-scoring research clusters around κ
0.70–0.85 against human raters. We are below the research range
by design at v1.0 because:

1. We have not yet accumulated the 200-row expert-rater dataset
   that ADR-037 requires for a `κ_gold` claim. We have a small
   sample; we say so.
2. The calibration layer trades small amounts of κ for stability
   (the inflation guard, ADR-040, clamps over-eager LLM scores).

The published κ table lives in the README (per ADR-048). Until we
hit the v1.1 target of κ ≥ 0.75 against a 200-row expert set, we
ship with an **"experimental"** badge on rubric scores. R-010
documents the open work.

Practical implication for you as a candidate: treat the rubric
scores as the system's *opinion*, not an examiner's verdict. If
the system gives you 4/5 on `grammatical_accuracy` and you got
3/5 on a real practice exam, the gap is well within the κ
uncertainty.

The system surfaces this with:

- A confidence badge on every rubric score.
- The "Auto-feedback is approximate. A trained examiner could
  see more." disclaimer in the feedback panel (ADR-031).
- A link to italki / Alliance Française for a human review when
  you near booking time.

R-044 (`RISK_REGISTER.md`) tracks the related risk of
confidently-wrong qualitative feedback.

---

## 5. Pronunciation scoring is a coarse proxy

The EO pronunciation sub-score is derived from Whisper-fr
transcripts + Montreal Forced Aligner. Both tools have known
accuracy issues on non-Hexagonal French — Canadian, West-African,
North-African, Belgian accents are under-represented in the
training data.

ADR-031 (`docs/adrs/0031-pronunciation-signal-coarse-proxy.md`)
binds the project to never:

- Gate readiness on the pronunciation sub-score alone.
- Render the sub-score without the "coarse proxy" label.
- Penalise an accent as if it were an error.

R-002 (`RISK_REGISTER.md`) documents the open work to expand the
multi-accent evaluation set.

Practical implication: the pronunciation feedback is most useful
for *isolated phoneme misalignments* (your /ø/ collapsing to
/ə/, your final consonants surfacing where they should be
silent). It is *not* a substitute for a tutor who can hear your
prosody, hesitation patterns, and natural register.

---

## 6. We don't substitute for booking time with native speakers

The four-week production-skill arc in `LEARNER_GUIDE.md §5`
recommends booking conversation partners from Week 4 onward —
HelloTalk, Tandem, italki, Alliance Française. The reason is
simple: the EO section of the TCF Canada asks you to *converse
naturally* with an examiner; no automated drill can fully
replicate that pressure.

We provide:

- Speaking drills (`speaking_role`, `speaking_mono`, `eo_picture`,
  `eo_spontaneous`) calibrated to the EO rubric.
- Shadowing drills for prosody (ADR-030).
- Auto-scoring of recorded responses.

We don't provide:

- Real-time conversation.
- A human in the loop.
- Anxiety management beyond pacing the practice volume.

If your bottleneck is EO and your anxiety is high, the v1.0
system will help less than a hybrid path that includes a tutor.
We say so in the readiness widget when your EO posterior
plateaus despite practice volume.

---

## 7. The system is single-tenant

v1.0 is built for a single learner (or a self-hosted operator
running it for themselves and a small circle). It is not a
multi-tenant SaaS. There is no "tutor mode" or "classroom
console" in v1.0; both are on the v1.1 roadmap
(`docs/roadmap/v1.1.md`).

If you are a language school looking for a system to deploy for
your students at v1.0, the supported path is one container set
per learner — *not* shared. We don't claim to have hardened the
multi-user data-isolation surface beyond what the per-user-JWT
authorization tests cover, and we won't pretend otherwise.

---

## 8. Privacy posture

`local_only` is the default at the database layer (ADR-0017).
That means:

- ASR runs on the operator's machine (faster-whisper local model).
- LLM calls happen only when you opt in to a cloud LLM gateway
  (default: off). The opt-in surface tells you exactly what data
  leaves the machine.
- Logs do not contain learner text or audio (verified by
  `tests/unit/test_logging_no_pii.py`).

What we *don't* do:

- We don't run a hosted instance you can sign up for. v1.0 is
  self-hosted only. If you want to use the system, you (or your
  operator) run it on your own machine.
- We don't ship analytics. The `apps/web/` build has no
  third-party analytics scripts.

What you should do:

- If you self-host on a cloud VM, you are the data controller.
  Set up TLS at the proxy, follow `OPERATIONS.md §4` for the JWT
  secret rotation policy, and rotate your credentials on a
  schedule.

---

## 9. Cost of self-hosting

The system is OSS. Running it is not free. The honest cost
breakdown (`OPERATIONS.md §11`) at v1.0:

- **Local-only mode (privacy default)**: free, modulo your own
  electricity. CPU-only Whisper inference is feasible on any
  machine with ≥ 16 GB RAM; GPU is faster but optional.
- **Cloud LLM opt-in**: you pay the LLM provider directly. Phase
  7 cost-profiling estimates ~$0.30–0.80 per full EE/EO
  scoring session under our default prompts. R-005 documents the
  budget concern; the inflation guard (ADR-040) gates expensive
  re-calls.

A learner doing two scored mocks per week for 12 weeks under the
cloud opt-in: ~$10–25 in LLM costs. We document this so you can
budget honestly.

---

## 10. Things we deliberately do NOT have

The "what's missing" list, made explicit so you can pre-empt
disappointment:

- **No streaks, no leaderboards, no friend-comparison surfaces.**
  ADR-042 documents the no-gamification stance. Coercive UI
  patterns produce study under duress, not durable learning.
- **No notifications by default.** All three notification
  toggles (`apps/web/.../settings/notifications`) initialise to
  `false` (ADR-043). You can opt in; we won't ping you
  uninvited.
- **No celebratory animations on readiness 🟢.** The screen
  renders calmly. We are not trying to manipulate your dopamine.
- **No "your friends are ahead" or peer pressure.** v1 is solo
  by design.
- **No tutor chat / Q&A surface.** This is a structured course,
  not a free-form chatbot.
- **No native iOS / Android apps in v1.0.** The web app installs
  as a PWA from `/today`; that is the v1 mobile story.
- **No A1 / pre-B1 onboarding in v1.0.** The system assumes a
  baseline of B1; below that, the diagnostic recommends a
  foundation course first.
- **No DELF/DALF, no TEF Canada, no other exam in v1.0.** TCF
  Canada only. The v1.1 roadmap mentions parallel tracks; v1.0
  stays focused.

---

## 11. What to do if any of this is a blocker

You have options:

- **You need a guarantee or a tutor.** Book Alliance Française
  or an italki tutor. They can give you the human accountability
  this system doesn't.
- **You need C2.** Use this system for the B1 → NCLC 7–9 window;
  then move to a CAPES/DALF C2 prep program.
- **You're Deaf or hard-of-hearing and the CE/EE/EO routing
  isn't enough.** Contact IRCC accommodations directly; they
  have processes we cannot speak to.
- **Your bottleneck is EO + anxiety.** Pair this system with a
  human tutor from Week 1, not Week 4.
- **You need multi-tenant deployment for a school.** Wait for
  v1.1 or contact us about the design.

If none of those apply, and the honest target band of NCLC 7–9
in 12 weeks is what you're aiming at, the system is built for
you. Welcome.

---

## 12. How we keep this page honest

Every claim in this document is tied to a piece of code, a
test, or an ADR:

| Claim | Anchor |
|---|---|
| 12-week target band (NCLC 7–9) | `tests/pedagogy/launch_audit.py` |
| Honest refusal on C2 cohort | `tests/pedagogy/launch_audit.py::test_aggressive_cohort_is_honestly_refused` |
| Readiness 🟢 gating | `packages/sla/.../planner/readiness.py` + ADR-045 |
| No-bare-NCLC rule | `apps/web/eslint/no-bare-nclc.js` + Phase 8 evaluate §2 |
| `local_only` default | ADR-0017 |
| Pronunciation as coarse proxy | ADR-031 |
| Auto-feedback disclaimer | Phase 7 + ADR-031 |
| No gamification / no streaks | ADR-042, Phase 8 evaluate §2 |
| Notifications opt-in only | ADR-043 |

If you find a claim in the README or in the in-app onboarding
that contradicts a claim here, **file a bug** — the claim here
is the source of truth.
