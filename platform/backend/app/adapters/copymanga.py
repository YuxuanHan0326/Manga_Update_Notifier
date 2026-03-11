from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from threading import Lock
from time import monotonic

import httpx

from ..config import settings
from .base import (
    AdapterSearchResult,
    AdapterUpdate,
    AdapterUpstreamError,
    SearchPage,
)

log = logging.getLogger(__name__)


class CopyMangaAdapter:
    code = "copymanga"
    name = "CopyManga"

    def __init__(self) -> None:
        self.client = httpx.Client(timeout=15)
        # Short TTL cache avoids repeated HTML scraping during paged search.
        self._web_meta_cache_ttl_seconds = 300.0
        self._web_meta_cache: dict[str, tuple[float, dict]] = {}
        self._web_meta_cache_lock = Lock()

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": "COPY/3.0.0",
            "Accept": "application/json",
            "version": "2025.08.15",
            "platform": "1",
            "webp": "1",
            "region": "1",
        }

    @staticmethod
    def _web_headers() -> dict[str, str]:
        return {
            "User-Agent": "COPY/3.0.0",
            "Accept": "text/html,application/xhtml+xml",
        }

    @staticmethod
    def _normalize_meta_text(value: str) -> str:
        text = unescape(value or "")
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if "\\\\u" in text:
            text = text.replace("\\\\u", "\\u")
        if re.search(r"\\u[0-9a-fA-F]{4}", text):
            try:
                text = text.encode("utf-8").decode("unicode_escape")
            except UnicodeDecodeError:
                pass
        return text.strip()

    @staticmethod
    def _normalize_cover_url(value: str) -> str:
        text = unescape(value or "").replace("\\/", "/").strip()
        if not text:
            return ""
        if text.startswith("//"):
            return f"https:{text}"
        return text

    @classmethod
    def _extract_web_meta(cls, html: str) -> dict:
        meta: dict[str, str | list[str]] = {}
        flags = re.IGNORECASE | re.DOTALL

        cover_patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
            r'"cover"\s*:\s*"([^"]+)"',
        ]
        for pattern in cover_patterns:
            match = re.search(pattern, html, flags=flags)
            if not match:
                continue
            cover = cls._normalize_cover_url(match.group(1))
            if cover:
                meta["cover"] = cover
                break

        date_patterns = [
            r'"datetime_updated"\s*:\s*"([^"]+)"',
            r'"datetimeUpdated"\s*:\s*"([^"]+)"',
            (
                r"(?:\u6700\u5f8c\u66f4\u65b0|\u6700\u540e\u66f4\u65b0|\u66f4\u65b0\u65f6\u95f4|\u66f4\u65b0\u6642\u9593)"
                r"[^<]{0,12}</[^>]+>\s*<[^>]+>([^<]+)</"
            ),
        ]
        for pattern in date_patterns:
            match = re.search(pattern, html, flags=flags)
            if not match:
                continue
            date_text = cls._normalize_meta_text(match.group(1))
            if date_text:
                meta["latest_update_time"] = date_text
                break

        latest_chapters: list[str] = []
        chapter_keys: set[str] = set()

        def chapter_token(text: str) -> str | None:
            token_patterns = [
                re.compile(
                    r"(第[0-9０-９一二三四五六七八九十百千萬万零〇兩两]{1,8}"
                    r"(?:部[0-9０-９一二三四五六七八九十百千萬万零〇兩两]{1,8})?"
                    r"(?:卷|話|话|回|章|節|节))"
                ),
                re.compile(r"(第[0-9０-９一二三四五六七八九十百千萬万零〇兩两]{1,8}(?:卷|話|话|回|章|節|节))"),
            ]
            for pattern in token_patterns:
                matches = pattern.findall(text)
                if matches:
                    return matches[-1]
            return None

        def add_latest_chapter(raw_value: str, source: str) -> None:
            text = cls._normalize_meta_text(raw_value)
            text = re.sub(
                (
                    r"^(?:\u6700\u65b0(?:\u8bdd|\u8a71|\u56de|\u7ae0\u8282|\u7ae0\u7bc0)?|"
                    r"\u66f4\u65b0\u81f3|Latest(?:\s*Chapter)?)\s*[:\uff1a-]*\s*"
                ),
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()
            if "\u6f2b\u756b-" in text or "\u6f2b\u753b-" in text:
                text = re.split(r"(?:\u6f2b\u756b-|\u6f2b\u753b-)", text)[-1].strip()

            if not text or len(text) > 120:
                return

            token = chapter_token(text)
            key = token or text
            if source == "fallback" and token is None:
                return

            display = token or text
            if len(display) > 48:
                return

            if key in chapter_keys:
                return

            chapter_keys.add(key)
            latest_chapters.append(display)

        title_match = re.search(r"<title>\s*([^<]+?)\s*</title>", html, flags=flags)
        if title_match:
            title_text = cls._normalize_meta_text(title_match.group(1))
            title_patterns = [
                (
                    r"(?:\u6f2b\u756b|\u6f2b\u753b)-(.+?)-"
                    r"(?:\u9023\u8f09\u4e2d|\u8fde\u8f7d\u4e2d|\u5df2\u5b8c\u7d50|\u5df2\u5b8c\u7ed3|"
                    r"\u5b8c\u7d50|\u5b8c\u7ed3|\u9023\u8f09|\u8fde\u8f7d)-"
                ),
                r"(?:\u6f2b\u756b|\u6f2b\u753b)-(.+?)-",
            ]
            for pattern in title_patterns:
                match = re.search(pattern, title_text, flags=re.IGNORECASE)
                if not match:
                    continue
                add_latest_chapter(match.group(1), source="title")
                if latest_chapters:
                    break

        chapter_json_patterns = [
            r'"last_chapter"\s*:\s*\{[^{}]{0,500}?"name"\s*:\s*"([^"]+)"',
            r'"lastChapter"\s*:\s*\{[^{}]{0,500}?"name"\s*:\s*"([^"]+)"',
            r'"last_chapter_name"\s*:\s*"([^"]+)"',
            r'"lastChapterName"\s*:\s*"([^"]+)"',
        ]
        for pattern in chapter_json_patterns:
            for match in re.finditer(pattern, html, flags=flags):
                add_latest_chapter(match.group(1), source="json")
                if len(latest_chapters) >= 3:
                    break
            if len(latest_chapters) >= 3:
                break

        if len(latest_chapters) < 3:
            chapter_label_patterns = [
                (
                    r"(?:\u6700\u65b0(?:\u8bdd|\u8a71|\u56de|\u7ae0\u8282|\u7ae0\u7bc0)?|"
                    r"\u66f4\u65b0\u81f3)[^<]{0,12}</[^>]+>\s*<[^>]+>([^<]+)</"
                ),
            ]
            for pattern in chapter_label_patterns:
                for match in re.finditer(pattern, html, flags=flags):
                    add_latest_chapter(match.group(1), source="label")
                    if len(latest_chapters) >= 3:
                        break
                if len(latest_chapters) >= 3:
                    break

        if len(latest_chapters) < 3:
            chapter_fallback_patterns = [
                re.compile(r"\u7b2c[^<]{0,40}\u8bdd"),
                re.compile(r"\u7b2c[^<]{0,40}\u8a71"),
                re.compile(r"\u7b2c[^<]{0,40}\u56de"),
            ]
            for pattern in chapter_fallback_patterns:
                for chapter in pattern.findall(html):
                    # Fallback path keeps only chapter-token-like snippets to avoid noisy captures.
                    add_latest_chapter(chapter, source="fallback")
                    if len(latest_chapters) >= 3:
                        break
                if len(latest_chapters) >= 3:
                    break

        if latest_chapters:
            meta["latest_chapters"] = latest_chapters[:3]
        return meta

    def _read_cached_web_meta(self, item_id: str) -> dict | None:
        now = monotonic()
        with self._web_meta_cache_lock:
            cached = self._web_meta_cache.get(item_id)
            if cached is None:
                return None
            expires_at, meta = cached
            if expires_at <= now:
                self._web_meta_cache.pop(item_id, None)
                return None
            return dict(meta)

    def _write_cached_web_meta(self, item_id: str, meta: dict) -> None:
        with self._web_meta_cache_lock:
            self._web_meta_cache[item_id] = (
                monotonic() + self._web_meta_cache_ttl_seconds,
                dict(meta),
            )

    def _fetch_web_meta(self, item_id: str) -> dict:
        cached = self._read_cached_web_meta(item_id)
        if cached is not None:
            return cached

        try:
            resp = self.client.get(
                f"https://www.mangacopy.com/comic/{item_id}",
                headers=self._web_headers(),
                timeout=8,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("copymanga web meta fetch failed for %s: %s", item_id, exc)
            meta = {"meta_fetch_status": "fetch_failed"}
            self._write_cached_web_meta(item_id, meta)
            return meta

        try:
            meta = self._extract_web_meta(resp.text)
        except Exception as exc:  # noqa: BLE001
            log.warning("copymanga web meta parse failed for %s: %s", item_id, exc)
            meta = {"meta_fetch_status": "fetch_failed"}
            self._write_cached_web_meta(item_id, meta)
            return meta

        meta["meta_fetch_status"] = "ok"
        # Keep response shape deterministic for frontend state handling.
        meta.setdefault("latest_chapters", [])
        self._write_cached_web_meta(item_id, meta)
        return meta

    def fetch_item_snapshot(self, item_id: str, item_meta: dict | None = None) -> dict:
        _ = item_meta
        meta = self._fetch_web_meta(item_id)
        return {
            "cover": meta.get("cover", ""),
            "latest_update_time": meta.get("latest_update_time", ""),
            "latest_chapters": meta.get("latest_chapters", []),
        }

    def _enrich_search_items(self, items: list[AdapterSearchResult]) -> None:
        candidates = [item for item in items if item.item_id]
        if not candidates:
            return

        max_workers = min(5, len(candidates))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self._fetch_web_meta, item.item_id): item for item in candidates}
            for future in as_completed(futures):
                item = futures[future]
                try:
                    meta = future.result()
                except Exception as exc:  # noqa: BLE001
                    log.warning("copymanga web meta parse failed for %s: %s", item.item_id, exc)
                    continue
                item.meta = {**(item.meta or {}), **(meta or {})}

    @staticmethod
    def _json_or_raise(resp: httpx.Response, context: str) -> dict:
        try:
            payload = resp.json()
        except ValueError as exc:
            content_type = resp.headers.get("content-type", "unknown")
            preview = (resp.text or "").strip().replace("\n", " ")[:120]
            raise AdapterUpstreamError(
                f"{context} returned non-JSON payload "
                f"(status={resp.status_code}, content_type={content_type}, preview={preview!r})"
            ) from exc

        if not isinstance(payload, dict):
            raise AdapterUpstreamError(f"{context} returned unsupported JSON structure")
        return payload

    def search(self, query: str, page: int) -> SearchPage:
        limit = 20
        offset = (max(page, 1) - 1) * limit
        try:
            resp = self.client.get(
                f"{settings.cm_api_base_url}/api/v3/search/comic",
                params={
                    "limit": limit,
                    "offset": offset,
                    "q": query,
                    "q_type": "",
                    "platform": 1,
                },
                headers=self._headers(),
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AdapterUpstreamError(f"copymanga search request failed: {exc}") from exc

        payload = self._json_or_raise(resp, "copymanga search")
        results = payload.get("results", {})
        if not isinstance(results, dict):
            raise AdapterUpstreamError("copymanga search returned malformed results payload")
        items = []
        for raw in results.get("list", []):
            if not isinstance(raw, dict):
                continue
            authors = raw.get("author", [])
            author = ", ".join(
                a.get("name", "")
                for a in authors
                if isinstance(a, dict) and a.get("name")
            )
            items.append(
                AdapterSearchResult(
                    item_id=raw.get("path_word", ""),
                    title=raw.get("name", ""),
                    cover=raw.get("cover", ""),
                    author=author,
                    group_word="default",
                    meta={"alias": raw.get("alias")},
                )
            )

        self._enrich_search_items(items)
        return SearchPage(page=page, total=results.get("total", 0), items=items)

    def list_updates(self, item_id: str, item_meta: dict | None = None) -> list[AdapterUpdate]:
        group_word = (item_meta or {}).get("group_word", "default")
        try:
            resp = self.client.get(
                f"{settings.cm_api_base_url}/api/v3/comic/{item_id}/group/{group_word}/chapters",
                params={"limit": 500, "offset": 0, "platform": 3, "in_mainland": "false"},
                headers=self._headers(),
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AdapterUpstreamError(f"copymanga updates request failed: {exc}") from exc

        payload = self._json_or_raise(resp, "copymanga updates")
        results = payload.get("results", {})
        if not isinstance(results, dict):
            raise AdapterUpstreamError("copymanga updates returned malformed results payload")
        chapters = [c for c in results.get("list", []) if isinstance(c, dict)]
        ordered = sorted(chapters, key=lambda c: c.get("index", 0))
        return [
            AdapterUpdate(
                update_id=chapter.get("uuid", ""),
                title=chapter.get("name", ""),
                url=f"https://www.mangacopy.com/comic/{item_id}",
            )
            for chapter in ordered
            if chapter.get("uuid")
        ]

    def healthcheck(self) -> bool:
        try:
            self.client.get(f"{settings.cm_api_base_url}/api/v3/search/comic", params={"q": "a"})
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("copymanga healthcheck failed: %s", exc)
            return False

