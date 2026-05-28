# Security Policy

## Supported Versions

`tcf-accel` is pre-1.0 during Phases 1–9 of the build. Once `v1.0.0` is tagged
(Phase 9), the latest minor release and the previous minor will receive
security fixes.

| Version | Supported |
|---|---|
| `v1.0.x` | ✅ (post-Phase-9) |
| pre-`v1.0` | ⚠️ best-effort during active build |

## Reporting a Vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.**

Email the maintainers privately, with subject line `[tcf-accel security]`:

- Preferred: open a [GitHub Security Advisory](https://github.com/) in the repository (private; triaged by maintainers).
- Alternative: email the maintainer listed in the project README.

We aim to acknowledge within **3 business days** and ship a fix or disclosure
plan within **14 business days** for High/Critical findings. Lower-severity
findings are batched into the next minor release.

What to include:

- A description of the vulnerability and the affected component(s).
- Steps to reproduce (ideally a minimal proof-of-concept).
- The version / commit hash you tested against.
- Your assessment of severity (Low / Medium / High / Critical).
- Whether you intend to publish; we appreciate coordinated disclosure.

We will credit reporters in the release notes unless they prefer otherwise.

## In-Scope Vulnerabilities

- Authentication / authorization bypass on any `/v1/...` endpoint.
- IDOR (insecure direct object reference) across users.
- Injection (SQL, command, prompt-injection of the LLM gateway, NoSQL).
- Sensitive data leakage (learner audio, learner text, PII in logs).
- Server-side request forgery via the ingestion pipeline.
- Container-escape or privileged-execution issues in the published Docker images.
- Supply-chain vulnerabilities in the published artifacts (Docker images, PyPI packages, npm packages).

## Out of Scope

- Findings requiring physical access to a learner's device.
- Self-XSS or theoretical issues without a demonstrated impact.
- Reports against unsupported pre-1.0 commits (we will accept these but cannot
  guarantee a fix in the unsupported version).
- Findings in third-party services the operator chooses to enable (e.g., the
  OpenAI Whisper API in cloud-fallback mode).

## Privacy Defaults (Cross-Reference)

Several "common" web findings are not applicable here because of our defaults:

- Learner audio **does not** leave the device unless `privacy_mode=cloud_optin`
  is explicitly enabled. ASR runs locally. See `RATIONALE.md` R-003 and master
  prompt §6.4.
- The system collects **no analytics, no third-party tracking, no telemetry**
  by default. Phase 9 audits this.
- Learner text and audio **never** appear in logs or traces. The structured
  logger redacts at the field level. Phase 2 §2.6 specifies; Phase 9 audits.

If you find a deviation from these defaults, that is a vulnerability — please
report it.

## Hardening Roadmap

Tracked in Phase 9 (`09_QUALITY_AUDIT_AND_LAUNCH.md` §2.2): OWASP Top 10 review,
ZAP scan, dependency CVE monitoring (Renovate), security headers, JWT rotation,
input-size limits, secrets scanning, license-and-CVE gate in CI.
