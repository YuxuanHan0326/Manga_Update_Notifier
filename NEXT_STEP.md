# Next Step

## Current Task
Collect user acceptance feedback for CopyManga cover fix and monitor for additional CDN edge cases.

## Progress So Far
- Root cause confirmed for reported comic:
  - CopyManga page provided cover via `<img data-src=.../cover/...>` instead of `og:image`/JSON `cover`.
  - CDN returned image bytes with `content-type: binary/octet-stream`, causing proxy rejection.
- Applied minimal fixes:
  - `copymanga.py`: add cover extraction fallback from `img data-src/src` and normalize relative cover URL.
  - `api.py`: cover proxy accepts `octet-stream` only when URL path looks like image, then maps to inferred `image/*` type.
- Added regression coverage:
  - `test_copymanga_adapter.py`: cover extraction from lazyload `data-src`, relative cover normalization.
  - `test_api_flow.py`: cover-proxy accepts `octet-stream` for image-like cover URL.
- Validation done:
  - `ruff check .` passed.
  - `pytest ../tests` passed (`55 passed`).
  - Docker rebuild/start + runtime health passed.
  - Live proxy probe for reported cover URL returned `200 image/jpeg`.

## Current Blockers
- None.

## Next Concrete Edits
1. Ask user to hard-refresh frontend and recheck previously failing CopyManga covers.
2. If any specific cover still fails, capture that cover URL and proxy error detail for targeted host-level fallback.
3. Optionally add one more integration test for any newly observed host/content-type edge case.

## Constraints Not To Forget
- Keep proxy safety boundary strict (allowed host list + image-like URL requirement).
- Do not broaden to generic open proxy behavior.
- Update ledger/docs per protocol.
