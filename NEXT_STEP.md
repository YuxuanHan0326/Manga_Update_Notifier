# Next Step

## Current Task
Collect runtime acceptance for the CopyManga request-fingerprint alignment (T-067).

## Progress So Far
- `copymanga.py` now enforces one strict API header contract and uses a bounded retry wrapper for transient failures.
- `search`/`list_updates`/`healthcheck` now all share the same request path, reducing per-endpoint drift risk.
- Unit regressions passed (`39 passed`) and Docker runtime verification passed (`/api/health` = ok).

## Current Blockers
- None.

## Next Concrete Edits
1. User side acceptance on NAS:
   - run manual check for known subscriptions and confirm no regression;
   - verify search + update check remain stable under normal use.
2. If any source still intermittently fails:
   - capture one failing response sample/log for targeted adapter retry/timeout tuning (without changing product scope).

## Constraints Not To Forget
- Keep CopyManga robustness fixes adapter-local (no KXO or notification behavior changes).
- Avoid over-design (no account-pool/login extension in this round).
