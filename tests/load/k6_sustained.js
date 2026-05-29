// Phase 9 — sustained load test.
//
// 100 concurrent learners hitting the mixed-drill workload for 10 min.
// Gate (phase9_design.md §4.1):
//   - http_req_duration p95 < 250 ms
//   - http_req_failed rate < 0.001
//
// Run:
//   k6 run -e BASE_URL=https://staging.example -e AUTH=$TOKEN tests/load/k6_sustained.js
//
// The script avoids any data mutation that would persist across runs
// (the POST /v1/session/answer call targets a no-op practice session
// id, documented in OPERATIONS.md §8). The auth token is a service-
// account read-mostly token; see OPERATIONS.md §4.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH = __ENV.AUTH || '';

const errorRate = new Rate('errors');

export const options = {
  scenarios: {
    sustained_mixed: {
      executor: 'constant-vus',
      vus: 100,
      duration: '10m',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<250'],
    http_req_failed: ['rate<0.001'],
    errors: ['rate<0.001'],
  },
};

function authedGet(path) {
  return http.get(`${BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${AUTH}` },
    tags: { path },
  });
}

function authedPost(path, body) {
  return http.post(`${BASE_URL}${path}`, JSON.stringify(body), {
    headers: {
      Authorization: `Bearer ${AUTH}`,
      'Content-Type': 'application/json',
    },
    tags: { path },
  });
}

export default function () {
  const roll = Math.random();
  let res;
  if (roll < 0.6) {
    res = authedGet('/v1/plan/today');
  } else if (roll < 0.8) {
    res = authedPost('/v1/session/answer', {
      session_id: '00000000-0000-0000-0000-000000000000',
      item_id: '00000000-0000-0000-0000-000000000001',
      response: { kind: 'mcq', choice: 0 },
      elapsed_ms: 4200,
    });
  } else if (roll < 0.9) {
    res = authedGet('/v1/insights/skill_summary');
  } else {
    res = authedGet('/v1/mock_exam/state');
  }
  const ok = check(res, {
    'status is 2xx or 4xx (not 5xx)': (r) => r.status < 500,
  });
  errorRate.add(!ok);
  // Pace ~5 RPS per VU.
  sleep(0.2);
}

export function handleSummary(data) {
  return {
    'data/audit/phase9/perf_sustained.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data),
  };
}

function textSummary(data) {
  const p95 = data.metrics.http_req_duration.values['p(95)'].toFixed(1);
  const fail = (data.metrics.http_req_failed.values.rate * 100).toFixed(3);
  return `sustained p95=${p95}ms failrate=${fail}%\n`;
}
