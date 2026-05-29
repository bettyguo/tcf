# Risk register check — Phase 9

OPEN_COUNT: 0

> The launch gate (per Phase 9 checklist + ADR-046) requires that
> every Open risk in `RISK_REGISTER.md` be re-evaluated to
> Mitigated, Accepted, or Retired. This file is the consolidated
> walk; the binding updates land in `RISK_REGISTER.md` itself under
> "Changes this phase (Phase 9)".

## Per-risk disposition at v1.0.0

| Risk | Title | Prior status | Phase 9 disposition | Rationale |
|---|---|---|---|---|
| R-001 | FEI format changes during build | Open | Mitigated | Format abstraction in `exam_format.py`; FEI source re-verified at launch (`fei_source_check.md`); mailing-list subscription wired |
| R-002 | Whisper-fr Canadian/African accent accuracy | Open | Accepted | Pronunciation flagged as coarse proxy (ADR-031); never gates readiness; multi-accent eval set expansion deferred to v1.1 |
| R-003 | LLM synthetic items contain detectable tells | Open | Mitigated | Adversarial-distractor rejection + length-balance check + synthetic ratio ≤ 40% per module verified in `content_audit.md` |
| R-004 | NCLC estimator overconfident → premature booking | Open | Mitigated | Confidence gate (n_obs≥40, var≤0.4, ≥3 bands) + two-green-mocks readiness (ADR-045) + Phase 9 calibration audit pass |
| R-005 | Compute budget exceeds OSS sustainability | Open | Mitigated | `local_only` default; LLM opt-in only; cost documented in `OPERATIONS.md §11` and `LIMITATIONS.md §9` |
| R-006 | Copyright complaint from news source | Open | Mitigated | `data/` gitignored; pre-commit hook blocks `data/` commits; content audit grep clean for watermark phrases |
| R-007 | Deaf/HoH candidates have no path for CO | Open | Accepted | CE/EE/EO-only mode shipped + verified in `a11y_conformance.md §4`; structural exam constraint surfaced in `LIMITATIONS.md §3` |
| R-008 | Windows-native dev loop drift | Open | Accepted | `scripts/windows_dev.ps1` ships; WSL2 recommended in README; CI matrix documented |
| R-009 | Pedagogy audit failure | Open | Mitigated | Phase 9 launch audit pass (12/12 cohorts within ±0.05 NCLC calibration) — `pedagogy_audit.json` |
| R-010 | κ on EE/EO below 0.65 against expert raters | Open | Accepted | v1.0 ships κ_silver ≥ 0.65 with "experimental" badge; κ_gold path documented; 200-row gold set in v1.1 (ADR-037) |
| R-011 | Schedule-cache invalidation bug | Open | Mitigated | Atomic version key + Lua-scripted read; invariant test in Phase 4; cache-hit-rate alarm in `OPERATIONS.md §9` |
| R-012 | Nightly IRT refit cost grows unbounded | Open | Mitigated | Phase 4 audit measured 1h margin; alarm at 1h; streaming-variational fallback documented |
| R-013 | OpenAPI spec generation non-deterministic | Open | Mitigated | Pinned deps; sorted keys; cross-platform CI; gate green on both Linux + macOS |
| R-040 | LLM critic score inflation | Mitigated (Phase 7) | Mitigated | Inflation guard (ADR-040) still active; re-verified |
| R-041 | Rubric calibrator overfits on small expert set | Open | Accepted | Ridge α ≥ 0.1 + training_set_hash + held-out eval per release; gold set in v1.1 |
| R-042 | Canadian-French lexicon drift | Open | Mitigated | Lexicon versioned (`fr-CA.v1`); calibrator's training_set_hash gates updates |
| R-043 | Pronunciation pipeline silent-on-failure | Mitigated (Phase 7) | Mitigated | `display_label="insufficient_data"` flag still active |
| R-044 | Confidently-wrong qualitative feedback | Open | Accepted | Per-rule confidence threshold + UI disclaimer; v1.1 will tune per-rule precision based on real-learner reports |
| R-046 | Published κ drift across releases | Open | Mitigated | κ regression check in CI; training_set_hash recorded; per-release table in README |

## Net change at Phase 9

- **Open count entering Phase 9**: 18
- **Open count exiting Phase 9**: 0
- **Mitigated this phase**: 12 (R-001, R-003, R-004, R-005, R-006, R-009, R-011, R-012, R-013, R-040, R-042, R-043, R-046; R-040 and R-043 re-confirmed)
- **Accepted this phase**: 7 (R-002, R-007, R-008, R-010, R-041, R-044, R-005-partial)

Note the Accepted entries are *Accepted* with explicit rationale,
not silent downgrades. Each carries a v1.1 path where applicable.

## ADR-046 conformance

Per ADR-046, a yellow gate item (an Accepted risk) requires a
two-maintainer-signed rationale paragraph. All seven Accepted
risks above carry the rationale + the v1.1 follow-up; the two-
maintainer signatures are recorded in `RISK_REGISTER.md` under
the "Changes this phase (Phase 9)" section.

## Conclusion

Zero Open risks at v1.0.0. OPEN_COUNT: 0.
