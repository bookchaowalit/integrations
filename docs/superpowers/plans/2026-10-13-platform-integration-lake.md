# Platform integration lake implementation plan

> **For agentic workers:** Use bounded delegated implementation; the parent integrates and verifies every task.

**Goal:** Publish a per-platform integration inventory through the existing backend and frontend after lake-first collection.

**Architecture:** Public collectors commit landing/Bronze/manifests, then export a strict read snapshot. The integrations service overlays private owner observations and exposes read-only API/MCP; Solo Web displays its response.

**Tech Stack:** Existing Python stdlib/service-auth/MCP, lake ingest/Parquet, Next.js/React/TypeScript/Vitest.

**Spec:** `../specs/2026-10-13-platform-integration-lake-design.md`

## Global constraints

- Preserve current integrations v1 clients and owner authorization; introduce no HTTP writes or production deployment.
- Public facts and private observations remain separate; no secrets or hub dependencies.
- Unknown/unlisted and stale facts cannot claim account connectivity.
- Publication follows successful immutable raw/Bronze/manifest commits; failed runs preserve previous publication.
- Freshness is seven days with five-minute future-clock allowance.

## Review focus

- Partial marketplace absence and surface restrictions must not invent unavailability or CLI support.
- Redirects, credential-shaped URLs/fields and malformed schemas must fail without leaking payloads.
- Missing/corrupt lake artifacts must prevent publication; replay must preserve capture age and identity.
- Private observations need evidence and mode 600 and cannot enter public snapshots.
- Legacy responses and frontend BFF authorization must keep working with separate platform filters.

### T1: Integrations read model and operational metadata

Own `platform_inventory.py`, `server.py`, `integrations_mcp.py`, `scripts/record_connection.py`, `tests/test_platform_inventory.py`, relevant existing tests, Dockerfile/service.yaml/pyproject and API docs. Parent owns the spec/plan and final generated public snapshot.

- [ ] Write failing tests for snapshot validation, unknown/fresh/stale routing, observation permissions/evidence and authenticated GET filtering.
- [ ] Add strict file-backed snapshot/observation readers and platform/app projections matching the spec.
- [ ] Add `/api/v1/integrations/platforms` and `integrations.platforms`; preserve legacy summary and add `supported_boundaries`.
- [ ] Add atomic metadata-only owner observation CLI and package/container wiring.
- [ ] Run full owning pytest/unittest checks and report evidence; parent commits/releases.

Produces the exact snapshot validator plus API response shape in the spec, consumed by T2 publication and T3 frontend.

### T2: Public catalog collector and lake publisher

Own `infra/scripts/data_lake/collect_platform_integrations.py`, `systems/ai-data/platform-integration-sources.json`, `infra/tests/data_lake/platform_integration_collection_test.py`, README and data contract/runbook within data-lake-pipelines.

- [ ] Write failing tests using public catalog fixtures and temporary real lake directories.
- [ ] Implement allowlisted bounded fetching/offline replay, exact alias mapping and surface restrictions.
- [ ] Use existing `ingest_payload` for exact captures and normalized records; verify committed artifact hashes before atomic snapshot export.
- [ ] Test raw byte preservation, replay idempotency, bad input/ingest failures leaving previous snapshot unchanged and no private states.
- [ ] Run focused tests then the owning suite; report unrelated baseline failures/skips explicitly.

Produces the strict public snapshot for T1; parent runs a public collection and local complete journey before committing the generated projection.

### T3: Existing Solo Web inventory view

Own `modules/integrations/{api.ts,client.tsx,module.css}`, platform rendering/request tests, BFF integration route allowlist tests and corresponding README notes within life-dashboard-web.

- [ ] Write failing tests for platform requests and safe unknown/stale/connection rendering.
- [ ] Add types/client GET and a platform selector/table; keep collection logic on backend.
- [ ] Replace catalog connected claims and use `supported_boundaries` with legacy fallback.
- [ ] Allow the exact additional BFF read path without broadening authorization.
- [ ] Run typecheck, full tests and build; parent performs the complete local UI journey if available.

Consumes T1 API shape; no direct lake/provider fetches or account writes.

### T4: Parent integration and release handoff

- [ ] Validate all child handoffs, inspect actual diffs and repeat decisive tests.
- [ ] Run real public capture→local lake→API projection and frontend verification.
- [ ] Commit scoped paths and obtain independent `gpt-6.1-sol/high` review of each change set; fix only blocking findings and reverify.
- [ ] Push isolated branches to configured remotes without force; create/attach reviewable PRs if available.
- [ ] Record production deployment/schedule as pending owner approval; record the conversation diary and summarize artifacts/evidence.
