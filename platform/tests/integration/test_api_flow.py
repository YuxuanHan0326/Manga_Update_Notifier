from __future__ import annotations

from app import api as api_module
from app.adapters.base import (
    AdapterSearchResult,
    AdapterUpdate,
    AdapterUpstreamError,
    SearchPage,
)
from app.adapters.registry import register_adapter
from app.main import app
from fastapi.testclient import TestClient


class FakeAdapter:
    code = "testsource"
    name = "Test Source"

    def search(self, query: str, page: int):
        return SearchPage(
            page=page,
            total=1,
            items=[
                AdapterSearchResult(
                    item_id="comic-1",
                    title=f"{query}-result",
                    group_word="default",
                )
            ],
        )

    def list_updates(self, item_id: str, item_meta: dict | None = None):
        return [
            AdapterUpdate(update_id="base", title="base", url="http://example/base"),
            AdapterUpdate(update_id="new-1", title="new-1", url="http://example/new1"),
        ]

    def healthcheck(self) -> bool:
        return True


class BrokenSearchAdapter:
    code = "brokensource"
    name = "Broken Source"

    def search(self, query: str, page: int):
        raise AdapterUpstreamError("non-json upstream payload")

    def list_updates(self, item_id: str, item_meta: dict | None = None):
        return []

    def healthcheck(self) -> bool:
        return True


def test_api_search_subscribe_and_check_flow():
    register_adapter(FakeAdapter())
    client = TestClient(app)

    s = client.get("/api/search", params={"source": "testsource", "q": "hello", "page": 1})
    assert s.status_code == 200
    assert s.json()["items"][0]["item_id"] == "comic-1"

    payload = {
        "source_code": "testsource",
        "item_id": "comic-1",
        "item_title": "hello-result",
        "group_word": "default",
        "item_meta": {"group_word": "default"},
    }
    c = client.post("/api/subscriptions", json=payload)
    assert c.status_code == 200

    run1 = client.post("/api/jobs/run-check")
    assert run1.status_code == 200
    assert run1.json()["discovered"] == 0

    run2 = client.post("/api/jobs/run-check")
    assert run2.status_code == 200
    assert run2.json()["discovered"] >= 0

    subs = client.get("/api/subscriptions")
    assert subs.status_code == 200
    first_sub = subs.json()[0]
    assert first_sub["last_seen_update_id"] == "new-1"
    assert first_sub["last_seen_update_title"] == "new-1"
    assert isinstance(first_sub["last_seen_update_at"], str)

    events = client.get("/api/events", params={"status": "all"})
    assert events.status_code == 200
    assert isinstance(events.json(), list)


def test_api_search_returns_502_on_adapter_upstream_error():
    register_adapter(BrokenSearchAdapter())
    client = TestClient(app)

    out = client.get("/api/search", params={"source": "brokensource", "q": "hello", "page": 1})
    assert out.status_code == 502
    assert "upstream source error" in out.json()["detail"]


def test_debug_simulated_update_is_excluded_from_daily_summary():
    register_adapter(FakeAdapter())
    client = TestClient(app)

    payload = {
        "source_code": "testsource",
        "item_id": "comic-1",
        "item_title": "hello-result",
        "group_word": "default",
        "item_meta": {"group_word": "default"},
    }
    create = client.post("/api/subscriptions", json=payload)
    assert create.status_code == 200
    sub_id = create.json()["id"]

    simulate = client.post(f"/api/subscriptions/{sub_id}/debug/simulate-update")
    assert simulate.status_code == 200
    assert simulate.json()["status"] == "ok"

    summary = client.post("/api/jobs/run-daily-summary")
    assert summary.status_code == 200
    assert summary.json()["status"] == "no_updates"
    assert summary.json()["candidates"] == 0


def test_debug_notify_test_reports_channel_status():
    register_adapter(FakeAdapter())
    client = TestClient(app)

    payload = {
        "source_code": "testsource",
        "item_id": "comic-1",
        "item_title": "hello-result",
        "group_word": "default",
        "item_meta": {"group_word": "default"},
    }
    create = client.post("/api/subscriptions", json=payload)
    assert create.status_code == 200
    sub_id = create.json()["id"]

    # Keep webhook disabled to avoid external network dependency in test.
    saved = client.put(
        "/api/settings",
        json={
            "webhook_enabled": False,
            "rss_enabled": True,
        },
    )
    assert saved.status_code == 200

    out = client.post(f"/api/subscriptions/{sub_id}/debug/notify-test")
    assert out.status_code == 200
    body = out.json()
    assert body["status"] == "ok"
    assert "rss" in body["delivered_channels"]
    assert "webhook" in body["skipped_channels"]


def test_settings_auto_timezone_uses_ip_lookup(monkeypatch):
    monkeypatch.setattr(api_module, "detect_timezone_from_ip", lambda _: "Europe/London")

    client = TestClient(app)
    out = client.get("/api/settings", headers={"x-forwarded-for": "8.8.8.8"})
    assert out.status_code == 200
    body = out.json()
    assert body["timezone_auto"] is True
    assert body["timezone"] == "Europe/London"


def test_timezones_endpoint_returns_timezone_list():
    client = TestClient(app)
    out = client.get("/api/timezones")
    assert out.status_code == 200
    body = out.json()
    assert isinstance(body, list)
    assert "UTC" in body


def test_subscription_create_prefills_last_seen_from_search_meta():
    client = TestClient(app)
    payload = {
        "source_code": "copymanga",
        "item_id": "demo-item",
        "item_title": "Demo",
        "group_word": "default",
        "item_meta": {
            "group_word": "default",
            "latest_update_time": "2026-03-01",
            "latest_chapters": ["第12话"],
        },
    }
    out = client.post("/api/subscriptions", json=payload)
    assert out.status_code == 200
    body = out.json()
    assert body["last_seen_update_title"] == "第12话"
    assert body["last_seen_update_at"] == "2026-03-01"
