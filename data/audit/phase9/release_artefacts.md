# Release artefact build — Phase 9

STATUS: pass

> Runs `scripts/release/build_release.py` in the release workflow.
> This file mirrors the script's output for the v1.0.0 tag build.

## Build context

- Release tag: `v1.0.0`
- Registry: `ghcr.io/tcf-accel`
- Build date (UTC): 2026-05-28
- Built by: CI (workflow `release.yml`)
- Signed: yes (cosign keyless via OIDC)

## Per-step results

| Step | OK | Notes |
|---|---|---|
| `git diff --quiet` | ✅ | working tree clean at tag |
| `make verify` | ✅ | lint + typecheck + unit + integration green |
| `pytest tests/pedagogy/launch_audit.py` | ✅ | 8/8 passing; `pedagogy_audit.json` written |
| `scripts/eval_kappa.py --release v1.0.0` | ✅ | κ table emitted; no regression vs Phase 7 baseline |
| `build wheel tcf-accel-shared` | ✅ | `tcf_accel_shared-1.0.0-py3-none-any.whl` |
| `build wheel tcf-accel-sla` | ✅ | `tcf_accel_sla-1.0.0-py3-none-any.whl` |
| `build wheel tcf-accel-ml` | ✅ | `tcf_accel_ml-1.0.0-py3-none-any.whl` |
| `build wheel tcf-accel-content` | ✅ | `tcf_accel_content-1.0.0-py3-none-any.whl` |
| `docker buildx tcf-accel-api` | ✅ | multi-arch linux/amd64,linux/arm64 |
| `docker buildx tcf-accel-worker` | ✅ | multi-arch |
| `docker buildx tcf-accel-web` | ✅ | multi-arch |
| `helm package infra/helm` | ✅ | `tcf-accel-1.0.0.tgz` |
| `syft .` (SBOM) | ✅ | `data/audit/phase9/sbom.spdx.json` written |
| sha256 manifest | ✅ | `dist/release/SHA256SUMS` (47 entries) |
| `cosign sign-blob` | ✅ | `dist/release/SHA256SUMS.sig` |

## Published artefacts

| Artefact | Location |
|---|---|
| Docker images | `ghcr.io/tcf-accel/tcf-accel-{api,worker,web}:v1.0.0` |
| Helm chart | `oci://ghcr.io/tcf-accel/charts/tcf-accel:1.0.0` |
| Python wheels | PyPI: `tcf-accel-{shared,sla,ml,content} 1.0.0` |
| SBOM | `data/audit/phase9/sbom.spdx.json` |
| SHA-256 manifest | `dist/release/SHA256SUMS` (cosign signed) |
| Source tarball | GH release: `tcf-accel-1.0.0.tar.gz` |

## Conclusion

All release artefacts built, signed, and published. STATUS: pass.
