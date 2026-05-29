# Content audit — Phase 9

STATUS: pass

> Three sub-audits: distribution, hand-review, FEI drift. Plus the
> PII/copyright/harm grep.

## 1. Distribution check (`scripts/seed_bank.py --audit-only`)

Re-runs the Phase 3 quota matrix verification against the
post-seed bank.

| Module | Target count | Observed | Delta | Synthetic ratio | Within ±5% / ≤ 40%? |
|---|---|---|---|---|---|
| CO | 1200 | 1184 | -1.3% | 28% | ✅ |
| CE | 1600 | 1612 | +0.8% | 31% | ✅ |
| EE | 400 (prompts) | 392 | -2.0% | 38% | ✅ |
| EO | 400 (prompts) | 411 | +2.8% | 35% | ✅ |
| Shadowing | 300 | 304 | +1.3% | 0% | ✅ |
| Sub-skill (CO_dictation, etc.) | 800 | 821 | +2.6% | 24% | ✅ |

Per-CEFR-band histogram balanced per the quota matrix; no band
> 5% from target.

## 2. Hand review (100 items / module × 4 modules = 400 items)

Reviewer: one per module, not the author (per `phase9_design.md §5.2`).
Each item scored on: CEFR-label-correctness, MCQ-key-correctness,
audio-playable (CO), prompt-appropriateness (EE/EO).

| Module | Reviewer | Sample | Agree | Disagree | Notes count | Pass rate |
|---|---|---|---|---|---|---|
| CO | Maintainer A | 100 | 97 | 3 | 5 | 97% ✅ ≥ 95% |
| CE | Maintainer B | 100 | 96 | 4 | 7 | 96% ✅ ≥ 95% |
| EE | Maintainer C | 100 | 98 | 2 | 3 | 98% ✅ ≥ 95% |
| EO | Maintainer D | 100 | 95 | 5 | 8 | 95% ✅ ≥ 95% |

Disagreements logged in `data/audit/phase9/content_handreview.md`
(individual item ids + reviewer notes). All 14 disagreements are
single-CEFR-band shifts; none are catastrophic mislabels. Three
items pulled from the bank (CE: 2; EO: 1) for re-leveling in v1.1.

## 3. FEI drift check (10 CO items per CEFR band, qualitative)

Compared against the 2025/2026 FEI published samples:

| CEFR band | Items compared | Difficulty match | Register match | Genre coverage | Verdict |
|---|---|---|---|---|---|
| A2 | 10 | OK | OK | OK | ✅ |
| B1 | 10 | OK | OK | OK | ✅ |
| B2 | 10 | OK | OK | minor drift on news-genre | ⚠ noted |
| C1 | 10 | OK | OK | OK | ✅ |

Noted drift: our B2 CO bank under-represents news/current-affairs
items relative to the latest FEI samples. Not launch-blocking;
added to v1.1 content backlog. R-042 (Canadian lexicon drift) is
adjacent but distinct; no new R needed.

## 4. PII / copyright / harm grep

| Pattern | Hits | Action |
|---|---|---|
| Email regex (`\S+@\S+\.\S+`) | 0 | — |
| Phone regex (NANP + EU) | 0 | — |
| Postal codes (CA + FR) | 0 | — |
| Watermark phrases (RFI / TV5MONDE / Radio-Canada short list) | 0 | — |
| Topic filter (self-harm, hate-speech, political-inflammatory) | 0 | — |

The pre-commit hook `scripts/check_no_data_commit.py` is wired and
verified blocking any commit under `data/`. R-006 (copyright
complaint) mitigation re-verified.

## Conclusion

All four sub-audits pass. One minor B2 CO genre drift noted for
v1.1; not launch-blocking. STATUS: pass.
