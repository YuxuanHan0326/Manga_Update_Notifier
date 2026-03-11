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
  - `notification_payloads.py`: unified event enrichment + webhook payload composition
  - `settings.py`: runtime config persistence/merge + in-memory ephemeral overrides
  - `timezone.py`: client-IP timezone detection with private-IP fallback lookup
  - `bootstrap.py`: seed source metadata
- `app.notifications`:
  - `webhook.py`: outbound POST delivery (v2 payload body transport)
  - `rss.py`: RSS feed rendering (reader-friendly description text)

## Key API Additions (Current)
- `GET /api/timezones`: returns available timezone identifiers for UI dropdown.
- `GET /api/cover-proxy`: proxies allowed source cover hosts for stable UI rendering (includes host-specific referer fallback for KXO CDN behavior).
- `POST /api/subscriptions/{id}/debug/simulate-update`: creates debug-only synthetic event.
- `POST /api/subscriptions/{id}/debug/notify-test`: runs per-subscription notification test.
- `DELETE /api/subscriptions/{id}`: removes subscription and default-cleans unsummarized events.
  - Optional query `purge_history=true` also deletes summarized historical events.
- `GET /api/events`: default filters to active-subscription + non-debug events for cleaner operator view.
  - Optional query switches: `include_debug=true`, `include_inactive=true`.
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
5. Daily summary job reads unsummarized events for active subscriptions only and dispatches:
  - Webhook (if enabled)
  - RSS channel record (if enabled)
   - Summary candidate query excludes debug events (`dedupe_key` with `debug:` prefix).
   - Events tied to paused/deleted subscriptions are excluded from automatic summary.
   - Event payload enrichment attaches subscription title/cover/source links for downstream templating.
6. Successful delivery marks events `summarized_at`/`notified_at`.
7. RSS feed query also joins active subscriptions only, so paused/deleted-subscription residual events are hidden from feed output.

## Notification Payload Contract
- Webhook uses `schema_version=2.0` payload with:
  - summary metadata (`event_type`, `generated_at`, `timezone`, counters)
  - enriched per-event blocks:
    - `subscription`: `item_id`, `item_title`, `cover`, `source_item_url`
    - `update`: `update_id`, `update_title`, `update_url`, UTC/local detected time, `dedupe_key`
- RSS items are generated from the same enriched event view and target direct reader usability:
  - title: `作品名 · 最新话`
  - description: short summary line for compact list rendering in readers
  - `content:encoded`: detailed text block for expanded reading
  - `media:thumbnail` + `enclosure`: cover metadata without polluting text body
  - CopyManga URL normalization: legacy/bad-domain links are rewritten to official `www.mangacopy.com` at payload-build time

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
