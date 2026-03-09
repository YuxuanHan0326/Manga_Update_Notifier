from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import Subscription
from ..schemas import SubscriptionCreate, SubscriptionUpdate


def _decode_meta(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return {}


def _first_non_empty_str(values: list) -> str | None:
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _prefill_last_seen_meta(meta: dict) -> None:
    # Prefill keeps new subscriptions informative before first scheduled check runs.
    if not isinstance(meta.get("last_seen_update_title"), str):
        latest_chapters = meta.get("latest_chapters")
        if isinstance(latest_chapters, list):
            chapter_title = _first_non_empty_str(latest_chapters)
            if chapter_title:
                meta["last_seen_update_title"] = chapter_title
        elif isinstance(latest_chapters, str):
            chapter_title = latest_chapters.strip()
            if chapter_title:
                meta["last_seen_update_title"] = chapter_title

    if not isinstance(meta.get("last_seen_update_at"), str):
        for key in ("latest_update_time", "latest_update_at"):
            value = meta.get(key)
            if isinstance(value, str):
                timestamp = value.strip()
                if timestamp:
                    meta["last_seen_update_at"] = timestamp
                    break


def list_subscriptions(db: Session) -> list[Subscription]:
    return db.query(Subscription).order_by(Subscription.id.desc()).all()


def create_subscription(db: Session, payload: SubscriptionCreate) -> Subscription:
    meta = dict(payload.item_meta)
    meta.setdefault("group_word", payload.group_word)
    # Align create-time metadata with list rendering contract.
    _prefill_last_seen_meta(meta)
    row = Subscription(
        source_code=payload.source_code,
        item_id=payload.item_id,
        item_title=payload.item_title,
        item_meta_json=json.dumps(meta, ensure_ascii=False),
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_subscription(
    db: Session, sub_id: int, payload: SubscriptionUpdate
) -> Subscription | None:
    row = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if row is None:
        return None

    if payload.item_title is not None:
        row.item_title = payload.item_title
    if payload.status is not None:
        row.status = payload.status
    if payload.group_word is not None:
        meta = _decode_meta(row.item_meta_json)
        meta["group_word"] = payload.group_word
        row.item_meta_json = json.dumps(meta, ensure_ascii=False)

    db.commit()
    db.refresh(row)
    return row


def delete_subscription(db: Session, sub_id: int) -> bool:
    row = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
