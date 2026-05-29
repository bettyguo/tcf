"""Phase 9 — build the v1.0.0 release artefacts.

Steps (mirrors `phase9_design.md §11`):

1. Validate working tree clean; current branch sane.
2. Run `make verify` (lint + typecheck + unit + integration).
3. Run `pytest tests/pedagogy/launch_audit.py` (pedagogy gate).
4. Run `python scripts/eval_kappa.py --release v1.0.0` (κ gate).
5. Build wheels for tcf-accel-{shared,sla,ml,content}.
6. Build Docker images for api, worker, web (multi-arch).
7. Render Helm chart values.
8. Generate SBOM via `syft .`.
9. Generate SHA-256 manifest covering built artefacts + audit JSON.
10. (Optional) cosign sign-blob over the manifest.

The script is *driver-style*: it shells out to the canonical tools
rather than re-implementing build logic in Python. Each step writes a
brief status line to ``data/audit/phase9/release_artefacts.md`` so
``sign_audit_report.py`` can verify the gate.

The script can be run in *dry-run* mode (``--dry-run``) which prints
every command without executing it. Use this in the first release
rehearsal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
AUDIT_DIR: Final[Path] = REPO_ROOT / "data" / "audit" / "phase9"
ARTEFACT_DIR: Final[Path] = REPO_ROOT / "dist" / "release"
STATUS_FILE: Final[Path] = AUDIT_DIR / "release_artefacts.md"
MANIFEST_FILE: Final[Path] = ARTEFACT_DIR / "SHA256SUMS"
SBOM_FILE: Final[Path] = AUDIT_DIR / "sbom.spdx.json"

# Default image registry; overridden via --registry.
DEFAULT_REGISTRY: Final[str] = "ghcr.io/tcf-accel"


@dataclass
class StepResult:
    name: str
    cmd: list[str]
    ok: bool
    notes: str = ""


@dataclass
class BuildContext:
    release_tag: str
    registry: str
    dry_run: bool
    sign: bool
    steps: list[StepResult] = field(default_factory=list)

    def run(self, name: str, cmd: list[str], *, check: bool = True) -> StepResult:
        if self.dry_run:
            print(f"[dry-run] {name}: {' '.join(cmd)}")
            res = StepResult(name=name, cmd=cmd, ok=True, notes="dry-run")
            self.steps.append(res)
            return res
        print(f"[run] {name}: {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        ok = proc.returncode == 0
        notes = (proc.stdout or "")[-1000:] + (proc.stderr or "")[-1000:]
        res = StepResult(name=name, cmd=cmd, ok=ok, notes=notes)
        self.steps.append(res)
        if check and not ok:
            print(f"step failed: {name}\n{notes}", file=sys.stderr)
        return res


def step_validate_tree(ctx: BuildContext) -> None:
    ctx.run("git status clean", ["git", "diff", "--quiet"], check=False)


def step_make_verify(ctx: BuildContext) -> None:
    target = "verify"
    ctx.run("make verify", ["make", target])


def step_pedagogy_gate(ctx: BuildContext) -> None:
    ctx.run(
        "pytest pedagogy launch_audit",
        ["pytest", "-q", "tests/pedagogy/launch_audit.py"],
    )


def step_kappa_gate(ctx: BuildContext) -> None:
    ctx.run(
        "scripts/eval_kappa.py",
        ["python", "scripts/eval_kappa.py", "--release", ctx.release_tag],
        check=False,  # Phase 7 script may take optional args; allow soft fail
    )


def step_build_wheels(ctx: BuildContext) -> None:
    ARTEFACT_DIR.mkdir(parents=True, exist_ok=True)
    for pkg in ("shared", "sla", "ml", "content"):
        ctx.run(
            f"build wheel tcf-accel-{pkg}",
            [
                "python",
                "-m",
                "build",
                "--wheel",
                "--outdir",
                str(ARTEFACT_DIR),
                str(REPO_ROOT / "packages" / pkg),
            ],
            check=False,
        )


def step_build_docker(ctx: BuildContext) -> None:
    for svc, ctx_dir in (
        ("api", "apps/api"),
        ("worker", "apps/worker"),
        ("web", "apps/web"),
    ):
        tag = f"{ctx.registry}/tcf-accel-{svc}:{ctx.release_tag}"
        ctx.run(
            f"docker buildx tcf-accel-{svc}",
            [
                "docker",
                "buildx",
                "build",
                "--platform",
                "linux/amd64,linux/arm64",
                "--tag",
                tag,
                "--load",
                ctx_dir,
            ],
            check=False,
        )


def step_render_helm(ctx: BuildContext) -> None:
    ctx.run(
        "helm package infra/helm",
        ["helm", "package", "infra/helm", "--destination", str(ARTEFACT_DIR)],
        check=False,
    )


def step_sbom(ctx: BuildContext) -> None:
    SBOM_FILE.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("syft") is None:
        ctx.steps.append(
            StepResult(
                name="syft sbom",
                cmd=["syft", "."],
                ok=False,
                notes="syft not installed — SBOM skipped (operator must install)",
            )
        )
        return
    ctx.run(
        "syft .",
        ["syft", ".", "-o", "spdx-json", "--file", str(SBOM_FILE)],
        check=False,
    )


def step_manifest(ctx: BuildContext) -> None:
    """SHA-256 manifest over built artefacts + audit JSON files."""
    files: list[Path] = []
    if ARTEFACT_DIR.exists():
        files.extend(sorted(p for p in ARTEFACT_DIR.rglob("*") if p.is_file()))
    if AUDIT_DIR.exists():
        files.extend(
            sorted(p for p in AUDIT_DIR.rglob("*") if p.is_file() and p.suffix == ".json")
        )
    lines = []
    for f in files:
        if not f.exists():
            continue
        if f == MANIFEST_FILE:
            continue
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        rel = f.relative_to(REPO_ROOT).as_posix()
        lines.append(f"{h}  {rel}")
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.steps.append(
        StepResult(
            name="sha256 manifest",
            cmd=["sha256sum", "..."],
            ok=True,
            notes=f"wrote {MANIFEST_FILE} ({len(lines)} entries)",
        )
    )


def step_cosign(ctx: BuildContext) -> None:
    if not ctx.sign:
        return
    if shutil.which("cosign") is None:
        ctx.steps.append(
            StepResult(
                name="cosign sign",
                cmd=["cosign", "sign-blob"],
                ok=False,
                notes="cosign not installed — release unsigned",
            )
        )
        return
    ctx.run(
        "cosign sign-blob",
        [
            "cosign",
            "sign-blob",
            "--yes",
            "--output-signature",
            str(MANIFEST_FILE.with_suffix(".sig")),
            str(MANIFEST_FILE),
        ],
        check=False,
    )


def write_status(ctx: BuildContext) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    overall = all(s.ok for s in ctx.steps if "dry-run" not in s.notes) or ctx.dry_run
    lines = [
        f"# Release artefact build — {ctx.release_tag}",
        "",
        f"- Timestamp (UTC): {datetime.now(UTC).isoformat()}",
        f"- Registry: `{ctx.registry}`",
        f"- Dry-run: {ctx.dry_run}",
        f"- Cosign signed: {ctx.sign}",
        f"- Manifest: `{MANIFEST_FILE.relative_to(REPO_ROOT).as_posix()}`",
        "",
        f"STATUS: {'pass' if overall else 'fail'}",
        "",
        "## Steps",
        "",
        "| Step | OK | Notes |",
        "|---|---|---|",
    ]
    for s in ctx.steps:
        ok = "✅" if s.ok else "❌"
        notes = s.notes.replace("\n", " ").replace("|", "\\|")[:200]
        lines.append(f"| {s.name} | {ok} | {notes} |")
    STATUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {STATUS_FILE}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the v1.0.0 release.")
    parser.add_argument("--release-tag", default="v1.0.0")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every command without executing it.",
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Cosign sign the manifest (requires cosign in PATH + key material).",
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help=(
            "Step names to skip. Useful when a step is intentionally manual on "
            "a given environment (e.g. 'docker' on a machine without buildx)."
        ),
    )
    args = parser.parse_args(argv)

    ctx = BuildContext(
        release_tag=args.release_tag,
        registry=args.registry,
        dry_run=args.dry_run,
        sign=args.sign,
    )

    steps = [
        ("tree", step_validate_tree),
        ("verify", step_make_verify),
        ("pedagogy", step_pedagogy_gate),
        ("kappa", step_kappa_gate),
        ("wheels", step_build_wheels),
        ("docker", step_build_docker),
        ("helm", step_render_helm),
        ("sbom", step_sbom),
        ("manifest", step_manifest),
        ("cosign", step_cosign),
    ]
    for name, fn in steps:
        if name in args.skip:
            ctx.steps.append(
                StepResult(name=f"{name} (skipped)", cmd=[], ok=True, notes="skipped via --skip")
            )
            continue
        fn(ctx)

    write_status(ctx)
    overall = all(s.ok for s in ctx.steps if "dry-run" not in s.notes and "skipped" not in s.notes)
    return 0 if overall or ctx.dry_run else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
