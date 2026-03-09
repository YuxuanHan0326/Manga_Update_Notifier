# Tasks

## Rules
- Status values: TODO, IN_PROGRESS, DONE, BLOCKED
- Each task maps to one or more requirement IDs
- Always write the IN_PROGRESS task entry and start implementation
- Do not remove completed tasks; move to DONE section

## TODO

| ID | Task | Req | Priority | Owner | Notes |
|---|---|---|---|---|---|
| T-012 | Maintain short-term execution memory (`NEXT_STEP.md` + `WORKLOG.md`) per implementation round | NFR-002 | High | Agent | Must update during every coding round |
| T-021 | Maintain root `README.md` and `.gitignore` on every implementation round | NFR-002 | High | Agent | `README.md` must remain accurate Chinese user-facing documentation |

## IN_PROGRESS

| ID | Task | Req | Started | Notes |
|---|---|---|---|---|
| T-035 | Protocol/doc governance refresh + comment hardening + public-repo cleanup | NFR-002, NFR-001, FR-008 | 2026-03-09 | Protocol/docs/comments/public repo work completed; pending final Docker runtime verification after daemon recovery |

## BLOCKED

| ID | Task | Req | Blocker | Notes |
|---|---|---|---|---|
| T-036 | Re-run mandatory Docker runtime verification for current implementation round | FR-008 | Local Docker daemon unavailable (`dockerDesktopLinuxEngine` pipe not found) | Required close-out step for T-035 once daemon is restored |

## DONE

| ID | Task | Req | Completed | Notes |
|---|---|---|---|---|
| T-034 | Fix missing prefill for subscription last-seen time/chapter on create | FR-003, FR-004, NFR-001 | 2026-03-09 | Added create-time prefill from search metadata (`latest_chapters`, `latest_update_time`) and covered with integration/runtime validation |
| T-037 | Align requirement/architecture docs with current implementation and protocol update | NFR-002 | 2026-03-09 | Updated `REQUIREMENTS.md`/`ARCHITECTURE.md` and synced protocol wording in `PROMPT_TEMPLATE.md`; approved before editing requirements |
| T-033 | Fix auto-timezone failure under private/LAN client IPs | FR-005, NFR-001 | 2026-03-09 | Added private-IP fallback timezone lookup (`MUP_IP_TIMEZONE_SELF_API_URL`) and unit tests; runtime `/api/settings` now resolves `Europe/London` in current environment |
| T-032 | Fix settings UI regression (timezone overlap and auto-checkbox toggle lock) | FR-005, NFR-001 | 2026-03-09 | Added grid/form width constraints to prevent timezone select overflow and removed forced settings reload on timezone-auto checkbox change so manual uncheck works |
| T-031 | Implement timezone dropdown UX, subscription last-seen details, and backlog-safe summary logic | FR-003, FR-005, FR-006, NFR-001 | 2026-03-09 | Added `/api/timezones`, timezone select/hint UI, subscription last-seen time+chapter display, checker metadata persistence, and unsummarized-real-event summary window to avoid downtime misses |
| T-030 | Rotate oversized worklog archive and reset concise active worklog | NFR-002 | 2026-03-09 | `WORKLOG.md` exceeded 150 lines and was archived to `worklog_archive/WORKLOG_ARCHIVE_20260309_070704.md`; new concise worklog initialized with archive summary |
| T-029 | Implement IP-based timezone auto-setting and subscription debug controls | FR-003, FR-005, FR-006, FR-007, NFR-001 | 2026-03-09 | Added `timezone_auto` setting, IP timezone lookup fallback, UI guide text, and subscription debug notify/simulate buttons; debug-event exclusion remains active (same-day cutoff was later superseded by `D-021`) |
| T-028 | Add protocol exceptions for explanation-only rounds and docs-only Docker skip | NFR-002, FR-008 | 2026-03-09 | Updated `PROMPT_TEMPLATE.md` and decision `D-019`; docs-only rounds can skip Docker, explanation-only rounds can skip memory-file updates |
| T-027 | Fix latest-chapter over-capture (duplicate/noisy entries) | FR-002, FR-004, NFR-001 | 2026-03-09 | Added canonical token dedupe + fallback noise filter; runtime JoJo outputs now concise (`第27话`, `第110話`) |
| T-026 | Fix non-standard latest chapter name extraction (JoJo examples) | FR-002, FR-004, NFR-001 | 2026-03-09 | Added title-based latest-name fallback parsing and regression tests; runtime API now returns `恶灵的失恋2` / `第7部24卷` for reported queries |
| T-025 | Add and apply worklog auto-archive rotation policy (`>150` lines) | NFR-002 | 2026-03-09 | Added protocol and decision rule, archived oversized worklog, and initialized new concise worklog with archive summary |
| T-024 | Enforce post-change Docker build/start verification protocol | FR-008, NFR-002 | 2026-03-09 | Added protocol rule in `PROMPT_TEMPLATE.md`, recorded as `D-015`, and executed immediate `docker compose up -d --build` verification |
| T-023 | Fix CopyManga unknown last-update parsing for search metadata | FR-002, FR-004, NFR-001 | 2026-03-09 | Hardened web metadata extraction for JSON/HTML variants and added regression tests for non-standard/escaped chapter names |
| T-014 | Add branch protection/ruleset setup docs for required checks in GitHub | NFR-002 | 2026-03-09 | Added `docs/branch-protection.md` and `docs/nas-ops-runbook.md` with manual setup and NAS operations guidance |
| T-022 | Improve search metadata resilience and UX wording | FR-002, FR-004, NFR-001 | 2026-03-09 | Added per-item short TTL cache in CopyManga adapter and frontend copy distinction for fetch-failed vs no-chapter states |
| T-020 | Establish repository baseline (Git init + GPLv3 + root README/.gitignore governance) | NFR-002 | 2026-03-09 | Root Git initialized; GPLv3 LICENSE added; Chinese README and root .gitignore created; governance protocol recorded |
| T-019 | Enhance search UX with cover display, pagination, and update metadata text | FR-002, FR-004, NFR-001 | 2026-03-09 | Implemented cover rendering, page navigation, and metadata display from adapter web scraping fallback |
| T-018 | Prevent local frontend artifacts from breaking Docker build context | FR-008, NFR-002 | 2026-03-09 | Added `platform/.dockerignore` to exclude `frontend/node_modules` and `frontend/dist` from image build context |
| T-017 | Restore CopyManga search usability under upstream header constraints | FR-002, FR-004, NFR-001 | 2026-03-09 | Added required headers (`version/webp/region`) and regression test; runtime `/api/search` returns 200 |
| T-016 | Harden CopyManga adapter response handling for non-JSON/error pages | NFR-001 | 2026-03-09 | Implemented adapter/API guards and added regression test for `/api/search` 502 behavior |
| T-000 | Project initialization and memory docs bootstrap | NFR-002 | 2026-03-09 | Baseline memory docs created |
| T-004 | Draft initial decisions log | NFR-002 | 2026-03-09 | `DECISIONS.md` created |
| T-013 | Activate short-term execution-memory protocol | NFR-002 | 2026-03-09 | `NEXT_STEP.md` + `WORKLOG.md` created and read-cycle verified |
| T-001 | Confirm Phase 1 notification channels and fallback policy | FR-006, FR-007 | 2026-03-09 | Confirmed as Webhook + RSS |
| T-002 | Define source adapter interface and error contract | FR-001 | 2026-03-09 | Implemented in `platform/backend/app/adapters/base.py` |
| T-003 | Draft initial architecture document | NFR-002 | 2026-03-09 | `ARCHITECTURE.md` created |
| T-005 | Define DB schema (subscriptions, events, deliveries, schedules) | FR-003, FR-005, FR-006 | 2026-03-09 | Implemented with SQLAlchemy models |
| T-006 | Build backend skeleton (API + scheduler + storage) | FR-005, FR-008 | 2026-03-09 | FastAPI + APScheduler + SQLite delivered |
| T-007 | Implement CopyManga adapter: search + update listing | FR-002, FR-004 | 2026-03-09 | Adapter shipped in backend |
| T-008 | Implement Web UI: subscriptions + search + scheduler settings | FR-003, FR-004, FR-005 | 2026-03-09 | Vite frontend shipped |
| T-009 | Implement daily summary aggregator and notifier abstraction | FR-006, FR-007 | 2026-03-09 | Webhook + RSS delivered |
| T-010 | Create Docker compose and deployment docs | FR-008 | 2026-03-09 | Dockerfile/compose/README added |
| T-011 | Add integration tests for adapter and scheduling flow | NFR-001, NFR-002 | 2026-03-09 | Unit + integration tests added and passing |
| T-015 | Validate Docker smoke build in an environment with running Docker daemon | FR-008 | 2026-03-09 | Docker build + compose + API smoke validated on active daemon |
