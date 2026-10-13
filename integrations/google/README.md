---
title: Google Integration Boundary
aliases: [Google Calendar Integration]
tags: [integrations, google, calendar, index]
created: 2026-08-16
updated: 2026-08-16
description: Account-agnostic boundary for the local Google Calendar integration.
status: active
parent: integrations/README.md
related: [../../platform-accounts-api/README.md, ../INTEGRATION-GUIDE.md]
---

# Google Integration Boundary

This folder contains the account-agnostic Google Calendar OAuth setup. The
local calendar projection (`calendar_sync.py`, the `calendar_events` table) was
retired with the SQLite control plane on 2026-10-11; read-only Calendar probes
live in `infra/scripts/sync/sync_google_calendar.py`.

## Files

- [`setup_calendar.py`](setup_calendar.py) — local OAuth setup helper
- [`requirements.txt`](requirements.txt) — package declaration for this boundary

## Runtime rules

- OAuth material belongs in the documented local secret/config location, never
  in this repository.
- This folder does not store calendar events; a future calendar cell owns them.
- Add a provider-specific subfolder only when the integration has a distinct
  lifecycle, credentials boundary, or deployment contract.

## Commands

```bash
python3 integrations/google/setup_calendar.py
```
