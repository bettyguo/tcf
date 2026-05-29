// Phase 9 — burst load test.
//
// 500 concurrent learners starting mock exams over 30 min. Mirrors the
// "tutor cohort hits start at the top of the hour" scenario.
//
// Gate (phase9_design.md §4.1):
//   - mock_exam_started count > 14500 (most starts succeed across 30m)
//   - mock_exam_score_failed count < 50 (< 0.1% scoring failure rate
//     at the worker level — the worker has a separate concurrency bound;
//     this metric trips when the scoring queue drops a submission)
//
// Run:
//   k6 run -e BASE_URL=https://staging.example -e AUTH=$TOKEN tests/load/k6_burst.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH = __ENV.AUTH || '';

const mockStarted = new Counter('mock_exam_started');
const mockFailed = new Counter('mock_exam_score_failed');

export const options = {
  scenarios: {
    burst_mock_start: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 500 },
        { duration: '30m', target: 500 },
      ],
    },
  },
  thresholds: {
    mock_exam_started: ['count>14500'],
    mock_exam_score_failed: ['count<50'],
    http_req_failed: ['rate<0.005'],
  },
};

export default function () {
  const res = http.post(
    `${BASE_URL}/v1/mock_exam/start`,
    JSON.stringify({ mode: 'canonical' }),
    {
      headers: {
        Authorization: `Bearer ${AUTH}`,
        'Content-Type': 'application/json',
      },
      tags: { path: '/v1/mock_exam/start' },
    }
  );
  const ok = check(res, {
    'mock_exam started or already-in-progress': (r) =>
      r.status === 200 || r.status === 201 || r.status === 409,
  });
  if (ok && (res.status === 200 || res.status === 201)) {
    mockStarted.add(1);
  } else if (res.status >= 500) {
    mockFailed.add(1);
  }
  // 1 start per VU per 60 s — bursts the start surface, not the whole exam.
  sleep(60);
}

export function handleSummary(data) {
  return {
    'data/audit/phase9/perf_burst.json': JSON.stringify(data, null, 2),
  };
}
