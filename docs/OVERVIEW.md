# External API Integrations

This directory contains integrations with external services to sync data into the operating database.

## 🎯 Overview

These integrations allow you to:
- Sync Google Calendar events
- Sync Gmail emails
- Sync local Brave browser bookmarks
- Sync Todoist tasks
- Check active external API connectivity
- Receive signed LINE Official Account webhook events (credentials pending)
- Check Stripe account balance and receive signed payment events (credentials pending)
- Check Sentry organization health and read bounded unresolved issue summaries
- Read PostHog saved-insight metadata without capturing events or changing flags
- Read Slack public-channel metadata without reading messages or sending actions
- Read Notion page/data-source metadata without reading block content or mutating pages
- Read Asana workspace and project metadata without reading task content or mutating projects
- Track health metrics (coming soon)
- Track financial transactions (coming soon)

All data is stored in your local SQLite database and can be queried through the Solo Empire CLI or MCP tools.

## 📦 Available Integrations

### ✅ Google Calendar
- **Status**: Ready to setup
- **What it does**: Syncs calendar events to `calendar_events` table
- **Boundary guide**: [`google/README.md`](../integrations/google/README.md)
- **Setup**: `python3 integrations/google/setup_calendar.py`
- **Sync**: `python3 integrations/google/calendar_sync.py --sync`

### ✅ Gmail (canonical data pipeline)
- **Status**: Retired 2026-10-11 — the local pipeline scripts (`email_data_pipeline.py`, `sync_gmail_crm.py`) and the SQLite `emails` projection were removed. The description below is the historical contract.
- **Flow**: Gmail API → landing + Bronze Parquet → Iceberg → DuckDB read →
  `emails` SQLite projection (id = Gmail message id) → classify → route
  (`crm_activities` / local `tasks`) → `data_pipeline_runs` +
  `email_pipeline_events` for audit and idempotency
- **Lineage**: The `emails` projection keeps the lake event, run, snapshot,
  table, and raw object key. Object Storage/Parquet/Iceberg is the durable data
  plane; SQLite is the mutable Ops plane.
- **Routing rules**:
  - Client match on email / name / company → `crm_activities`
  - Unread **action** mail or **starred** mail → local `tasks` (`external_source=gmail`)
  - Explicit `[TASK][PATH:<slug>]` subject or `TASK/GENERALIST/<slug>` label →
    `🌐 Generalist Paths` task with a `path:<slug>` tag
  - Payment / invoice / payout / transaction keywords → category `finance`,
    `pipeline_status=needs_review` (human confirmation only)
- **Safety**: the ingestion pipeline never auto-creates `revenue` rows and
  never sends outbound email or other external side effects; logs omit
  subjects, snippets, bodies, and secrets
- **Task digest**: `infra/scripts/sync/task_email_digest.py` groups open tasks
  by path/category. It is dry-run by default and sends through Gmail API OAuth
  with a dedicated `gmail.send` token; SMTP is an explicit compatibility
  fallback via `--transport smtp`.
- **Secrets health (no values printed)**:
  `python3 infra/scripts/utils/secrets_health.py --json`
- **Gmail pipeline verification**: retired 2026-10-11 (script removed).
- **Offline tests**: `task test:secrets`
- **Credentials**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
  `GOOGLE_REFRESH_TOKEN` resolve at runtime through Infisical/Vault; local
  `infra/.env` is only the documented fallback. See
  Solo Empire `systems/cloud-platform/secret-management.md`.
  If health reports a blocker, use **provider + error_class only** — never paste
  secrets into chat.
- **Safe OAuth rotation**: `python3 infra/scripts/utils/get_google_refresh_token.py --store-infisical`
  completes consent and stores the new refresh token in Infisical `/google`
  without printing it.

### ✅ Brave Bookmarks (local lake-first pipeline)
- **Status**: Active for the local Brave profile files
- **What it does**: Imports bookmark JSON from all Brave profiles into landing +
  Bronze Parquet and a searchable `browser_bookmarks` SQLite projection; it also
  supports deterministic folder/subfolder organization and an approved proposal
  write-back path
- **Direction**: Import is automatic/read-safe; browser write-back requires an
  approved proposal, a closed Brave process, hash verification, and a backup
- **AI intake**: `manage_brave_bookmark_proposals` (MCP) creates private
  proposals; AI does not write the live Brave profile directly
- **Automatic maintenance**: `brave_bookmarks_maintenance` runs every 4 hours
  through the targeted user crontab on this machine; if Brave is open it skips
  browser write-back and retries on the next run
- **Sync**: `task bookmarks:sync -- --json`
- **Propose**: `task bookmarks:propose -- --url ... --title ...`
- **Review/apply**: `task bookmarks:review -- --json` then
  `task bookmarks:apply -- --json`
- **Search**: `task bookmarks:sync -- --search "keyword"`
- **Guide**: [`brave-bookmarks/README.md`](../integrations/brave-bookmarks/README.md) and
  Solo Empire `docs/references/BRAVE-BOOKMARKS.md`

### ✅ Todoist
- **Status**: Active when the Todoist API token is valid
- **What it does**: Syncs tasks and projects to `external_tasks`
- **Credentials**: `TODOIST_API_TOKEN` resolves from Infisical/Vault
- **Health check**: `python3 infra/scripts/sync/integration_health.py --json`

### 🟡 LINE Official Account (Ingress ready; account pending)
- **Status**: Signed webhook ingress and read-only health check implemented;
  account credentials and public HTTPS deployment are still pending
- **What it does**: Receives LINE events, persists them idempotently in
  `webhook_log` with `processed=0`, and exposes them for the central router
- **Outbound messaging**: Not implemented; no messages are sent by this route
- **Account metadata**: [`accounts/line/business/solo-empire/`](https://github.com/bookchaowalit/platform-accounts-api/tree/main/accounts/line/business/solo-empire)
- **Integration guide**: [`line/README.md`](../integrations/line/README.md)
- **Implementation**: `POST /api/webhook/line` verifies `x-line-signature`
  before parsing and does not require the internal Bearer token; the
  `integrations:line:process` worker routes verified events into the
  lake-first intake queue only with explicit `--apply`

### 🟡 Stripe (Read-only API and webhook ingress ready)
- **Status**: Read-only balance health check and signed webhook ingress
  implemented; Stripe credentials and public HTTPS deployment are pending
- **What it does**: Checks `GET /v1/balance` without creating payments and
  stores verified Stripe events as pending `webhook_log` rows
- **Safety**: No checkout, charge, refund, payout, or automatic revenue write
  is enabled
- **Credentials**: `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` resolve
  through the `/stripe` secret-provider folder
- **Webhook**: `POST /api/webhook/stripe`, using the raw body and
  `Stripe-Signature`

### 🟡 Sentry (Read-only observability ready)
- **Status**: Organization health and unresolved issue summary are implemented;
  Sentry credentials and public account configuration are pending
- **What it does**: Reads bounded issue metadata with `query=is:unresolved`;
  it does not read event payloads or mutate issues, releases, projects, or alerts
- **Credentials**: `SENTRY_AUTH_TOKEN` and `SENTRY_ORG_SLUG`; the token should
  be scoped to organization/project read access and resolves through `/sentry`
- **Optional self-hosted URL**: `SENTRY_BASE_URL` (defaults to `https://sentry.io`)
- **API**: Authenticated `GET /api/integrations/sentry/issues?limit=20`, capped
  at 100 issues; use `?offline=true` to verify the route without a provider call

### 🟡 PostHog (Read-only analytics ready)
- **Status**: Saved-insight metadata health check and read-only summary are
  implemented; PostHog credentials and project configuration are pending
- **What it does**: Reads at most 100 saved-insight summaries and strips query,
  event, result, and person payloads from the response
- **Credentials**: `POSTHOG_API_KEY` and `POSTHOG_PROJECT_ID`; use a private API
  key with `insight:read`, resolved through the `/posthog` secret-provider folder
- **Host**: `POSTHOG_HOST` must be the private regional API host, such as
  `https://us.posthog.com` or `https://eu.posthog.com`
- **Safety**: Event capture, feature-flag evaluation, and all write operations
  are outside this boundary
- **API**: Authenticated `GET /api/integrations/posthog/insights?limit=20`,
  capped at 100 insights; use `?offline=true` for route-only verification

### 🟡 Slack (Read-only workspace metadata ready)
- **Status**: Authentication and bounded public-channel metadata are implemented;
  Slack credentials and workspace configuration are pending
- **What it does**: Calls `auth.test` and reads public, non-archived channel
  metadata only; private channel and message contents are not returned
- **Credentials**: `SLACK_BOT_TOKEN`, resolved through the `/slack`
  secret-provider folder, with the least-privilege `channels:read` scope
- **Safety**: Sending messages, reading message history, creating channels,
  joining channels, and other workspace mutations are outside this boundary
- **API**: Authenticated `GET /api/integrations/slack/channels?limit=20`,
  capped at 100 channels; use `?offline=true` for route-only verification

### 🟡 Notion (Read-only inventory ready)
- **Status**: Bounded page/data-source inventory is implemented through the
  Notion REST API; the existing Notion MCP/task-sync boundary remains separate
- **What it does**: Searches shared pages and data sources and returns only
  bounded metadata such as IDs, timestamps, URLs, parent IDs, and title
- **Credentials**: `NOTION_BOT_TOKEN`, resolved through the `/notion`
  secret-provider folder; API version defaults to `2026-03-11`
- **Safety**: Block content, arbitrary page properties, user details, and all
  create/update/archive/delete operations are outside this boundary
- **API**: Authenticated `GET /api/integrations/notion/search?limit=20`,
  with an optional bounded `query`; use `?offline=true` for route-only verification

### 🟡 Asana (Read-only project metadata ready)
- **Status**: Workspace and project metadata access is implemented; an Asana
  personal access token and workspace configuration are still pending
- **What it does**: Lists visible workspaces and compact projects, capped at
  100 records per request; project queries require an explicit workspace GID
- **Credentials**: `ASANA_PERSONAL_ACCESS_TOKEN`, resolved through the `/asana`
  secret-provider folder; use least-privilege `workspaces:read` and
  `projects:read` access where supported
- **Safety**: Task descriptions, comments, custom fields, and all create/update/
  archive/delete operations are outside this boundary
- **API**: Authenticated `GET /api/integrations/asana/workspaces?limit=20` and
  `GET /api/integrations/asana/projects?workspace=<gid>&limit=20`; use
  `?offline=true` for route-only verification

### 🔄 Health APIs (Coming Soon)
- **Status**: Not implemented yet
- **What it will do**: Sync health metrics to the `health-metrics` cell
- **Services**: Google Fit, Apple Health, Fitbit

### 🔄 Other Finance APIs (Coming Soon)
- **Status**: Not implemented yet
- **What it will do**: Sync transactions to `financial_transactions` table
- **Services**: Bank APIs, Credit Cards, Investment platforms

## 🚀 Quick Start

### 1. Setup Google Calendar Integration

```bash
# Run the setup script
python3 integrations/google/setup_calendar.py

# Follow the instructions to:
# 1. Create Google Cloud Project
# 2. Enable Calendar API
# 3. Create OAuth credentials
# 4. Download credentials.json
```

### 2. Sync Your Calendar

```bash
# Sync last 7 days and next 30 days
python3 integrations/google/calendar_sync.py --sync

# Show upcoming events
python3 integrations/google/calendar_sync.py --upcoming 7

# Show statistics
python3 integrations/google/calendar_sync.py --stats
```

### 3. Unified email pipeline

Retired 2026-10-11: the local pipeline script and the SQLite `emails` tables were removed.

### 4. Sync All Integrations

```bash
# Sync all configured integrations
python3 infra/scripts/sync/sync_all_integrations.py --all

# Sync specific services
python3 infra/scripts/sync/sync_all_integrations.py --calendar --email

# Show sync status
python3 infra/scripts/sync/sync_all_integrations.py --status

External API health commands:

python3 infra/scripts/sync/integration_health.py --json
python3 infra/scripts/sync/integration_health.py --json --offline
```

The REST API exposes the 100-app discovery registry and the implemented direct
boundary without proxying provider tokens:

```text
GET  /api/integrations                     # 100-app registry + 18 direct boundaries
GET  /api/integrations/health              # authenticated live health check
GET  /api/integrations/health?offline=true # authenticated credential-only check
GET  /api/integrations/discovery?source=all&limit=1000 # live public catalog discovery
POST /api/webhook/line                     # signed LINE ingress; no outbound send
POST /api/webhook/stripe                   # signed Stripe ingress; no payment mutation
GET  /api/integrations/sentry/issues?limit=20 # authenticated read-only issue summary
GET  /api/integrations/posthog/insights?limit=20 # authenticated read-only analytics summary
GET  /api/integrations/slack/channels?limit=20 # authenticated read-only channel metadata
GET  /api/integrations/notion/search?limit=20 # authenticated read-only page metadata
GET  /api/integrations/asana/workspaces?limit=20 # authenticated read-only workspace metadata
GET  /api/integrations/asana/projects?workspace=<gid>&limit=20 # authenticated read-only project metadata
```

The health route is read-only and delegates to `integration_health.py`; it
does not expose credential values or act as a generic external API proxy.
Discovery can use the APIs.guru OpenAPI directory or the Official MCP Registry;
it is metadata-only and bounded to 10,000 records per request.

## 📊 Database Tables

All integration data is stored in these tables:

| Table | Description | Fields |
|-------|-------------|--------|
| `calendar_events` | Calendar events from Google Calendar | id, title, start_time, end_time, location, attendees, etc. |
| `emails` | Canonical normalized Gmail source records | id, from_address, subject, received_at, labels, category, pipeline_status |
| `data_pipeline_runs` | Pipeline batch status and counts | source, status, records_read, records_routed |
| `email_pipeline_events` | Idempotent per-email route audit | email_id, action_type, target_type, target_id |
| `external_tasks` | Tasks from Todoist | id, title, due_date, priority, status, project, etc. |
| `financial_transactions` | Financial transactions | amount, category, merchant, transaction_date, etc. |

## 🔧 Configuration

### Google Calendar

Credentials are stored in:
```
~/.config/solo-empire/integrations/google/
├── credentials.json    # OAuth credentials from Google Cloud
└── calendar_token.json # Auto-generated after first auth
```

### Gmail

Uses the same Google OAuth environment variables as Calendar:
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`.

### Todoist (Coming Soon)

Credentials will be stored in:
```
~/.config/solo-empire/integrations/todoist/
└── token.json  # API token from Todoist
```

### LINE Official Account

LINE credentials are not stored in `accounts/` or `docs/`. Use the local
environment or credential store referenced by the account metadata:

```text
LINE_SOLO_EMPIRE_CHANNEL_ACCESS_TOKEN
LINE_SOLO_EMPIRE_WEBHOOK_SECRET
LINE_SOLO_EMPIRE_WEBHOOK_URL
```

Do not configure or test outbound messaging against real recipients until the
account allowlist and confirmation policy are in place. See
[`line/README.md`](../integrations/line/README.md) for the setup checklist and platform
constraints.

## 🤖 Automation

### Manual Sync

```bash
# Sync all integrations
python3 infra/scripts/sync/sync_all_integrations.py --all
```

### Automatic Sync with Cron

Add to your crontab (`crontab -e`):

```bash
# Sync every hour
0 * * * * /usr/bin/python3 /path/to/operating-hub/infra/scripts/sync/sync_all_integrations.py --all >> /tmp/integration_sync.log 2>&1

# Sync calendar every 30 minutes
*/30 * * * * /usr/bin/python3 /path/to/integrations/integrations/google/calendar_sync.py --sync >> /tmp/calendar_sync.log 2>&1
```

### Using systemd (Linux)

Create a systemd timer for more reliable scheduling:

```bash
# Create service file
sudo nano /etc/systemd/system/solo-empire-sync.service

# Create timer file
sudo nano /etc/systemd/system/solo-empire-sync.timer

# Enable and start
sudo systemctl enable solo-empire-sync.timer
sudo systemctl start solo-empire-sync.timer
```

## 📝 Usage Examples

### Query Calendar Events

```bash
# Using CLI
cd ~/operating-hub
npx tsx infra/cli.ts calendar --upcoming 7

# Using SQL
sqlite3 <operational-db> "SELECT title, start_time FROM calendar_events WHERE start_time > datetime('now') ORDER BY start_time LIMIT 10;"
```

### Query Emails

```bash
# Using SQL
sqlite3 <operational-db> "SELECT from_address, subject, received_at FROM emails ORDER BY received_at DESC LIMIT 10;"
```

### Query Tasks

```bash
# Using SQL
sqlite3 <operational-db> "SELECT title, due_date, priority FROM external_tasks WHERE status = 'pending' ORDER BY due_date;"
```

## 🔐 Security

- All credentials are stored locally in `~/.config/solo-empire/integrations/`
- Credentials are never committed to git (see `.gitignore`)
- OAuth tokens are encrypted at rest
- API keys should be kept secret

## 🐛 Troubleshooting

### Google Calendar Setup Issues

**Problem**: "Credentials file not found"
- **Solution**: Download `credentials.json` from Google Cloud Console and place it in `~/.config/solo-empire/integrations/google/`

**Problem**: "Authentication failed"
- **Solution**: Delete `calendar_token.json` and run setup again

**Problem**: "No events found"
- **Solution**: This is normal if your calendar is empty. Try syncing a wider date range.

### Sync Issues

**Problem**: "Integration not configured"
- **Solution**: Run the setup script for that integration

**Problem**: "API quota exceeded"
- **Solution**: Wait for quota to reset (usually 24 hours) or reduce sync frequency

## 📚 API Documentation

- [Google Calendar API](https://developers.google.com/calendar/api)
- [Gmail API](https://developers.google.com/gmail/api)
- [Todoist API](https://developer.todoist.com/guides/)
- [LINE Messaging API](https://developers.line.biz/en/docs/messaging-api/overview/)
- [LINE Bot MCP Server](https://github.com/line/line-bot-mcp-server)

## 🤝 Contributing

Want to add a new integration? See [INTEGRATION-GUIDE.md](INTEGRATION-GUIDE.md) for details on how to create new integrations.

## 📄 License

Part of Solo Empire - Personal Knowledge Base System

## Local documents

- [External App Registry](EXTERNAL-APP-REGISTRY.md)
- [Landing Page Integration](landing-page-integration.md)
