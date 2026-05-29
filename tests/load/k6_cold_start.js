// Phase 9 — cold-start probe.
//
// Verifies the dev stack reaches a healthy state within 60 s of
// `docker compose up`. The operator runs this immediately after
// `docker compose up -d`; the script polls /healthz on api + worker +
// db endpoints and asserts all three return 200 within 60 s.
//
// Gate (phase9_design.md §4.2): cold-start ≤ 60 s.
//
// Run:
//   docker compose up -d && k6 run tests/load/k6_cold_start.js

import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const WORKER_URL = __ENV.WORKER_URL || 'http://localhost:8001';

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    'checks{check:api_healthy}': ['rate==1'],
    'checks{check:worker_healthy}': ['rate==1'],
    'checks{check:db_healthy}': ['rate==1'],
    'checks{check:cold_start_within_60s}': ['rate==1'],
  },
};

function waitForHealthy(url, name, deadlineMs) {
  while (Date.now() < deadlineMs) {
    const r = http.get(url, { timeout: '2s' });
    if (r.status === 200) {
      return true;
    }
    // No k6 builtin sleep with sub-second granularity in this VU loop;
    // a 500 ms busy-wait keeps the test bounded.
    const t0 = Date.now();
    while (Date.now() - t0 < 500) {}
  }
  console.error(`${name} not healthy by deadline`);
  return false;
}

export default function () {
  const start = Date.now();
  const deadline = start + 60_000;
  const api = waitForHealthy(`${BASE_URL}/healthz`, 'api', deadline);
  const worker = waitForHealthy(`${WORKER_URL}/healthz`, 'worker', deadline);
  const db = waitForHealthy(`${BASE_URL}/v1/health?check=db`, 'db', deadline);
  const elapsed = Date.now() - start;
  check(null, {
    api_healthy: () => api,
    worker_healthy: () => worker,
    db_healthy: () => db,
    cold_start_within_60s: () => elapsed < 60_000,
  });
  console.log(`cold-start elapsed: ${elapsed} ms`);
}

export function handleSummary(data) {
  return {
    'data/audit/phase9/perf_cold_start.json': JSON.stringify(data, null, 2),
  };
}
