"""Regenerate the TS + Python client SDKs from `docs/api/openapi.v1.yaml`.

Phase 2 ships a thin handwritten wrapper in each client package; this
script is the seam for future regeneration. Phase 3+ runs it when the
spec evolves additively (ADR-016).

Usage:

    uv run python scripts/generate_clients.py            # both
    uv run python scripts/generate_clients.py --target python
    uv run python scripts/generate_clients.py --target typescript

The TS path requires `openapi-typescript` on PATH (provided by
`pnpm --filter @tcf-accel/client install`). The Python path uses
`openapi-python-client` if available; otherwise it leaves the
handwritten wrapper untouched and prints a hint.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "docs" / "api" / "openapi.v1.yaml"
TS_OUT = REPO_ROOT / "packages" / "client-ts" / "src" / "types.gen.ts"


def _run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, check=False).returncode  # noqa: S603 — args constructed locally


def generate_typescript() -> int:
    if shutil.which("openapi-typescript") is None:
        print(
            "openapi-typescript not on PATH; run `pnpm install` in packages/client-ts first.",
            file=sys.stderr,
        )
        return 2
    TS_OUT.parent.mkdir(parents=True, exist_ok=True)
    return _run(["openapi-typescript", str(SPEC), "-o", str(TS_OUT)])


def generate_python() -> int:
    if shutil.which("openapi-python-client") is None:
        print(
            "openapi-python-client not installed. Phase 2 ships a handwritten "
            "wrapper at packages/client-py/src/tcf_accel_client/client.py; "
            "regeneration is deferred until Phase 3.",
            file=sys.stderr,
        )
        return 0
    return _run([
        "openapi-python-client", "generate",
        "--path", str(SPEC),
        "--output-path", str(REPO_ROOT / "packages" / "client-py" / "src" / "tcf_accel_client" / "_generated"),
        "--overwrite",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate client SDKs from the OpenAPI spec.")
    parser.add_argument(
        "--target",
        choices=("typescript", "python", "both"),
        default="both",
    )
    args = parser.parse_args(argv)
    rc = 0
    if args.target in {"typescript", "both"}:
        rc |= generate_typescript()
    if args.target in {"python", "both"}:
        rc |= generate_python()
    return rc


if __name__ == "__main__":
    sys.exit(main())
