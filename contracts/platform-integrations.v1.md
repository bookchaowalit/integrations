# Platform integrations v1

`GET /api/v1/integrations/platforms?platform=&app=&route=&q=` is an
owner-authorized, read-only projection. Authorization is identical to the
legacy integrations route (`aud=integrations-api`, `scope=integrations:read`,
`tenant_id=owner`, allowlisted owner subject). No write route exists.

The public snapshot uses `solo-empire.platform-integrations.v1`; exact top-level
fields are `schema_version`, `captured_at`, `platforms`, `capabilities`, `lineage`.
Platforms have `id`, `name`, `mcp_transports` (`stdio`, `sse`, `streamable_http`),
`docs_url`. Capabilities have `platform_id`, `app_id`, `channel` (`plugin`,
`connector`, `manual_mcp`), `availability` (`available`, `unavailable`, `unknown`),
nullable `entry_id`, nullable `endpoint_url`, `evidence_url`, `captured_at`.
The unique grain is platform/app/channel/entry. Identifiers are bounded;
entry IDs use letters, digits, dots, colons, underscores and hyphens.
URLs require HTTPS without userinfo, query, fragment or control characters.

Lineage requires `dataset=platform_integrations`, `manifest_key`,
`manifest_sha256`, `raw_sha256`, `bronze_sha256`, `source_manifests`.
Each source manifest has `source_id` and the same key/hash fields. Keys are
relative `control/manifests/` paths without traversal; hashes are lowercase
SHA256. Source manifests are nonempty. Extra fields, duplicate JSON keys and
duplicate grains fail closed. All timestamps must use UTC; more than five
minutes in the future is invalid.

The response contains:

| Field | Shape |
| --- | --- |
| `schema_version` | `solo-empire.platform-integrations.v1` |
| `generated_at` | UTC response timestamp |
| `snapshot` | `captured_at`, `freshness` (`fresh`, `stale`), exact-file SHA256 `revision`, public `lineage` |
| `platforms` | All declared platform records |
| `summary` | `rows_total`, `rows_matched`, `native_available`, `manual_mcp_available`, `installed`, `authenticated`, `health_verified`, `paused`, `unknown`, `needs_review` |
| `rows` | Platform/app records described below |

Each row has `id` (`platform_id:app_id`), `platform_id`, `app_id`, `app_name`,
`category`, `registry_status`, `channels`, `recommended_route`, `connection`.
`channels` is keyed by `plugin`, `connector`, `manual_mcp`. Each has
`availability` and `entries` (matching public capability records). Missing
channels are unknown; conflicting available/unavailable entries are unknown.
A partial catalog never establishes absence. App names and categories come
from the canonical local registry; the response spans every declared platform
and every registry app, including unobserved pairs.

Fresh recommendations prefer available plugin, then connector, then manual
MCP. A manual MCP recommendation only asserts an evidenced option. Explicitly
unavailable on all three channels gives `unavailable`; otherwise no available
channel gives `unknown`. After seven days, snapshots or recommended-channel
evidence yield `needs_review`. Paused registry apps always yield `paused`.

`connection` contains `installation`, `authentication`, `health`, nullable
`checked_at`, nullable `evidence_id`, `freshness` (`unknown`, `fresh`, `stale`).
No observation means unknown for all three states. Old observations remain
labelled stale and never count in `installed`, `authenticated`, `health_verified`.
Availability counts are public capability counts, not connected-account counts.
All summary counts span the full inventory except `rows_matched`.

Filters are bounded (`q`/IDs 80 characters), with a single value per field.
Platform/app IDs must exist; route must be a declared recommendation enum.
Unknown arguments, invalid IDs/enums and duplicate fields return 400.
Filters combine with AND; text search matches app ID/name/category/platform ID.
Missing/invalid snapshots, registry or observations return fixed 503
`platform_inventory_unavailable` without upstream contents or filesystem paths.

## Sources and private observations

`INTEGRATIONS_API_PLATFORM_SNAPSHOT` defaults to
`data/platform_integrations.snapshot.json`. A collector/worker owned by
`data-lake-pipelines` commits exact raw bytes, Bronze and immutable manifests
before atomically publishing this consumer snapshot. The API validates the
published contract; it never scrapes providers or reads lake credentials.
Artifact hash verification happens in the publisher, not this API.

`INTEGRATIONS_API_CONNECTIONS_PATH` defaults to
`.runtime/platform-connections.json`. This optional owner-local file is separate
from the public lake and excluded from Git/image. It contains only
`schema_version=solo-empire.integration-connections.v1` and `observations`.
Each observation has exactly `platform_id`, `app_id`, `installation`
(`installed`, `not_installed`, `unknown`), `authentication` (`connected`,
`disconnected`, `unknown`), `health` (`verified`, `failed`, `unknown`),
`checked_at`, `evidence_id`. Non-unknown states require UTC timestamp and bounded
evidence identifier. Symlinks, nonregular files, duplicate pairs, extra fields,
non-owner ownership and any mode other than 600 are rejected. Absence is valid;
malformed observations fail closed. Never put credentials or personal payloads
in an evidence ID.

`python3 scripts/record_connection.py --platform codex-app --app gmail
--installation installed --evidence-id owner-check-1` records owner metadata
through a mode-600 atomic replacement and serializes concurrent CLI writes.
It makes no network call, performs no provider authentication and does not
publish data. CLI errors are fixed messages.

MCP `integrations.platforms` is a strict read-only HTTP adapter with optional
`platform`, `app`, `route`, `q`. Unknown arguments including identity,
credentials and arbitrary URLs are rejected before HTTP. Its fixed auth and
upstream-error rules are identical to `integrations.list`.

`/health`, `/ready` and the legacy route keep their existing semantics.
Readiness checks the legacy registry/auth configuration; use the platform
route to verify a published platform snapshot. No deployment or provider
account availability is implied by local tests.
