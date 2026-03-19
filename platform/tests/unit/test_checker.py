from __future__ import annotations

import json

from app.adapters.base import AdapterSearchResult, AdapterUpdate, SearchPage
from app.adapters.registry import register_adapter
from app.models import Subscription, UpdateEvent
from app.services.checker import run_update_check


class FakeAdapter:
    code = "testsource"
    name = "Test Source"

    def search(self, query: str, page: int):
        return SearchPage(
            page=page,
            total=1,
            items=[AdapterSearchResult(item_id="id1", title="title")],
        )

    def list_updates(self, item_id: str, item_meta: dict | None = None):
        return [
            AdapterUpdate(update_id="u1", title="c1", url="http://example/1"),
            AdapterUpdate(update_id="u2", title="c2", url="http://example/2"),
            AdapterUpdate(update_id="u3", title="c3", url="http://example/3"),
        ]

    def healthcheck(self) -> bool:
        return True


def test_update_check_deduplicates(db_session):
    register_adapter(FakeAdapter())
    sub = Subscription(
        source_code="testsource",
        item_id="id1",
        item_title="Demo",
        item_meta_json=json.dumps({"group_word": "default"}),
        status="active",
        last_seen_update_id="u1",
    )
    db_session.add(sub)
    db_session.commit()

    first = run_update_check(db_session)
    assert first["scanned"] == 1
    assert first["discovered"] == 2

    second = run_update_check(db_session)
    assert second["discovered"] == 0

    count = db_session.query(UpdateEvent).count()
    assert count == 2

    db_session.refresh(sub)
    meta = json.loads(sub.item_meta_json)
    assert sub.last_seen_update_id == "u3"
    assert meta["last_seen_update_title"] == "c3"
    assert isinstance(meta["last_seen_update_at"], str)


def test_update_check_detects_change_after_baseline_seed(db_session):
    class BaselineThenUpdateAdapter:
        code = "baseline_source"
        name = "Baseline Source"

        def __init__(self) -> None:
            self.calls = 0

        def search(self, query: str, page: int):
            return SearchPage(
                page=page,
                total=1,
                items=[AdapterSearchResult(item_id="id2", title="title2")],
            )

        def list_updates(self, item_id: str, item_meta: dict | None = None):
            _ = (item_id, item_meta)
            self.calls += 1
            if self.calls == 1:
                return [AdapterUpdate(update_id="f-108", title="第108话", url="http://example/108")]
            return [AdapterUpdate(update_id="f-109", title="第109话", url="http://example/109")]

        def healthcheck(self) -> bool:
            return True

    register_adapter(BaselineThenUpdateAdapter())
    sub = Subscription(
        source_code="baseline_source",
        item_id="id2",
        item_title="Demo2",
        item_meta_json=json.dumps({"group_word": "default"}),
        status="active",
        last_seen_update_id=None,
    )
    db_session.add(sub)
    db_session.commit()

    first = run_update_check(db_session)
    assert first["scanned"] == 1
    assert first["discovered"] == 0

    second = run_update_check(db_session)
    assert second["discovered"] == 1

    db_session.refresh(sub)
    assert sub.last_seen_update_id == "f-109"


def test_update_check_emits_catchup_event_when_id_missing_but_title_advanced(db_session):
    class FallbackAdapter:
        code = "fallback_source"
        name = "Fallback Source"

        def search(self, query: str, page: int):
            return SearchPage(
                page=page,
                total=1,
                items=[AdapterSearchResult(item_id="id3", title="title3")],
            )

        def list_updates(self, item_id: str, item_meta: dict | None = None):
            _ = (item_id, item_meta)
            return [AdapterUpdate(update_id="fallback-109", title="第109话", url="http://example/109")]

        def healthcheck(self) -> bool:
            return True

    register_adapter(FallbackAdapter())
    sub = Subscription(
        source_code="fallback_source",
        item_id="id3",
        item_title="Demo3",
        item_meta_json=json.dumps(
            {
                "group_word": "default",
                "last_seen_update_title": "第108话",
                "last_seen_update_at": "2026-03-05",
            }
        ),
        status="active",
        last_seen_update_id=None,
    )
    db_session.add(sub)
    db_session.commit()

    out = run_update_check(db_session)
    assert out["scanned"] == 1
    assert out["discovered"] == 1

    db_session.refresh(sub)
    assert sub.last_seen_update_id == "fallback-109"
    events = db_session.query(UpdateEvent).filter(UpdateEvent.subscription_id == sub.id).all()
    assert len(events) == 1
    assert events[0].update_title == "第109话"
