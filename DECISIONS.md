# Decisions

## D-001 Greenfield Implementation
- Date: 2026-03-09
- Status: Accepted
- Context: Existing repositories provide useful ideas but are oriented to downloader workflows.
- Decision: Build a new project from zero as the primary codebase; use existing projects as references only.
- Reason: Keeps architecture clean for update-monitoring and multi-source extensibility.
- Impact: No direct dependency on old repository structures.

## D-002 Phase 1 Source Scope
- Date: 2026-03-09
- Status: Accepted
- Context: Need fast delivery of first working version.
- Decision: Phase 1 supports CopyManga only; multi-source framework is mandatory.
- Reason: Reduce delivery risk while validating adapter architecture.
- Impact: Adapter interface must be generic from day one.

## D-003 Product Scope Boundaries
- Date: 2026-03-09
- Status: Accepted
- Context: Reference projects include download/packaging capabilities.
- Decision: Phase 1 focuses on update detection and notification, not chapter downloading or CBZ packaging.
- Reason: Align to product goal and avoid unnecessary complexity.
- Impact: Data model and APIs center on subscriptions, events, schedules, and notifications.

## D-004 Deployment Baseline
- Date: 2026-03-09
- Status: Accepted
- Context: Target runtime is NAS via Docker.
- Decision: Docker/Compose is the default deployment model for first release.
- Reason: Matches user environment and improves portability.
- Impact: All runtime configuration must be container-friendly and volume-persisted.

## D-005 Documentation-Driven Memory Protocol
- Date: 2026-03-09
- Status: Accepted
- Context: Long-running multi-session development needs stable external memory.
- Decision: Session execution must be rebuilt from project memory files, not chat history.
- Reason: Prevent context loss and inconsistent implementation behavior.
- Impact: Every implementation round must read and update memory docs as required.

## D-006 CI Platform and Gate
- Date: 2026-03-09
- Status: Accepted
- Context: Phase 1 needs enforceable quality gates for backend, frontend, and container buildability.
- Decision: Use GitHub Actions with required PR checks: backend (`ruff + pytest`), frontend (`lint + test + build`), and docker smoke build.
- Reason: Aligns with existing ecosystem and provides low-friction branch protections.
- Impact: Root Makefile is the canonical entrypoint for CI steps to avoid workflow script drift.

## D-007 Release Strategy
- Date: 2026-03-09
- Status: Accepted
- Context: Need reproducible release automation without slowing PR validation.
- Decision: Separate CI and CD. PR/main pipelines validate only; tag pipeline builds and pushes multi-arch images to GHCR.
- Reason: Keeps daily development fast and release behavior explicit.
- Impact: `release.yml` is tag-driven (`v*.*.*`) and publishes `latest` + version tags.

## D-008 Channel and Runtime Defaults (Phase 1)
- Date: 2026-03-09
- Status: Accepted
- Context: Plan v2 fixed operational defaults for first implementation.
- Decision: Default channels are Webhook + RSS, timezone default is `Asia/Shanghai`, check frequency default is every 6 hours, daily summary at 21:00 local timezone.
- Reason: Matches user-selected defaults and minimizes initial setup complexity.
- Impact: Defaults are encoded in backend settings and can be changed via API/UI.

## D-009 Adapter Upstream Error Boundary for Search
- Date: 2026-03-09
- Status: Accepted
- Context: CopyManga upstream may return non-JSON anti-bot/error pages; unhandled parse errors caused `/api/search` to return `500`.
- Decision: Adapter-level upstream parse/request failures are converted to typed adapter exceptions and exposed by `/api/search` as controlled `502 Bad Gateway` responses.
- Reason: Prevents internal-server-error behavior while keeping failure semantics explicit to UI/clients.
- Impact: Search failure path is stable and test-covered; clients can distinguish upstream-source problems from local server crashes.

## D-010 CopyManga Search Header Contract
- Date: 2026-03-09
- Status: Accepted
- Context: Runtime probes and reference client comparison showed CopyManga search can return `200 text/html` (`error`) when specific request headers are missing.
- Decision: CopyManga adapter must send `version=2025.08.15`, `platform=1`, `webp=1`, `region=1` together with existing `User-Agent` and `Accept` headers for search/update requests.
- Reason: Restores stable JSON responses and keeps Phase 1 search UX usable.
- Impact: `/api/search` success path is restored in runtime validation; header contract is now regression-tested.

## D-011 Search Metadata Source and Fallback
- Date: 2026-03-09
- Status: Accepted
- Context: Requirement changed to show last update + latest chapter text in search results, but CopyManga detail/chapter APIs can return risk-control `210` in this environment.
- Decision: Keep search API as primary result source and enrich each item via comic webpage HTML scraping for metadata; if chapter text is absent, return only available fields instead of failing search.
- Reason: Meets UX requirement while preserving reliability under unstable upstream anti-bot behavior.
- Impact: Search returns richer item metadata (`latest_update_time`, `latest_chapters`) with graceful degradation and no API contract break.

## D-012 Repository Governance Baseline
- Date: 2026-03-09
- Status: Accepted
- Context: Project entered collaborative delivery stage and needs explicit repository/legal/process baseline.
- Decision:
  - Initialize Git at repository root.
  - License project under GPLv3.
  - Enforce process rule: every implementation round must maintain `README.md` and `.gitignore`; `README.md` must remain accurate Chinese user-facing documentation.
- Reason: Ensures reproducible collaboration, clear legal status, and continuously usable user-facing documentation.
- Impact: Documentation hygiene becomes part of normal delivery definition; prompt template and ledgers must reflect this rule.

## D-013 Search Meta Fetch Status Contract
- Date: 2026-03-09
- Status: Accepted
- Context: UI now needs to distinguish metadata "not fetched" vs "fetched but no chapter" without breaking existing search API shape.
- Decision: CopyManga adapter enriches each search item with `meta.meta_fetch_status` (`ok` or `fetch_failed`) and normalizes missing chapter list to `latest_chapters: []` on successful fetch.
- Reason: Enables precise UI copy for fetch-failed vs no-chapter states while keeping backend changes minimal and backward compatible.
- Impact: Frontend uses `meta_fetch_status` to render user-facing metadata hints; adapter behavior is test-covered and cached by `item_id` for short-term fetch deduplication.

## D-014 CopyManga Web Meta Multi-Signal Parsing
- Date: 2026-03-09
- Status: Accepted
- Context: Users reported many `last-update` values still falling back to unknown despite official page showing update time and latest chapter.
- Decision: Expand webpage metadata extraction from single narrow regex to layered parsing:
  - JSON embedded keys (`datetime_updated`, `last_chapter.name`, and variants)
  - HTML label/value patterns for update time and latest chapter
  - fallback chapter-title patterns
  - escaped unicode normalization for embedded payload snippets
- Reason: Improves robustness against page-structure variance without introducing additional upstream API dependencies.
- Impact: Unknown-rate should drop significantly for search metadata enrichment; behavior is covered by adapter unit regressions.

## D-015 Post-Change Docker Verification
- Date: 2026-03-09
- Status: Accepted
- Context: User requires immediate runtime verifiability after each implementation round in NAS-target Docker environment.
- Decision: After every change round, run `cd platform && docker compose up -d --build` and report container status plus health endpoint result.
- Reason: Ensures each delivered change is quickly verifiable in the real deployment path and reduces feedback delay.
- Impact: Docker build/start check becomes a mandatory delivery step, and execution notes must include verification evidence.

## D-016 Worklog Rotation Policy
- Date: 2026-03-09
- Status: Accepted
- Context: Worklog has grown too long for practical handoff and quick context rebuild.
- Decision: When `WORKLOG.md` exceeds 150 lines, archive it to `worklog_archive/WORKLOG_ARCHIVE_<timestamp>.md` and start a new concise `WORKLOG.md` whose header summarizes key archived outcomes.
- Reason: Keeps active execution memory compact while preserving complete historical traceability.
- Impact: Worklog maintenance now includes automatic rotation threshold handling in every implementation round.

## D-017 Title-Based Latest-Chapter Fallback
- Date: 2026-03-09
- Status: Accepted
- Context: Non-standard latest chapter/volume names (for example `恶灵的失恋2`, `第7部24卷`) were still missing for some works even after multi-signal parser update.
- Decision: Add `<title>` parsing as high-priority latest-chapter fallback in CopyManga web metadata extraction, using `...漫畫-<latest>-<status>...` style patterns.
- Reason: Real pages reliably expose latest chapter/volume text in title metadata even when other HTML/JSON fields are absent or non-uniform.
- Impact: Search metadata coverage for non-standard latest names improves; behavior is locked by new adapter unit tests and runtime API verification.

## D-018 Latest-Chapter De-Dupe and Noise Filtering
- Date: 2026-03-09
- Status: Accepted
- Context: After title-based fallback, some items showed over-captured latest chapter data (duplicate long/short variants and noisy fallback sentences).
- Decision: Canonicalize latest chapter candidates by chapter-token extraction, dedupe by canonical token, and ignore fallback candidates that do not contain valid chapter tokens.
- Reason: Preserve non-standard names while preventing duplicate/noisy UI output.
- Impact: Search metadata quality improves with concise `latest_chapters` values; behavior is regression-tested and runtime-verified on reported JoJo cases.

## D-019 Protocol Exceptions for Memory and Docker Verification
- Date: 2026-03-09
- Status: Accepted
- Context: Team workflow needs explicit exceptions to avoid unnecessary ledger churn and unnecessary runtime rebuilds for non-implementation rounds.
- Decision:
  - If user only asks for explanation and no new implementation task is requested, ending without memory-file updates is allowed.
  - If a round does not touch program body (for example only `README.md`/protocol/ledger docs), Docker build/start verification can be skipped.
- Reason: Keeps workflow efficient while preserving strict validation for actual runtime-impacting changes.
- Impact: `D-015` remains default for implementation rounds, but this decision defines explicit exception boundaries.

## D-020 IP Timezone Auto-Detection and Debug Event Isolation
- Date: 2026-03-09
- Status: Accepted
- Context: User requested timezone to be auto-set by IP, added subscription-level debug tools, and required that simulated updates must not pollute normal daily summary behavior.
- Decision:
  - Add `timezone_auto` runtime setting (default enabled) and apply request-IP-based timezone lookup on settings/schedule reads with safe fallback to existing timezone.
  - Add per-subscription debug endpoints for manual notify test and simulated update creation.
  - Mark simulated events via `dedupe_key` prefix `debug:` and exclude them from daily summary candidate query.
  - Daily summary auto-push evaluates same-day events only in configured timezone; when there are no same-day real updates, it returns `no_updates` and sends nothing.
- Reason: Satisfies requested operability/debug UX while preventing false positives in production notifications.
- Impact:
  - Settings API/UI now expose auto-timezone behavior.
  - Debug operations are available without schema migration.
  - Automatic daily summary was initially tied to same-day real updates (later superseded by `D-021`).

## D-021 Backlog-Safe Summary Window (Supersedes D-020 Same-Day Cutoff)
- Date: 2026-03-09
- Status: Accepted
- Context: User reported downtime/restart scenario where updates could be detected after previous summary time and then missed by strict same-day filtering.
- Decision:
  - Daily summary candidates are all unsummarized real events (`summarized_at is null` and non-`debug:`), regardless calendar day.
  - Keep `no_updates` behavior when candidate set is empty.
- Reason: Prevents cross-day missed notifications while preserving no-noise behavior and debug-event isolation.
- Impact:
  - Replaces D-020 sub-decision of same-day cutoff.
  - Recovery after outage will still deliver pending real updates in next successful summary run.

## D-022 Auto-Timezone Private-IP Fallback
- Date: 2026-03-09
- Status: Accepted
- Context: In NAS/LAN deployments, incoming client IP is often private (`192.168.x.x`/`172.x.x.x`) so direct IP geolocation returns no timezone and system stayed on fallback timezone.
- Decision:
  - Keep public-IP direct lookup as first path.
  - Add fallback lookup endpoint for service-side source-IP detection when request IP is private or direct lookup fails.
  - Introduce `MUP_IP_TIMEZONE_SELF_API_URL` (default `https://ipapi.co/json/`).
- Reason: Ensures auto-timezone works in common private-network setups.
- Impact:
  - Auto-timezone now resolves correctly in LAN scenarios without requiring reverse-proxy public-IP headers.

## D-023 Documentation Sync and Debug-Comment Baseline
- Date: 2026-03-09
- Status: Accepted
- Context: Ongoing multi-round implementation requires docs to stay in sync with behavior changes, and developers need stable in-code debug context during maintenance.
- Decision:
  - Every implementation/code-change round must review and update related docs (`README.md` and, when applicable, `docs/*`) to reflect actual behavior.
  - Every feature implementation or bugfix that touches program code should add concise, meaningful comments around non-trivial logic for debug and handoff.
- Reason: Reduces drift between behavior and documentation, and improves maintainability/debug efficiency without large refactors.
- Impact:
  - Documentation maintenance is part of done criteria for code changes.
  - Core runtime modules progressively include explanatory comments for key paths and fallback logic.

## D-024 Approval Gate for Requirements/Brief Changes
- Date: 2026-03-09
- Status: Accepted
- Context: `REQUIREMENTS.md` and `PROJECT_BRIEF.md` are scope-control documents and should not be edited casually during implementation.
- Decision:
  - `REQUIREMENTS.md` / `PROJECT_BRIEF.md` changes require reporting a concrete edit plan to developer first, then editing only after explicit approval.
  - For normal implementation/protocol rounds, update ledgers (`NEXT_STEP.md`, `WORKLOG.md`, `TASKS.md`, `STATE.md`) and update `ARCHITECTURE.md`/`DECISIONS.md` when needed.
- Reason: Prevents requirement drift and keeps product scope changes explicitly approved.
- Impact:
  - Requirement/brief modifications become a gated operation.
  - Session protocol now distinguishes architecture/decision maintenance from requirement-level scope changes.

## D-025 Security Workflow Hardening for Reliability
- Date: 2026-03-10
- Status: Accepted
- Context: Security workflow failed in two ways:
  - `pip-audit` blocked by known `starlette` CVEs in current dependency resolution.
  - `trivy-action` failed during `setup-trivy` binary install before actual image scan.
- Decision:
  - Upgrade backend framework dependency baseline (`fastapi`) to resolve vulnerable `starlette` lineage.
  - Split security dependency audits into separate jobs (`python-audit`, `frontend-audit`) so one failure does not hide the other result.
  - Run Trivy scan via official container image instead of setup-trivy binary install path.
- Reason: Keep security checks strict while reducing pipeline fragility and improving failure diagnosability.
- Impact:
  - Security workflow becomes more robust and easier to debug.
  - Dependency vulnerability findings remain blocking at `HIGH/CRITICAL` severity.

## D-026 Friendly Schedule Controls with Advanced Cron Fallback
- Date: 2026-03-11
- Status: Accepted
- Context: Raw cron input (`0 */6 * * *`) is not user-friendly for normal users configuring schedule in UI.
- Decision:
  - Add friendly schedule controls in settings UI:
    - check every N hours
    - daily summary time (`HH:MM`)
  - Keep advanced cron fields for compatibility and non-standard schedules.
  - Friendly controls generate standard cron expressions; advanced fields remain source of truth for save payload.
- Reason: Improve usability without breaking existing cron-based backend contract or custom schedules.
- Impact:
  - FR-005 usability is improved with minimal backend change.
  - Existing custom cron users keep full compatibility.

## D-027 KXO Dual-Path Integration and Cookie Persistence Policy
- Date: 2026-03-11
- Status: Accepted
- Context: KXO source probing confirmed:
  - update data can be fetched via detail-token + `book_data.php` in same session
  - site search is authentication-gated and requires valid cookie session
  - account/password login automation is unstable in this environment
- Decision:
  - Introduce KXO source as dual-path v1:
    - `guest` mode: manual URL/ID subscription + scheduled update detection
    - `cookie` mode: search + one-click subscription when valid cookie is configured
  - Keep credential model password-free:
    - no account/password storage path
    - cookie non-persistent by default (in-memory override)
    - optional persistence only when `kxo_remember_session=true`
  - Map missing/invalid auth to explicit API errors (`auth_required` / `session_invalid`) instead of 500.
- Reason: Delivers usable KXO integration quickly while reducing security risk and avoiding brittle login automation dependency.
- Impact:
  - Backend added `KxoAdapter`, manual KXO subscription endpoint, and KXO settings test endpoint.
  - Settings schema now includes KXO runtime options and cookie-configured status.
  - Frontend gained KXO settings UI, manual-add entry, and auth guidance.

## D-028 KXO One-Shot Credential Login Entry (No Password Persistence)
- Date: 2026-03-11
- Status: Accepted
- Context: User requested in-app account/password login entry for KXO while keeping security baseline that credentials must not be stored.
- Decision:
  - Add `POST /api/settings/kxo/login` for one-shot credential login.
  - Adapter performs credential submit and returns session cookie only.
  - Username/password are never persisted to DB/settings and never echoed by settings API.
  - Cookie persistence still follows existing `remember_session` policy (`false` in-memory only, `true` persisted).
- Reason: Improves operability for users who prefer direct credential login while preserving established no-password-storage security constraints.
- Impact:
  - Frontend KXO settings now includes credential login form.
  - Backend supports runtime cookie acquisition from credentials without changing core scheduling/search contracts.

## D-029 KXO Scope Rollback to Manual-Only Path
- Date: 2026-03-11
- Status: Accepted
- Context: Runtime reliability and session fragility of KXO auth/search path caused repeated operator confusion and unstable behavior.
- Decision:
  - KXO scope is rolled back to manual-only in current phase.
  - Keep `manual URL/ID subscription + update detection`.
  - Remove KXO credential login entry and disable KXO search API path with a clear manual-only error.
  - Keep KXO base URL / user-agent connectivity settings and manual subscription endpoint.
- Reason: Prioritize stable update-detection workflow over fragile auth/search coupling.
- Impact:
  - Supersedes D-027 `cookie search` path and D-028 credential-login path.
  - Frontend KXO tab now focuses on manual add + connectivity settings only.
  - Backend `GET /api/search?source=kxo` returns manual-only guidance instead of auth/session flows.

## D-030 Cover Proxy with Host Allowlist
- Date: 2026-03-11
- Status: Accepted
- Context: User reported subscription covers consistently failing to render when browser fetched source-host image URLs directly.
- Decision:
  - Add backend `GET /api/cover-proxy` endpoint to fetch cover images server-side for frontend rendering.
  - Restrict proxy target hosts to known source/cdn suffixes (`mangafunb.fun`, `mangacopy.com`, `mxomo.com`, `kzo.moe`, `kxo.moe`) to avoid open-proxy risk.
- Reason: Improve cover render stability under hotlink/policy/network variability while keeping security boundary explicit.
- Impact:
  - Frontend cover display now uses proxied URLs with fallback placeholder on load error.
  - API surface gains a constrained media-proxy endpoint for UI only.
