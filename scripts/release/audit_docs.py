"""Phase 9 — documentation audit.

Greps every load-bearing doc for ``# TODO``, ``FIXME``, ``XXX``,
emits ``data/audit/phase9/docs_audit.md`` with a per-doc status
table. Exits 0 / writes ``STATUS: pass`` only if every required doc
exists and has no markers.

The set of required docs mirrors ``phase9_design.md §7``.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
AUDIT_DIR: Final[Path] = REPO_ROOT / "data" / "audit" / "phase9"
OUT_FILE: Final[Path] = AUDIT_DIR / "docs_audit.md"

# Required docs. Each entry: (path, owner).
REQUIRED_DOCS: Final[tuple[tuple[str, str], ...]] = (
    ("README.md", "Lead"),
    ("LIMITATIONS.md", "Product"),
    ("PEDAGOGY.md", "ML / Pedagogy"),
    ("ARCHITECTURE.md", "Backend"),
    ("OPERATIONS.md", "DevOps"),
    ("LEARNER_GUIDE.md", "Product"),
    ("CONTRIBUTING.md", "Lead"),
    ("CHANGELOG.md", "Lead"),
    ("LICENSE", "Lead"),
    ("CONTENT_LICENSE", "Lead"),
    ("SECURITY.md", "DevOps"),
    ("RISK_REGISTER.md", "Lead"),
)

TODO_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:^|\W)(#\s*TODO|FIXME|XXX)\b", re.IGNORECASE
)


@dataclass
class DocResult:
    path: str
    owner: str
    exists: bool
    todo_hits: list[tuple[int, str]]

    @property
    def ok(self) -> bool:
        return self.exists and not self.todo_hits


def _audit_one(rel_path: str, owner: str) -> DocResult:
    p = REPO_ROOT / rel_path
    if not p.exists():
        return DocResult(path=rel_path, owner=owner, exists=False, todo_hits=[])
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        m = TODO_PATTERN.search(line)
        if m:
            hits.append((i, line.strip()[:120]))
    return DocResult(path=rel_path, owner=owner, exists=True, todo_hits=hits)


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    results = [_audit_one(p, o) for p, o in REQUIRED_DOCS]
    overall = all(r.ok for r in results)
    lines: list[str] = []
    lines.append("# Documentation audit (Phase 9)")
    lines.append("")
    lines.append(f"STATUS: {'pass' if overall else 'fail'}")
    lines.append("")
    lines.append("| Doc | Owner | Exists | TODO hits | OK |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        ex = "✅" if r.exists else "❌"
        hits = "0" if not r.todo_hits else f"{len(r.todo_hits)}"
        ok = "✅" if r.ok else "❌"
        lines.append(f"| `{r.path}` | {r.owner} | {ex} | {hits} | {ok} |")
    failing = [r for r in results if not r.ok]
    if failing:
        lines.append("")
        lines.append("## Failures")
        for r in failing:
            lines.append("")
            lines.append(f"### `{r.path}`")
            if not r.exists:
                lines.append("- MISSING")
            for line_no, snippet in r.todo_hits:
                lines.append(f"- L{line_no}: {snippet}")
    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_FILE}; status={'pass' if overall else 'fail'}")
    return 0 if overall else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
