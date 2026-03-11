# Worklog

## Archive Summary
- Archive file: worklog_archive/WORKLOG_ARCHIVE_20260311_061924.md
- Reason: active WORKLOG.md exceeded 150 lines and was rotated per protocol.
- Key outcomes carried forward:
  - Completed subscription cover bugfix for CopyManga + KXO.
  - Added on-read backfill for historical subscriptions missing `item_meta.cover`.
  - Added regression tests (unit + integration) and validation passed.
  - Docker runtime verification passed (`compose up`, container `Up`, `/api/health=200`).

## 2026-03-11

### 01. Worklog Rotation
- Rotated oversized WORKLOG (>150 lines) into archive.
- Recreated concise WORKLOG with handoff summary.
### 02. Final Validation Snapshot
- Backend lint/tests passed (`ruff`, `pytest unit=23`, `pytest integration=10`).
- Frontend checks passed (`npm run lint`, `npm run test`, `npm run build`; test/build required elevated mode due sandbox `spawn EPERM`).
- Runtime verified: `docker compose ps` is `Up`, `/api/health` returned `200`.
### 03. Bugfix Round Start: Cover Render + Schedule Tick Alignment
- Marked `T-047` as `IN_PROGRESS` and updated `NEXT_STEP.md`.
- Planned to fix two user-facing issues in one minimal round: subscription cover rendering failure and schedule toggle tick alignment.
### 04. Bugfix Round: Cover Render + Schedule Toggle Alignment
- Diagnosis:
  - `/api/subscriptions` returned valid cover URLs, but browser-side direct fetch failed under source hotlink/host policy.
- Backend change:
  - Added `GET /api/cover-proxy` in `app/api.py` with explicit allowed host suffix checks to avoid open-proxy behavior.
- Frontend change:
  - Updated `frontend/src/main.js` to render cover images through `/api/cover-proxy` and keep `No Cover` fallback on load failure.
  - Updated `frontend/src/main.js` + `frontend/src/style.css` to align schedule toggle checkbox next to label text.
- Validation:
  - `ruff` passed.
  - `pytest unit` passed (23).
  - `pytest integration` passed (12).
  - `npm run lint/test/build` passed (test/build required elevated mode due esbuild `spawn EPERM` in sandbox).
  - Docker runtime verification passed (`compose up -d --build`, `compose ps`, `/api/health`).
- Runtime smoke:
  - `/api/cover-proxy` returned `200 image/jpeg` for tested cover URLs and image rendering recovered.
### 05. Bugfix Round Start: KXO Cover Extraction Debug
- Set `T-048` to IN_PROGRESS and updated `NEXT_STEP.md` for KXO cover diagnostic scope.
- Plan: inspect live KXO snapshot output, confirm cover URL format/reachability, then apply minimal parser fix if needed.
### 06. KXO Cover Extraction Debug and Fix
- Diagnostic result:
  - KXO `item_meta.cover` exists (adapter extraction path works).
  - Failure point is cover proxy fetch policy for `kmimg.mxomo.com`: previous referer strategy produced upstream `403`.
- Implementation:
  - `app/api.py` cover proxy now uses host-specific referer fallback for `mxomo` hosts (`None -> https://kzo.moe/ -> https://kxo.moe/`).
  - Added helper `_cover_referer_candidates` and kept allowlist boundary unchanged.
- Validation:
  - `ruff` passed.
  - `pytest unit` passed (23).
  - `pytest integration` passed (13).
  - Docker rebuild + runtime check passed (`compose up -d --build`, `compose ps`, `/api/health`).
  - Runtime smoke: KXO cover via `/api/cover-proxy` now returns `200 image/png`.
### 07. Docs Garble Repair + Commit Prep
- Started `T-049` to fix markdown garbled text and prepare a clean repository commit.
- Rebuilt session context from required memory files before edits.
- Repaired broken `WORKLOG.md` section entries that had placeholder `?` corruption.
- Restored accidentally re-encoded docs and verified markdown files are valid UTF-8.
- Repaired `STATE.md` sample text entries for non-standard latest-chapter examples.
- Confirmed markdown scan has no remaining control-character mojibake or triple-question corruption patterns.
