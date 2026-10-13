# Integrations API v1 contract

`schema_version: solo-empire.integrations.v1`

Read-only projection of [`data/external_app_registry.ts`](../data/external_app_registry.ts) (snapshot of solo-empire `infra/api/external_app_registry.ts`, retired 2026-10-11).
A listed app is not proof of a working connector; see the registry's
[status meanings](../docs/EXTERNAL-APP-REGISTRY.md).

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness and schema version |
| `GET` | `/api/v1/integrations` | Summary, signals, and app rows |

Optional filters: `status` (`live` / `mcp_only` / `paused` / `planned`),
`category` (exact), and `q` (case-insensitive substring over id, name,
category, and note; max 80 characters). Other methods return `405`.

## Response fields

- `source`: registry `path`, file `modified_at`, and `status_definitions`.
- `summary` (unfiltered except `apps_matched`): `apps_total`, `apps_matched`,
  `categories`, `connected` (`live` + `mcp_only`), `live`, `mcp_only`,
  `paused`, `planned`, `with_guide`.
- `signals`: unfiltered `{value, count}` lists for `statuses`, `categories`,
  and `sections` (the registry's `//` section comments).
- `apps`: `id`, `name`, `category`, `status`, `api_docs` (HTTPS), `note`,
  `section`, and `guide` (`integrations/<name>/README.md` or `null`).

## Boundary

- Registry metadata only: no credential, provider call, or health check.
- Errors use `{"error": {"code", "message"}}`; an unreadable registry returns
  `503 registry_unavailable`.

## Authorization, readiness and snapshot revision

Production GET reads require owner-scoped RS256 JWT authorization using
`INTEGRATIONS_API_AUTH_ISSUER`, `INTEGRATIONS_API_AUTH_PUBLIC_KEY`, and
`INTEGRATIONS_API_AUTH_SUBJECTS`. Required audience is `integrations-api`, scope is
`integrations:read`, tenant is `owner`, and subject is an allowed OIDC owner.
Required `iat/nbf/exp/jti` constrain lifetime to 120 seconds (5 seconds leeway).
See [runtime configuration](../README.md#scoped-authorization-and-readiness).
Errors keep the v1 envelope: 401 invalid token, 403 owner/tenant/scope denial,
503 missing or invalid JWT configuration. Static tokens are local-development only.

`GET /health` remains public liveness. `GET /ready` returns safe
`status`, `source` (available/unavailable), and `auth`
(ready/development/disabled); 200 requires parsed source and configured JWT,
otherwise 503. No metadata rows appear in readiness responses.
`source.revision` is the SHA-256 source checksum, an additive v1
field. Source date and reload semantics remain unchanged.
# Additive platform inventory

The legacy summary includes `supported_boundaries`; `connected` remains an
identical compatibility alias for registry-supported boundaries and never
asserts authenticated accounts. See [Platform integrations v1](platform-integrations.v1.md)
for the separate per-platform capabilities and explicit owner observations.
