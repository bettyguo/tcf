r"""Export the running FastAPI app's OpenAPI spec to a YAML file.

Usage:

    uv run python -m tcf_accel_api.scripts.export_openapi \\
        --output docs/api/openapi.v1.yaml

Verify mode (CI):

    uv run python -m tcf_accel_api.scripts.export_openapi \\
        --check docs/api/openapi.v1.yaml

The verify mode exits 0 if the on-disk file equals the running app's
emitted spec, and 1 on drift. This is the contract-stability gate
(ADR-016 + `phase2_design.md §4.5`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from tcf_accel_api.main import create_app


def _build_spec() -> dict[str, Any]:
    """Build a *deterministic* OpenAPI spec dict from the app.

    FastAPI's default `openapi()` produces a dict whose key order varies
    by version; we serialize via `yaml.safe_dump(sort_keys=True)` to
    pin the bytes-level shape.
    """
    app = create_app()
    return app.openapi()


def _dump(spec: dict[str, Any]) -> str:
    """Render the spec to canonical YAML."""
    return yaml.safe_dump(spec, sort_keys=True, allow_unicode=True, default_flow_style=False)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Export or verify the OpenAPI spec.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path, help="Write the spec to this path.")
    group.add_argument(
        "--check",
        type=Path,
        help="Verify that the spec on disk matches the running app; exit 1 on drift.",
    )
    args = parser.parse_args(argv)

    rendered = _dump(_build_spec())

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        return 0

    on_disk = args.check.read_text(encoding="utf-8") if args.check.exists() else ""
    if on_disk == rendered:
        return 0

    sys.stderr.write(
        f"OpenAPI drift detected: {args.check} differs from the running app's spec.\n"
        f"Re-run: uv run python -m tcf_accel_api.scripts.export_openapi --output {args.check}\n",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
