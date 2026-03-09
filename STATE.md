# State

## Snapshot
- Date: 2026-03-09
- Phase: Phase 1 MVP Implemented
- Overall Status: IN_PROGRESS

## Current Objective
Stabilize and harden the shipped Phase 1 implementation for production use on NAS.

## What Is Done In This Iteration
- Delivered greenfield implementation under `platform/`:
  - Backend (FastAPI + scheduler + adapters + services + models)
  - Frontend (Vite UI for search/subscriptions/settings/events)
  - Docker artifacts (`platform/Dockerfile`, `platform/docker-compose.yml`)
  - CI/CD artifacts (`Makefile`, `.github/workflows/*.yml`)
- Added architecture and memory ledgers (`ARCHITECTURE.md`, decisions/tasks/state/next-step/worklog).
- Fixed search reliability issues (upstream non-JSON handling + header contract alignment).
- Delivered search UX enhancements (cover, pagination, metadata rendering).
- Added short-term metadata cache and fetch-state contract (`meta_fetch_status`) for search enrichment.
- Added T-014 docs:
  - `docs/branch-protection.md`
  - `docs/nas-ops-runbook.md`
- Completed unknown last-update bugfix round:
  - Hardened CopyManga web metadata extraction with multi-signal parsing (JSON keys + HTML label/value + fallback).
  - Added escaped unicode normalization for embedded payloads.
  - Added regression tests for non-standard and escaped chapter names.
  - Adapter unit tests pass (`7 passed`).
- Completed protocol update round:
  - Added mandatory post-change Docker verification rule in `PROMPT_TEMPLATE.md`.
  - Recorded decision `D-015` for post-change Docker build/start verification.
  - Executed immediate runtime verification via `docker compose up -d --build` and confirmed healthy service.
- Completed worklog rotation protocol round:
  - Added worklog auto-archive threshold rule (`>150` lines) to `PROMPT_TEMPLATE.md`.
  - Recorded decision `D-016` for worklog rotation policy.
  - Archived oversized worklog and initialized a new concise `WORKLOG.md` with archive summary header.
- Completed non-standard latest-name bugfix round:
  - Added `<title>`-based latest-chapter/volume fallback extraction in CopyManga parser.
  - Added unit tests for reported non-standard names (`恶灵的失恋2`, `第7部24卷`).
  - Runtime API verification confirms JoJo example queries now return expected latest names.
- Completed over-capture refinement round:
  - Added canonical chapter-token extraction and dedupe for latest chapter candidates.
  - Filtered fallback noise entries without valid chapter tokens.
  - Runtime verification confirms concise outputs for reported cases (`第27话`, `第110話`) without noisy duplicates.
- Completed protocol-exception round:
  - Added rule: explanation-only rounds with no new implementation task may skip memory-file updates.
  - Added rule: docs-only rounds that do not touch program body may skip Docker build/start verification.
  - Recorded these boundaries in `D-019`.
- Completed timezone/debug-tools round:
  - Added IP-based timezone auto-detection (`timezone_auto`) with fallback behavior.
  - Added subscription debug buttons and backend endpoints for notify-test + simulate-update.
  - Enforced simulated-event isolation from daily summary (`debug:` dedupe key excluded).
  - Summary trigger was temporarily tightened to same-day real updates (later superseded by `D-021`).
  - Added regression tests and passed validation (`ruff` + `pytest 19 passed` + frontend lint/test/build).
  - Completed runtime Docker verification (`docker compose up -d --build`, `docker compose ps`, `/api/health`).
- Completed timezone-dropdown + backlog-safe-summary round:
  - Replaced timezone text input with dropdown backed by `/api/timezones`.
  - Added timezone hint to show current auto/manual timezone value in settings UI.
  - Subscriptions now show last-seen timestamp and latest chapter title.
  - Summary trigger now uses unsummarized real events across day boundaries (same-day cutoff superseded by `D-021`).
  - Added/updated tests and passed validation (`ruff` + `pytest 20 passed` + frontend lint/test/build).
  - Completed runtime Docker verification (`docker compose up -d --build`, `docker compose ps`, `/api/health`).
- Completed settings UI bugfix round:
  - Fixed timezone select overflow/overlap in `Schedules & Settings` by adding grid label/control width constraints.
  - Fixed `Timezone Auto (by IP)` checkbox toggle lock by removing immediate settings reload on checkbox change.
  - Frontend validation passed (`npm run lint/test/build`).
  - Completed runtime Docker verification (`docker compose up -d --build`, `docker compose ps`, `/api/health`).
- Completed auto-timezone LAN fallback round:
  - Added private-IP fallback lookup path for auto-timezone detection.
  - Added `MUP_IP_TIMEZONE_SELF_API_URL` config for service-side source-IP timezone lookup.
  - Added unit tests for public lookup, private-IP fallback, and failure fallback.
  - Runtime verification confirms `/api/settings` now returns `Europe/London` in current environment.
  - Completed runtime Docker verification (`docker compose up -d --build`, `docker compose ps`, `/api/health`).
- Completed subscription-prefill bugfix round:
  - Self-check confirmed list-render path existed but create-time prefill was missing.
  - Added create-time prefill for `last_seen_update_title` and `last_seen_update_at` from search metadata.
  - Added integration test and runtime smoke check for prefilled subscription response.
  - Completed runtime Docker verification (`docker compose up -d --build`, `docker compose ps`, `/api/health`).
- Active worklog rotated automatically after exceeding 150 lines; archive created at `worklog_archive/WORKLOG_ARCHIVE_20260309_070704.md`.
- Completed public-repo hardening round (in progress closure pending Docker daemon availability):
  - Updated protocol with docs-sync + meaningful code-comment requirements (`D-023`).
  - Added public collaboration/security docs (`CONTRIBUTING.md`, `SECURITY.md`) and env template (`platform/.env.example`).
  - Reviewed and updated user/operator docs (`README.md`, `.gitignore`, `docs/nas-ops-runbook.md`).
  - Added targeted debug-oriented comments across core backend/frontend runtime paths.
  - Validation passed: backend (`ruff`, `pytest 24 passed`) and frontend (`npm run lint/test/build`).
  - Docker runtime verification attempted but blocked due unavailable daemon pipe (`dockerDesktopLinuxEngine`).
- Completed documentation alignment round (approved requirement update):
  - Updated `REQUIREMENTS.md` acceptance details for subscription Last Seen, search pagination/metadata, and manual timezone dropdown.
  - Updated `ARCHITECTURE.md` to reflect current API/service behavior (`/api/timezones`, debug endpoints, timezone fallback service, summary debug exclusion, adapter meta cache).
  - Synced protocol wording in `PROMPT_TEMPLATE.md` and recorded decision `D-024` for approval-gated requirement/brief edits.
  - This round touched docs only; Docker rebuild was skipped by protocol exception.

## Next Step
1. Start Docker daemon and rerun mandatory runtime verification (`compose up -d --build`, `compose ps`, `/api/health`) to close this round.
2. Apply branch protection/ruleset in GitHub UI using `docs/branch-protection.md` and verify required checks are enforced.
3. Continue adapter observability hardening (structured warning fields for source/status/content-type) without API contract changes.

## Active Risks
- R-001: Source anti-bot/rate-limit behavior may still impact long-term stability.
- R-002: CopyManga anti-bot behavior remains an upstream risk; request/header contract may drift.
- R-003: Reverse-proxy auth is external; misconfiguration could expose APIs.
- R-004: Webpage metadata availability is non-uniform; some comics may still expose partial fields.
- R-005: Metadata cache is in-process TTL and not persisted across restarts (intentional for Phase 1 simplicity).
- R-006: CopyManga page schema may continue evolving; parser is broader now but still depends on detectable JSON/HTML hints.
- R-007: Local Docker daemon availability can temporarily block mandatory runtime verification despite code/test success.

## Assumptions In Effect
- Single-instance NAS deployment for Phase 1.
- CopyManga is first supported source.
- Existing repositories are references, not codebase foundation.
- Default timezone fallback is `Asia/Shanghai`; `timezone_auto` is enabled and may auto-adjust by client IP.
- Notification channels enabled by design: Webhook + RSS.

## Handover Notes
- Re-read `PROJECT_BRIEF.md`, `REQUIREMENTS.md`, `DECISIONS.md`, `TASKS.md`, `STATE.md`, and `NEXT_STEP.md` at the start of each implementation session.
- If chat instructions conflict with documented decisions, resolve and update files first.
- Every implementation round must also review and maintain root `README.md` and `.gitignore`.
