// Frontend API client. Wraps the SDK from @tcf-accel/client and adds:
// - cookie-based auth (HttpOnly tcf_auth set by the API)
// - 401 → /v1/auth/refresh → retry-once interceptor
// - typed query-key factory consumed by hooks.ts
// - JSON envelope unwrapping (ErrorEnvelope from Phase 2)
//
// On the server, fetch() is called directly with the cookie forwarded
// from headers(). On the client, `credentials: "include"` keeps the
// cookie attached without us ever reading its value.

import { TCFAccelError, type ErrorEnvelope } from "@tcf-accel/client";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/v1";

export interface ClientOpts {
  fetch?: typeof fetch;
  cookie?: string; // server-side forwarded
}

async function call(
  path: string,
  init: RequestInit,
  opts: ClientOpts = {},
): Promise<unknown> {
  const f = opts.fetch ?? fetch;
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (opts.cookie) headers.set("Cookie", opts.cookie);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let res = await f(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: opts.cookie ? "omit" : "include",
    cache: "no-store",
  });

  if (res.status === 401 && !opts.cookie) {
    const refresh = await f(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (refresh.ok) {
      res = await f(`${BASE}${path}`, {
        ...init,
        headers,
        credentials: "include",
        cache: "no-store",
      });
    }
  }
  return unwrap(res);
}

async function unwrap(res: Response): Promise<unknown> {
  if (res.ok) {
    const ct = res.headers.get("content-type") ?? "";
    return ct.includes("application/json") ? res.json() : res.text();
  }
  let envelope: ErrorEnvelope;
  try {
    const body = (await res.json()) as { detail: ErrorEnvelope };
    envelope = body.detail;
  } catch {
    envelope = {
      code: "E_BASE_000",
      http_status: res.status,
      message: res.statusText,
      message_localized: {},
      context: {},
      phase: null,
    };
  }
  throw new TCFAccelError(envelope);
}

export const api = {
  get: (path: string, opts?: ClientOpts) =>
    call(path, { method: "GET" }, opts),
  post: (path: string, body?: unknown, opts?: ClientOpts) =>
    call(
      path,
      { method: "POST", body: body == null ? undefined : JSON.stringify(body) },
      opts,
    ),
  put: (path: string, body?: unknown, opts?: ClientOpts) =>
    call(
      path,
      { method: "PUT", body: body == null ? undefined : JSON.stringify(body) },
      opts,
    ),
  delete: (path: string, opts?: ClientOpts) =>
    call(path, { method: "DELETE" }, opts),
};

export { TCFAccelError };
