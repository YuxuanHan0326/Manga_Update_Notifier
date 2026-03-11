from __future__ import annotations

from app import api as api_module
from app.adapters.base import AdapterSearchResult, AdapterUpdate, AdapterUpstreamError, SearchPage
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


class FakeKxoAdapter:
    code = "kxo"
    name = "KXO"

    @staticmethod
    def parse_item_id(raw_ref: str) -> str | None:
        return "20001" if "20001" in raw_ref else None

    def configure_runtime(self, cfg: dict) -> None:
        _ = cfg

    def fetch_item_snapshot(self, item_id: str) -> dict:
        return {
            "item_title": "KXO Demo",
            "cover": "https://img/cover.jpg",
            "latest_update_time": "2026-03-10",
            "latest_chapters": ["第2卷"],
        }

    def search(self, query: str, page: int):
        # Search should never be called for KXO in manual-only mode.
        _ = (query, page)
        raise AdapterUpstreamError("kxo search should be disabled")

    def list_updates(self, item_id: str, item_meta: dict | None = None):
        _ = item_meta
        return [
            AdapterUpdate(update_id="kxo:1", title="第1卷", url="https://kzo.moe/c/20001.htm"),
            AdapterUpdate(update_id="kxo:2", title="第2卷", url="https://kzo.moe/c/20001.htm"),
        ]

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


def test_kxo_manual_subscription_endpoint_supports_url_ref():
    register_adapter(FakeKxoAdapter())
    client = TestClient(app)

    created = client.post(
        "/api/subscriptions/manual-kxo",
        json={"ref": "https://kzo.moe/c/20001.htm"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["source_code"] == "kxo"
    assert body["item_id"] == "20001"
    assert body["item_title"] == "KXO Demo"
    assert body["item_meta"]["cover"] == "https://img/cover.jpg"
    assert body["last_seen_update_title"] == "第2卷"
    assert body["last_seen_update_at"] == "2026-03-10"


def test_kxo_search_endpoint_is_manual_only():
    register_adapter(FakeKxoAdapter())
    client = TestClient(app)

    out = client.get("/api/search", params={"source": "kxo", "q": "jojo", "page": 1})
    assert out.status_code == 400
    assert "manual subscription only" in out.json()["detail"]


def test_subscription_create_prefills_last_seen_from_search_meta_and_cover():
    client = TestClient(app)
    payload = {
        "source_code": "copymanga",
        "item_id": "demo-item",
        "item_title": "Demo",
        "group_word": "default",
        "item_meta": {
            "group_word": "default",
            "cover": "https://img/demo.jpg",
            "latest_update_time": "2026-03-01",
            "latest_chapters": ["第12话"],
        },
    }
    out = client.post("/api/subscriptions", json=payload)
    assert out.status_code == 200
    body = out.json()
    assert body["item_meta"]["cover"] == "https://img/demo.jpg"
    assert body["last_seen_update_title"] == "第12话"
    assert body["last_seen_update_at"] == "2026-03-01"


def test_get_subscriptions_backfills_missing_cover_from_adapter_snapshot():
    register_adapter(FakeKxoAdapter())
    client = TestClient(app)

    created = client.post(
        "/api/subscriptions",
        json={
            "source_code": "kxo",
            "item_id": "20001",
            "item_title": "KXO No Cover",
            "group_word": "default",
            "item_meta": {"group_word": "default"},
        },
    )
    assert created.status_code == 200
    assert created.json()["item_meta"].get("cover", "") == ""

    listed = client.get("/api/subscriptions")
    assert listed.status_code == 200
    top = listed.json()[0]
    assert top["source_code"] == "kxo"
    assert top["item_meta"]["cover"] == "https://img/cover.jpg"


def test_cover_proxy_allows_known_host_and_returns_image(monkeypatch):
    class _FakeImageResponse:
        status_code = 200
        headers = {"content-type": "image/jpeg"}
        content = b"demo-bytes"

        def raise_for_status(self) -> None:
            return None

    def _fake_get(url: str, headers: dict, timeout: int, follow_redirects: bool):
        assert url.startswith("https://sj.mangafunb.fun/")
        assert timeout == 15
        assert follow_redirects is True
        return _FakeImageResponse()

    monkeypatch.setattr(api_module.httpx, "get", _fake_get)
    client = TestClient(app)

    out = client.get(
        "/api/cover-proxy",
        params={"url": "https://sj.mangafunb.fun/j/demo/cover/a.jpg"},
    )
    assert out.status_code == 200
    assert out.headers["content-type"].startswith("image/")
    assert out.content == b"demo-bytes"


def test_cover_proxy_mxomo_uses_referer_fallback(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code
            self.headers = {"content-type": "image/png" if status_code == 200 else "text/plain"}
            self.content = b"img" if status_code == 200 else b"blocked"

    calls: list[str | None] = []

    def _fake_get(url: str, headers: dict, timeout: int, follow_redirects: bool):
        _ = (url, timeout, follow_redirects)
        referer = headers.get("Referer")
        calls.append(referer)
        if referer is None:
            return _Resp(200)
        return _Resp(403)

    monkeypatch.setattr(api_module.httpx, "get", _fake_get)
    client = TestClient(app)

    out = client.get(
        "/api/cover-proxy",
        params={
            "url": (
                "https://kmimg.mxomo.com/cover/sigl/demo.jpg"
                "!cover_l?sign=test"
            )
        },
    )
    assert out.status_code == 200
    assert out.content == b"img"
    assert calls[0] is None


def test_cover_proxy_rejects_unknown_host():
    client = TestClient(app)
    out = client.get(
        "/api/cover-proxy",
        params={"url": "https://example.org/cover.jpg"},
    )
    assert out.status_code == 400
    assert "not allowed" in out.json()["detail"]
