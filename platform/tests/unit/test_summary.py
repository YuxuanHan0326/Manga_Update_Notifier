from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import UpdateEvent
from app.services.settings import upsert_settings
from app.services.summary import run_daily_summary


def test_daily_summary_marks_events(db_session):
    upsert_settings(
        db_session,
        {
            "webhook_enabled": False,
            "rss_enabled": True,
        },
    )

    now = datetime.now(UTC)
    db_session.add_all(
        [
            UpdateEvent(
                source_code="testsource",
                subscription_id=1,
                update_id="u1",
                update_title="chapter1",
                update_url="http://example/1",
                detected_at=now,
                dedupe_key="a",
            ),
            UpdateEvent(
                source_code="testsource",
                subscription_id=1,
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

    now = datetime.now(UTC)
    db_session.add(
        UpdateEvent(
            source_code="testsource",
            subscription_id=1,
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

    now = datetime.now(UTC)
    db_session.add(
        UpdateEvent(
            source_code="testsource",
            subscription_id=1,
            update_id="old-u1",
            update_title="old chapter",
            update_url="http://example/old",
            detected_at=now - timedelta(days=1, minutes=5),
            dedupe_key="testsource:1:old-u1",
        )
    )
    db_session.commit()

    result = run_daily_summary(db_session)
    assert result["status"] == "sent"
    assert result["candidates"] == 1
    assert "rss" in result["delivered_channels"]
