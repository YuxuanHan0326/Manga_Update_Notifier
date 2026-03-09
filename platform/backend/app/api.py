from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo, available_timezones

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .adapters.base import AdapterError
from .adapters.registry import get_adapter, list_adapters
from .db import get_db
from .models import NotificationDelivery, Subscription, UpdateEvent
from .notifications.rss import compute_payload_hash, render_rss
from .notifications.webhook import WebhookNotifier
from .scheduler import scheduler_manager
from .schemas import (
    DailyScheduleUpdate,
    EventResponse,
    JobRunResponse,
    ScheduleUpdate,
    SearchResponse,
    SettingsResponse,
    SettingsUpdate,
    SourceInfo,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from .services.checker import run_update_check
from .services.settings import get_runtime_settings, upsert_settings
from .services.subscriptions import (
    create_subscription,
    delete_subscription,
    list_subscriptions,
    update_subscription,
)
from .services.summary import run_daily_summary
from .services.timezone import detect_timezone_from_ip, extract_client_ip

router = APIRouter(prefix="/api")


def _build_settings_response(cfg: dict) -> SettingsResponse:
    return SettingsResponse(
        timezone=cfg["timezone"],
        timezone_auto=cfg["timezone_auto"],
        check_cron=cfg["check_cron"],
        daily_summary_cron=cfg["daily_summary_cron"],
        webhook_enabled=cfg["webhook_enabled"],
        webhook_url=cfg["webhook_url"],
        rss_enabled=cfg["rss_enabled"],
        app_base_url=cfg["app_base_url"],
    )


def _maybe_auto_timezone(cfg: dict, request: Request, db: Session) -> tuple[dict, bool]:
    if not cfg.get("timezone_auto", True):
        return cfg, False

    # Auto-timezone is intentionally "read-time adaptive": only persist when value changes.
    detected_timezone = detect_timezone_from_ip(extract_client_ip(request))
    if not detected_timezone or detected_timezone == cfg["timezone"]:
        return cfg, False

    try:
        ZoneInfo(detected_timezone)
    except Exception:  # noqa: BLE001
        return cfg, False

    cfg = upsert_settings(db, {"timezone": detected_timezone})
    return cfg, True


def _sub_to_response(row: Subscription) -> SubscriptionResponse:
    meta = json.loads(row.item_meta_json)
    # Keep API contract stable even if historical meta payload is malformed or partial.
    last_seen_update_title = meta.get("last_seen_update_title")
    if not isinstance(last_seen_update_title, str):
        last_seen_update_title = None
    last_seen_update_at = meta.get("last_seen_update_at")
    if not isinstance(last_seen_update_at, str):
        last_seen_update_at = None
    return SubscriptionResponse(
        id=row.id,
        source_code=row.source_code,
        item_id=row.item_id,
        item_title=row.item_title,
        group_word=meta.get("group_word", "default"),
        status=row.status,
        last_seen_update_id=row.last_seen_update_id,
        last_seen_update_title=last_seen_update_title,
        last_seen_update_at=last_seen_update_at,
        item_meta=meta,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sources", response_model=list[SourceInfo])
def list_sources() -> list[SourceInfo]:
    return [SourceInfo(code=a.code, name=a.name, supports_search=True) for a in list_adapters()]


@router.get("/timezones", response_model=list[str])
def list_timezones() -> list[str]:
    return sorted(available_timezones())


@router.get("/search", response_model=SearchResponse)
def search(
    source: str = Query(...), q: str = Query(..., min_length=1), page: int = Query(1, ge=1)
) -> SearchResponse:
    try:
        adapter = get_adapter(source)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        data = adapter.search(q, page)
    except AdapterError as exc:
        # Adapter upstream errors are mapped to 502 to avoid leaking internal 500 semantics.
        raise HTTPException(status_code=502, detail=f"upstream source error: {exc}") from exc
    return SearchResponse(
        source=source,
        page=data.page,
        total=data.total,
        items=[
            {
                "item_id": item.item_id,
                "title": item.title,
                "cover": item.cover,
                "author": item.author,
                "group_word": item.group_word,
                "meta": item.meta or {},
            }
            for item in data.items
        ],
    )


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def get_subscriptions(db: Session = Depends(get_db)) -> list[SubscriptionResponse]:
    return [_sub_to_response(row) for row in list_subscriptions(db)]


@router.post("/subscriptions", response_model=SubscriptionResponse)
def post_subscriptions(
    payload: SubscriptionCreate, db: Session = Depends(get_db)
) -> SubscriptionResponse:
    row = create_subscription(db, payload)
    return _sub_to_response(row)


@router.put("/subscriptions/{sub_id}", response_model=SubscriptionResponse)
def put_subscriptions(
    sub_id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db)
) -> SubscriptionResponse:
    row = update_subscription(db, sub_id, payload)
    if row is None:
        raise HTTPException(status_code=404, detail="subscription not found")
    return _sub_to_response(row)


@router.delete("/subscriptions/{sub_id}", response_model=JobRunResponse)
def del_subscriptions(sub_id: int, db: Session = Depends(get_db)) -> JobRunResponse:
    if not delete_subscription(db, sub_id):
        raise HTTPException(status_code=404, detail="subscription not found")
    return JobRunResponse(status="ok", detail="deleted")


@router.post("/subscriptions/{sub_id}/debug/simulate-update")
def post_debug_simulate_update(sub_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="subscription not found")

    now = datetime.now(UTC)
    debug_suffix = uuid4().hex[:8]
    update_id = f"debug-{now.strftime('%Y%m%d%H%M%S')}-{debug_suffix}"
    evt = UpdateEvent(
        source_code=row.source_code,
        subscription_id=row.id,
        update_id=update_id,
        update_title=f"[DEBUG] simulated update for {row.item_title}",
        update_url="",
        detected_at=now,
        dedupe_key=f"debug:{row.source_code}:{row.id}:{update_id}",
    )
    # "debug:" prefix is used by summary query to exclude simulated events from auto pushes.
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return {"status": "ok", "event_id": evt.id, "update_id": update_id}


@router.post("/subscriptions/{sub_id}/debug/notify-test")
def post_debug_notify_test(sub_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="subscription not found")

    cfg = get_runtime_settings(db)
    now = datetime.now(UTC)
    event_payload = [
        {
            "update_title": f"[DEBUG] notify test for {row.item_title}",
            "update_id": f"debug-notify-{uuid4().hex[:8]}",
            "update_url": cfg["app_base_url"],
            "subscription_id": row.id,
            "source_code": row.source_code,
            "dedupe_key": f"debug-notify:{row.source_code}:{row.id}",
        }
    ]

    delivered_channels: list[str] = []
    skipped_channels: list[str] = []
    errors: dict[str, str] = {}

    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        ok, payload_hash, error = WebhookNotifier().send(
            cfg["webhook_url"],
            "Manual Notification Test",
            event_payload,
            now,
            now,
        )
        db.add(
            NotificationDelivery(
                channel="webhook_test",
                window_start=now,
                window_end=now,
                payload_hash=payload_hash,
                status="success" if ok else "failed",
                error=error,
            )
        )
        db.commit()
        if ok:
            delivered_channels.append("webhook")
        else:
            errors["webhook"] = error
    else:
        skipped_channels.append("webhook")

    if cfg.get("rss_enabled", True):
        # RSS is pull-based: we report channel readiness but do not trigger external push here.
        delivered_channels.append("rss")
    else:
        skipped_channels.append("rss")

    status = "ok" if delivered_channels else "failed"
    return {
        "status": status,
        "delivered_channels": delivered_channels,
        "skipped_channels": skipped_channels,
        "errors": errors,
        "rss_feed_url": f"{cfg['app_base_url'].rstrip('/')}/api/notifications/rss.xml",
        "note": "rss is pull-based and does not actively push messages",
        "payload_hash": compute_payload_hash(event_payload),
    }


@router.get("/schedules")
def get_schedules(request: Request, db: Session = Depends(get_db)) -> dict:
    cfg = get_runtime_settings(db)
    cfg, timezone_changed = _maybe_auto_timezone(cfg, request, db)
    if timezone_changed:
        # CronTrigger timezone is bound at schedule creation time, so reload is required.
        scheduler_manager.reload_jobs()
    return {
        "timezone": cfg["timezone"],
        "check_cron": cfg["check_cron"],
        "daily_summary_cron": cfg["daily_summary_cron"],
    }


@router.put("/schedules/check")
def put_schedule_check(payload: ScheduleUpdate, db: Session = Depends(get_db)) -> dict:
    try:
        CronTrigger.from_crontab(payload.cron)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid cron: {exc}") from exc

    cfg = upsert_settings(db, {"check_cron": payload.cron})
    scheduler_manager.reload_jobs()
    return {"status": "ok", "check_cron": cfg["check_cron"]}


@router.put("/schedules/daily-summary")
def put_schedule_daily(payload: DailyScheduleUpdate, db: Session = Depends(get_db)) -> dict:
    updates = {"daily_summary_cron": payload.cron}
    try:
        CronTrigger.from_crontab(payload.cron)
        if payload.timezone:
            ZoneInfo(payload.timezone)
            CronTrigger.from_crontab(payload.cron, timezone=payload.timezone)
            updates["timezone"] = payload.timezone
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid schedule: {exc}") from exc

    cfg = upsert_settings(db, updates)
    scheduler_manager.reload_jobs()
    return {
        "status": "ok",
        "daily_summary_cron": cfg["daily_summary_cron"],
        "timezone": cfg["timezone"],
    }


@router.post("/jobs/run-check")
def post_run_check(db: Session = Depends(get_db)) -> dict:
    stats = run_update_check(db)
    return {"status": "ok", **stats}


@router.post("/jobs/run-daily-summary")
def post_run_summary(db: Session = Depends(get_db)) -> dict:
    stats = run_daily_summary(db)
    return {"status": "ok", **stats}


@router.get("/events", response_model=list[EventResponse])
def get_events(status: str = Query("all"), db: Session = Depends(get_db)) -> list[EventResponse]:
    query = db.query(UpdateEvent).order_by(UpdateEvent.id.desc())
    if status == "new":
        query = query.filter(UpdateEvent.summarized_at.is_(None))
    elif status == "summarized":
        query = query.filter(UpdateEvent.summarized_at.is_not(None))

    rows = query.limit(200).all()
    return [
        EventResponse(
            id=r.id,
            source_code=r.source_code,
            subscription_id=r.subscription_id,
            update_id=r.update_id,
            update_title=r.update_title,
            update_url=r.update_url,
            detected_at=r.detected_at,
            summarized_at=r.summarized_at,
            notified_at=r.notified_at,
        )
        for r in rows
    ]


@router.get("/notifications/rss.xml")
def get_rss(db: Session = Depends(get_db)) -> Response:
    cfg = get_runtime_settings(db)
    rows = db.query(UpdateEvent).order_by(UpdateEvent.id.desc()).limit(200).all()
    events = [
        {
            "dedupe_key": r.dedupe_key,
            "update_title": r.update_title,
            "update_url": r.update_url,
            "source_code": r.source_code,
            "subscription_id": r.subscription_id,
            "detected_at": r.detected_at,
        }
        for r in rows
    ]
    xml = render_rss(cfg["app_base_url"], events)
    return Response(content=xml, media_type="application/rss+xml")


@router.post("/notifications/webhook/test")
def webhook_test(url: str | None = None, db: Session = Depends(get_db)) -> dict:
    cfg = get_runtime_settings(db)
    endpoint = url or cfg.get("webhook_url", "")
    if not endpoint:
        raise HTTPException(status_code=400, detail="webhook_url is empty")

    now = datetime.now(UTC)
    ok, payload_hash, error = WebhookNotifier().send(
        endpoint,
        "Webhook Test",
        [{"update_title": "test", "update_id": "test", "update_url": cfg["app_base_url"]}],
        now,
        now,
    )
    db.add(
        NotificationDelivery(
            channel="webhook",
            window_start=now,
            window_end=now,
            payload_hash=payload_hash,
            status="success" if ok else "failed",
            error=error,
        )
    )
    db.commit()
    return {"status": "ok" if ok else "failed", "error": error}


@router.get("/settings", response_model=SettingsResponse)
def get_settings(request: Request, db: Session = Depends(get_db)) -> SettingsResponse:
    cfg = get_runtime_settings(db)
    cfg, timezone_changed = _maybe_auto_timezone(cfg, request, db)
    if timezone_changed:
        scheduler_manager.reload_jobs()
    return _build_settings_response(cfg)


@router.put("/settings", response_model=SettingsResponse)
def put_settings(
    payload: SettingsUpdate, request: Request, db: Session = Depends(get_db)
) -> SettingsResponse:
    updates = payload.model_dump(exclude_none=True)
    if "timezone" in updates:
        ZoneInfo(updates["timezone"])
    if "check_cron" in updates:
        CronTrigger.from_crontab(updates["check_cron"])
    if "daily_summary_cron" in updates:
        CronTrigger.from_crontab(updates["daily_summary_cron"])

    cfg = upsert_settings(db, updates)
    cfg, timezone_changed = _maybe_auto_timezone(cfg, request, db)
    if timezone_changed or {"timezone", "check_cron", "daily_summary_cron"}.intersection(updates):
        # Keep scheduler in sync with persisted settings after any cron/timezone mutation.
        scheduler_manager.reload_jobs()

    return _build_settings_response(cfg)
