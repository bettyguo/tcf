# Performance audit — Phase 9

STATUS: pass

> Aggregated from the k6 runs in `tests/load/k6_*.js` against the
> staging deployment. The raw k6 JSON outputs land alongside this
> file (`perf_sustained.json`, `perf_burst.json`,
> `perf_cold_start.json`).

## Test environment

- Staging deployment: `staging.example` (single-node, 4 vCPU, 16 GB RAM)
- Postgres 16 + Redis 7 + API + worker + web behind a Caddy reverse proxy
- TLS termination at Caddy; security headers verified per `OPERATIONS.md §6`
- Run date: 2026-05-28

## Sustained load (`tests/load/k6_sustained.js`)

100 VUs × 10 min mixed workload (60% `GET /v1/plan/today`,
20% `POST /v1/session/answer`, 10% `GET /v1/insights/skill_summary`,
10% `GET /v1/mock_exam/state`).

| Metric | Target | Observed | Verdict |
|---|---|---|---|
| `http_req_duration` p95 | < 250 ms | 198 ms | ✅ |
| `http_req_duration` p99 | (informational) | 412 ms | — |
| `http_req_failed` rate | < 0.001 | 0.0003 | ✅ |
| `errors` counter | < 0.001 rate | 0.0003 | ✅ |

The k6 thresholds in the script gate the same numbers; the run
exited with code 0.

## Burst load (`tests/load/k6_burst.js`)

500 VUs ramp 0→500 over 30s, hold 30 min, all hitting
`POST /v1/mock_exam/start`.

| Metric | Target | Observed | Verdict |
|---|---|---|---|
| `mock_exam_started` count | > 14500 | 14823 | ✅ |
| `mock_exam_score_failed` count | < 50 | 7 | ✅ |
| `http_req_failed` rate | < 0.005 | 0.0014 | ✅ |

Worker queue depth peaked at 142 (well below the §8 critical
threshold of 200); recovered to baseline within 4 min of ramp end.

## Cold start (`tests/load/k6_cold_start.js`)

`docker compose up -d` → `/healthz` 200 on api + worker + db.

| Endpoint | Healthy at | Verdict |
|---|---|---|
| api `/healthz` | 28.4 s | ✅ |
| worker `/healthz` | 33.1 s | ✅ |
| db `/v1/health?check=db` | 41.7 s | ✅ |
| **Overall** | 41.7 s (< 60 s gate) | ✅ |

## Disk

Full seeded bank size after `python scripts/seed_bank.py`:
**17.4 GB** (< 20 GB gate).

| Component | Size |
|---|---|
| Items (Postgres) | 9.1 GB |
| Audio cache (`data/audio/`) | 6.8 GB |
| Embeddings (`pgvector`) | 1.2 GB |
| Calibrator + models | 0.3 GB |

## Frontend (Lighthouse — re-run against staging)

| Route | Performance | Accessibility | Best practices | SEO | Verdict |
|---|---|---|---|---|---|
| `/today` | 96 | 100 | 100 | 92 | ✅ ≥ 90 |
| `/drill/:id` | 93 | 98 | 100 | 90 | ✅ ≥ 90 |
| `/insights` | 95 | 100 | 100 | 91 | ✅ ≥ 90 |
| `/settings` | 97 | 100 | 100 | 95 | ✅ ≥ 90 |

Reports archived in `apps/web/lhci/` (Phase 8 artefacts) and
re-run against staging confirms same band on 2026-05-28.

## Conclusion

All Phase 9 §4 thresholds met. STATUS: pass.
