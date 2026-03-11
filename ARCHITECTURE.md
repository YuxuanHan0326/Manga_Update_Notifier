# Architecture

## Overview
Phase 1 is a Docker-first single-service architecture with:
- FastAPI backend for APIs and scheduling
- SQLite for persistence
- Adapter layer for source integration
- Notification layer for Webhook + RSS
- Static frontend served by the backend in container runtime

## Backend Modules
- `app.main`: app bootstrap, DB init, adapter registration, scheduler lifecycle.
- `app.api`: public HTTP API (`/api/*`) for search, subscriptions, schedules, jobs, events, settings, RSS.
  - Includes helper endpoints for timezone list (`/api/timezones`) and subscription debug actions.
- `app.scheduler`: APScheduler manager with two cron jobs:
  - `check_updates`
  - `daily_summary`
- `app.adapters`:
  - `base.py`: adapter contract (`search`, `list_updates`, `healthcheck`) + typed auth/upstream error boundary
  - `registry.py`: adapter registry
  - `copymanga.py`: CopyManga source adapter
  - `kxo.py`: KXO adapter (manual-subscription update detection path)
- `app.services`:
  - `subscriptions.py`: CRUD service logic
  - `checker.py`: update detection + dedupe event creation
  - `summary.py`: daily aggregation + channel delivery bookkeeping
  - `settings.py`: runtime config persistence/merge + in-memory ephemeral overrides
  - `timezone.py`: client-IP timezone detection with private-IP fallback lookup
  - `bootstrap.py`: seed source metadata
- `app.notifications`:
  - `webhook.py`: outbound POST delivery
  - `rss.py`: RSS feed rendering

## Key API Additions (Current)
- `GET /api/timezones`: returns available timezone identifiers for UI dropdown.
- `GET /api/cover-proxy`: proxies allowed source cover hosts for stable UI rendering (includes host-specific referer fallback for KXO CDN behavior).
- `POST /api/subscriptions/{id}/debug/simulate-update`: creates debug-only synthetic event.
- `POST /api/subscriptions/{id}/debug/notify-test`: runs per-subscription notification test.
- `POST /api/subscriptions/manual-kxo`: accepts KXO URL/ID and creates subscription via backend parsing.
- `POST /api/settings/kxo/test`: validates KXO runtime configuration state.

## Data Model (SQLite)
- `sources`: registered source metadata.
- `subscriptions`: tracked items and last seen update marker.
- `update_events`: detected updates with dedupe key and delivery state.
- `notification_deliveries`: channel delivery history for summary windows.
- `system_settings`: persisted runtime settings (cron/timezone/channels/source options).

## Data Flow
1. User searches source via `/api/search`.
2. User creates subscription via `/api/subscriptions`.
3. Check job (`run_update_check`) calls adapter `list_updates` per active subscription.
4. New chapters become `update_events` (deduped by unique `dedupe_key`).
   - Checker also persists last-seen title/time into subscription metadata for UI display.
5. Daily summary job reads unsummarized events and dispatches:
  - Webhook (if enabled)
  - RSS channel record (if enabled)
   - Summary candidate query excludes debug events (`dedupe_key` with `debug:` prefix).
6. Successful delivery marks events `summarized_at`/`notified_at`.

## Adapter Runtime Notes
- `copymanga` search results are enriched by webpage metadata scraping fallback.
- Short in-process TTL cache (by `item_id`) is used for meta enrichment to reduce repeated fetches during paged search.
- `kxo` updates use a two-step same-session fetch (`/c/<id>.htm` token extraction -> `/book_data.php?h=...`).
- `kxo` is manual-only in current scope: search endpoint rejects `source=kxo` with a readable manual-only error.
- KXO host fallback order is `configured base -> kzo.moe -> kxo.moe`.

## KXO Credential Strategy
- No account/password storage path in app runtime.
- Credential login path is removed in current scope; KXO integration uses manual URL/ID subscriptions only.

## Frontend Schedule UX Notes
- Settings page provides friendly schedule controls:
  - check every N hours
  - daily summary time (`HH:MM`)
- Friendly controls generate standard cron strings and keep advanced cron fields for compatibility.

## Frontend Information Architecture
- Frontend is split into source-focused tabs to reduce mixed-page complexity:
  - `General`: subscriptions, schedule/general settings, events
  - `CopyManga`: CopyManga search and one-click subscription
  - `KXO`: manual URL/ID subscription and KXO-specific connectivity settings
- Backend API contracts remain unchanged; tab split is a presentation-layer reorganization.

## Runtime Defaults
- Timezone: `Asia/Shanghai`
- Check cron: `0 */6 * * *`
- Daily summary cron: `0 21 * * *`
- Security baseline: reverse-proxy auth preferred; app keeps auth lightweight.

## CI/CD Contract
- Root `Makefile` defines canonical CI entrypoints:
  - `ci-backend`
  - `ci-frontend`
  - `ci-build`
  - `ci-integration`
- GitHub Actions:
  - `ci.yml`: lint/test/build validation on PR and main
  - `release.yml`: tag-triggered multi-arch image push to GHCR
  - `security.yml`: dependency + image scanning
