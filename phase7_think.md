# Phase 7 — THINK

> Auto-scoring of L2 writing and speaking is the **most reviewer-skeptical
> surface** of this system. The phase deliverable is not a clever scoring
> trick; it is an honest, calibrated rubric pipeline that publishes its
> own Cohen's κ alongside every release and refuses to claim numeric
> precision it cannot defend.

This document is the load-bearing reasoning for Phase 7. It precedes the
design and pins the constraints we will not relax later.

---

## 1. The honesty imperative

Auto-scoring of L2 essays and speech is a 40-year-old research problem.
Commercial systems with decades of human-labelled calibration data (ETS
e-rater, Pearson IntelliMetric) report ~κ 0.65–0.75 against expert
raters on *prompt-controlled* essays. We will not exceed that.

Three commitments follow:

1. **Score reliably inside the published-research band.** A claim of
   κ ≥ 0.80 from a system with <500 expert ratings is a flag of poor
   methodology, not capability.
2. **Be honest about the proxy nature of subscale scores.** Lexical
   range is measurable; "register appropriateness" is a judgement call
   that even two trained examiners disagree on. The UI must communicate
   the distinction.
3. **Provide qualitative feedback with higher learner-value than the
   numeric score.** Span-level error annotation with a suggested
   correction, a one-sentence explanation, and a linked drill is worth
   more than a single 14/20 number. The drill link closes the loop into
   Phase 5.

The system MUST publish, with every release, the κ achieved against the
best available expert-labelled subset. Pretending we have not measured
it is forbidden (ADR-038).

---

## 2. The rubric (pinned in Phase 2 schemas)

`WritingRubric` and `SpeakingRubric` already lock the wire shape. Phase
7 fills the components.

### 2.1 EE — Expression écrite

Six dimensions, each scored 0–5:

| Dimension                       | Notes                                          |
|---------------------------------|------------------------------------------------|
| Task completion                 | Did the response answer the prompt?            |
| Coherence & cohesion            | Logical flow, paragraph structure, connectors. |
| Lexical range                   | Type/token, MATTR, register-appropriate words. |
| Grammatical accuracy            | Density × severity of detected errors.         |
| Register appropriateness        | Familier-to-soutenu axis match.                |
| Canadian context integration    | Task 2 & 3 only; null for Task 1.              |

Total per task is mapped 0–20 by scaling sum(components) ∈ [0, 25] → [0, 20]
(see `schemas/scoring.py::WritingRubric._total_consistent_with_components`).

### 2.2 EO — Expression orale

Six dimensions, each 0–5: task completion, fluency & pace,
pronunciation & prosody, lexical range, grammatical accuracy,
interaction responsiveness. Sum ∈ [0, 30] → [0, 20].

The TCF Canada uses a coarse 6-band scale (1–6) that maps to NCLC. We
score finer-grained internally (0–20 per task, averaged across the
three tasks) and aggregate. The mapping is a published lookup table
loaded at scorer-init time.

---

## 3. Scoring architecture

```
EE submission:
  text → linguistic analyzer (spaCy fr + regex error detectors) → WritingFeatures
                                                                       ↓
                                + LLM critic (Claude Sonnet 4.6, strict prompt)
                                                                       ↓
                                                       calibration layer (per-rubric Ridge)
                                                                       ↓
                                                                  WritingRubric + ErrorAnnotation[]

EO submission:
  audio → Whisper-fr (Phase 5) → transcript → WritingFeatures (content dims)
        → MFA + prosody (Phase 5) → SpeakingFeatures (pronunciation/prosody/fluency dims)
        → calibration layer
        → SpeakingRubric
```

The two pipelines share the calibration layer's shape and most of the
feature implementation; EO inherits all writing features computed on
the transcript and adds the speech-specific signals.

---

## 4. Why a hybrid features + LLM + calibration architecture

| Approach                              | Problem                                                |
|---------------------------------------|--------------------------------------------------------|
| Pure regex / hand-crafted features    | Plateaus around κ 0.45; brittle across topics.         |
| Fine-tuned BERT-fr on rubric scores   | Needs thousands of labels we do not have for v1.       |
| LLM-only with chain-of-thought        | Documented score inflation; high variance prompt-to-prompt. |
| **Hybrid features + LLM + calibration** | ← chosen.                                            |

The LLM gives structured per-rubric scores; the feature pipeline gives
objective floor measurements (TTR ≥ 0.65 for NCLC 9, error density
< 2/100w, etc.); the calibration layer (small Ridge regression per
rubric) fuses them against the expert-labeled set.

The calibration layer is small enough (~6 inputs, 1 output, ~200 rows)
that it does not over-fit even when expert labels are scarce.

---

## 5. Alternatives considered

- **Pure regex/feature scoring.** Brittle on prompts that vary in
  topic. Rejected: ceiling well below research κ.
- **Fine-tuned classifier (BERT-fr on rubric scores).** Would need
  thousands of labels per rubric dimension. We will not have that
  during v1. Rejected.
- **LLM-only with chain-of-thought.** Inflation. The LLM happily gives
  4/5 on coherence to a five-sentence essay if asked. Rejected.
- **Hybrid features + LLM + calibration.** Chosen. The feature
  pipeline anchors the floor; the LLM provides the qualitative
  judgement; the calibrator constrains the LLM with regression weights
  fit on expert labels.

---

## 6. Error annotation

Every flagged error carries:

- **type:** `agreement | tense | preposition | article | spelling |
  vocabulary | syntax | register | cohesion | other`
- **span:** `(span_start, span_end)` char offsets in the source text or
  transcript.
- **detected_by:** `spacy_rule | language_tool | llm | custom`
- **severity:** `minor | major`
- **suggestion:** a single proposed fix (`ErrorAnnotation.suggestion`).
- **confidence:** [0, 1] — every annotation carries this; the UI
  filters under a confidence threshold.
- **pedagogical_tag:** links to a drill that targets this error class
  (the feedback render uses this to populate the `[drill: …]` link).
  Carried in the scorer's structured payload — the wire schema's
  `ErrorAnnotation` does not yet have a field for it (Phase 2 freeze
  decision), so the scorer attaches it via the side-channel
  `pedagogical_tags` map in the graded_score dict.

Errors are **deduplicated** across detectors: LanguageTool + the LLM
critic + custom spaCy rules routinely flag the same span. The dedup
key is `(span_start, span_end, error_type)`; the surviving annotation
keeps the highest-confidence `suggestion`.

---

## 7. The pronunciation sub-score

Phase 5 already produces `PronunciationSignal` with `score`,
`display_label`, and `per`. Phase 7 consumes it for the EO rubric's
`pronunciation_prosody` dimension. Components:

- Phoneme error rate (PER) from Phase 5's MFA + reference.
- Prosody score: pitch range, stress placement on final syllable,
  pause distribution.
- WPM ratio: 130–180 WPM is the target band for connected speech at
  B2+; below 100 or above 220 is penalized.

The Phase-5 coarse-proxy disclaimer (ADR-031) propagates: any UI
surface that shows pronunciation feedback renders the disclaimer
adjacent. Reported separately in the final report as a coarse signal,
not a fine-grained score.

---

## 8. The honesty guards (load-bearing)

### 8.1 Confidence indicator on every score

Every rubric returned to a learner must carry a confidence indicator.
The default UI rule: when the calibrator's posterior variance on a
dimension exceeds the threshold, render the score as a band
("Coherence: 3–4/5") instead of a point estimate. This is the
structural mirror of ADR-025 (`SkillPosterior.confident`): refuse to
predict when the model cannot.

### 8.2 Inflation guard (ADR-040)

When the LLM critic's per-rubric score is more than 3 points above the
feature-predicted score on any rubric dimension, the final score is
clamped to `feature_score + 2` and a `needs_human_review` flag is set
on the rubric. The clamp is logged for audit. This catches the most
common LLM failure mode (over-grading short or fluent-but-empty
responses).

### 8.3 Published κ

Every release runs `scripts/eval_kappa.py` against the available
expert subset. The κ table is emitted as JSON for the audit and
embedded in the release notes. A release whose published κ < 0.55
requires an explicit "experimental" badge on the in-app rubric
surface (ADR-038).

### 8.4 No quote-back without attribution

The feedback rendering MUST visually distinguish quoted-back learner
text from the system's prose. A learner re-reading their own sentence
back from us as if it were our judgement is a privacy and trust
violation; the renderer always wraps the learner's words in a styled
blockquote (ADR-040 anti-criterion).

---

## 9. The expert-labelled set

For v1 we need ≥ 200 EE submissions and ≥ 200 EO recordings, each
rated by at least 2 expert raters using the official rubric. Three
acquisition paths, in priority:

1. **Partner Alliance Française or DELF/TCF examiners** — pay an
   honorarium for 200 ratings; reproducible reference set,
   gold-standard.
2. **Crowd-sourced learners on the project's mailing list** (with
   informed consent + a license to use ratings for training).
3. **LLM-as-rater stand-in** — ensemble of two frontier LLMs with
   explicit per-criterion scoring; treat as "silver" labels with a
   documented ~0.5 NCLC deflated calibration to match expert-rater
   behavior, validated against a smaller (~30-essay) actual-expert
   subset.

Path 1 is the target. Paths 2–3 bootstrap until path 1 is in place.
The system MUST publish, with every release, the κ achieved against
whichever expert subset is at hand, and MUST label the κ as `gold` or
`silver` based on the rater type.

---

## 10. Architectural risks (carried into RISK_REGISTER)

- **R-040 LLM score inflation.** Mitigated by ADR-040 inflation guard
  + temperature ≤ 0.2 + structured output enforcement (ADR-039).
- **R-041 Calibrator over-fit on a tiny expert set.** Mitigated by
  Ridge regularization (α tuned by leave-one-out CV) and a held-out
  set; the calibrator is re-fit only when ≥ 50 new labels arrive.
- **R-042 Canadian-context lexicon drift.** Mitigated by versioning
  the lexicon and re-running the audit on each lexicon bump.
- **R-043 Pronunciation pipeline silent-on-failure.** Already
  mitigated by Phase 5's `display_label == "insufficient_data"` path
  (ADR-031); Phase 7 inherits the gate.
- **R-044 Confidently-wrong qualitative feedback.** Mitigated by the
  confidence indicator (§8.1) and the LLM critic's structured
  refusal-to-justify path: an LLM that cannot quote evidence for a 5/5
  is required to drop to 4/5.

---

## 11. Out of scope for Phase 7

- Real-time / sub-second scoring. The task is async-by-design (≤ 2 min
  P95 to graded). The "submission lifecycle" wire shape (Phase 2
  freeze) already encodes this.
- Multilingual scoring. The pipeline is FR-only for v1; EN/ES/etc. is
  a Phase 10+ concern.
- Auto-grading of free-form CO/CE rationale (we do not collect that).
- A self-serve "tune your own rubric" surface. The rubric is pinned to
  the published TCF Canada criteria; learner-tunable rubrics would
  break the calibration claim.
