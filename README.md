# solo-integrations

Moved out of solo-empire `services/integrations-api` on 2026-10-11 with its history
(subtree split). Owns the external app registry (`data/external_app_registry.ts`, moved
from `infra/api/external_app_registry.ts`) and the read-only `/api/v1/integrations` API.
**Source of truth:** solo-empire `integrations/external_app_registry.ts` (Tools Hub and the
building-block guard read it there); `data/external_app_registry.ts` here is the deployed snapshot,
refreshed by copying that file.
`vendor/service-auth` is a vendored copy of `bookchaowalit/solo-service-auth`.

Test: `PYTHONPATH=vendor/service-auth python3 -m unittest discover -s tests -v`

---

# Solo Empire Integrations API

`integrations-api` is a small read-only backend that turns
[`data/external_app_registry.ts`](data/external_app_registry.ts)
into JSON for the `/integrations` module of `solo-web` (`bookchaowalit/solo-web`).
The TypeScript registry (a snapshot of solo-empire `integrations/external_app_registry.ts`); the service parses its
one-record-per-line literal, adds the matching `integrations/<id>/README.md`
guide when one exists, and reloads when the file changes.

Parsing is strict: an unreadable line, unknown status, non-HTTPS docs link, or
duplicate id makes the route answer `503 registry_unavailable` instead of a
partial list. Keep each record on one line when editing the registry.

## Run

From this repository root:

```bash
python3 -m pip install ./vendor/service-auth .
python3 server.py
```

The default listener is `http://127.0.0.1:3480`. Configure
`INTEGRATIONS_API_HOST`, `INTEGRATIONS_API_PORT`,
`INTEGRATIONS_API_REGISTRY_PATH`, and `INTEGRATIONS_API_CORS_ORIGINS` as
needed. A non-loopback host requires valid scoped JWT configuration and enforces production authorization.

```text
GET /health
GET /api/v1/integrations?status=&category=&q=
```

See the [Integrations API v1 contract](contracts/integrations.v1.md).

## Deploy

This folder is an independent deploy unit described by [`service.yaml`](service.yaml).
The repository root is the Docker build context; it contains the service, the
vendored `service-auth` dependency (`vendor/service-auth`) and the registry
(`data/external_app_registry.ts`). The `integrations/<app>/README.md` guides are a snapshot
copied from solo-empire `integrations/` (only the per-app guides).

```bash
docker build -t solo-integrations .
```

The image enforces scoped JWT authorization and binds `0.0.0.0`.
`deploy.target` stays `unassigned` until the parent deployment configuration selects a target. See the decentralized services spec in solo-empire (`docs/superpowers/specs/2026-10-04-decentralized-services-and-storage-design.md`).

## Test

```bash
PYTHONPATH=vendor/service-auth python3 -m unittest discover -s tests -v
```

## Scoped authorization and readiness

[Railway configuration](railway.toml) selects the Dockerfile and `/ready`
health check (30 seconds), with at most 3 restarts after failure. It declares
no region, resources, runtime secret values, or existing cloud deployment.

Configure `INTEGRATIONS_API_AUTH_ISSUER` with the exact HTTPS origin of Solo Web,
`INTEGRATIONS_API_AUTH_PUBLIC_KEY` with its PEM RSA public key (at least 2048 bits),
and `INTEGRATIONS_API_AUTH_SUBJECTS` with the comma-separated allowed OIDC owner
subjects. See [.env.example](.env.example); provide configuration at runtime.
The signing private key belongs only to Solo Web and is never copied to this image.

Reads require an RS256 JWT: `iss` matches that origin, `aud=integrations-api`,
`sub` is allowed, `tenant_id=owner`, `scope=integrations:read`, and
`iat`, `nbf`, `exp`, `jti` are required. Lifetime is at most 120 seconds
with 5 seconds clock leeway. The verifier uses only the configured local key
and rejects remote key headers. Key rotation replaces the configured public
key and restarts the service; old signatures then fail. Missing configuration
returns `503 reads_disabled`; invalid tokens return `401 unauthorized`;
a valid token for another owner/tenant/scope returns `403 forbidden`.
Production never accepts `INTEGRATIONS_API_TOKEN`. Partial JWT configuration
fails closed even in development.

`GET /health` is public liveness. `GET /ready` returns 200 only when the
source snapshot parses and JWT configuration is valid; otherwise it returns
503 with safe source/auth states. A local fixture with auth disabled reports
`auth=development`, not deployment readiness. Metadata contains a SHA-256
`revision` of its source snapshot and preserves its original dates.
Atomic source replacement triggers reload. This does not assert provider
freshness or a live deployment.

The listener accepts PaaS `PORT`; explicit `INTEGRATIONS_API_PORT` or `--port`
takes precedence. Package installation is required; no sibling source-path
injection is used at runtime.
