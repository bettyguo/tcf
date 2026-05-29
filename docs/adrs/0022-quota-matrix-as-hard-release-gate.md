# ADR-0022: Quota matrix is a hard release gate, not a guideline

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Content lead, Product
- **Phase**: 3

## Context

`03_CONTENT_PIPELINE.md §2.4` defines a quota matrix the bank must
satisfy:

| Dimension | Required distribution |
|---|---|
| CEFR level | A1: 5%, A2: 10%, B1: 25%, B2: 30%, C1: 20%, C2: 10% |
| Genre (CE) | News 25%, Ad 10%, Letter 15%, Admin 15%, Academic 20%, Narrative 15% |
| Audio accent (CO) | fr-FR 50%, fr-CA 25%, fr-BE/CH 10%, fr-AF 10%, mixed 5% |
| Register | Standard 60%, Familier 20%, Soutenu 20% |
| Canadian context (EE T2/T3) | ≥ 60% Canadian-flavored |
| Topic cluster (any) | No cluster > 5% of bank |

Master prompt §1.4 (Canadian context is required on EE Tasks 2 & 3;
omission costs ~3–4 points on real exams) and §1.2 (independent-skill
floor governs immigration outcomes) compose: a bank that under-
represents Canadian accents on CO or Canadian context on EE actively
trains the wrong skill for the actual immigration pathway.

The question is **how strictly** to enforce the matrix. Two postures:

- **Guideline**: the matrix is the target; the bank may ship if it
  is "close enough" with a follow-up plan to converge.
- **Hard release gate**: violation > 10% on any cell fails the phase
  audit; no shipping until the bank converges.

A guideline posture is convenient for shipping fast. A hard gate is
the only posture compatible with the master prompt §6.1 ("correctness
over coverage") commitment, because under-representation of a quota
cell is not "a feature gap" — it is an *active mis-training* of the
learner.

## Decision

**The quota matrix is a hard release gate.** Specifically:

- For every cell in the matrix, the audit
  (`tests/content/test_bank_distribution.py`,
  `phase3_design.md §12.6`) computes the actual distribution.
- A cell is *in tolerance* if `abs(actual − target) ≤ 0.10 × target`
  (10% relative tolerance), with the floor of `abs(actual −
  target) ≤ 0.02` (2 percentage points absolute, to avoid spurious
  failures on very-small cells).
- A cell is *over*: the `≤` direction; for "No cluster > 5%" this
  means no cluster exceeds 5%.
- Any cell out of tolerance → audit fails → phase gate fails → no
  ship.

The gate runs against whichever bank is being audited:

- `seed_bank.py --open-only` mode: the quota matrix is **a heuristic**
  in this mode. The open-license seed cannot guarantee Canadian-
  accent coverage (Common Voice fr is dominantly Hexagonal). The
  open-only mode emits a `BANK_STATS.md` showing the cells it fills
  and explicitly names the cells it does not — but the *phase gate*
  applies to the full bank.
- `seed_bank.py --with-operator-ingest` mode (with RFI, ICI Première,
  etc.): the quota matrix is **the hard gate**. Operators who do not
  reach quota cannot ship.

## Consequences

- **Positive**:
  - The bank's "balanced diet" property is verifiable mechanically
    on every release.
  - Mis-training (over-representation of one accent or genre) is
    detected before it reaches a learner.
  - The audit report is the artifact: `BANK_STATS.md` shows every
    cell with its actual vs target, making over/under-fill visible
    at a glance.
- **Negative**:
  - Operators may need multiple ingestion runs to reach quota
    (e.g., a first pass yields 80% fr-FR audio because the open
    corpora are skewed; a second pass with ICI Première brings
    fr-CA up to 25%). The pipeline supports this via the resumable
    Celery state (`phase3_design.md §9`).
  - A genuinely under-supplied cell (e.g., fr-BE / fr-CH audio is
    rare in CC-licensed corpora) may block a release. The
    `LIMITATIONS.md` escape valve allows the maintainer to
    *explicitly accept* a known-gap with a documented rationale;
    this is a one-line ADR-revision event, not a silent override.
  - The 10% relative tolerance is itself a parameter. Tighter
    (5%) would reject legitimate fluctuation at small bank sizes;
    looser (20%) would let real mis-representation through.
- **Neutral**:
  - The matrix can evolve. Adding a new dimension (e.g., topic
    diversity sub-quotas) is an additive change with a new ADR;
    existing cells keep their tolerance.

## Alternatives considered

- **Guideline only**: rejected because it is incompatible with master
  prompt §6.1 (correctness over coverage) and §1.4 (Canadian
  context is a 3–4 point exam penalty if omitted).
- **Per-cell hard gate but only for CEFR + accent** (the immigration-
  relevant cells), guideline for the rest: rejected because the
  partial gate creates a precedent for relaxing the rest. A
  uniform rule is easier to enforce.
- **Hard gate with 5% relative tolerance**: rejected as too tight for
  bank sizes under 10k items — random sampling fluctuation alone
  can push small cells out by 5% even when the underlying process
  is on-target.
- **Hard gate with 20% relative tolerance**: rejected as too loose;
  20% on a 25% target means the bank could be 20–30% on a cell that
  should be 25%, which is meaningful mis-representation.

## What would change our mind

- **A bank size > 50k items where 5% relative tolerance becomes
  statistically appropriate.** We'd tighten the tolerance, not relax
  the gate.
- **A demonstrated source-availability gap** (e.g., the operator
  cannot reach 25% fr-CA on CO because no CC-licensed Canadian-accent
  audio exists at scale and the operator-tier ICI Première ingest
  is unavailable). We'd amend `LIMITATIONS.md` to document the
  structural gap and either (a) accept the gap with a deduction in
  the readiness-claim, or (b) carve out an exception ADR for that
  specific cell. The hard-gate posture itself does not change.
- **Phase 9 launch audit finds a *different* dimension is the
  dominant mis-training signal** (e.g., topic concentration despite
  passing the 5% cluster cap, because clusters are too coarse). We'd
  add a new dimension to the matrix and re-audit.

## References

- `03_CONTENT_PIPELINE.md §2.4, §4, §5`
- `phase3_think.md §3` (deferred quota tolerance), `§5` (hard-gate
  invariant 9)
- `phase3_design.md §10.1` (open-only mode caveat), `§12.6`
- Master prompt §1.2 (independent-skill rule), §1.4 (Canadian
  context), §6.1 (correctness over coverage)
- ADR-0021 (synthetic cap, related gating posture)
