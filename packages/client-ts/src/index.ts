// tcf-accel client (TypeScript). Phase 2 ships a minimal handwritten
// wrapper. The fully-typed surface arrives once `npm run generate` is
// run against a stable spec (Phase 3+).
//
// Until then, callers can use `createClient` for an opaque `fetch` shim
// that knows the v1 base URL and decodes `ErrorEnvelope` payloads.

export interface ErrorEnvelope {
  code: string;
  http_status: number;
  message: string;
  message_localized: Record<string, string>;
  context: Record<string, unknown>;
  phase: number | null;
}

export class TCFAccelError extends Error {
  envelope: ErrorEnvelope;
  constructor(envelope: ErrorEnvelope) {
    super(envelope.message);
    this.envelope = envelope;
    this.name = "TCFAccelError";
  }
}

export interface ClientOptions {
  baseUrl: string;
  token?: string;
  fetch?: typeof fetch;
}

export function createClient(opts: ClientOptions) {
  const f = opts.fetch ?? fetch;
  const headers = (extra?: HeadersInit): HeadersInit => {
    const base: Record<string, string> = { Accept: "application/json" };
    if (opts.token) base.Authorization = `Bearer ${opts.token}`;
    return { ...base, ...((extra as Record<string, string>) ?? {}) };
  };

  async function unwrap(response: Response): Promise<unknown> {
    if (response.ok) {
      const ct = response.headers.get("content-type") ?? "";
      return ct.includes("application/json") ? response.json() : response.text();
    }
    let envelope: ErrorEnvelope;
    try {
      const body = (await response.json()) as { detail: ErrorEnvelope };
      envelope = body.detail;
    } catch {
      envelope = {
        code: "E_BASE_000",
        http_status: response.status,
        message: await response.text(),
        message_localized: {},
        context: {},
        phase: null,
      };
    }
    throw new TCFAccelError(envelope);
  }

  return {
    async get(path: string): Promise<unknown> {
      const r = await f(`${opts.baseUrl}${path}`, { method: "GET", headers: headers() });
      return unwrap(r);
    },
    async post(path: string, body?: unknown): Promise<unknown> {
      const r = await f(`${opts.baseUrl}${path}`, {
        method: "POST",
        headers: headers({ "Content-Type": "application/json" }),
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return unwrap(r);
    },
  };
}
