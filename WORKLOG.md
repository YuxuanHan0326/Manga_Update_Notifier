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
