"""Pre-commit hook: forbid `TODO` inside *public* docstrings.

Phase 1 anti-criterion: ❌ Any `# TODO` in a public docstring.

Internal `# TODO` comments inside function bodies are fine (we encourage them
as bookmarks). The contract surface — the docstring of a public function or
class — must not carry TODOs, because that docstring is part of the public
API and a TODO there signals an unfinished contract.

A "public" symbol = top-level (or class-method) function/class whose name does
not start with `_`. We walk the AST to find docstrings without executing code.

Usage (invoked by pre-commit):
    python scripts/check_no_todo_docstring.py path/one.py path/two.py ...

Exits 1 if any public docstring contains "TODO" (case-insensitive); 0 otherwise.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable
from pathlib import Path

TODO_PATTERN = re.compile(r"\btodo\b", re.IGNORECASE)


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _walk_definitions(tree: ast.Module) -> Iterable[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield node


def _check_file(path: Path) -> list[tuple[int, str]]:
    """Return a list of (lineno, snippet) offending nodes for `path`."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    offenders: list[tuple[int, str]] = []

    # Module-level docstring counts as public.
    mod_doc = ast.get_docstring(tree, clean=False)
    if mod_doc and TODO_PATTERN.search(mod_doc):
        offenders.append((1, mod_doc.strip().splitlines()[0][:80]))

    for node in _walk_definitions(tree):
        name = getattr(node, "name", "")
        if not _is_public(name):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc and TODO_PATTERN.search(doc):
            first_line = doc.strip().splitlines()[0][:80]
            offenders.append((node.lineno, f"{name}: {first_line}"))

    return offenders


def main(argv: list[str] | None = None) -> int:
    paths = (argv if argv is not None else sys.argv[1:])
    failed = False
    for raw in paths:
        path = Path(raw)
        if not path.exists() or path.suffix != ".py":
            continue
        offenders = _check_file(path)
        if not offenders:
            continue
        failed = True
        print(f"{path}: TODO found in public docstring", file=sys.stderr)
        for lineno, snippet in offenders:
            print(f"  L{lineno}: {snippet}", file=sys.stderr)
    if failed:
        print(
            "\nPhase 1 anti-criterion: no TODO in public docstrings. Move the\n"
            "TODO into a function-body comment or open an issue.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
