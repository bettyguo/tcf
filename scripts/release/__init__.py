"""Phase 9 release pipeline scripts.

`build_release.py` — builds wheels, Docker images, Helm chart, SBOM,
and SHA-256 manifest. `sign_audit_report.py` — walks the launch
checklist and emits `LAUNCH_READINESS_REPORT.md`.

See `phase9_design.md §11` for the full flow.
"""
