from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..models import NotificationDelivery, UpdateEvent
from ..notifications.rss import compute_payload_hash
from ..notifications.webhook import WebhookNotifier
from .settings import get_runtime_settings

log = logging.getLogger(__name__)


def run_daily_summary(db: Session) -> dict:
    settings = get_runtime_settings(db)
    candidates = (
        db.query(UpdateEvent)
        .filter(UpdateEvent.summarized_at.is_(None))
        # Debug/simulated events should never pollute automatic daily summary pushes.
        .filter(UpdateEvent.dedupe_key.notlike("debug:%"))
        .order_by(UpdateEvent.id.asc())
        .all()
    )
    if not candidates:
        return {"candidates": 0, "delivered_channels": [], "status": "no_updates"}
    now = datetime.now(UTC)
    window_start = candidates[0].detected_at
    window_end = candidates[-1].detected_at

    events_payload = [
        {
            "id": item.id,
            "source_code": item.source_code,
            "subscription_id": item.subscription_id,
            "update_id": item.update_id,
            "update_title": item.update_title,
            "update_url": item.update_url,
            "detected_at": item.detected_at.isoformat(),
            "dedupe_key": item.dedupe_key,
        }
        for item in candidates
    ]

    delivered_channels: list[str] = []

    if settings.get("webhook_enabled") and settings.get("webhook_url"):
        ok, payload_hash, err = WebhookNotifier().send(
            settings["webhook_url"],
            "Daily Manga Updates",
            events_payload,
            window_start,
            window_end,
        )
        db.add(
            NotificationDelivery(
                channel="webhook",
                window_start=window_start,
                window_end=window_end,
                payload_hash=payload_hash,
                status="success" if ok else "failed",
                error=err,
            )
        )
        db.commit()
        if ok:
            delivered_channels.append("webhook")

    if settings.get("rss_enabled", True):
        # RSS delivery means feed availability, not outbound push.
        db.add(
            NotificationDelivery(
                channel="rss",
                window_start=window_start,
                window_end=window_end,
                payload_hash=compute_payload_hash(events_payload),
                status="success",
                error="",
            )
        )
        db.commit()
        delivered_channels.append("rss")

    if delivered_channels:
        # Mark all included events summarized only after at least one channel delivered.
        for item in candidates:
            item.summarized_at = now
            item.notified_at = now
        db.commit()
        return {
            "candidates": len(candidates),
            "delivered_channels": delivered_channels,
            "status": "sent",
        }

    return {"candidates": len(candidates), "delivered_channels": [], "status": "failed"}
