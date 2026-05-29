# Phase 5 — THINK

> Phase 5 (`05_PRACTICE_AND_DRILLS.md §1`) — the drill engines and the
> pronunciation pipeline that turn the calibrated item bank (Phase 3) and
> the learner model (Phase 4) into the surface a learner actually
> *touches*. The phase where pedagogical doctrine meets a UI. Four
> load-bearing decisions; for each, the option space, the chosen path,
> and the empirical signal that would flip the decision. Date:
> 2026-05-28.

---

## 0. Frame

Phases 1–4 stood up the spine: contracts, schema, bank, scheduler,
estimator, planner. Nothing the learner ever sees. Phase 5 is the first
phase whose output a human will *use* — a CO MCQ that plays once, a
shadowing drill that records their voice, a writing task with a
counting widget, an EO simulator with a TTS examiner. Three things
about that change the cost shape relative to Phases 2–4:

1. **The surface is the doctrine.** Master prompt §2.1 lists eight SLA
   principles. Phase 4 implemented the *scheduling* consequences
   (FSRS, LECTOR, allocator). Phase 5 implements the *interaction*
   consequences — Krashen-i+1 by drawing items at the posterior mean,
   pushed output by gating session-complete on word/minute floors,
   single-play because that is what the exam does. If a drill ships
   that lets a learner re-listen during the question, the system has
   undone its own pedagogy at the UI layer; the well-calibrated
   estimator behind it now reports a confident, wrong number. The harm
   shape composes with R-004 (over-prediction), not just R-???.
2. **Phase 5 is the first phase that *records the learner*.** Every
   spoken interaction produces a waveform. Every written interaction
   produces a paragraph the learner may not want stored. ADR-017
   (privacy-default-local-only) is a Phase 1 commitment that has been
   cheap until now because nothing has been recorded. Phase 5 makes it
   load-bearing — every storage and processing decision in the
   pronunciation pipeline either honors ADR-017 or breaks it. There
   is no middle.
3. **Phase 5 makes its first claims the learner will believe.** The
   pronunciation score has the same harm shape as the NCLC point
   estimate (R-004): a confident, wrong number degrades the learner's
   self-model and, downstream, their plan. Phase 4 solved this for
   NCLC with the `confident=False` gate (ADR-025). Phase 5 inherits
   the doctrine: any signal we surface must either *be* calibrated or
   be *structurally marked* as a coarse proxy that the UI cannot
   accidentally reify. Phoneme-error-rate is the canonical example.

The questions below are the ones whose architectural shape, once
chosen, the rest of Phase 5 cannot back out of without rewriting
several drills. Numeric thresholds, timer constants, and per-drill UX
choices are deferred to `phase5_design.md` (see §3 of this doc).

---

## 1. The four hardest questions

### 1.1 How do we enforce exam-realistic CO single-play without breaking accessibility?

The TCF Canada CO plays each item's audio **once**, and the exam-day
failure mode of a learner who has only practiced with replay-enabled
drills is well documented (master prompt §2.1.1, §1.4 of the spec).
Therefore the *default* drill mode must enforce single-play —
specifically, the audio element must not expose scrubbing, the
keyboard shortcut must not seek, the buffer must not be persistable,
and the "review" mode that *does* allow replay must be reachable only
*after* the answer has been submitted. Building this is straightforward.

The cost shape is at the accessibility seam. WCAG 2.2 (master prompt
§5.5; Phase 8 gate criterion) requires that auditory information be
available via an equivalent text alternative — typically a transcript.
A transcript shown *during* the question defeats the drill (the
learner reads instead of listens). A transcript shown only *after*
the answer leaves a Deaf or hard-of-hearing user unable to attempt the
drill in the first place. The naive resolution — "always show the
transcript, always allow replay" — re-creates the failure mode the
single-play rule exists to prevent.

**Options:**

| Option | Single-play | Accessibility | Cost |
|---|---|---|---|
| **(a)** Hard single-play, no transcript ever; replay locked behind submission | Maximally exam-aligned | Deaf/HoH users cannot use CO drills | Violates WCAG 2.2 SC 1.2.1 (audio-only alternative). |
| **(b)** Soft single-play; transcript always shown, "muscle memory" warning | Maximally accessible | Defeats the drill for sighted hearing users; degrades to a CE drill in disguise | Trains the wrong skill; downstream NCLC estimator over-predicts CO. |
| **(c)** Single-play default + per-user accessibility profile that swaps to a transcript-mode drill that **rebrands** as a vocabulary/lexical drill, not as a CO drill, and is **excluded from the CO posterior update** | Single-play preserved for the population the exam tests | Deaf/HoH users have an equivalent productive surface, but it produces a different `Interaction.skill` (`lexical`, not `CO`) | Two drill paths; planner must route by profile; the Phase 4 posterior never receives `CO` interactions from users who cannot do single-play CO, which is the right answer — we cannot honestly predict their CO score from a different drill. |

**Pick (c).** The load-bearing reason is that the alternative — letting
the same drill produce `CO` interactions whether or not the audio was
heard — collapses the meaning of the CO posterior. A CO estimate built
on a mix of "heard once" and "read transcript twice" interactions is
not a CO estimate; it's a register-confused average that the
allocator will then over-allocate against. Better to ship two surfaces,
two `Interaction.skill` values, and an honest UX message:

> "This drill measures lexical and reading comprehension on
> conversational French. It is not a substitute for CO and does not
> contribute to your CO NCLC estimate. For Deaf/HoH learners,
> see the [TCF Canada accommodations page] for the official process."

This decision is also why §2.7 of the spec ("Skip-the-drill alternative
for Deaf/HoH users that routes them only to CE/EE/EO") needs to be
sharpened in the design doc: the routing is not "skip CO"; it is "do
the lexical drill, do not pretend it is CO."

A second-order consequence: the keyboard-only path for the *default*
drill must not let a sighted keyboard-only user accidentally seek the
audio. The space-bar plays/pauses (cannot be removed; expected
keyboard contract), but the `<audio>` element is rendered with
`controls={false}` and a custom React control that does not bind to
arrow-key seek. The "replay" affordance appears only after
`POST /v1/session/{id}/answer` returns 200.

### 1.2 What is the structural guarantee that pronunciation feedback is never reified as evaluative?

The pronunciation pipeline (§2.6 of the spec) produces a number — PER,
per-phoneme accuracy, prosody score — that *will* show up on a screen.
The spec acknowledges this in the UX caveat: "Pronunciation feedback
is a coarse signal. A human examiner judges intelligibility, accent
acceptability, and prosody holistically. Use this signal for trends,
not for final readiness." The question is whether that caveat is
*decorative* (a tooltip the user dismisses) or *structural* (a property
of the type the UI cannot remove without deleting a contract).

Phase 4 solved the analogous problem for the NCLC point estimate with
ADR-025: every `SkillPosterior` ships with a credible interval, the
`confident` flag is launch-blocking, and `compute_readiness` is
*incapable* of returning 🟢 when any predicate fails. The structural
guarantee, not the UI convention.

**Options:**

| Option | Shape of the contract | Cost |
|---|---|---|
| **(a)** Decorative caveat: pronunciation score is a `float`; the UI puts a tooltip next to it | Cheap; no API churn | One careless UI engineer (or one A/B test) removes the tooltip; the harm shape returns; the system has no recourse. |
| **(b)** Score is bucketed (no number, only `weak`/`fair`/`strong`); the UI cannot show a number | Cheap; structurally prevents "85%" reification | The signal is *too* coarse to drive the planner (the planner needs a continuous value for §2.6's rubric integration). We'd lose the diagnostic capacity. |
| **(c)** `PronunciationSignal` is a Pydantic model with `score: float`, `signal_kind: Literal["coarse_proxy"]`, and a required `disclaimer_version: str` field that the UI must render adjacent to the score; serializers refuse to emit the score without the disclaimer field; the Phase 7 rubric consumes `score` but the surfaced UI consumes a separate `display_label: Literal["weak","fair","strong","insufficient_data"]` derived from the score | Structural at the contract layer | Two surfaces (planner / UI) for one number; the discipline is the *separation*. |

**Pick (c).** The load-bearing reason is symmetric to ADR-025: a
future contributor cannot "simplify" the contract without deleting an
explicit field. The planner reads `PronunciationSignal.score`; the UI
reads `PronunciationSignal.display_label`; the two are computed from
the same model, but they are not the same field, and a UI that wanted
to surface the raw score would have to (i) reach past `display_label`,
(ii) ignore `signal_kind`, and (iii) suppress `disclaimer_version`.
That is the right level of friction. The new ADR (ADR-031 in the spec)
locks this in.

A consequence the design doc must commit to: when PER is computed but
the underlying audio is sub-2-seconds, ASR confidence is below a
floor, or the canonical phoneme sequence is unavailable for the
prompt's reference text, `display_label` becomes `insufficient_data`
and the score does not contribute to the planner. The Phase 4
estimator's same refuse-to-predict posture applies here: when in
doubt, do not predict. The shadowing drill in particular will produce
many short-utterance interactions that fail the floor; this is
expected.

A subtler consequence: per-phoneme accuracy in the UI (the spec's §2.6
"per-phoneme accuracy" field) is the most reifiable surface. We do
not show a phoneme-by-phoneme heatmap in v1, because the unit of
intelligibility is *not* a single phoneme — it's a syllable or word in
context. We surface phoneme-level signal only as an aggregate (e.g.,
"vowel nasals: needs work") with the same disclaimer scaffolding.

### 1.3 Where does learner audio live, and what crosses the network?

Phase 5 records the learner. ADR-017 (Phase 1, master prompt §6.4)
commits the system to a **privacy-default-local-only** posture: by
default, no learner-generated audio leaves the operator's machine.
Every drill in §2.2 (shadowing), §2.5 (every EO drill), and the
pronunciation pipeline in §2.6 records a waveform. The naive choice —
"send the audio to a cloud Whisper endpoint" — breaks ADR-017 silently
and is the single largest privacy regression we could ship.

The Phase 5 question is not "should we honor ADR-017" (we must) but
*how* — which components can run locally, which require a network
boundary, and what the operator's escape hatch looks like for power
users who explicitly opt in to cloud ASR for quality.

**Options:**

| Option | What runs locally | What crosses the network | Cost |
|---|---|---|---|
| **(a)** Cloud-default: Whisper-large-v3-french via a hosted endpoint; MFA via a hosted service | (nothing) | Every utterance | Best ASR/MFA quality; violates ADR-017; learner waveforms become a third-party data flow we cannot guarantee deletion of. |
| **(b)** Local-only, no escape hatch: Whisper-large-v3-french as a local Python process; MFA local; the entire pronunciation pipeline is local | Everything | (nothing) | Honors ADR-017 maximally; CPU-only Whisper-large is ~3× real-time on consumer hardware (master prompt §8), so a 3-min EO Task 1 produces ~9 min of wait; UX-degrading. |
| **(c)** Local-default + per-operator opt-in cloud bypass: ships with local Whisper-large-v3-french and MFA, exposes an opt-in env var (`TCF_ACCEL_ASR_BACKEND=cloud:litellm` or similar) that routes through the existing LLM gateway (ADR-009), with a startup banner naming the consequence; the *learner* never makes this choice — only the operator | Default: everything; opt-in: nothing | Opt-in: utterance audio + transcript | Two-mode pipeline; the opt-in is a deliberate operator action, the default is the doctrinal one; satisfies ADR-017 and the spec's §1.4 "be modest about pronunciation scoring" because the local path is the canonical reference. |

**Pick (c).** Load-bearing reasons:

1. **The repo's posture is the default.** If the default required a
   cloud key, every contributor's first clone would either fail or
   silently regress privacy. The default is local.
2. **The operator owns the deviation.** Cloud ASR is plausibly the
   right choice for a power user with a fast network and no privacy
   concern; we do not pretend otherwise. The choice is *theirs*, made
   once at deploy, and it is loud (startup banner + env var).
3. **The Phase 4 / Phase 7 calibration is against the local
   pipeline.** Phase 7's auto-scorer is calibrated against
   Whisper-large-v3-french + MFA on a held-out set. The opt-in cloud
   path may have different latency and slightly different WER; we do
   not re-calibrate Phase 7 against it. The operator who opts in is
   accepting drift from the calibrated path. We document this
   explicitly.

**Concrete consequences** the design doc must commit to:

- **No learner waveform is persisted by default.** Audio is captured
  in-memory, run through Whisper / MFA, and dropped after the
  resulting `Interaction` row is written. The `Interaction.audio_path`
  field is `None` by default. (A separate operator-opt-in stores
  waveforms under `data/` for the operator's own review; never
  uploaded; gitignored per Phase 1 I5.)
- **No learner text crosses the network by default.** EE auto-scoring
  (Phase 7) runs locally; only when the operator opts in to a
  cloud LLM via the existing LiteLLM gateway (ADR-009) does
  written learner text leave the box. The opt-in surface for EE is
  the same one as ASR — one operator decision, two consequences,
  documented together.
- **The pronunciation pipeline's storage is content-addressed, not
  user-addressed.** The MFA alignment lattice for an utterance is
  keyed by `sha256(waveform)` not by `user_id`. Two learners who
  produced acoustically-identical waveforms (vanishingly unlikely
  but well-defined) would share the cache row. This is a privacy
  posture, not just an optimization.
- **Cloud-opt-in is not a per-drill setting.** It is a deployment
  setting. There is no "try cloud just this once" button in the
  learner UI — that would create a per-interaction privacy decision
  for someone who cannot consent meaningfully under time pressure.

### 1.4 Is the 80/20 drill/exam-shape split a hard gate, a soft nudge, or both?

Section 1.3 of the spec asserts the 80/20 split between rich-feedback
drills and feedback-withheld exam-shape sessions, and the planner
"force-converts the next session to exam-shape" if a learner has been
doing only drills for seven days. ADR-028 locks the policy. The Phase 5
question is *how forcefully*.

The tension: too soft, and the system reproduces the failure mode it
exists to prevent (learners who have only practiced with feedback
build a self-model that does not survive exam day). Too hard, and the
system becomes paternalistic in a way master prompt §2.4 explicitly
warns against — refusing to let the learner work on their stated weak
spot is *not* the same risk shape as refusing to let them coast on
their strength (§2.1.5). The system is allowed to be opinionated
about *what skill to allocate time to*; it is on less solid ground
when it overrides the *shape* of practice.

**Options:**

| Option | Enforcement | Cost |
|---|---|---|
| **(a)** Soft nudge: dashboard suggests exam-shape; learner can ignore indefinitely | Maximally autonomous | The doctrine the system was built on is now a toolbar tip; the failure mode returns at scale; we cannot make a master-prompt-grade claim of exam alignment. |
| **(b)** Hard gate: on day 8, the only session the planner will start is exam-shape; the drill catalog is read-only until the exam-shape session completes | Maximally enforced | Adversarial vs the learner; one bad UX moment (learner only has 20 min, exam-shape needs 60+) and trust collapses. |
| **(c)** Hard *floor* + soft *cadence*: the planner refuses to start a drill session if the rolling 7-day exam-shape time has been zero (the hard floor — one exam-shape session per week, minimum), but otherwise nudges via dashboard for the 80/20 split. The floor is dismissable once per week with a confirm dialog ("I understand this is the wrong call; remind me Friday"); the dismissal is logged so the audit can flag chronic dismissals. | Enforces the doctrine where it most matters (no zero-exam-shape weeks) without becoming a gate on every session | Two policies (floor + nudge) to maintain; the dismissal log is a privacy-adjacent surface and must respect ADR-017 (it is local-only state). |

**Pick (c).** Load-bearing reasons:

1. **The failure mode is the long tail of zero, not the 75/25.** A
   learner doing 75/25 instead of 80/20 still gets exam-shape
   practice. A learner doing 100/0 has built no exam-day skill at all.
   The hard component should target the catastrophic-mode boundary
   only.
2. **Dismissal-with-confirmation is calibrated friction.** It
   communicates the doctrine, it costs the learner a moment, but it
   does not refuse them. The audit catches abuse.
3. **The audit surface is local-only.** The dismissal log is part of
   the operator's local `data/` and is the operator's to inspect.
   This composes with §1.3 above.

A consequence the design doc must commit to: the hard floor's
boundary is `rolling_7d_exam_shape_minutes >= EXAM_SHAPE_FLOOR_MIN`
where `EXAM_SHAPE_FLOOR_MIN` defaults to 30 (one mock half-section).
This is a tunable threshold the operator can raise but not lower
below 20 — twenty minutes is approximately one full CE half-section
under exam pace, the smallest unit that resembles exam shape.

---

## 2. What would change our mind

These are the empirical signals that, if observed, would warrant
revisiting the decisions in §1. Vague triggers do not count.

### 2.1 On accessibility-by-rebranding (1.1)

- **Deaf/HoH usage data shows the lexical alternative is treated as a
  CO substitute** — e.g., qualitative feedback says "I'm using your
  CO drills and they're working." This means the rebranding has
  failed at the UI level even though the contract is correct. We'd
  push harder on the labeling (a banner, not a tooltip) and consider
  routing the lexical drill out of the CO module entirely (it lives
  under "Reading & Vocabulary" instead of under "Listening").
- **The CO posterior for the default-mode population diverges from
  exam-day outcomes by > 0.5 NCLC** — the calibration we *thought* we
  preserved by routing alternative drills elsewhere has not in fact
  been preserved. We'd audit whether the default-mode keyboard path
  is leaking replay capability (e.g., via screen-reader audio
  controls) and tighten the audio element implementation.
- **A WCAG 2.2 audit finds the single-play default fails SC 1.4.2
  (Audio Control)** in a way the lexical-alternative route does not
  fix. This is an open question and we'd want a real audit verdict;
  the lexical-alternative route is our best understanding of the
  intent of 1.2.1 / 1.4.2 but is not a substitute for an external
  review.

### 2.2 On the structural pronunciation contract (1.2)

- **A UI engineer surfaces `PronunciationSignal.score` as a number in
  a card** despite the `display_label` separation. The contract held;
  the discipline did not. We'd add a runtime check in the
  serializer (`@model_validator` that refuses to serialize without
  the `display_label` field included) and a lint rule that
  disallows direct `.score` access outside `packages/sla/scoring`
  and `apps/worker/tasks/score_*`. The contract becomes harder to
  bypass.
- **Phoneme-level signal turns out to be more reliable than the
  bucketed `display_label` suggests** — e.g., correlation with
  expert-rated pronunciation > 0.8 on a held-out set. We'd revisit
  whether the bucketing is too aggressive (4 buckets instead of 3?
  a continuous strip with no number?) but we would *not* surface the
  raw float; the structural guarantee is the floor.
- **Phoneme-level signal turns out to be much *less* reliable than
  assumed** — correlation < 0.4. We'd downgrade the surfaced signal
  to two buckets (`enough_signal`/`not_yet`) and remove
  pronunciation from the rubric scoring entirely until Phase 7
  recalibrates against an MFA replacement (e.g., Whisper-based
  alignment).

### 2.3 On local-default audio + opt-in cloud (1.3)

- **Whisper-large-v3-french local-CPU latency exceeds 10× real-time
  on a target-class machine** (master prompt §8 documents the
  hardware baseline). The 9-minute wait for a 3-minute Task 1
  recording is no longer a paper-cut; it is a UX gate. We'd consider
  shipping a smaller default (Whisper-medium-fr) for fast feedback
  with a "high-accuracy re-score" worker that runs in the background,
  rather than relaxing the local default.
- **A privacy near-miss** — e.g., a contributor commits a code path
  that uploads audio bytes by default without the operator-opt-in
  banner. This is the failure shape ADR-017 exists to prevent;
  we'd treat as a P0, harden the lint (a `network` capability
  test in CI that blocks if `httpx`/`requests` are called from the
  ASR module without the opt-in flag), and document the catch.
- **Operators report that the cloud-opt-in is *too* hidden** — they
  did not realize the option existed and accepted slow local
  inference. We'd raise the startup banner's discoverability (a
  one-line note in the install README's "performance" section)
  while keeping the per-deploy granularity.

### 2.4 On the 80/20 floor (1.4)

- **The floor is silently dismissed > 50% of weeks** across the
  user base. The "calibrated friction" hypothesis is wrong; the
  dismissal is too low-effort. We'd raise the friction (e.g.,
  require the learner to type the words "I understand this is the
  wrong call") or move the floor closer to a gate (option (b)
  above). We do *not* lower the floor — the long-tail failure mode
  is the point.
- **Chronic-dismissal learners' exam-day outcomes match
  non-dismissing learners'**. The doctrine is wrong, or the
  exam-shape practice is doing less than we believed. We'd
  re-examine the Phase 6 mock-exam composition and the audit's
  exam-day calibration before relaxing the floor.
- **The floor blocks a learner who genuinely could not sit a 30-min
  block this week** (medical, work emergency). The current
  dismissal mechanism handles this; if it becomes a recurring
  pattern across the user base, we'd add a one-week-deferral
  mechanism that does *not* count as a dismissal but rolls the
  floor's window forward.

---

## 3. Adjacent decisions deferred to design (`phase5_design.md`)

These are real choices, but they are tunable parameters of the chosen
architecture rather than load-bearing pivots. The design doc locks
specific values and the rationale; here we record what is up for
binding.

- **CO exam-pace timing.** 35 min / 39 items ≈ 53.8 s/item; the spec
  rounds to ~54 s. The actual exam is item-paced (each item has its
  own clock determined by audio length + answer window), not a uniform
  53.8 s. The design doc commits to a per-item budget = `audio_length
  + 20 s answer window`, with the 35-min total as a hard ceiling.
- **Shadowing WPM target band.** 0.85–1.10 of source WPM (spec §2.2).
  This is the prosody-acquisition literature's typical range; we
  lock the values and the calibration set in design.
- **Dictation error classification.** Five categories in the spec
  (spelling, missing, extra, agreement, register). The classifier is
  rule-based on the alignment between learner transcription and
  ground truth; the *register* class is the only ML-flavored one and
  uses the Phase 3 register classifier. Locked in design.
- **CE skim-and-scan exposure time.** 30 s (spec §2.3). The
  literature on skimming-under-time-pressure suggests 25–45 s for
  passages of 150–250 words; 30 s is the midpoint and matches the
  exam's effective skim time. Tunable per release.
- **EE word-count tolerance.** 80–110% (spec §2.4) per FEI guidance.
  The penalty function is a piecewise linear: 0 inside the band,
  −1 pt per 5% outside, capped at −4. Locked in design.
- **EE connector density target.** ≥ 1 / 25 words across ≥ 4
  categories (master prompt §1.4). Drill ramps to this; the rubric
  scorer (Phase 7) evaluates against it. Locked in design.
- **EO prep / production timings.** 30 s prep + 90 s production
  (picture description), 5 s + 60 s (spontaneous opinion). These
  approximate the exam's own pacing. Locked in design.
- **EO follow-up LLM model.** Defaults to the LiteLLM gateway's
  current default (Claude Sonnet 4.6 per ADR-009). The follow-up
  prompt is templated; the LLM choice does not require a Phase 5
  ADR.
- **Pronunciation pipeline insufficient-data thresholds.** Utterance
  < 2 s, ASR mean-token-confidence < 0.5, or canonical phoneme
  sequence missing → `display_label = "insufficient_data"`. Locked
  in design.
- **`PronunciationSignal` field layout.** The Pydantic model with
  `score`, `signal_kind`, `disclaimer_version`, `display_label` per
  §1.2 above. Schema bump: `SCHEMA_VERSION` to `0.4.0` (additive
  but new required fields).
- **Cloud-opt-in env var.** `TCF_ACCEL_ASR_BACKEND` (default
  `local`), `TCF_ACCEL_LLM_BACKEND` (already exists per ADR-009),
  with a single startup banner that names both. Locked in design.
- **Exam-shape floor threshold.** `EXAM_SHAPE_FLOOR_MIN = 30`
  minutes / rolling 7 days, floor of 20. Tunable per release.
- **Dismissal-log retention.** Local-only, 90 days, then deleted
  unless the operator opts to persist. Locked in design.
- **Drill-diversity audit floor.** ≥ 4 drill types per module over
  100 sessions (spec §4). This is a planner-side audit, not a Phase
  5 invariant per se; the planner's selection logic (Phase 4)
  satisfies it as a consequence of the bottleneck allocator
  exploring multiple drill kinds. Locked in design.

The four new ADRs to be drafted in design:

- **ADR-028**: 80/20 drill / exam-shape split, with a hard floor and
  soft cadence (the policy from §1.4).
- **ADR-029**: Single-play default for CO; lexical-alternative drill
  for accessibility produces a different `Interaction.skill` and does
  not contribute to the CO posterior (the policy from §1.1).
- **ADR-030**: Mandatory 10 min/day shadowing in default plans
  (spec §1.4 / §2.2; the planner enforces).
- **ADR-031**: `PronunciationSignal` structural contract with
  `score`/`display_label` separation and required `disclaimer_version`
  (the contract from §1.2).

---

## 4. Out of scope for Phase 5

Phase 5 ships the drill engines and the pronunciation pipeline. It
does *not* ship the things below, and the design doc must not drift
into them.

- **Full EE auto-scoring rubric.** Phase 7. Phase 5 wires the
  pipeline (audio → ASR → MFA → PER → `PronunciationSignal`) and
  emits the `Interaction` rows; Phase 7 implements the rubric that
  consumes them. The hand-off is the `Interaction` payload schema.
- **Full EO rubric scoring.** Phase 7. Same shape — Phase 5 wires the
  pipeline, Phase 7 scores.
- **Mock-exam composition.** Phase 6. Phase 5 ships *drills*; a
  drill session is one drill type at a time. A mock-exam session is
  a multi-module interleaved composition; that's Phase 6.
- **Front-end polish.** Phase 8. Phase 5 ships drill stubs sufficient
  for keyboard / a11y audit; Phase 8 polishes typography,
  motion, mobile chrome.
- **Item generation.** Phase 3. Phase 5 consumes the bank as-is. If
  a drill needs items the bank does not have (e.g., minimal-pair
  audio for accent discrimination), we either (a) generate them in a
  Phase 3 follow-up under the Phase 3 quality gate, or (b) defer
  the drill. We do not author items inside `packages/sla/drills`.
- **Per-user FSRS optimization.** ADR-023 defers this; Phase 5
  honors the deferral.
- **Nightly IRT refit.** Spec §3 lists `apps/worker/tasks/score_*`.
  The *refit* job is a separate task and is gated on Phase 5's
  `Interaction` rows reaching a sufficient volume; the design doc
  pencils in the worker shape but does not require the volume.
  Reference: `phase4_think.md §6`.
- **Telemetry over the network.** ADR-017. Phase 5 emits structured
  logs locally; cloud-attached telemetry (Sentry, Honeycomb) is an
  operator opt-in inherited from Phase 1.
- **EO TTS model selection beyond the master-prompt default.** The
  spec §1.5 chose XTTS-v2; that decision stands. Phase 5 ships the
  pipeline against XTTS-v2 and the prompt-library shape; a
  voice-quality A/B vs other TTS is a Phase 8 / post-launch
  exercise.
- **The auto-scorer's "lowest sub-criterion" identifier.** Spec §2.5
  Repair-After-Feedback drill needs the Phase 7 scorer to identify
  the lowest-scoring sub-criterion. Phase 5 ships the drill's *shell*
  (the micro-drill catalog, the routing rule) and stubs the
  identifier with a placeholder that picks at random across the
  rubric criteria; Phase 7 swaps the stub for the real identifier.
  The hand-off is a typed interface.

---

## 5. Phase 5 invariants going into design

These must hold during and after Phase 5, forever:

1. **The CO default drill is single-play.** Audio elements are
   rendered with `controls={false}`, scrubbing is not bindable, and
   the replay affordance is gated on `POST /v1/session/{id}/answer`
   having returned. Enforced by component-level tests +
   keyboard-walkthrough audit (spec §4).
2. **A drill that runs in the accessibility-alternative mode emits
   a different `Interaction.skill`** and does not contribute to the
   posterior of the skill it visually resembles. Enforced at the
   `Interaction` write path; a property test asserts that no row
   with `drill_mode=accessibility_lexical` has `skill='CO'`.
3. **Every `PronunciationSignal` carries `signal_kind="coarse_proxy"`
   and `disclaimer_version`.** Serializer refuses to emit otherwise.
   The UI consumes `display_label`, not `score`, outside the
   planner / Phase 7 scorer modules.
4. **No learner audio is persisted to disk by default.** The
   `Interaction.audio_path` field is `None` unless the operator
   explicitly opted into local audio retention. Enforced at the
   audio pipeline entry point; a property test asserts that a
   default-mode drill session writes zero bytes to `data/`.
5. **No learner audio or text crosses the network by default.**
   Local Whisper, local MFA, local LLM (when present) for EE
   feedback; cloud opt-in is an operator-deploy decision, never a
   per-interaction one. CI capability test enforces.
6. **The exam-shape floor is enforced.** `rolling_7d_exam_shape_minutes
   >= EXAM_SHAPE_FLOOR_MIN` is checked at the
   `POST /v1/session/start` path before opening a drill session;
   below-floor returns `409 Conflict` with `next_action="exam_shape"`.
7. **Every drill produces a typed `Interaction` row.** The row's
   schema is the contract Phase 4's estimator consumes; no drill
   ships without a passing round-trip test that the `Interaction`
   validates against `Interaction.model_validate` and is consumed by
   the estimator without raising.
8. **Phase 2 / Phase 3 / Phase 4 contracts hold.** No `Item`
   schema change. No `SkillPosterior` schema change. No new
   required field on `Interaction` without a `SCHEMA_VERSION` bump.
   The Phase 5 schema bump is `0.4.0` (additive: `PronunciationSignal`
   appears as a new type referenced from a new optional
   `Interaction.pronunciation` field).
9. **Drill UIs are keyboard-navigable and axe-clean.** Spec §4 audit
   gates this; we do not ship a drill that fails it.
10. **Shadowing is in the default plan.** The planner schedules
    ≥ 10 min/day shadowing by default (ADR-030); a learner can
    reduce it but not eliminate it without an operator-level
    plan-template change. Audit asserts the default plan satisfies
    the floor across 100 synthetic cohorts.
11. **The "perfect agent" passes every drill.** Spec §4 first
    bullet. For every drill type, a scripted agent that always
    answers correctly produces a session report with 100% accuracy,
    the expected FSRS state shift, and the expected posterior shift.
    This is the structural-correctness gate.

These invariants are restated at the top of `phase5_design.md`'s §0.

---

## 6. Hand-off to DESIGN

`phase5_design.md` takes these decisions and turns them into:

- The drill-loop state machine (spec §2.1) rendered with concrete
  transitions, the event names emitted to the `Interaction` stream,
  and the resume-within-24h state-store shape.
- The five-per-module drill catalogs (CO §2.2, CE §2.3, EE §2.4,
  EO §2.5) as typed module specs in `packages/sla/src/drills/`,
  one file per drill type, with typed inputs (`Item` variants from
  Phase 2/3) and typed outputs (`Interaction`).
- The pronunciation pipeline DAG (spec §2.6) with explicit
  components: `whisper_fr.py` (ASR with confidence threshold),
  `mfa.py` (forced alignment), `prosody/` (pitch / stress / pause),
  and the `PronunciationSignal` assembly step.
- The `PronunciationSignal` Pydantic model with `score`,
  `signal_kind`, `disclaimer_version`, `display_label`, and the
  serializer guards (§1.2).
- The lexical-alternative drill spec (§1.1) — input type, output
  type, the explicit `Interaction.skill='lexical'` routing, and the
  UX banner copy.
- The exam-shape floor logic (§1.4) — the rolling-window
  computation, the 409 response shape, the dismissal mechanism
  and the local-only audit log.
- The cloud-opt-in seam (§1.3) — env var names, startup banner
  text, the LiteLLM gateway integration touch points, and the
  CI capability test that prevents network calls in default mode.
- The four new ADRs (ADR-028 through ADR-031).
- The accessibility spec per drill type (spec §2.7) sharpened with
  the §1.1 decision: which drills have a CO-alternative path, which
  use STT input, which use text-input fallback with the explicit
  "does not measure real EO" disclaimer.
- The test plan: unit per drill type; property tests on the
  `Interaction` write path's skill-routing invariants; integration
  test that runs a 5-drill "perfect agent" session end-to-end and
  asserts the posterior shift; a11y test that runs axe-core +
  keyboard walkthrough per drill UI stub; perf test that the
  exam-pace CO timer is within ±1 s over a 35-min stretch (spec §4).
- The hand-off package: the `Interaction` schema doc that Phase 6
  composes with and Phase 7 scores against.
