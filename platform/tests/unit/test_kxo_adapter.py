from __future__ import annotations

from app.adapters.base import AdapterAuthRequiredError
from app.adapters.kxo import KxoAdapter


def test_parse_item_id_supports_numeric_and_url():
    assert KxoAdapter.parse_item_id("20001") == "20001"
    assert KxoAdapter.parse_item_id("https://kzo.moe/c/20001.htm") == "20001"
    assert KxoAdapter.parse_item_id("/c/25000.htm") == "25000"
    assert KxoAdapter.parse_item_id("invalid-ref") is None


def test_parse_book_data_extracts_stable_updates():
    text = (
        '<script>parent.postMessage( "volinfo=1001,0,1,單行本,1,第1卷,160,160,0.0,35.0,33.8,33.8,,'
        '2023-05-20,2025-12-21 10:20:30,2025-12-21,2025-12-21", "*" );</script>'
        '<script>parent.postMessage( "volinfo=1002,0,1,單行本,2,第2卷,160,160,0.0,35.0,33.8,33.8,,'
        '2023-05-21,2026-01-02 11:30:40,2026-01-02,2026-01-02", "*" );</script>'
    )
    updates, latest_time = KxoAdapter._parse_book_data(  # noqa: SLF001
        text,
        item_id="20001",
        detail_url="https://kzo.moe/c/20001.htm",
    )
    assert [item.update_id for item in updates] == [
        "20001:1001:單行本",
        "20001:1002:單行本",
    ]
    assert updates[-1].title == "第2卷"
    assert latest_time == "2026-01-02 11:30:40"


def test_parse_search_items_extracts_basic_cards():
    html = (
        "disp_divinfo('div_info_1','https://kzo.moe/c/20001.htm','https://img/cover.jpg','#fff',"
        "'','','','','8.9','示例漫画','作者A','连载中','2026-03-10');"
    )
    items = KxoAdapter._parse_search_items(html)  # noqa: SLF001
    assert len(items) == 1
    first = items[0]
    assert first.item_id == "20001"
    assert first.title == "示例漫画"
    assert first.author == "作者A"
    assert first.meta["latest_update_time"] == "2026-03-10"


def test_search_requires_cookie_by_default():
    adapter = KxoAdapter()
    adapter.configure_runtime({"kxo_cookie": ""})
    try:
        adapter.search("jojo", 1)
    except AdapterAuthRequiredError:
        return
    raise AssertionError("search should fail with auth_required when cookie is missing")


def test_extract_cover_supports_meta_and_json_fallbacks():
    html = """
    <html>
      <head>
        <meta content="https://img.kxo.test/cover-main.jpg" property="og:image" />
      </head>
    </html>
    """
    assert KxoAdapter._extract_cover(html) == "https://img.kxo.test/cover-main.jpg"  # noqa: SLF001

    json_html = (
        '<script>window.__DATA__={"cover":"https:\\/\\/img.kxo.test\\/cover-json.jpg"}'
        "</script>"
    )
    assert KxoAdapter._extract_cover(json_html) == "https://img.kxo.test/cover-json.jpg"  # noqa: SLF001
