from __future__ import annotations

import httpx
from app.adapters.copymanga import CopyMangaAdapter


class _MockResponse:
    status_code = 200
    headers = {"content-type": "application/json"}
    text = '{"code":200}'

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "code": 200,
            "results": {
                "total": 1,
                "list": [
                    {
                        "path_word": "comic-1",
                        "name": "demo",
                        "cover": "",
                        "author": [{"name": "author"}],
                        "alias": None,
                    }
                ],
            },
        }


class _MockWebResponse:
    status_code = 200
    headers = {"content-type": "text/html"}

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _MockChaptersResponse:
    headers = {"content-type": "application/json"}

    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = "{}"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_search_uses_required_headers_for_copymanga_api():
    adapter = CopyMangaAdapter()
    adapter._enrich_search_items = lambda items: None  # type: ignore[method-assign]

    def _fake_get(url: str, params: dict, headers: dict):
        assert url.endswith("/api/v3/search/comic")
        assert headers["User-Agent"] == "COPY/3.0.0"
        assert headers["Accept"] == "application/json"
        assert headers["platform"] == "1"
        assert headers["version"] == "2025.08.15"
        assert headers["webp"] == "1"
        assert headers["region"] == "1"
        return _MockResponse()

    adapter.client.get = _fake_get  # type: ignore[method-assign]

    out = adapter.search("demo", 1)

    assert out.total == 1
    assert len(out.items) == 1
    assert out.items[0].item_id == "comic-1"


def test_extract_web_meta_parses_update_time_and_latest_chapters():
    html = """
    <li>
      <span class="comicParticulars-sigezi">\u6700\u5f8c\u66f4\u65b0\uff1a</span>
      <span class="comicParticulars-right-txt">2026-02-09</span>
    </li>
    <div>\u7b2c83\u8bdd</div>
    <div>\u7b2c01\u8a71</div>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)

    assert meta["latest_update_time"] == "2026-02-09"
    assert meta["latest_chapters"] == ["\u7b2c83\u8bdd", "\u7b2c01\u8a71"]


def test_extract_web_meta_parses_cover_from_meta_and_json():
    html = """
    <html>
      <head>
        <meta content="https://img.copy.test/cover-a.jpg" property="og:image" />
      </head>
    </html>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)
    assert meta["cover"] == "https://img.copy.test/cover-a.jpg"

    json_html = (
        r'<script>window.__NUXT__={"comic":{"cover":"https:\/\/img.copy.test\/cover-b.jpg"}};'
        r"</script>"
    )
    meta2 = CopyMangaAdapter._extract_web_meta(json_html)
    assert meta2["cover"] == "https://img.copy.test/cover-b.jpg"


def test_extract_web_meta_parses_cover_from_lazyload_data_src():
    html = """
    <div class="comicParticulars-left-img loadingIcon">
      <img class="lazyload" data-src="https://sy.mangafunb.fun/y/demo/cover/123.jpg.328x422.jpg">
    </div>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)
    assert meta["cover"] == "https://sy.mangafunb.fun/y/demo/cover/123.jpg.328x422.jpg"


def test_normalize_cover_url_supports_relative_path():
    out = CopyMangaAdapter._normalize_cover_url("/y/demo/cover/123.jpg")  # noqa: SLF001
    assert out == "https://www.mangacopy.com/y/demo/cover/123.jpg"


def test_extract_web_meta_parses_json_embedded_update_and_non_standard_chapter_name():
    html = """
    <script>
      window.__NUXT__ = {
        "comic": {
          "datetime_updated": "2026-03-09 10:20:30",
          "last_chapter": {"name": "\u5355\u884c\u672c Vol.07 \u7279\u88c5\u7248"}
        }
      };
    </script>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)

    assert meta["latest_update_time"] == "2026-03-09 10:20:30"
    assert meta["latest_chapters"] == ["\u5355\u884c\u672c Vol.07 \u7279\u88c5\u7248"]


def test_extract_web_meta_decodes_escaped_json_chapter_name():
    html = r"""
    <script>
      window.__NUXT__ = {
        "comic": {
          "datetime_updated": "2026-03-09",
          "last_chapter": {"name": "\\u5355\\u884c\\u672c\\u0020Vol.08"}
        }
      };
    </script>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)

    assert meta["latest_update_time"] == "2026-03-09"
    assert meta["latest_chapters"] == ["\u5355\u884c\u672c Vol.08"]


def test_extract_web_meta_parses_non_standard_latest_name_from_title():
    html = """
    <html>
      <head>
        <title>
          JoJo\u7684\u5947\u5999\u5192\u96aa-JoJo\u7684\u5947\u5999\u5192\u96aa\u6f2b\u756b-\u6076\u7075\u7684\u5931\u604b2-\u9023\u8f09\u4e2d-\u5728\u7ebf\u9605\u8bfb
        </title>
      </head>
      <body></body>
    </html>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)

    assert meta["latest_chapters"] == ["\u6076\u7075\u7684\u5931\u604b2"]


def test_extract_web_meta_parses_latest_volume_name_from_title():
    html = """
    <html>
      <head>
        <title>
          JoJo\u7684\u5947\u5999\u5192\u96aa\u5168\u5f69\u7248-JoJo\u7684\u5947\u5999\u5192\u96aa\u5168\u5f69\u7248\u6f2b\u756b-\u7b2c7\u90e824\u5377-\u9023\u8f09\u4e2d-\u5728\u7ebf\u9605\u8bfb
        </title>
      </head>
      <body></body>
    </html>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)

    assert meta["latest_chapters"] == ["\u7b2c7\u90e824\u5377"]


def test_extract_web_meta_dedupes_long_title_variants_and_filters_fallback_noise():
    html = """
    <html>
      <head>
        <title>
          JoJo\u7684\u5947\u5999\u5192\u96aa\u7b2c8\u90e8\u4e54\u4e54\u798f\u97f3-JOJO\u7684\u5947\u5999\u5192\u96aa\u7b2c8\u90e8\u4e54\u4e54\u798f\u97f3\u6f2b\u756b-\u7b2c110\u8a71-\u9023\u8f09\u4e2d
        </title>
      </head>
      <body>
        <script>
          {"last_chapter":{"name":"\u7b2c8\u90e8\u4e54\u4e54\u798f\u97f3-JOJO\u7684\u5947\u5999\u5192\u96aa\u7b2c8\u90e8\u4e54\u4e54\u798f\u97f3\u6f2b\u756b-\u7b2c110\u8a71"}}
        </script>
        <div>\u7b2c\u4e03\u90e8\u4f5c\u54c1\u6700\u7d42\u56de</div>
      </body>
    </html>
    """
    meta = CopyMangaAdapter._extract_web_meta(html)

    assert meta["latest_chapters"] == ["\u7b2c110\u8a71"]


def test_search_enriches_meta_with_web_fields():
    adapter = CopyMangaAdapter()

    def _fake_get(url: str, params: dict, headers: dict):
        assert url.endswith("/api/v3/search/comic")
        return _MockResponse()

    adapter.client.get = _fake_get  # type: ignore[method-assign]
    adapter._fetch_web_meta = lambda item_id: {  # type: ignore[method-assign]
        "latest_update_time": "2026-02-09",
        "latest_chapters": ["\u7b2c83\u8bdd"],
    }

    out = adapter.search("demo", 1)

    assert out.items[0].meta["alias"] is None
    assert out.items[0].meta["latest_update_time"] == "2026-02-09"
    assert out.items[0].meta["latest_chapters"] == ["\u7b2c83\u8bdd"]


def test_fetch_web_meta_uses_short_ttl_cache_by_item_id():
    adapter = CopyMangaAdapter()
    calls = 0

    def _fake_get(url: str, headers: dict, timeout: int):
        nonlocal calls
        calls += 1
        assert url.endswith("/comic/comic-1")
        assert timeout == 8
        return _MockWebResponse("<div>\u7b2c12\u8bdd</div>")

    adapter.client.get = _fake_get  # type: ignore[method-assign]

    first = adapter._fetch_web_meta("comic-1")
    second = adapter._fetch_web_meta("comic-1")

    assert calls == 1
    assert first["meta_fetch_status"] == "ok"
    assert second["meta_fetch_status"] == "ok"
    assert second["latest_chapters"] == ["\u7b2c12\u8bdd"]


def test_fetch_web_meta_marks_fetch_failed_when_request_errors():
    adapter = CopyMangaAdapter()

    def _fake_get(url: str, headers: dict, timeout: int):
        raise httpx.HTTPError("boom")

    adapter.client.get = _fake_get  # type: ignore[method-assign]

    meta = adapter._fetch_web_meta("comic-2")

    assert meta["meta_fetch_status"] == "fetch_failed"


def test_list_updates_uses_numeric_sort_for_string_index():
    adapter = CopyMangaAdapter()

    def _fake_get(url: str, params: dict, headers: dict):
        assert "comic-sort/group/default/chapters" in url
        assert headers["User-Agent"] == "COPY/3.0.0"
        assert headers["Accept"] == "application/json"
        assert headers["platform"] == "1"
        assert headers["version"] == "2025.08.15"
        assert headers["webp"] == "1"
        assert headers["region"] == "1"
        assert params["platform"] == 1
        return _MockChaptersResponse(
            {
                "code": 200,
                "results": {
                    "list": [
                        {"uuid": "c9", "name": "第9话", "index": "9"},
                        {"uuid": "c10", "name": "第10话", "index": "10"},
                        {"uuid": "c2", "name": "第2话", "index": "2"},
                    ]
                },
            }
        )

    adapter.client.get = _fake_get  # type: ignore[method-assign]
    updates = adapter.list_updates("comic-sort", {"group_word": "default"})

    assert [u.update_id for u in updates] == ["c2", "c9", "c10"]


def test_list_updates_falls_back_to_web_meta_when_api_blocked():
    adapter = CopyMangaAdapter()

    def _fake_get(url: str, params: dict, headers: dict):
        _ = (url, params, headers)
        return _MockChaptersResponse(
            {
                "code": 210,
                "message": "blocked",
                "results": {"detail": "risk-control"},
            },
            status_code=210,
        )

    adapter.client.get = _fake_get  # type: ignore[method-assign]
    adapter._fetch_web_meta = lambda item_id: {  # type: ignore[method-assign]
        "latest_update_time": "2026-03-19",
        "latest_chapters": ["第109话"],
    }

    updates = adapter.list_updates("wueyxingxuanlv", {"group_word": "default"})

    assert len(updates) == 1
    assert updates[0].title == "第109话"
    assert updates[0].update_id.startswith("fallback-")

def test_search_retries_on_transient_http_error():
    adapter = CopyMangaAdapter()
    adapter._enrich_search_items = lambda items: None  # type: ignore[method-assign]
    adapter._api_retry_total_seconds = 0.3
    adapter._api_retry_base_delay_seconds = 0.0
    calls = 0

    def _fake_get(url: str, params: dict, headers: dict):
        _ = (url, params, headers)
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("transient timeout")
        return _MockResponse()

    adapter.client.get = _fake_get  # type: ignore[method-assign]
    out = adapter.search("demo", 1)

    assert calls == 2
    assert out.total == 1


def test_healthcheck_uses_required_headers():
    adapter = CopyMangaAdapter()

    def _fake_get(url: str, params: dict, headers: dict):
        assert url.endswith("/api/v3/search/comic")
        assert params["q"] == "a"
        assert params["platform"] == 1
        assert headers["User-Agent"] == "COPY/3.0.0"
        assert headers["Accept"] == "application/json"
        assert headers["platform"] == "1"
        assert headers["version"] == "2025.08.15"
        assert headers["webp"] == "1"
        assert headers["region"] == "1"
        return _MockResponse()

    adapter.client.get = _fake_get  # type: ignore[method-assign]
    assert adapter.healthcheck() is True
