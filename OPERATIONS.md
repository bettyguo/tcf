# OPERATIONS

> Runbooks for the operator. Read this once before you stand up the
> system; consult it when something pages you. Pair with
> `ARCHITECTURE.md` (system shape) and `SECURITY.md` (disclosure
> policy).

This document is intentionally terse and command-first. It assumes
you've read `README.md` and `ARCHITECTURE.md`.

---

## 1. First-time stand-up

### 1.1 Prerequisites

- Linux / macOS / WSL2 on Windows (Windows-native: use
  `scripts/windows_dev.ps1`).
- Docker Engine 24+ with `docker compose` v2.
- `make`, `git`, `curl`.
- (Optional) `cosign`, `syft`, `trivy`, `gitleaks` for release work.

### 1.2 Bring up the stack

```bash
git clone <repo-url> && cd tcf-accel
cp .env.example .env          # then edit .env (see §3 below)
make setup                    # Python + JS deps + pre-commit
docker compose up -d          # Postgres + Redis + API + Worker + Web
```

Cold-start probe (Phase 9 §4.2 gate; ≤ 60 s):

```bash
k6 run tests/load/k6_cold_start.js
```

Verify health:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/v1/health?check=db
curl http://localhost:8000/v1/health?check=redis
```

### 1.3 Seed the bank (one-time, ~6 h on a 16-core machine)

```bash
make setup-models                # one-time pull of Whisper-fr + CEFR + embeddings
python scripts/seed_bank.py      # ingests open-license sources only
python scripts/seed_bank.py --audit-only   # Phase 9 distribution check
```

For news-audio ingestion (RFI, TV5MONDE, ICI Première, Radio-Canada),
see `docs/runbooks/news_ingest.md` (Phase 3). Respect publisher TOS;
cached content lives in `data/` (gitignored) and is **never**
redistributed.

---

## 2. The supported deployments

### 2.1 Solo / self-hosted

`infra/docker-compose.yml`. The stack defaults to single-tenant
local-only (ADR-0017). No internet egress is required to operate
the core loop; the cloud LLM gateway is opt-in only.

### 2.2 Institutional (Helm)

`infra/helm/` chart. Single-tenant per learner. Multi-tenant is on
the v1.1 roadmap (`docs/roadmap/v1.1.md`); do not promise
multi-tenancy to your stakeholders at v1.0.

```bash
helm install tcf-accel oci://ghcr.io/tcf-accel/charts/tcf-accel \
  --version 1.0.0 \
  -f infra/helm/values.yaml
```

---

## 3. Environment variables (the load-bearing ones)

Copy `.env.example` to `.env` and edit:

| Var | Default | Purpose |
|---|---|---|
| `TCF_DB_URL` | `postgresql+asyncpg://tcf:tcf@db:5432/tcf` | Postgres DSN |
| `TCF_REDIS_URL` | `redis://redis:6379/0` | Redis broker + cache |
| `TCF_JWT_SECRET` | *(unset → server refuses to start)* | 32+ random bytes; rotate quarterly |
| `TCF_JWT_ACCESS_TTL` | `900` | 15 min |
| `TCF_JWT_REFRESH_TTL` | `604800` | 7 d |
| `TCF_PRIVACY_MODE` | `local_only` | Set to `cloud_opt_in` only after legal review |
| `TCF_LLM_GATEWAY` | *(empty)* | Set only when `TCF_PRIVACY_MODE=cloud_opt_in` |
| `TCF_LLM_MODEL` | `claude-sonnet-4-6` | Per ADR-0009 |
| `TCF_LOG_LEVEL` | `INFO` | `DEBUG` only with PII scrubber verified |

Secret hygiene: never check `.env` in; `gitleaks` runs in pre-commit
and CI to enforce.

---

## 4. JWT secret rotation

Cadence: quarterly.

```bash
NEW_SECRET=$(openssl rand -hex 32)
docker compose exec api python -c "print('TCF_JWT_SECRET=' + '$NEW_SECRET')"
# Edit .env, then:
docker compose restart api
```

Active sessions are invalidated. Refresh tokens are rotated on
next use. Users see a "please sign in again" prompt.

If you operate behind a reverse proxy with TLS termination, ensure
HSTS and the security headers from
`apps/api/.../middleware/security_headers.py` reach the client
(they're set on the API response; the proxy must not strip them).

---

## 5. Backups

Postgres:

```bash
# nightly cron entry
0 2 * * * docker compose exec -T db pg_dump -U tcf tcf | gzip > /backups/tcf-$(date +%F).sql.gz
```

Retention: 30 days local, 90 days off-site (operator responsibility).

Redis: ephemeral; do not back up. The cache is rebuilt from
Postgres state.

Item bank (`data/items/`):

- Open-license items: backed up with the DB (they live in
  Postgres).
- News-cached items: never backed up off-machine; license forbids
  redistribution.

---

## 6. Security headers verification

```bash
curl -sI https://your-staging-url | grep -E '^(strict-transport|content-security|x-frame|x-content|referrer|permissions)'
```

Expected:

- `strict-transport-security: max-age=31536000; includeSubDomains; preload`
- `content-security-policy: default-src 'self'; ...`
- `x-frame-options: DENY`
- `x-content-type-options: nosniff`
- `referrer-policy: strict-origin-when-cross-origin`
- `permissions-policy: microphone=(self), camera=(), geolocation=()`

If any header is missing, the proxy is stripping it. Fix the proxy
config, not the API.

---

## 7. Database maintenance

### 7.1 Migrations

```bash
docker compose exec api alembic upgrade head
```

Migrations are forward-only at v1.0; rollbacks happen via restore
from backup (§5).

### 7.2 Vacuum / analyze

Postgres autovacuum is on by default. Add a weekly analyze:

```bash
0 3 * * 0 docker compose exec -T db psql -U tcf -d tcf -c "ANALYZE;"
```

### 7.3 Nightly IRT refit

The worker runs the IRT refit nightly (R-012). Watch the elapsed
time:

```bash
docker compose logs worker | grep "irt_refit_elapsed"
```

Alarm at > 1 hour (per ADR-0013 + R-012). If exceeded, the
documented fallback is streaming variational IRT; the second
fallback is CEFR-band sharding.

---

## 8. Worker queue health

```bash
docker compose exec redis redis-cli llen celery
docker compose exec redis redis-cli llen celery.scoring
docker compose exec redis redis-cli llen celery.mock_grading
```

Alarms:

| Queue | Warn | Critical |
|---|---|---|
| `celery` | > 100 | > 500 |
| `celery.scoring` | > 50 | > 200 |
| `celery.mock_grading` | > 20 | > 100 |

If `celery.scoring` is climbing, the LLM gateway is slow or
rate-limited. Check `apps/worker` logs for `RateLimitError`.

---

## 9. Schedule-cache invalidation alarms

R-011 (schedule-cache invalidation bug). The worker keeps a
version key per user; the API reads from the cache via a
Lua-scripted atomic get. The cache-hit-rate is exposed as a
metric.

```bash
# cache hit rate over the last 5m
docker compose exec api curl -s http://localhost:8000/metrics | grep schedule_cache_hit_rate
```

Alarm: < 0.95 cache hit rate sustained for > 10 min. Cause is
usually a worker that died mid-rebuild; restart `worker`.

---

## 10. Real-learner trajectory capture (post-launch)

The post-launch operational discipline (closing the loop from
`PEDAGOGY.md §3`):

```bash
# Weekly: export anonymised posterior trajectories for the
# pedagogy team to compare against the simulator.
docker compose exec api python -m tcf_accel_api.scripts.export_trajectories \
  --since "7 days ago" --out /tmp/trajectories.jsonl
```

The export anonymises user IDs (HMAC under a salt the operator
keeps; never published with the data). The pedagogy team uses
these to recalibrate `LEARNING_RATE_PER_MINUTE` for v1.1.

If a learner trajectory diverges from the simulator by > 1 NCLC
over 4 weeks, the worker fires a `posterior_divergence_alert`
(ADR-034 extended in `OPERATIONS.md`). The action: re-run the
diagnostic; do not blame the learner.

---

## 11. Cost of operation

Honest cost breakdown (also in `LIMITATIONS.md §9`):

| Mode | LLM cost / learner / week | Notes |
|---|---|---|
| `local_only` | $0 | Modulo your electricity |
| `cloud_opt_in`, 2 mocks/week | $1.50–4.00 | At `claude-sonnet-4-6` rates |
| `cloud_opt_in`, daily LLM feedback | $3–8 | Phase 7 §6 budget |

For a 12-week prep arc, budget $10–25 per learner under the cloud
opt-in. The inflation guard (ADR-040) gates expensive re-calls,
so a misconfigured learner won't burn 10× the budget on a single
broken rubric.

---

## 12. Incident response

### 12.1 The five P0 alerts

| Alert | Page | First action |
|---|---|---|
| API 5xx rate > 1% / 5min | Y | `docker compose logs api --tail 200`; restart if recent deploy |
| Worker queue critical | Y | §8; usually LLM gateway issue |
| Schedule-cache hit rate < 0.9 / 10min | Y | §9; restart worker |
| `posterior_divergence_alert` storm (> 5 / hr) | Y | Pedagogy team review; recalibrate |
| Disk > 90% | Y | Check `data/` cache; rotate news-audio cache |

### 12.2 Disclosure

Security issues: `SECURITY.md`. Do not file public issues for
security; email the address in `SECURITY.md` with a GPG-encrypted
report.

---

## 13. Upgrading to v1.1 (when it lands)

`v1.0.x` patch releases are drop-in. `v1.1.0` will ship a
migration guide; expect ~30 min downtime for the IRT
recalibration step.

Do not run `make` targets that pull from `main` between releases
on a production instance. Pin to the release tag.

---

## 14. The escalation chain

For the operator running this for themselves: there is no
escalation chain. Read the docs, file an issue, wait.

For institutional deployments: maintain your own escalation chain
internally. The OSS project does not provide SLAs.

---

## 15. Closing posture

The operator is the data controller. The system is honest about
its limits (`LIMITATIONS.md`); the operator should be honest
with their learners about what the operator can and cannot do.
Don't add features the underlying system doesn't provide; don't
hide limitations the system documents.

When in doubt: read the ADR. The ADRs are the load-bearing
record of the project's decisions.
