from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo, available_timezones

import httpx
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .adapters.base import AdapterAuthRequiredError, AdapterError, AdapterSessionInvalidError
from .adapters.kxo import KxoAdapter
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
    KxoManualSubscriptionCreate,
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
from .services.notification_payloads import (
    build_enriched_events,
    build_notification_event,
    build_source_item_url,
    build_webhook_payload,
)
from .services.settings import get_runtime_settings, upsert_ephemeral_settings, upsert_settings
from .services.subscriptions import (
    backfill_subscription_covers,
    create_subscription,
    delete_subscription,
    list_subscriptions,
    update_subscription,
)
from .services.summary import run_daily_summary
from .services.text_normalization import repair_mojibake_text
from .services.timezone import detect_timezone_from_ip, extract_client_ip

router = APIRouter(prefix="/api")

_ALLOWED_COVER_HOST_SUFFIXES = (
    "mangafunb.fun",
    "mangacopy.com",
    "mxomo.com",
    "kzo.moe",
    "kxo.moe",
)


def _is_allowed_cover_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if not normalized:
        return False
    return any(
        normalized == suffix or normalized.endswith(f".{suffix}")
        for suffix in _ALLOWED_COVER_HOST_SUFFIXES
    )


def _cover_referer_candidates(parsed_url) -> list[str | None]:
    host = (parsed_url.hostname or "").lower()
    # Some KXO CDN hosts (for example `*.mxomo.com`) reject same-host referer but
    # accept source-site referer or no referer. Ordered fallback keeps behavior stable.
    if host.endswith("mxomo.com"):
        return [None, "https://kzo.moe/", "https://kxo.moe/"]
    return [None, f"{parsed_url.scheme}://{parsed_url.netloc}/"]


def _build_settings_response(cfg: dict) -> SettingsResponse:
    kxo_cookie = cfg.get("kxo_cookie", "")
    return SettingsResponse(
        timezone=cfg["timezone"],
        timezone_auto=cfg["timezone_auto"],
        check_cron=cfg["check_cron"],
        daily_summary_cron=cfg["daily_summary_cron"],
        webhook_enabled=cfg["webhook_enabled"],
        webhook_url=cfg["webhook_url"],
        rss_enabled=cfg["rss_enabled"],
        app_base_url=cfg["app_base_url"],
        kxo_base_url=cfg["kxo_base_url"],
        kxo_auth_mode=cfg["kxo_auth_mode"],
        kxo_cookie_configured=bool(isinstance(kxo_cookie, str) and kxo_cookie.strip()),
        kxo_remember_session=cfg["kxo_remember_session"],
        kxo_user_agent=cfg["kxo_user_agent"],
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
    else:
        last_seen_update_title = repair_mojibake_text(last_seen_update_title)
    last_seen_update_at = meta.get("last_seen_update_at")
    if not isinstance(last_seen_update_at, str):
        last_seen_update_at = None
    return SubscriptionResponse(
        id=row.id,
        source_code=row.source_code,
        item_id=row.item_id,
        item_title=repair_mojibake_text(row.item_title),
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


@router.get("/cover-proxy")
def get_cover_proxy(url: str = Query(..., min_length=1)) -> Response:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="invalid cover url")

    host = (parsed.hostname or "").lower()
    # Keep proxy scope narrow to prevent it from becoming a generic open proxy.
    if not _is_allowed_cover_host(host):
        raise HTTPException(status_code=400, detail=f"cover host is not allowed: {host}")

    base_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    last_error = "cover proxy upstream error: unknown"
    for referer in _cover_referer_candidates(parsed):
        headers = dict(base_headers)
        if referer:
            headers["Referer"] = referer
        try:
            upstream = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        except httpx.HTTPError as exc:
            last_error = f"cover proxy upstream transport error: {exc}"
            continue

        if upstream.status_code >= 400:
            last_error = (
                f"cover proxy upstream status={upstream.status_code} "
                f"for referer={referer or '<none>'}"
            )
            continue

        content_type = str(upstream.headers.get("content-type", "")).lower()
        if not content_type.startswith("image/"):
            last_error = (
                "cover proxy upstream returned non-image payload "
                f"(referer={referer or '<none>'})"
            )
            continue

        return Response(
            content=upstream.content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=21600"},
        )

    raise HTTPException(status_code=502, detail=last_error)


@router.get("/sources", response_model=list[SourceInfo])
def list_sources() -> list[SourceInfo]:
    return [SourceInfo(code=a.code, name=a.name, supports_search=True) for a in list_adapters()]


@router.get("/timezones", response_model=list[str])
def list_timezones() -> list[str]:
    return sorted(available_timezones())


@router.get("/search", response_model=SearchResponse)
def search(
    source: str = Query(...),
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
) -> SearchResponse:
    if source == "kxo":
        # KXO is manual-only in current scope to avoid auth/session fragility.
        raise HTTPException(
            status_code=400,
            detail=(
                "kxo source supports manual subscription only; "
                "use /api/subscriptions/manual-kxo"
            ),
        )

    try:
        adapter = get_adapter(source)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    cfg = get_runtime_settings(db)
    if hasattr(adapter, "configure_runtime"):
        adapter.configure_runtime(cfg)  # type: ignore[attr-defined]

    try:
        data = adapter.search(q, page)
    except AdapterAuthRequiredError as exc:
        raise HTTPException(status_code=401, detail=f"auth_required: {exc}") from exc
    except AdapterSessionInvalidError as exc:
        raise HTTPException(status_code=401, detail=f"session_invalid: {exc}") from exc
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
    rows = list_subscriptions(db)
    backfill_subscription_covers(db, rows)
    return [_sub_to_response(row) for row in rows]


@router.post("/subscriptions", response_model=SubscriptionResponse)
def post_subscriptions(
    payload: SubscriptionCreate, db: Session = Depends(get_db)
) -> SubscriptionResponse:
    row = create_subscription(db, payload)
    return _sub_to_response(row)


@router.post("/subscriptions/manual-kxo", response_model=SubscriptionResponse)
def post_manual_kxo_subscription(
    payload: KxoManualSubscriptionCreate, db: Session = Depends(get_db)
) -> SubscriptionResponse:
    try:
        adapter = get_adapter("kxo")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not hasattr(adapter, "fetch_item_snapshot"):
        raise HTTPException(status_code=500, detail="kxo adapter is unavailable")

    cfg = get_runtime_settings(db)
    if hasattr(adapter, "configure_runtime"):
        adapter.configure_runtime(cfg)  # type: ignore[attr-defined]
    if hasattr(adapter, "parse_item_id"):
        item_id = adapter.parse_item_id(payload.ref)  # type: ignore[attr-defined]
    else:
        item_id = KxoAdapter.parse_item_id(payload.ref)
    if not item_id:
        raise HTTPException(
            status_code=400,
            detail="invalid kxo ref: expected URL /c/<id>.htm or numeric ID",
        )

    snapshot = {}
    try:
        snapshot = adapter.fetch_item_snapshot(item_id)
    except AdapterError as exc:
        # Manual add can still proceed with explicit title when upstream snapshot fetch fails.
        if not payload.item_title:
            raise HTTPException(status_code=502, detail=f"upstream source error: {exc}") from exc

    item_title = (payload.item_title or "").strip()
    if not item_title:
        item_title = str(snapshot.get("item_title", "")).strip()
    if not item_title:
        item_title = f"kxo:{item_id}"

    item_meta = {
        "group_word": "default",
        "cover": snapshot.get("cover", ""),
        "latest_update_time": snapshot.get("latest_update_time", ""),
        "latest_chapters": snapshot.get("latest_chapters", []),
    }
    row = create_subscription(
        db,
        SubscriptionCreate(
            source_code="kxo",
            item_id=item_id,
            item_title=item_title,
            group_word="default",
            item_meta=item_meta,
        ),
    )
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
def del_subscriptions(
    sub_id: int,
    purge_history: bool = Query(False),
    db: Session = Depends(get_db),
) -> JobRunResponse:
    ok, removed_events = delete_subscription(db, sub_id, purge_history=purge_history)
    if not ok:
        raise HTTPException(status_code=404, detail="subscription not found")
    return JobRunResponse(
        status="ok",
        detail=(
            "deleted, "
            f"removed_events={removed_events}, "
            f"purge_history={str(purge_history).lower()}"
        ),
    )


@router.post("/subscriptions/{sub_id}/debug/simulate-update")
def post_debug_simulate_update(sub_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.query(Subscription).filter(Subscription.id == sub_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="subscription not found")

    now = datetime.now(UTC)
    debug_suffix = uuid4().hex[:8]
    update_id = f"debug-{now.strftime('%Y%m%d%H%M%S')}-{debug_suffix}"
    normalized_item_title = repair_mojibake_text(row.item_title)
    evt = UpdateEvent(
        source_code=row.source_code,
        subscription_id=row.id,
        update_id=update_id,
        update_title=f"[DEBUG] simulated update for {normalized_item_title}",
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
    # Keep debug endpoint resilient even if historical metadata is malformed.
    try:
        row_meta = json.loads(row.item_meta_json) if row.item_meta_json else {}
    except Exception:  # noqa: BLE001
        row_meta = {}
    debug_update_id = f"debug-notify-{uuid4().hex[:8]}"
    debug_dedupe_key = f"debug-notify:{row.source_code}:{row.id}"
    source_item_url = build_source_item_url(row.source_code, row.item_id, cfg)
    normalized_item_title = repair_mojibake_text(row.item_title)
    event_payload = [
        build_notification_event(
            source_code=row.source_code,
            subscription_id=row.id,
            item_id=row.item_id,
            item_title=normalized_item_title,
            cover=str(row_meta.get("cover") or ""),
            source_item_url=source_item_url,
            update_id=debug_update_id,
            update_title=f"[DEBUG] notify test for {normalized_item_title}",
            update_url=cfg["app_base_url"],
            detected_at=now,
            dedupe_key=debug_dedupe_key,
            timezone_name=str(cfg.get("timezone", "UTC")),
        )
    ]
    webhook_payload = build_webhook_payload(
        event_type="manual_test",
        title="Manual Notification Test",
        events=event_payload,
        window_start=now,
        window_end=now,
        generated_at=now,
        timezone_name=str(cfg.get("timezone", "UTC")),
    )

    delivered_channels: list[str] = []
    skipped_channels: list[str] = []
    errors: dict[str, str] = {}

    if cfg.get("webhook_enabled") and cfg.get("webhook_url"):
        ok, payload_hash, error = WebhookNotifier().send(
            cfg["webhook_url"],
            webhook_payload,
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
def get_events(
    status: str = Query("all"),
    include_debug: bool = Query(False),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[EventResponse]:
    # Default event list is user-facing, so we hide debug and non-active/orphan noise.
    query = db.query(UpdateEvent).join(Subscription, Subscription.id == UpdateEvent.subscription_id)
    if not include_inactive:
        query = query.filter(Subscription.status == "active")
    if not include_debug:
        query = query.filter(UpdateEvent.dedupe_key.notlike("debug:%"))
    query = query.order_by(UpdateEvent.id.desc())
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
            update_title=repair_mojibake_text(r.update_title),
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
    rows = (
        db.query(UpdateEvent)
        .join(Subscription, Subscription.id == UpdateEvent.subscription_id)
        # RSS should only expose events from currently active subscriptions.
        .filter(Subscription.status == "active")
        .order_by(UpdateEvent.id.desc())
        .limit(200)
        .all()
    )
    events = build_enriched_events(db, rows, cfg)
    xml = render_rss(cfg["app_base_url"], events, timezone_name=cfg["timezone"])
    return Response(content=xml, media_type="application/rss+xml")


@router.post("/notifications/webhook/test")
def webhook_test(url: str | None = None, db: Session = Depends(get_db)) -> dict:
    cfg = get_runtime_settings(db)
    endpoint = url or cfg.get("webhook_url", "")
    if not endpoint:
        raise HTTPException(status_code=400, detail="webhook_url is empty")

    now = datetime.now(UTC)
    event_payload = [
        build_notification_event(
            source_code="system",
            subscription_id=0,
            item_id="webhook-test",
            item_title="Webhook Test",
            cover="",
            source_item_url=cfg["app_base_url"],
            update_id="test",
            update_title="Webhook Test Message",
            update_url=cfg["app_base_url"],
            detected_at=now,
            dedupe_key="system:webhook:test",
            timezone_name=str(cfg.get("timezone", "UTC")),
        )
    ]
    webhook_payload = build_webhook_payload(
        event_type="webhook_test",
        title="Webhook Test",
        events=event_payload,
        window_start=now,
        window_end=now,
        generated_at=now,
        timezone_name=str(cfg.get("timezone", "UTC")),
    )
    ok, payload_hash, error = WebhookNotifier().send(
        endpoint,
        webhook_payload,
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
    if "kxo_auth_mode" in updates and updates["kxo_auth_mode"] not in {"guest", "cookie"}:
        raise HTTPException(status_code=400, detail="invalid kxo_auth_mode")
    if "kxo_base_url" in updates and not str(updates["kxo_base_url"]).startswith("http"):
        raise HTTPException(status_code=400, detail="invalid kxo_base_url")

    cfg_before = get_runtime_settings(db)
    remember_session = bool(
        updates.get("kxo_remember_session", cfg_before.get("kxo_remember_session", False))
    )
    if not remember_session and "kxo_cookie" in updates:
        # Non-persistent cookie mode keeps credential only in process memory by default.
        cookie_value = str(updates.pop("kxo_cookie") or "").strip()
        upsert_ephemeral_settings({"kxo_cookie": cookie_value})
        updates["kxo_cookie"] = ""
    elif (
        remember_session
        and updates.get("kxo_remember_session") is True
        and "kxo_cookie" not in updates
    ):
        # If user switches to remember mode, persist the currently effective in-memory cookie.
        updates["kxo_cookie"] = str(cfg_before.get("kxo_cookie", "")).strip()
    elif not remember_session and updates.get("kxo_remember_session") is False:
        # Switching to non-persistent mode should immediately clear any stored cookie.
        upsert_ephemeral_settings({"kxo_cookie": str(cfg_before.get("kxo_cookie", "")).strip()})
        updates["kxo_cookie"] = ""

    cfg = upsert_settings(db, updates)
    cfg, timezone_changed = _maybe_auto_timezone(cfg, request, db)
    if timezone_changed or {"timezone", "check_cron", "daily_summary_cron"}.intersection(updates):
        # Keep scheduler in sync with persisted settings after any cron/timezone mutation.
        scheduler_manager.reload_jobs()

    return _build_settings_response(cfg)


@router.post("/settings/kxo/test")
def post_test_kxo_settings(db: Session = Depends(get_db)) -> dict:
    try:
        adapter = get_adapter("kxo")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cfg = get_runtime_settings(db)
    if hasattr(adapter, "configure_runtime"):
        adapter.configure_runtime(cfg)  # type: ignore[attr-defined]

    cookie_configured = bool(str(cfg.get("kxo_cookie", "")).strip())
    if cfg.get("kxo_auth_mode") == "cookie" and not cookie_configured:
        return {"status": "unconfigured", "detail": "kxo cookie is empty"}
    try:
        ok = adapter.healthcheck()
    except AdapterError as exc:
        return {"status": "invalid", "detail": str(exc)}
    return {
        "status": "ok" if ok else "invalid",
        "detail": "" if ok else "kxo healthcheck failed",
        "cookie_configured": cookie_configured,
    }
