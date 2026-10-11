# Zoom Read-only Integration

Solo Empire exposes a deliberately narrow Zoom boundary for the authenticated
user's profile summary.

## Supported boundary

- `GET /api/integrations/zoom/me` — authenticated; returns only `id`,
  `display_name`, and `status` from Zoom `/users/me`.
- `GET /api/integrations/health` — validates the same user metadata access.
- `?offline=true` — deterministic credential-free verification path.

Meetings, recordings, participants, chat, account-wide user lists, settings,
and all create/update/delete operations are intentionally out of scope.

## Credential contract

- Environment name: `ZOOM_ACCESS_TOKEN`
- Secret folder: `/zoom`
- Required OAuth permission: `user:read`

The access token is resolved by the shared secret resolver. It must never be
placed in this repository, logs, or chat.
