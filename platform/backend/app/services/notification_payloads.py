from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from urllib.parse import ParseResult, urlparse, urlunparse
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models import Subscription, UpdateEvent
from .text_normalization import repair_mojibake_text

_COPYMANGA_OFFICIAL_HOST = "www.mangacopy.com"
_COPYMANGA_LEGACY_HOSTS = {
    "copymanga.site",
    "www.copymanga.site",
}


def _safe_meta_load(meta_json: str) -> dict:
    try:
        loaded = json.loads(meta_json)
        if isinstance(loaded, dict):
            return loaded
    except Exception:  # noqa: BLE001
        return {}
    return {}


def _normalize_copymanga_url(raw_url: str) -> str:
    text = (raw_url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if host not in _COPYMANGA_LEGACY_HOSTS:
        return text

    # Rewrite historical/legacy host to official host while preserving path/query.
    replacement = ParseResult(
        scheme=parsed.scheme or "https",
        netloc=_COPYMANGA_OFFICIAL_HOST,
        path=parsed.path,
        params=parsed.params,
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunparse(replacement)


def build_source_item_url(source_code: str, item_id: str, settings: dict) -> str:
    normalized_source = (source_code or "").strip().lower()
    normalized_item = (item_id or "").strip()
    if not normalized_item:
        return ""
    if normalized_source == "copymanga":
        return f"https://{_COPYMANGA_OFFICIAL_HOST}/comic/{normalized_item}"
    if normalized_source == "kxo":
        base = str(settings.get("kxo_base_url", "https://kzo.moe")).rstrip("/")
        return f"{base}/c/{normalized_item}.htm"
    return ""


def build_notification_event(
    *,
    source_code: str,
    subscription_id: int,
    item_id: str,
    item_title: str,
    cover: str,
    source_item_url: str,
    update_id: str,
    update_title: str,
    update_url: str,
    detected_at: datetime,
    dedupe_key: str,
    timezone_name: str,
) -> dict:
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception:  # noqa: BLE001
        timezone = UTC

    detected_at_utc = detected_at.astimezone(UTC)
    detected_at_local = detected_at_utc.astimezone(timezone)
    normalized_source_item_url = source_item_url
    normalized_update_url = update_url or source_item_url
    if (source_code or "").strip().lower() == "copymanga":
        normalized_source_item_url = _normalize_copymanga_url(source_item_url)
        normalized_update_url = _normalize_copymanga_url(normalized_update_url)

    normalized_item_title = repair_mojibake_text(item_title)
    normalized_update_title = repair_mojibake_text(update_title)

    # Keep nested event structure explicit for downstream n8n/email templates.
    return {
        "id": None,
        "source_code": source_code,
        "subscription_id": subscription_id,
        "subscription": {
            "item_id": item_id,
            "item_title": normalized_item_title,
            "cover": cover,
            "source_item_url": normalized_source_item_url,
        },
        "update": {
            "update_id": update_id,
            "update_title": normalized_update_title,
            "update_url": normalized_update_url,
            "detected_at": detected_at_utc.isoformat(),
            "detected_at_local": detected_at_local.isoformat(),
            "dedupe_key": dedupe_key,
        },
    }


def build_enriched_events(db: Session, rows: list[UpdateEvent], settings: dict) -> list[dict]:
    if not rows:
        return []

    sub_ids = sorted({row.subscription_id for row in rows})
    subs = db.query(Subscription).filter(Subscription.id.in_(sub_ids)).all()
    sub_map = {sub.id: sub for sub in subs}
    timezone_name = str(settings.get("timezone", "UTC"))

    events: list[dict] = []
    for row in rows:
        sub = sub_map.get(row.subscription_id)
        meta = _safe_meta_load(sub.item_meta_json) if sub else {}
        item_id = sub.item_id if sub else ""
        item_title = sub.item_title if sub else f"subscription-{row.subscription_id}"
        cover = str(meta.get("cover") or "")
        source_item_url = build_source_item_url(row.source_code, item_id, settings)

        event = build_notification_event(
            source_code=row.source_code,
            subscription_id=row.subscription_id,
            item_id=item_id,
            item_title=item_title,
            cover=cover,
            source_item_url=source_item_url,
            update_id=row.update_id,
            update_title=row.update_title,
            update_url=row.update_url,
            detected_at=row.detected_at,
            dedupe_key=row.dedupe_key,
            timezone_name=timezone_name,
        )
        event["id"] = row.id
        events.append(event)

    return events


def build_webhook_payload(
    *,
    event_type: str,
    title: str,
    events: list[dict],
    window_start: datetime,
    window_end: datetime,
    generated_at: datetime,
    timezone_name: str,
) -> dict:
    source_counts = Counter(str(event.get("source_code", "")) for event in events)
    return {
        "schema_version": "2.0",
        "event_type": event_type,
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "timezone": timezone_name,
        "title": title,
        "window_start": window_start.astimezone(UTC).isoformat(),
        "window_end": window_end.astimezone(UTC).isoformat(),
        "count": len(events),
        "summary": {
            "total_updates": len(events),
            "sources": {k: source_counts[k] for k in sorted(source_counts)},
        },
        "events": events,
    }
