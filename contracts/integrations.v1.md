# Integrations API v1 contract

`schema_version: solo-empire.integrations.v1`

Read-only projection of [`infra/api/external_app_registry.ts`](../../../infra/api/external_app_registry.ts).
A listed app is not proof of a working connector; see the registry's
[status meanings](../../../integrations/EXTERNAL-APP-REGISTRY.md).

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
