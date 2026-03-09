from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..adapters.registry import get_adapter
from ..models import Subscription, UpdateEvent

log = logging.getLogger(__name__)


def _meta(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return {}


def run_update_check(db: Session) -> dict[str, int]:
    rows = db.query(Subscription).filter(Subscription.status == "active").all()
    scanned = 0
    discovered = 0

    for row in rows:
        scanned += 1
        try:
            meta = _meta(row.item_meta_json)
            adapter = get_adapter(row.source_code)
            updates = adapter.list_updates(row.item_id, meta)
            if not updates:
                continue

            latest_id = updates[-1].update_id
            latest_title = updates[-1].title
            seen_at = datetime.now(UTC).isoformat()
            if row.last_seen_update_id is None:
                # First successful fetch seeds baseline and avoids backfilling historical chapters.
                row.last_seen_update_id = latest_id
                meta["last_seen_update_title"] = latest_title
                meta["last_seen_update_at"] = seen_at
                row.item_meta_json = json.dumps(meta, ensure_ascii=False)
                db.commit()
                continue

            seen_index = next(
                (
                    i
                    for i, update in enumerate(updates)
                    if update.update_id == row.last_seen_update_id
                ),
                -1,
            )
            if seen_index == -1:
                # fallback when remote history no longer contains old marker
                new_updates = updates[-1:]
            else:
                new_updates = updates[seen_index + 1 :]

            for update in new_updates:
                dedupe_key = f"{row.source_code}:{row.id}:{update.update_id}"
                evt = UpdateEvent(
                    source_code=row.source_code,
                    subscription_id=row.id,
                    update_id=update.update_id,
                    update_title=update.title,
                    update_url=update.url,
                    detected_at=datetime.now(UTC),
                    dedupe_key=dedupe_key,
                )
                db.add(evt)
                try:
                    db.commit()
                    discovered += 1
                except IntegrityError:
                    # Another run already inserted the same dedupe_key; keep loop idempotent.
                    db.rollback()

            row.last_seen_update_id = latest_id
            meta["last_seen_update_title"] = latest_title
            meta["last_seen_update_at"] = seen_at
            row.item_meta_json = json.dumps(meta, ensure_ascii=False)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            log.exception("update check failed for subscription %s: %s", row.id, exc)

    return {"scanned": scanned, "discovered": discovered}
