# monday.com Read-only Integration

Solo Empire exposes a deliberately narrow monday.com boundary for board
metadata.

## Supported boundary

- `GET /api/integrations/monday/boards?limit=20` — authenticated; returns only
  board `id`, `name`, and `state`.
- `GET /api/integrations/health` — validates bounded board metadata access.
- `?offline=true` — deterministic credential-free verification path.

Items, columns, updates, docs, workspaces, account-wide search, and all
create/update/delete operations are intentionally out of scope.

## Credential contract

- Environment name: `MONDAY_API_TOKEN`
- Secret folder: `/monday`
- Required permission: `boards:read`

The token is resolved by the shared secret resolver. It must never be placed in
this repository, logs, or chat.
