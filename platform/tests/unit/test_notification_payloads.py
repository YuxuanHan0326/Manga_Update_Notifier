from __future__ import annotations

from datetime import UTC, datetime

from app.services.notification_payloads import (
    build_notification_event,
    build_source_item_url,
)


def test_build_source_item_url_uses_official_copymanga_domain():
    out = build_source_item_url("copymanga", "haizeiwang", {})
    assert out == "https://www.mangacopy.com/comic/haizeiwang"


def test_build_notification_event_normalizes_legacy_copymanga_update_url():
    event = build_notification_event(
        source_code="copymanga",
        subscription_id=1,
        item_id="haizeiwang",
        item_title="海贼王",
        cover="",
        source_item_url="https://www.copymanga.site/comic/haizeiwang",
        update_id="u1",
        update_title="第1话",
        update_url="https://www.copymanga.site/comic/haizeiwang?from=rss",
        detected_at=datetime.now(UTC),
        dedupe_key="copymanga:1:u1",
        timezone_name="UTC",
    )
    assert (
        event["subscription"]["source_item_url"]
        == "https://www.mangacopy.com/comic/haizeiwang"
    )
    assert (
        event["update"]["update_url"]
        == "https://www.mangacopy.com/comic/haizeiwang?from=rss"
    )


def test_build_notification_event_keeps_non_legacy_url_unchanged():
    event = build_notification_event(
        source_code="copymanga",
        subscription_id=1,
        item_id="haizeiwang",
        item_title="海贼王",
        cover="",
        source_item_url="https://www.mangacopy.com/comic/haizeiwang",
        update_id="u1",
        update_title="第1话",
        update_url="https://www.mangacopy.com/comic/haizeiwang/chapter/1",
        detected_at=datetime.now(UTC),
        dedupe_key="copymanga:1:u1",
        timezone_name="UTC",
    )
    assert (
        event["update"]["update_url"]
        == "https://www.mangacopy.com/comic/haizeiwang/chapter/1"
    )
