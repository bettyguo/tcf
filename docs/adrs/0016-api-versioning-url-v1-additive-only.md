# ADR-0016: API versioning — URL `/v1/`, additive-only; breaking changes ship under `/v2/` with ≥ 6 mo overlap

- **Date**: 2026-05-27
- **Status**: accepted
- **Deciders**: Lead engineer, Backend lead, Frontend lead
- **Phase**: 2

## Context

Phase 2 freezes the `/v1/` API surface (`02_ARCHITECTURE.md §2.4`,
`phase2_design.md §4`). 28 routes ship as 501-stubs; Phases 3–8 fill
them in. Throughout that period, the wire shape is the contract that
the generated TS/Py clients
(`packages/client-ts`, `packages/client-py`) consume.

Three versioning strategies were considered:

1. URL versioning (`/v1/...`, `/v2/...`).
2. Header versioning (`Accept: application/vnd.tcf-accel.v1+json`).
3. Implicit always-latest with no version namespace.

The forces:

- **Generated clients** lock to a spec; changing the spec without a
  version bump silently breaks consumers.
- **Self-hosted operators** may run the API behind a CDN or reverse
  proxy that doesn't easily route on headers; URL-based versioning is
  the path of least operational friction.
- **Long-tail of consumers**: third-party scripts, CLI tools, and
  archival data exports may call `/v1/data/export` years after we ship
  `/v2/`.

## Decision

**URL versioning** with the following rules:

1. **All routes live under `/v1/`** (except `/healthz`, which is
   unversioned by convention for liveness probes).
2. **Additive changes only under `/v1/`**:
   - New routes are allowed.
   - New optional fields on requests are allowed.
   - New fields on responses are allowed (clients must ignore unknown
     fields).
   - New enum values on response fields require a `SCHEMA_VERSION`
     minor bump + a CHANGELOG entry.
3. **Breaking changes ship under `/v2/`**. A breaking change is any
   one of:
   - Removing a route.
   - Removing a field from a request or response.
   - Renaming a field.
   - Changing the type or shape of an existing field.
   - Changing an enum value's meaning.
   - Changing an error code's HTTP status (ADR-014).
4. **`/v1/` is supported for ≥ 6 months** past the `/v2/` GA date.
   The sunset window is announced in CHANGELOG.md when `/v2/` GAs.
5. **Sunset behavior**: after the 6-month window, `/v1/` routes
   respond with `410 Gone` + a `Sunset:` header + a `Link:` header
   pointing at the migration doc.
6. **`SCHEMA_VERSION` discipline**: minor bumps for additive `/v1/`
   changes; major bump (1.0.0 → 2.0.0) only when `/v2/` GAs.
7. **The OpenAPI spec on disk is the law**: `docs/api/openapi.v1.yaml`
   is committed; CI verifies the running app emits the identical
   spec. A diff = an intentional, ADR-tracked change.

## Consequences

- **Positive**:
  - Operators routing through a CDN don't need header-based routing
    rules; path prefix is universal.
  - Clients can pin to a version by configuring a base URL; no
    Accept-header negotiation logic.
  - The 6-month overlap means consumers can plan migrations against
    a concrete sunset date.
  - The "additive only" rule under `/v1/` is mechanically checkable
    via OpenAPI diff in CI.
- **Negative**:
  - Eventually we will operate `/v1/` and `/v2/` side-by-side for 6+
    months. This doubles route handlers during the overlap. Mitigated
    by a *shim layer*: `/v1/` handlers in the overlap window translate
    to the `/v2/` Pydantic models, rather than duplicating business
    logic.
  - URL versioning is sometimes called "REST-naive" by header-versioning
    advocates. We do not find this argument persuasive given the
    operational benefits.
- **Neutral**:
  - We could in the future supplement URL versioning with optional
    header-based feature flagging (e.g., for opt-in beta routes
    under `/v1/`). Not in scope for Phase 2.

## Alternatives considered

- **Header versioning** (`Accept: application/vnd.tcf-accel.v1+json`):
  rejected because (a) operational friction at the CDN / proxy layer,
  (b) harder to test (developers can't just `curl /v1/...`), and
  (c) generated-SDK tooling for OpenAPI is more mature for URL
  versioning. *Would reconsider*: never; the operational cost is
  permanent and we have no compelling benefit to offset it.
- **No version namespace, always-latest**: rejected because we cannot
  ship breaking changes without breaking *every* client. Master prompt
  §3 mandates stable contracts. *Would reconsider*: never.
- **Semantic-version namespacing** (`/v1.2.3/...`): rejected because
  it explodes the surface area; each minor bump would mint new URLs.
  *Would reconsider*: never.

## What would change our mind

- **A consumer-base shift** to header-aware tooling such that URL
  versioning becomes the awkward path. We do not see this trend in
  2026.
- **An OpenAPI tooling regression** that makes URL-versioned spec
  generation harder than header-versioned. Unlikely.

## References

- `02_ARCHITECTURE.md §2.4`, `§2.8` ADR-016 entry.
- `phase2_design.md §4.1`.
- ADR-014 (error code stability; codes are a separate stability
  promise within the version).
- <https://www.iana.org/assignments/http-fields/http-fields.xhtml>
  (`Sunset`, `Link` headers).
