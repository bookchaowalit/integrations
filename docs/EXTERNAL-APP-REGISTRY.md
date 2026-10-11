---
title: External App Registry
tags: [integrations, api, inventory, roadmap]
updated: 2026-08-08
status: current
---

# External App Registry

The machine-readable registry lives in
`data/external_app_registry.ts` in the `bookchaowalit/solo-integrations` repository
(canonical owner since 2026-10-11; moved from `infra/api/` and then from this folder) and
currently tracks 100+ external apps with official API documentation links. The Solo Web
`/integrations` page reads it through the solo-integrations API. Tools Hub and the
building-block catalog read it from the sibling checkout (`SOLO_INTEGRATIONS_ROOT`
overrides the default Book Dev path; both skip with a warning when it is absent, e.g. in
CI). Keep each record on one line so the projection can parse it.

> The REST routes described below (`GET /api/integrations...`) were served by the retired
> local `infra/api` server (archived in `bookchaowalit/solo-platform-api`). They are kept as
> the historical per-provider read contract, not as a running endpoint.

## Status meanings

- `live` — the direct read-only health checker already supports the provider.
- `mcp_only` — an MCP boundary exists, but this REST API does not proxy it.
- `paused` — intentionally disabled until the account and safety gate are reopened.
- `planned` — discovery inventory only; no connector should be implied.

Adding an app to this registry is not enough to call it integrated. Promote a
`planned` app only after its credential folder, data-lake ingress/projection
contract, rate-limit policy, redaction rule, idempotent sync, and focused test
are implemented.

## Current API boundary

`GET /api/integrations` returns both the full registry and the 24 direct
boundaries. `GET /api/integrations/health` returns live status for the 19 active
health checks and requires `Authorization: Bearer <API_TOKEN>`; use
`?offline=true` for credential-only checks without provider network calls.

LINE's inbound webhook is a public signed route at `POST /api/webhook/line`; it
uses `LINE_SOLO_EMPIRE_WEBHOOK_SECRET` and persists verified events to
`webhook_log`; the downstream worker is dry-run by default and does not send
outbound messages.

Stripe's inbound webhook is a public signed route at `POST
/api/webhook/stripe`; it uses `STRIPE_WEBHOOK_SECRET`, verifies the raw body
and `Stripe-Signature`, then persists pending events without creating revenue
or mutating payment state.

Sentry is a read-only observability boundary. Authenticated `GET
/api/integrations/sentry/issues?limit=20` reads at most 100 unresolved issue
summaries using `SENTRY_AUTH_TOKEN` and `SENTRY_ORG_SLUG`; it never returns event
payloads or changes Sentry state. The token is resolved from `/sentry`, and
`SENTRY_BASE_URL` supports a self-hosted Sentry URL.

PostHog is a read-only analytics boundary. Authenticated `GET
/api/integrations/posthog/insights?limit=20` reads at most 100 saved-insight
metadata records using `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`, and the private
regional `POSTHOG_HOST`; it requires `insight:read` and strips query, event,
result, and person payloads. The route never captures events, evaluates flags,
or mutates PostHog data.

Slack is a read-only workspace metadata boundary. Authenticated `GET
/api/integrations/slack/channels?limit=20` calls `auth.test` and reads at most
100 public, non-archived channel summaries using `SLACK_BOT_TOKEN` with the
`channels:read` scope. It does not read messages or perform workspace actions;
the token is resolved from `/slack`.

Notion is a read-only knowledge boundary. Authenticated `GET
/api/integrations/notion/search?limit=20` searches pages and data sources shared
with the connection and returns bounded metadata only. It drops block content,
arbitrary properties, and user details; it uses `NOTION_BOT_TOKEN` from
`/notion` and the pinned `Notion-Version: 2026-03-11` header. No Notion object is
created or mutated by this route.

Asana is a read-only project-management boundary. Authenticated `GET
/api/integrations/asana/workspaces?limit=20` lists visible workspaces, while
`GET /api/integrations/asana/projects?workspace=<gid>&limit=20` lists compact
projects for one explicit workspace. Both routes are bounded at 100 records and
use `ASANA_PERSONAL_ACCESS_TOKEN` from `/asana`; no task content or mutation is
enabled.

Discord is a read-only communication boundary. Authenticated `GET
/api/integrations/discord/guilds?limit=20` lists bounded partial guild metadata
using `DISCORD_BOT_TOKEN` from `/discord`; messages, members, and mutations are
disabled.

WhatsApp Business is a read-only communication boundary. Authenticated `GET
/api/integrations/whatsapp-business/phone-numbers?limit=20` lists bounded WABA
phone metadata using `WHATSAPP_CLOUD_API_TOKEN` from `/whatsapp-business` and
`WHATSAPP_BUSINESS_ACCOUNT_ID`; returned phone numbers are masked and messaging
operations are disabled.

Microsoft Graph is a read-only productivity boundary. Authenticated `GET
/api/integrations/microsoft-graph/me` uses `MICROSOFT_GRAPH_ACCESS_TOKEN` from
`/microsoft-graph` with delegated `User.Read` and returns only `id` and
`displayName`; mail, files, calendar, Teams, and mutations are disabled.

Zoom is a read-only communication boundary. Authenticated `GET
/api/integrations/zoom/me` uses `ZOOM_ACCESS_TOKEN` from `/zoom` with the
OAuth `user:read` permission and returns only `id`, `display_name`, and
`status`; meetings, recordings, participants, chat, and mutations are disabled.

monday.com is a read-only project-management boundary. Authenticated `GET
/api/integrations/monday/boards?limit=20` uses `MONDAY_API_TOKEN` from `/monday`
with `boards:read` and returns only board `id`, `name`, and `state`; items,
columns, updates, docs, and mutations are disabled.
