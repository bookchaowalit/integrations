# Solo Empire Integrations API

`integrations-api` is a small read-only backend that turns
[`infra/api/external_app_registry.ts`](../../infra/api/external_app_registry.ts)
into JSON for the `/integrations` module of [`apps/solo-web`](../../apps/solo-web/).
The TypeScript registry stays canonical; the service parses its
one-record-per-line literal, adds the matching `integrations/<id>/README.md`
guide when one exists, and reloads when the file changes.

Parsing is strict: an unreadable line, unknown status, non-HTTPS docs link, or
duplicate id makes the route answer `503 registry_unavailable` instead of a
partial list. Keep each record on one line when editing the registry.

## Run

From the repository root:

```bash
python3 services/integrations-api/server.py
```

The default listener is `http://127.0.0.1:3480`. Configure
`INTEGRATIONS_API_HOST`, `INTEGRATIONS_API_PORT`,
`INTEGRATIONS_API_REGISTRY_PATH`, and `INTEGRATIONS_API_CORS_ORIGINS` as
needed. A non-loopback host fails to start unless `INTEGRATIONS_API_TOKEN` is
set, and `INTEGRATIONS_API_ENV=production` refuses reads without a token.

```text
GET /health
GET /api/v1/integrations?status=&category=&q=
```

See the [Integrations API v1 contract](contracts/integrations.v1.md).

## Test

```bash
python3 services/integrations-api/tests/test_server.py
```
