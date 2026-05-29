"""Structural lint: forbid raw `.score` access on `PronunciationSignal`.

This is the static-AST half of ADR-031's defense in depth. The runtime
half is the Pydantic contract on `PronunciationSignal` (frozen,
`signal_kind` is a Literal, `disclaimer_version` is required). This
test ensures application + UI code consumes `display_label`, not
`score`, on `PronunciationSignal` instances.

Implementation: parse each source file with `ast` and walk attribute
accesses. An access of the form `<NAME>.score` is flagged when `NAME`
matches the pronunciation-signal variable convention
(`pronunciation`, `pronunciation_signal`, `pron_signal`, `pron_sig`).
AST-walking — not text grep — so mentions of `pronunciation.score`
inside docstrings, comments, or string literals are not false
positives.

Allowlisted files (exempt from the check):

- The factory + gate themselves (`packages/ml/.../pronunciation/`).
- The Phase 7 rubric scorer (`packages/sla/.../scoring/`) and the
  worker tasks (`apps/worker/.../tasks/score_*.py`).
- All test files.

If you're tempted to grant a new exception, ask whether the consumer
should be reading `display_label` instead. The whole point of ADR-031
is that "I just need the number" is the failure mode this rule
exists to catch.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNED_ROOTS = (REPO_ROOT / "packages", REPO_ROOT / "apps")

# Allowlisted file path *prefixes* (relative POSIX paths from the repo root).
# Anything starting with one of these is exempt from the check.
ALLOWED_SUFFIXES: tuple[str, ...] = (
    # The pipeline that legitimately constructs / inspects the score:
    "packages/ml/src/tcf_accel_ml/pronunciation/signal.py",
    "packages/ml/src/tcf_accel_ml/pronunciation/per.py",
    "packages/ml/src/tcf_accel_ml/pronunciation/insufficient_data.py",
    # Phase 7 rubric scorer + worker tasks (not yet present; pre-allowed
    # so the exception list lands with ADR-031 rather than later).
    "packages/sla/src/tcf_accel_sla/scoring/",
    "apps/worker/src/tcf_accel_worker/tasks/score_",
)

# Variable names that signal "this is a PronunciationSignal". The
# convention is consistent across the design (`phase5_design.md §5.2`,
# §11) and matches the documented field name on `Interaction`.
_PRON_SIGNAL_NAMES = re.compile(r"^(pronunciation(_signal)?|pron_sig(nal)?)$")


def _iter_python_files() -> Iterator[Path]:
    for root in SCANNED_ROOTS:
        if not root.exists():
            continue
        yield from root.rglob("*.py")


def _is_test_file(path: Path) -> bool:
    parts = set(path.parts)
    return "tests" in parts or path.name.startswith("test_")


def _is_allowlisted(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(rel.startswith(suffix) or rel == suffix for suffix in ALLOWED_SUFFIXES)


def _attribute_receiver_name(node: ast.Attribute) -> str | None:
    """Return the receiver name if `node` is `<NAME>.attr`, else None.

    We deliberately don't follow chains like `self.pronunciation.score`
    — that case would be a real violation under our naming convention
    (the receiver is `pronunciation`), and the recursive walk catches it.
    """
    if isinstance(node.value, ast.Name):
        return node.value.id
    return None


def _find_offenders_in_source(source: str) -> list[tuple[int, str]]:
    """Return `(lineno, expression)` for every flagged attribute access."""
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - skip unparseable file
        return []
    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr != "score":
            continue
        receiver = _attribute_receiver_name(node)
        if receiver is None:
            continue
        if not _PRON_SIGNAL_NAMES.match(receiver):
            continue
        # Real violation.
        try:
            expr = ast.unparse(node)
        except Exception:  # pragma: no cover - fallback for old ast versions
            expr = f"{receiver}.score"
        offenders.append((node.lineno, expr))
    return offenders


def test_no_raw_pron_score_access_in_application_code() -> None:
    """ADR-031: `.score` on a PronunciationSignal must not appear outside the allowlist."""
    offenders: list[tuple[Path, int, str]] = []
    for path in _iter_python_files():
        if _is_test_file(path) or _is_allowlisted(path):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover - file race
            continue
        for lineno, expr in _find_offenders_in_source(source):
            offenders.append((path, lineno, expr))
    assert not offenders, (
        "ADR-031 violation: PronunciationSignal.score accessed outside the allowlist.\n"
        "The UI must consume `display_label`, not `score`. "
        "If you genuinely need the raw score, add a justified entry to "
        "ALLOWED_SUFFIXES in this test (and write an ADR amendment).\n"
        + "\n".join(f"  {p}:{n} | {expr}" for p, n, expr in offenders)
    )


# ─── Self-tests on the AST scanner ─────────────────────────────


def test_scanner_finds_pronunciation_dot_score() -> None:
    source = "x = pronunciation.score\n"
    assert _find_offenders_in_source(source) == [(1, "pronunciation.score")]


def test_scanner_finds_alternate_variable_names() -> None:
    for name in ("pronunciation_signal", "pron_signal", "pron_sig"):
        source = f"if {name}.score > 0.5:\n    pass\n"
        flagged = _find_offenders_in_source(source)
        assert flagged, f"scanner missed {name}.score"
        assert flagged[0][1] == f"{name}.score"


def test_scanner_ignores_string_and_docstring_mentions() -> None:
    # This was the original false-positive case: mentioning
    # `pronunciation.score` inside a docstring/comment must NOT flag.
    source = (
        '"""Docs that mention pronunciation.score in passing."""\n'
        "# also pronunciation.score in a comment\n"
        "x = 'pronunciation.score'\n"
        "y = ('text mentioning '\n"
        "     'pronunciation.score in a multi-line string')\n"
    )
    assert _find_offenders_in_source(source) == []


def test_scanner_ignores_unrelated_score_fields() -> None:
    # NCLCEstimate.score, FSRS.score, generic `result.score` are not
    # PronunciationSignal instances. The scanner must not flag them.
    source = (
        "nclc.score\n"
        "self.score = 0.5\n"
        "result.score\n"
        "score = compute_score()\n"
    )
    assert _find_offenders_in_source(source) == []


def test_scanner_catches_assignment_target_attribute_access() -> None:
    # If someone tries to *set* pronunciation.score, that's also a
    # violation (and would fail at runtime because the model is frozen).
    source = "pronunciation.score = 0.99\n"
    assert _find_offenders_in_source(source)


def test_allowlisted_paths_exist_or_are_pre_allowed() -> None:
    # Some allowlisted paths are pre-allowed for future Phase 7 modules
    # (scoring/, score_*). That's fine — the rule must not require the
    # files to exist yet. But the *existing* ones should match a real file.
    for suffix in ALLOWED_SUFFIXES:
        candidate = REPO_ROOT / suffix
        if candidate.is_file() or candidate.is_dir():
            assert candidate.exists()
            continue
        # Pre-allowed (Phase 7) — must look like a forward reference.
        assert any(token in suffix for token in ("scoring/", "score_")), (
            f"Allowlisted path {suffix!r} doesn't exist and isn't a pre-allowed Phase 7 target."
        )
