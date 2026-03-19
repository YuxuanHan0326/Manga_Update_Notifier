# Worklog

## Archive Summary
- Archive file: worklog_archive/WORKLOG_ARCHIVE_20260312_192258.md
- Reason: active WORKLOG.md exceeded 150 lines and was rotated per protocol.
- Key outcomes carried forward:
  - Security workflow compatibility hardening completed (Starlette baseline, pnpm setup order, Trivy flags/cache fixes).
  - Trivy shell continuation issue fixed so --ignore-unfixed is passed correctly.
  - Latest active task switched to T-065 (CopyManga cover render failure diagnosis/fix).

## 2026-03-12

### 01. Worklog Rotation
- Archived oversized worklog and reopened concise active log for new implementation round.
- Memory ledgers kept intact (TASKS.md + NEXT_STEP.md updated before code changes).

### 02. CopyManga Cover Bug Root-Cause Analysis (T-065)
- Reproduced reported sample (`yumaoxianglinshangbushilian`) with live page probe.
- Confirmed parser gap: page exposed cover via `<img class="lazyload" data-src=".../cover/...">`, while existing extraction only matched `og:image`/JSON `cover`.
- Confirmed proxy gap: target CDN URL returned `content-type: binary/octet-stream` with valid image bytes, which previous `/api/cover-proxy` rejected as non-image.

### 03. Minimal Fix Implementation
- `platform/backend/app/adapters/copymanga.py`
  - Added cover extraction fallback pattern for `img data-src/src` URLs containing `/cover/`.
  - Added relative cover URL normalization (`/path` -> `https://www.mangacopy.com/path`).
  - Normalized search API `cover` field before returning to frontend.
- `platform/backend/app/api.py`
  - Added image media-type inference from URL extension for cover URLs.
  - Allowed `binary/octet-stream`/`application/octet-stream` only when URL is image-like, then rewrote to inferred `image/*`.
  - Kept strict host allowlist and non-image rejection to avoid broad proxy expansion.

### 04. Regression Tests and Verification
- Added tests:
  - `platform/tests/unit/test_copymanga_adapter.py`
    - lazyload `data-src` cover extraction
    - relative cover URL normalization
  - `platform/tests/integration/test_api_flow.py`
    - cover-proxy octet-stream acceptance for image-like URL
- Validation:
  - `ruff check .` passed.
  - backend full suite passed (`pytest ../tests`: `55 passed`).
  - Live adapter probe now returns reported comic cover URL.
  - Live `/api/cover-proxy` probe now returns `200 image/jpeg` for the reported cover CDN URL.
- Runtime:
  - `cd platform && docker compose up -d --build` passed.
  - `docker compose ps` shows service `Up`.
  - `/api/health` returned `{\"status\":\"ok\"}`.

### 05. Ledger and Docs Sync
- Updated `TASKS.md` (`T-065` moved to DONE).
- Updated `NEXT_STEP.md` and `STATE.md` with current completion status and follow-up acceptance path.
- Updated `README.md` cover strategy note with CopyManga `octet-stream` compatibility explanation.
- Checked `.gitignore`; no new ignore rule required in this round.

## 2026-03-19

### 01. CopyManga Update-Miss Bugfix (T-066)
- User reported real-world mismatch: source already advanced chapter (108 -> 109), but manual check returned no updates and no notification.
- Live diagnosis against user runtime (`192.168.100.1:8000`) found all CopyManga subscriptions had `last_seen_update_id = null`.
- Adapter probe confirmed chapter API returned risk-control payload (`HTTP/code=210`) with no chapter list; existing logic silently produced empty updates.

### 02. Minimal Backend Fix
- `platform/backend/app/adapters/copymanga.py`:
  - Added numeric-first chapter index sorting helper to avoid lexicographic order issues for 100+ chapters.
  - Added chapter-API blocked/empty fallback: derive latest update from webpage meta (`latest_chapters` + `latest_update_time`) and emit stable fallback update id.
  - Added diagnostic warning log when fallback is triggered due non-200 upstream code.
- `platform/backend/app/services/checker.py`:
  - Added catch-up path for legacy subscriptions where `last_seen_update_id` is missing but `last_seen_update_title` exists.
  - On first successful post-fix check, if latest title advanced (e.g. 108 -> 109), emit one update event instead of silently seeding baseline.

### 03. Regression Coverage
- `platform/tests/unit/test_copymanga_adapter.py`:
  - Added test for numeric sorting when `index` is string.
  - Added test for chapter API blocked (`code=210`) fallback to webpage latest chapter.
- `platform/tests/unit/test_checker.py`:
  - Added baseline-seed then next-run-discovery test to ensure first run seeds marker and next chapter change is detected.
  - Added catch-up test for `last_seen_update_id=null` + stale `last_seen_update_title` case to verify one-time补发事件行为.

### 04. Validation and Runtime Verification
- `ruff check platform/backend platform/tests` passed.
- `pytest -q platform/tests` passed (`59 passed`).
- Live adapter probe now returns one fallback update for `wueyxingxuanlv` with title `第109話`.
- Local API smoke:
  - create temp `wueyxingxuanlv` subscription with stale `last_seen_update_title=第108話`;
  - run `/api/jobs/run-check`;
  - verify `discovered=1` and generated event title `第109話`;
  - cleanup temp subscription + event history (`purge_history=true`).
- Docker verification:
  - `cd platform && docker compose up -d --build` passed.
  - `docker compose ps` passed (elevated check).
  - `/api/health` returned `{\"status\":\"ok\"}`.

### 05. Ledger Sync
- Updated `TASKS.md` (`T-066` moved to DONE).
- Updated `NEXT_STEP.md` to acceptance/deploy follow-up.
- Updated `STATE.md` snapshot and iteration summary.
- Updated `README.md` with CopyManga chapter-API risk-control fallback note.
- Checked `.gitignore`; no change required.

### 06. T-067 Kickoff (CopyManga request fingerprint alignment)
- Rebuilt context from all memory ledgers and PROMPT_TEMPLATE before code edits.
- Created IN_PROGRESS task T-067 and rewrote NEXT_STEP to this implementation target.
- Scope locked to CopyManga adapter request contract + tests + Docker verification (no KXO/notification scope change).

### 07. T-067 Implementation (CopyManga request fingerprint alignment)
- Added centralized official-like API header contract in `platform/backend/app/adapters/copymanga.py`.
- Added `_api_get` wrapper with short-timeout bounded retry (max attempts + total retry window + jittered delay) and debug-friendly warning logs.
- Unified `search` / `list_updates` / `healthcheck` to use same API request path; aligned chapter API request `platform` to `1`.
- Added concise code comments near transport fallback/retry logic to improve debug handoff.

### 08. T-067 Regression Coverage
- Updated `platform/tests/unit/test_copymanga_adapter.py` to assert list-updates header contract and `platform=1` request parameter.
- Added tests for transient timeout retry success path and healthcheck header contract consistency.
- Validation results:
  - `ruff check backend/app/adapters/copymanga.py ../platform/tests/unit/test_copymanga_adapter.py` passed
  - `pytest -q platform/tests/unit/test_copymanga_adapter.py` passed (`17 passed`)
  - `pytest -q platform/tests/unit` passed (`39 passed`)

### 09. Runtime Verification + Docs/Ledger Sync
- Docker verification completed:
  - `cd platform && docker compose up -d --build` succeeded
  - `cd platform && docker compose ps` shows service `Up`
  - `GET /api/health` returned `{"status":"ok"}`
- Synced docs/ledger files:
  - updated `README.md` (CopyManga official-like request fingerprint + retry behavior note)
  - updated `.gitignore` (ignore local reference clone `.tmp_ref_copymanga_downloader/`)
  - updated `DECISIONS.md` (`D-040`) and `ARCHITECTURE.md` runtime adapter note
  - updated `TASKS.md`, `NEXT_STEP.md`, `STATE.md`
