from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import Subscription, UpdateEvent
from app.services import summary as summary_module
from app.services.settings import upsert_settings
from app.services.summary import run_daily_summary


def _create_subscription(
    db_session,
    *,
    source_code: str = "testsource",
    item_id: str = "demo-item",
    item_title: str = "Demo",
    status: str = "active",
) -> Subscription:
    sub = Subscription(
        source_code=source_code,
        item_id=item_id,
        item_title=item_title,
        item_meta_json="{}",
        status=status,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def test_daily_summary_marks_events(db_session):
    upsert_settings(
        db_session,
        {
            "webhook_enabled": False,
            "rss_enabled": True,
        },
    )

    sub = _create_subscription(db_session)
    now = datetime.now(UTC)
    db_session.add_all(
        [
            UpdateEvent(
                source_code="testsource",
                subscription_id=sub.id,
                update_id="u1",
                update_title="chapter1",
                update_url="http://example/1",
                detected_at=now,
                dedupe_key="a",
            ),
            UpdateEvent(
                source_code="testsource",
                subscription_id=sub.id,
                update_id="u2",
                update_title="chapter2",
                update_url="http://example/2",
                detected_at=now,
                dedupe_key="b",
            ),
        ]
    )
    db_session.commit()

    result = run_daily_summary(db_session)
    assert result["status"] == "sent"
    assert "rss" in result["delivered_channels"]

    remaining = db_session.query(UpdateEvent).filter(UpdateEvent.summarized_at.is_(None)).count()
    assert remaining == 0


def test_daily_summary_ignores_debug_events(db_session):
    upsert_settings(
        db_session,
        {
            "webhook_enabled": False,
            "rss_enabled": True,
        },
    )

    sub = _create_subscription(db_session)
    now = datetime.now(UTC)
    db_session.add(
        UpdateEvent(
            source_code="testsource",
            subscription_id=sub.id,
            update_id="debug-u1",
            update_title="[DEBUG] simulated update",
            update_url="",
            detected_at=now,
            dedupe_key="debug:testsource:1:debug-u1",
        )
    )
    db_session.commit()

    result = run_daily_summary(db_session)
    assert result["status"] == "no_updates"
    assert result["candidates"] == 0

    remaining = db_session.query(UpdateEvent).filter(UpdateEvent.summarized_at.is_(None)).count()
    assert remaining == 1


def test_daily_summary_includes_previous_day_unsummarized_events(db_session):
    upsert_settings(
        db_session,
        {
            "timezone": "Asia/Shanghai",
            "webhook_enabled": False,
            "rss_enabled": True,
        },
    )

    sub = _create_subscription(db_session)
    now = datetime.now(UTC)
    db_session.add(
        UpdateEvent(
            source_code="testsource",
            subscription_id=sub.id,
            update_id="old-u1",
            update_title="old chapter",
            update_url="http://example/old",
            detected_at=now - timedelta(days=1, minutes=5),
            dedupe_key=f"testsource:{sub.id}:old-u1",
        )
    )
    db_session.commit()

    result = run_daily_summary(db_session)
    assert result["status"] == "sent"
    assert result["candidates"] == 1
    assert "rss" in result["delivered_channels"]


def test_daily_summary_webhook_uses_v2_payload(monkeypatch, db_session):
    upsert_settings(
        db_session,
        {
            "timezone": "Europe/London",
            "webhook_enabled": True,
            "webhook_url": "http://example/webhook",
            "rss_enabled": False,
        },
    )

    sub = Subscription(
        source_code="copymanga",
        item_id="jojo-8",
        item_title="JOJO Part 8",
        item_meta_json='{"cover":"https://img.test/jojo.jpg"}',
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)

    now = datetime.now(UTC)
    db_session.add(
        UpdateEvent(
            source_code="copymanga",
            subscription_id=sub.id,
            update_id="c110",
            update_title="chapter 110",
            update_url="https://example/chapter/110",
            detected_at=now,
            dedupe_key=f"copymanga:{sub.id}:c110",
        )
    )
    db_session.commit()

    captured: dict = {}

    def _fake_send(self, url: str, payload: dict):  # noqa: ANN001
        captured["url"] = url
        captured["payload"] = payload
        return True, "hash", ""

    monkeypatch.setattr(summary_module.WebhookNotifier, "send", _fake_send)
    result = run_daily_summary(db_session)

    assert result["status"] == "sent"
    assert "webhook" in result["delivered_channels"]
    assert captured["url"] == "http://example/webhook"
    payload = captured["payload"]
    assert payload["schema_version"] == "2.0"
    assert payload["event_type"] == "daily_summary"
    assert payload["count"] == 1
    assert payload["summary"]["total_updates"] == 1
    event = payload["events"][0]
    assert event["subscription"]["item_title"] == "JOJO Part 8"
    assert event["subscription"]["cover"] == "https://img.test/jojo.jpg"
    assert event["update"]["update_title"] == "chapter 110"
    assert event["update"]["dedupe_key"].startswith("copymanga:")


def test_daily_summary_excludes_non_active_subscriptions(db_session):
    upsert_settings(
        db_session,
        {
            "webhook_enabled": False,
            "rss_enabled": True,
        },
    )

    active_sub = _create_subscription(db_session, item_id="active-item", status="active")
    paused_sub = _create_subscription(db_session, item_id="paused-item", status="paused")

    now = datetime.now(UTC)
    db_session.add_all(
        [
            UpdateEvent(
                source_code="testsource",
                subscription_id=active_sub.id,
                update_id="active-u1",
                update_title="active chapter",
                update_url="http://example/active",
                detected_at=now,
                dedupe_key=f"testsource:{active_sub.id}:active-u1",
            ),
            UpdateEvent(
                source_code="testsource",
                subscription_id=paused_sub.id,
                update_id="paused-u1",
                update_title="paused chapter",
                update_url="http://example/paused",
                detected_at=now,
                dedupe_key=f"testsource:{paused_sub.id}:paused-u1",
            ),
        ]
    )
    db_session.commit()

    result = run_daily_summary(db_session)
    assert result["status"] == "sent"
    assert result["candidates"] == 1

    active_event = (
        db_session.query(UpdateEvent).filter(UpdateEvent.subscription_id == active_sub.id).one()
    )
    paused_event = (
        db_session.query(UpdateEvent).filter(UpdateEvent.subscription_id == paused_sub.id).one()
    )
    assert active_event.summarized_at is not None
    assert paused_event.summarized_at is None
