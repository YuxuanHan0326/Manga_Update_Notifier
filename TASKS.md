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
| T-064 | Harden GitHub Actions security workflow for runner compatibility and stable diagnostics | NFR-005, NFR-002 | 2026-03-12 | Applied fixes for Starlette CVE baseline, pnpm cache order, Trivy env pass-through, runtime packaging CVE remediation, `ignore-unfixed` policy, and shell-continuation bugfix; awaiting remote rerun confirmation |

## BLOCKED

| ID | Task | Req | Blocker | Notes |
|---|---|---|---|---|
| None | - | - | - | - |

## DONE

| ID | Task | Req | Completed | Notes |
|---|---|---|---|---|
| T-063 | Collect user acceptance feedback for residual mojibake repair | FR-003, FR-006 | 2026-03-12 | Superseded by higher-priority CI/security stabilization round; acceptance follow-up deferred |
| T-062 | Fix residual Chinese mojibake in stored titles/events rendering path | FR-003, FR-006, NFR-001 | 2026-03-11 | Added safe mojibake repair helper and applied to subscription/event/notification output paths; cleaned garbled literals in tests; backend checks (`ruff`, `pytest 52 passed`) and Docker runtime verification passed |
| T-061 | Collect user acceptance feedback for text-only RSS output | FR-006, FR-007 | 2026-03-11 | User reported new residual mojibake issue before standalone acceptance closure; task superseded by bugfix round |
| T-060 | Remove RSS cover-image output and keep text-only RSS entries | FR-006, FR-007 | 2026-03-11 | Removed RSS image fields (`media:thumbnail`/`enclosure`) and media namespace; updated integration test and docs; backend checks + Docker health verification passed |
| T-059 | Collect user acceptance feedback for subscribe success hint and new title text | FR-003, FR-004 | 2026-03-11 | User moved to next RSS-format change before standalone acceptance closure; task superseded by new implementation round |
| T-058 | Add explicit subscribe success feedback and rename main title to `Manga Update Notifier` | FR-003, FR-004 | 2026-03-11 | Updated `main.js` title and subscribe success alert feedback; frontend lint/test/build + Docker runtime health verification passed |
| T-057 | Collect user acceptance feedback for the localization mojibake fix | FR-003, FR-004, FR-005 | 2026-03-11 | User requested follow-up UI changes before standalone acceptance closure; round superseded by new implementation task |
| T-056 | Fix mojibake in newly localized UI text and restore title to Manga_Update_Notifier | FR-003, FR-004, FR-005, NFR-001 | 2026-03-11 | Repaired garbled newly-added UI Chinese text in frontend rendering path, restored H1 title to exact `Manga_Update_Notifier`, and passed frontend lint/test/build + Docker health verification |
| T-055 | Localize Web UI text to Chinese (retain required proper nouns only) | FR-003, FR-004, FR-005, NFR-002 | 2026-03-11 | Localized page labels/buttons/messages and event status text; kept CopyManga/KXO/RSS/Webhook/Cron terms; frontend/backend validation and Docker verification passed |
| T-054 | Clean up Events view defaults: hide debug/orphan/non-active noise by default | FR-006, NFR-003 | 2026-03-11 | `/api/events` now defaults to active + non-debug only; added optional diagnostics flags, tests, docs, and Docker verification |
| T-053 | Implement subscription/event lifecycle v2: unsubscribe cleanup + active-subscription-only RSS/summary | FR-003, FR-006, FR-007, BR-003 | 2026-03-11 | Added unsubscribe `purge_history` option, default pending-event cleanup, active-only RSS and summary joins, regression tests, and Docker verification |
| T-052 | Fix CopyManga RSS links pointing to wrong domain by canonical URL normalization | FR-006, FR-007, NFR-001 | 2026-03-11 | URL builder switched to `www.mangacopy.com`; legacy `copymanga.site` links are normalized at payload-build time; tests + Docker verification passed |
| T-051 | Improve RSS reader display quality and information layout (without changing debug inclusion policy) | FR-006, FR-007, NFR-002 | 2026-03-11 | Refined RSS layout for reader UX (`description` summary + `content:encoded` details + media thumbnail/enclosure) with tests and Docker verification |
| T-050 | Upgrade notification payloads (Webhook + RSS) to reader/automation-friendly structures and drop legacy format | FR-006, FR-007, NFR-002 | 2026-03-11 | Replaced legacy webhook/rss payloads with webhook v2 enriched contract and reader-friendly RSS output; tests + Docker verification passed |
| T-049 | Normalize garbled markdown docs and prepare a clean repository commit | NFR-002 | 2026-03-11 | Repaired markdown garble/question-mark corruption in active ledger docs and completed commit handoff preparation |
| T-048 | Debug KXO cover extraction failure and fix if extraction path is broken | FR-003, NFR-001, NFR-002 | 2026-03-11 | Root cause: `mxomo` cover CDN rejects specific referer strategy in proxy path (403); fixed proxy referer fallback order and verified KXO cover proxy returns image 200 |
| T-047 | Fix subscription cover render failure and schedule checkbox alignment | FR-003, FR-005, NFR-001, NFR-002 | 2026-03-11 | Added constrained cover proxy endpoint + frontend cover fallback binding; adjusted schedule toggle layout (label left, checkbox right/near); validation and Docker runtime checks passed |
| T-046 | Fix subscription `No Cover` regression across CopyManga/KXO (source extraction + historical backfill) | FR-003, FR-004, NFR-001, NFR-002 | 2026-03-11 | Expanded KXO/CopyManga cover extraction fallback and added on-read subscription cover backfill for historical rows; tests and Docker verification passed |
| T-045 | Scope-change: keep KXO manual subscription only, remove login/search path, and add subscription cover display | FR-003, FR-004, NFR-002, NFR-005 | 2026-03-11 | Removed KXO login/search UI+API path, enforced KXO manual-only search response, added subscription cover column/rendering, and passed full validation + Docker runtime verification |
| T-044 | Fix schedule checkbox layout regression and add non-persistent KXO manual account/password login entry | FR-004, FR-005, NFR-001, NFR-002, NFR-005 | 2026-03-11 | Fixed checkbox layout with checkbox-specific styles; added one-shot KXO credential login endpoint/UI (password not persisted); validation passed (`ruff`, `pytest 32 passed`, frontend lint/test/build, Docker runtime health) |
| T-043 | Refactor UI into source-focused tabs/pages (General / CopyManga / KXO) for better manageability | FR-003, FR-004, FR-005, NFR-002 | 2026-03-11 | Split mixed single-page frontend into three tabs with source-specific search panes; kept backend API unchanged; frontend lint/test/build and Docker runtime verification passed |
| T-042 | Align `PROJECT_BRIEF.md` and `REQUIREMENTS.md` with delivered KXO dual-path implementation | NFR-002 | 2026-03-11 | Updated brief/requirements to reflect KXO dual-path scope, auth error contract, and cookie persistence policy; docs-only round (no Docker build required) |
| T-041 | Implement KXO source dual-path v1 (guest updates + cookie search) | FR-001, FR-003, FR-004, FR-005, NFR-001, NFR-002 | 2026-03-11 | Added `KxoAdapter`, KXO runtime settings, manual KXO subscription endpoint, auth-safe search errors, frontend KXO controls, test coverage (backend 31 passed + frontend lint/test/build), and Docker runtime verification passed |
| T-040 | Rotate oversized worklog after schedule UX round | NFR-002 | 2026-03-11 | `WORKLOG.md` exceeded 150 lines and was archived to `worklog_archive/WORKLOG_ARCHIVE_20260311_024526.md`; new concise worklog initialized |
| T-039 | Improve schedule configuration UX (friendly controls over cron) | FR-005, NFR-002 | 2026-03-11 | Added friendly schedule controls (hours/time) with advanced cron compatibility, plus frontend utility tests |
| T-036 | Re-run mandatory Docker runtime verification for current implementation round | FR-008 | 2026-03-11 | Docker daemon recovered; `docker compose up -d --build`, `docker compose ps`, and `/api/health` succeeded |
| T-035 | Protocol/doc governance refresh + comment hardening + public-repo cleanup | NFR-002, NFR-001, FR-008 | 2026-03-11 | Closed after successful runtime Docker verification and ledger sync |
| T-038 | Repair failing GitHub security workflow (audit + trivy) | NFR-005, NFR-002 | 2026-03-10 | Split security audits into independent jobs, switched trivy scan to container path, upgraded FastAPI baseline to address Starlette CVE findings |
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
