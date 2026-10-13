# LINE Official Account Integration

Status: `implementation-ready; credentials pending`

This document describes the planned LINE integration for Solo Empire. The
account-specific identity and workflow notes live at
[`accounts/line/business/solo-empire/`](../../platform-accounts-api/line/business/solo-empire).

## Scope

The integration is intended to provide a business-facing LINE entry point for
Solo Empire automation:

- Receive messages and account events through a LINE webhook.
- Route requests through one central webhook/router to internal workflows.
- Send replies, push messages, rich menus, and Flex Messages through the
  Messaging API.
- Let compatible AI agents call LINE through LINE's preview LINE Bot MCP
  Server.

## Architecture

```text
LINE user
   │
   ▼
LINE Official Account
   │ webhook event
   ▼
Central LINE webhook/router
   ├── Solo Empire operations
   ├── Notifications
   ├── Venture/customer workflows
   └── AI agent tools / MCP
   │
   └── Messaging API or LINE Bot MCP Server → LINE user
```

Inbound events should be handled by the central webhook/router. MCP is an
agent-facing integration layer and does not replace webhook verification or
the Messaging API server needed to receive events.

## Setup checklist

- [ ] Create or confirm the LINE Official Account.
- [ ] Enable the Messaging API for the account.
- [ ] Create the LINE Developers provider and Messaging API channel.
- [ ] Keep related LINE Login or LINE MINI App channels under the same provider
      if they will be linked later.
- [x] Add the central `POST /api/webhook/line` endpoint.
- [x] Verify LINE webhook signatures against the raw request body.
- [x] Persist accepted events idempotently to `webhook_log` as pending work.
- [x] Add a dry-run-by-default worker that routes only metadata into the
      lake-first `intake_queue`.
- [ ] Deploy the endpoint on a public HTTPS URL.
- [ ] Store the channel access token and webhook secret outside the repository.
- [ ] Configure the LINE Bot MCP Server only after the API path is verified.
- [ ] Add an allowlist and confirmation step before an AI agent can send
      messages to real users.
- [ ] Update [`account.yaml`](../../platform-accounts-api/line/business/solo-empire/account.yaml)
      from `planned` as each capability is verified.

## Important platform constraints

One LINE Official Account can have one Messaging API channel and one webhook
URL. Multiple tools may use the same channel, but they share channel tokens,
message quotas, rate limits, and webhook events. Use one central router for
multiple internal agents rather than assigning competing webhook endpoints.

The LINE Bot MCP Server is currently a preview implementation. Treat outbound
message tools as privileged operations and keep the channel access token
private.

## Official references

- [Get started with the Messaging API](https://developers.line.biz/en/docs/messaging-api/getting-started/)
- [Messaging API overview](https://developers.line.biz/en/docs/messaging-api/overview/)
- [Receive messages and webhook events](https://developers.line.biz/en/docs/messaging-api/receiving-messages/)
- [Messaging API pricing](https://developers.line.biz/en/docs/messaging-api/pricing/)
- [Using multiple tools with one Official Account](https://developers.line.biz/en/tips/2026/07/23/using-multiple-api-tools/)
- [LINE Bot MCP Server](https://github.com/line/line-bot-mcp-server)

## Implementation status

The infrastructure now registers LINE as a direct integration, checks
`GET https://api.line.me/v2/bot/info` when both credentials are available, and
accepts signed webhook events at `POST /api/webhook/line`. Events are stored in
`webhook_log` with `processed=0`. The worker
`process_line_webhooks.py` (retired 2026-10-11 with the `webhook_log` table)
was dry-run by default and only creates privacy-safe `intake_queue` metadata
after the LINE source is explicitly activated. Outbound messaging remains
disabled until the account allowlist and confirmation policy are in place.

To activate the lake-first route after the account is configured:

```bash
python3 infra/scripts/cli/data-intake-cli.py source register \
  --key line-official-account --name "LINE Official Account" \
  --kind webhook --provider line --domain communications \
  --dataset line_webhook_events --privacy-class restricted \
  --retention-class customer-communications --ingest-mode webhook
python3 infra/scripts/cli/data-intake-cli.py source set-status line-official-account active
task integrations:line:process -- --json
task integrations:line:process -- --apply --json
```
