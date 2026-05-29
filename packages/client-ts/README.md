# @tcf-accel/client (TypeScript)

TypeScript client SDK for the tcf-accel API. Phase 2 ships a thin
`fetch`-based wrapper that knows the `/v1/` base URL and decodes the
canonical `ErrorEnvelope` shape. Full type generation (`types.gen.ts`)
runs via `npm run generate` once the spec stabilizes.

## Usage

```ts
import { createClient } from "@tcf-accel/client";

const client = createClient({ baseUrl: "http://localhost:8000", token: "…" });
const health = await client.get("/v1/health");
```

## Regeneration

```bash
pnpm --filter @tcf-accel/client run generate
```

This emits `src/types.gen.ts` from `../../docs/api/openapi.v1.yaml`.
The generated file is committed alongside the wrapper.
