"""Phase 9 — sign the launch readiness report.

Walks the launch checklist (``scripts/release/launch_checklist.yaml``)
and renders ``LAUNCH_READINESS_REPORT.md`` at the repo root. Exits
non-zero if any required gate is not green.

The script is the *single source of truth* for what "v1.0.0-ready"
means at the file level — `phase9_design.md §11` describes the flow,
and the YAML is the executable form.

Usage::

    python scripts/release/sign_audit_report.py \
        --auditor "Jane Doe <jane@example>" \
        --release-tag v1.0.0

If a gate's evidence file is missing the gate is FAIL (unless
``required: false`` in the YAML). The script never invents passing
evidence — that would defeat the audit.

Example: omit ``--strict`` to render the report even when gates fail
(useful for the first-draft, pre-launch review). Pass ``--strict`` for
the actual release step.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - the dep is in pyproject
    print("pyyaml is required: pip install pyyaml", file=sys.stderr)
    raise

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
CHECKLIST: Final[Path] = REPO_ROOT / "scripts" / "release" / "launch_checklist.yaml"
EVIDENCE_ROOT: Final[Path] = REPO_ROOT / "data" / "audit" / "phase9"
REPORT_PATH: Final[Path] = REPO_ROOT / "LAUNCH_READINESS_REPORT.md"


@dataclass
class Gate:
    gid: str
    description: str
    evidence_path: Path
    required: bool
    pass_marker: str | None

    @classmethod
    def from_yaml(cls, entry: dict[str, object]) -> "Gate":
        evidence_name = str(entry["evidence"])
        path = EVIDENCE_ROOT / evidence_name
        return cls(
            gid=str(entry["id"]),
            description=str(entry["description"]),
            evidence_path=path,
            required=bool(entry.get("required", True)),
            pass_marker=(
                str(entry["pass_marker"]) if "pass_marker" in entry else None
            ),
        )


@dataclass
class GateResult:
    gate: Gate
    passed: bool
    detail: str

    @property
    def emoji(self) -> str:
        return "✅" if self.passed else ("❌" if self.gate.required else "⚠")


def _evaluate_gate(gate: Gate) -> GateResult:
    if not gate.evidence_path.exists():
        return GateResult(gate, False, f"evidence missing: {gate.evidence_path.name}")
    if gate.pass_marker is None:
        return GateResult(gate, True, f"evidence present: {gate.evidence_path.name}")
    contents = gate.evidence_path.read_text(encoding="utf-8")
    if re.search(gate.pass_marker, contents, re.MULTILINE):
        return GateResult(gate, True, f"pass_marker matched in {gate.evidence_path.name}")
    return GateResult(
        gate,
        False,
        f"pass_marker not found in {gate.evidence_path.name}",
    )


def _audit_bundle_files() -> list[Path]:
    if not EVIDENCE_ROOT.exists():
        return []
    return sorted(p for p in EVIDENCE_ROOT.rglob("*") if p.is_file())


def _audit_bundle_hash(files: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0\0")
    return h.hexdigest()


def _render_report(
    *,
    release_tag: str,
    auditor: str,
    timestamp: datetime,
    results: Sequence[GateResult],
    bundle_hash: str,
    bundle_files: Sequence[Path],
    overall_pass: bool,
) -> str:
    lines: list[str] = []
    lines.append("# LAUNCH READINESS REPORT")
    lines.append("")
    lines.append(f"- **Release**: `{release_tag}`")
    lines.append(f"- **Auditor**: {auditor}")
    lines.append(f"- **Timestamp (UTC)**: {timestamp.isoformat()}")
    lines.append(f"- **Verdict**: {'✅ READY TO SHIP' if overall_pass else '❌ BLOCKED'}")
    lines.append(f"- **Audit bundle SHA-256**: `{bundle_hash}`")
    lines.append(f"- **Audit bundle file count**: {len(bundle_files)}")
    lines.append("")
    lines.append("## Gate matrix")
    lines.append("")
    lines.append("| Gate | Status | Detail |")
    lines.append("|---|---|---|")
    for r in results:
        lines.append(f"| {r.gate.description} | {r.emoji} | {r.detail} |")
    lines.append("")
    lines.append("## Audit bundle contents")
    lines.append("")
    for p in bundle_files:
        rel = p.relative_to(REPO_ROOT).as_posix()
        lines.append(f"- `{rel}`")
    lines.append("")
    lines.append("## Signing")
    lines.append("")
    lines.append(
        "This report is the single source of truth for the v1.0.0 launch "
        "decision. The SHA-256 above covers the byte content of every "
        "evidence file under `data/audit/phase9/` at signing time; any "
        "post-signature edit to those files will produce a different "
        "hash. The auditor identity is recorded in plaintext above; ADR-046 "
        "binds the gate matrix.",
    )
    lines.append("")
    lines.append(
        "_Generated by `scripts/release/sign_audit_report.py`. To "
        "regenerate after refreshing evidence: re-run the script and "
        "commit the diff in the same PR as the evidence update._",
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sign the launch readiness report.")
    parser.add_argument(
        "--auditor",
        required=True,
        help='Auditor identity, e.g. "Jane Doe <jane@example>"',
    )
    parser.add_argument(
        "--release-tag",
        default=None,
        help="Override the release tag (defaults to the YAML's release_tag)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any required gate is not green.",
    )
    args = parser.parse_args(argv)

    if not CHECKLIST.exists():
        print(f"checklist missing: {CHECKLIST}", file=sys.stderr)
        return 2

    checklist = yaml.safe_load(CHECKLIST.read_text(encoding="utf-8"))
    release_tag = args.release_tag or checklist.get("release_tag", "v0.0.0")
    gates = [Gate.from_yaml(entry) for entry in checklist["gates"]]

    results = [_evaluate_gate(g) for g in gates]
    overall = all(r.passed for r in results if r.gate.required)

    files = _audit_bundle_files()
    bundle_hash = _audit_bundle_hash(files) if files else "no-files"

    report = _render_report(
        release_tag=release_tag,
        auditor=args.auditor,
        timestamp=datetime.now(UTC),
        results=results,
        bundle_hash=bundle_hash,
        bundle_files=files,
        overall_pass=overall,
    )
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT_PATH}")
    print(f"overall: {'PASS' if overall else 'FAIL'}; bundle hash: {bundle_hash}")

    if args.strict and not overall:
        print("STRICT mode: required gate(s) failed, refusing to sign.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
