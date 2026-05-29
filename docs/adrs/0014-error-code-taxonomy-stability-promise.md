# ADR-0014: Error code taxonomy stability is a public-API promise

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Backend lead, Frontend lead
- **Phase**: 2

## Context

Phase 1 shipped a seed error taxonomy in
`packages/shared/src/tcf_accel/errors.py` with codes of shape
`E_<DOMAIN>_<NNN>` (e.g., `E_SCORING_002`, `E_CALIB_002`). Phase 2 adds
~10 more codes (`02_ARCHITECTURE.md §2.5`, `phase2_design.md §5.2`)
covering auth, validation, rate-limiting, and the `501
E_NOT_IMPLEMENTED_001` stub envelope.

Clients (the web app, future mobile apps, third-party integrations)
will branch behavior on these codes:

- The UI shows a "please re-record" prompt on `E_SCORING_002`.
- The UI shows a localized "not enough data yet" message on
  `E_CALIB_002`.
- The TS/Py generated clients (`packages/client-{ts,py}`) carry the
  codes as union literals; renaming one is a breaking change.

Master prompt §6.3 names "every error has a stable code and a learner-
facing message in EN + FR". The stability part is what this ADR makes
contractual.

## Decision

Error codes are part of the public API surface. The contract:

1. **Codes are added monotonically.** When a new error class is
   introduced, it gets the next available `NNN` in its domain.
2. **Codes are never renamed.** A code shipped under `/v1/` is stable
   for the life of `/v1/`.
3. **Codes are never reissued.** If a code becomes unused, it is
   *retired* (documented in `RATIONALE.md` with the date and reason)
   but the number is never reassigned to a new error.
4. **HTTP status changes are minor-version events.** Changing the
   `http_status` of an existing code (e.g., 422 → 409) requires a
   `SCHEMA_VERSION` bump and a CHANGELOG entry; the wire shape is
   unchanged but client branching may shift.
5. **Message text may change.** The localized `message` and
   `message_localized` fields can be revised at any time (e.g., to
   improve tone or clarity); the contract is on the *key* and the
   *code*, not the message string.
6. **Context shape is documented per code.** Each code has a documented
   set of `context` keys (e.g., `E_SCORING_002` always carries
   `{score, threshold}`). Removing a key is breaking; adding a key is
   additive.

Enforcement:

- A test (`tests/unit/test_error_codes.py`) iterates every subclass of
  `TCFAccelError`, asserts the code matches the `E_<DOMAIN>_<NNN>`
  regex, asserts uniqueness across all subclasses, asserts the
  `http_status` is in the allow-list, and asserts the message template
  renders with the documented context keys.
- The same test snapshots the full code → class map into
  `tests/unit/error_codes_snapshot.json`; PRs that *change* the
  snapshot require a `SCHEMA_VERSION` bump + a CHANGELOG entry.
- A pre-commit hook (Phase 2 adds `scripts/check_error_codes.py`)
  scans for `raise TCFAccelError` (the base class) directly — only
  subclasses are allowed in production code.

## Consequences

- **Positive**:
  - Clients can rely on codes for branching; localization can ship
    independently.
  - Generated SDKs carry the codes as literal unions, giving compile-
    time errors when a client uses a wrong code.
  - The retirement path is explicit; we can deprecate without breaking.
- **Negative**:
  - Code numbering becomes an append-only sequence; we cannot
    "reorganize" the taxonomy without a major version bump.
  - PR review must check that a new error reuses an existing code
    when semantically equivalent, rather than minting a new one.
- **Neutral**:
  - The code is *not* meant to be human-readable in a deep way
    (`E_SCORING_002` is not self-documenting). The message is for
    humans; the code is for machines.

## Alternatives considered

- **String enum codes (e.g., `"scoring.asr_low_confidence"`)**: rejected
  because string codes are tempting to "improve" cosmetically (rename
  `"asr_low_confidence"` to `"asr_below_threshold"`), which is a
  breaking change disguised as a refactor. Numbered codes are
  obviously-not-cosmetic.
- **Embedding the HTTP status in the code (e.g., `E422_SCORING_002`)**:
  rejected because we want `http_status` to be revisable (point 4
  above) without changing the code.
- **One global counter (no `<DOMAIN>` segment)**: rejected because
  domain grouping helps reviewers understand "is this code in the
  right module?". A miscategorized code can still be retired and
  re-issued in the correct domain.

## What would change our mind

- A breaking-change opportunity at the `/v2/` boundary (ADR-016) where
  the taxonomy can be re-organized cleanly. At that point we revisit
  whether numbered codes still serve us, or whether string codes with
  enforced stability are cleaner.

## References

- `02_ARCHITECTURE.md §2.5`.
- `phase2_design.md §5`.
- ADR-016 (API versioning policy; defines the `/v2/` boundary).
- Master prompt §6.3.
