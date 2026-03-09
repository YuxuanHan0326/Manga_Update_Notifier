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
