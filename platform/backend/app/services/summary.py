from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..models import NotificationDelivery, Subscription, UpdateEvent
from ..notifications.rss import compute_payload_hash
from ..notifications.webhook import WebhookNotifier
from .notification_payloads import build_enriched_events, build_webhook_payload
from .settings import get_runtime_settings

log = logging.getLogger(__name__)


def run_daily_summary(db: Session) -> dict:
    settings = get_runtime_settings(db)
    candidates = (
        db.query(UpdateEvent)
        .join(Subscription, Subscription.id == UpdateEvent.subscription_id)
        # Keep automatic summary aligned with user-visible subscriptions only.
        .filter(Subscription.status == "active")
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

    events_payload = build_enriched_events(db, candidates, settings)

    delivered_channels: list[str] = []

    if settings.get("webhook_enabled") and settings.get("webhook_url"):
        webhook_payload = build_webhook_payload(
            event_type="daily_summary",
            title="Daily Manga Updates",
            events=events_payload,
            window_start=window_start,
            window_end=window_end,
            generated_at=now,
            timezone_name=str(settings.get("timezone", "UTC")),
        )
        ok, payload_hash, err = WebhookNotifier().send(
            settings["webhook_url"],
            webhook_payload,
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
