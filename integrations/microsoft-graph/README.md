# Microsoft Graph Read-only Integration

Solo Empire exposes a deliberately narrow Microsoft Graph boundary for the
delegated signed-in user profile.

## Supported boundary

- `GET /api/integrations/microsoft-graph/me` — authenticated; returns only
  `id` and `displayName` from Graph `/me`.
- `GET /api/integrations/health` — validates the same profile access.
- `?offline=true` — deterministic credential-free verification path.

Mail, files, calendar, contacts, Teams, groups, directory search, and all
create/update/delete operations are intentionally out of scope.

## Credential contract

- Environment name: `MICROSOFT_GRAPH_ACCESS_TOKEN`
- Secret folder: `/microsoft-graph`
- Required delegated permission: `User.Read`

The access token is resolved by the shared secret resolver. It must never be
placed in this repository, logs, or chat.
