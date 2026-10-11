# WhatsApp Business Read-only Integration

Solo Empire exposes a bounded metadata-only WhatsApp Business Cloud API
boundary for one configured WhatsApp Business Account (WABA).

## Supported boundary

- `GET /api/integrations/whatsapp-business/phone-numbers?limit=20` —
  authenticated, at most 100 phone-number metadata records.
- The returned phone number is masked to the final four digits.
- `GET /api/integrations/health` — validates WABA metadata access only.
- `?offline=true` — deterministic credential-free verification path.

Messages, contacts, templates, media, webhooks, number registration, and all
create/update/delete operations are intentionally out of scope.

## Credential contract

- Environment name: `WHATSAPP_CLOUD_API_TOKEN`
- Secret folder: `/whatsapp-business`
- Non-secret account identifier: `WHATSAPP_BUSINESS_ACCOUNT_ID`
- Optional Graph version: `WHATSAPP_GRAPH_API_VERSION` (default `v25.0`)

The access token must have the minimum Meta permission needed to read WABA phone
metadata. Secret values stay in the configured secret provider and never in
this repository or logs.
