from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from threading import Lock
from urllib.parse import quote

import httpx

from .base import (
    AdapterAuthRequiredError,
    AdapterSearchResult,
    AdapterSessionInvalidError,
    AdapterUpdate,
    AdapterUpstreamError,
    SearchPage,
)

log = logging.getLogger(__name__)


def _clean_text(value: str) -> str:
    text = unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class KxoAdapter:
    code = "kxo"
    name = "KXO"

    def __init__(self) -> None:
        self._timeout = 15
        self._runtime_lock = Lock()
        self._runtime_options: dict[str, str | bool] = {
            "kxo_base_url": "https://kzo.moe",
            "kxo_auth_mode": "guest",
            "kxo_cookie": "",
            "kxo_user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
        }

    def configure_runtime(self, options: dict | None) -> None:
        if not isinstance(options, dict):
            return
        with self._runtime_lock:
            for key in ("kxo_base_url", "kxo_auth_mode", "kxo_cookie", "kxo_user_agent"):
                if key not in options:
                    continue
                value = options.get(key)
                if isinstance(value, str):
                    self._runtime_options[key] = value.strip()
                elif isinstance(value, bool):
                    self._runtime_options[key] = value

    def _runtime(self) -> dict:
        with self._runtime_lock:
            return dict(self._runtime_options)

    @staticmethod
    def parse_item_id(raw_ref: str) -> str | None:
        text = (raw_ref or "").strip()
        if not text:
            return None
        if re.fullmatch(r"\d{1,12}", text):
            return text
        match = re.search(r"/c/(\d{1,12})\.htm", text)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _candidate_bases(primary: str) -> list[str]:
        ordered = [primary.strip(), "https://kzo.moe", "https://kxo.moe"]
        out: list[str] = []
        for base in ordered:
            if not base:
                continue
            normalized = base.rstrip("/")
            if normalized not in out:
                out.append(normalized)
        return out

    @staticmethod
    def _headers(cookie: str, user_agent: str) -> dict[str, str]:
        headers = {
            "User-Agent": user_agent
            or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if cookie:
            headers["Cookie"] = cookie
        return headers

    @staticmethod
    def _is_login_page(html: str, final_url: str) -> bool:
        lowered_url = (final_url or "").lower()
        if lowered_url.endswith("/login.php"):
            return True
        text = html or ""
        return (
            "action=\"/login_do.php\"" in text
            or "登錄 - kzo.moe" in text
            or "帳號密碼" in text
        )

    @staticmethod
    def _extract_title(html: str) -> str:
        match = re.search(r"<title>\s*([^<]+?)\s*</title>", html, flags=re.IGNORECASE)
        if not match:
            return ""
        text = _clean_text(match.group(1))
        if ":" in text:
            return text.split(":", 1)[0].strip()
        return text

    @staticmethod
    def _normalize_cover_url(raw: str) -> str:
        text = unescape(raw or "").replace("\\/", "/").strip()
        if not text:
            return ""
        if text.startswith("//"):
            return f"https:{text}"
        return text

    @classmethod
    def _extract_cover(cls, html: str) -> str:
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
            r'"cover"\s*:\s*"([^"]+)"',
            r'"img"\s*:\s*"([^"]+)"',
            r'<img[^>]+(?:id|class)=["\'][^"\']*(?:cover|book|comic)[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            cover = cls._normalize_cover_url(match.group(1))
            if cover:
                return cover
        return ""

    @staticmethod
    def _extract_token(html: str) -> str:
        match = re.search(r"/book_data\.php\?h=([A-Za-z0-9]+)", html)
        if not match:
            return ""
        return match.group(1)

    @staticmethod
    def _split_js_args(raw: str) -> list[str]:
        args: list[str] = []
        buf: list[str] = []
        quote_char = ""
        escaped = False
        for ch in raw:
            if escaped:
                buf.append(ch)
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if quote_char:
                if ch == quote_char:
                    quote_char = ""
                else:
                    buf.append(ch)
                continue
            if ch in ("'", '"'):
                quote_char = ch
                continue
            if ch == ",":
                args.append("".join(buf).strip())
                buf = []
                continue
            buf.append(ch)
        if buf:
            args.append("".join(buf).strip())
        return [unescape(value.strip()) for value in args]

    @classmethod
    def _parse_search_items(cls, html: str) -> list[AdapterSearchResult]:
        matches = re.finditer(r"disp_divinfo\((.*?)\);", html, flags=re.DOTALL)
        items: list[AdapterSearchResult] = []
        seen: set[str] = set()
        for match in matches:
            args = cls._split_js_args(match.group(1))
            if len(args) < 13:
                continue
            book_url = args[1]
            item_match = re.search(r"/c/(\d+)\.htm", book_url)
            if not item_match:
                continue
            item_id = item_match.group(1)
            if item_id in seen:
                continue
            seen.add(item_id)
            title = _clean_text(args[9])
            if not title:
                continue
            meta = {
                "summary": _clean_text(args[11]),
                "latest_update_time": _clean_text(args[12]),
                "meta_fetch_status": "pending",
            }
            items.append(
                AdapterSearchResult(
                    item_id=item_id,
                    title=title,
                    cover=args[2].strip(),
                    author=_clean_text(args[10]),
                    group_word="default",
                    meta=meta,
                )
            )
        return items

    @staticmethod
    def _extract_datetime(value: str) -> str:
        match = re.search(r"(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)", value or "")
        if not match:
            return ""
        return match.group(1)

    @classmethod
    def _parse_book_data(
        cls, text: str, item_id: str, detail_url: str
    ) -> tuple[list[AdapterUpdate], str]:
        vol_lines = re.findall(r'volinfo=([^"]+)"', text or "")
        rows: list[tuple[int, int, AdapterUpdate, str]] = []
        for line in vol_lines:
            fields = [part.strip() for part in line.split(",")]
            if len(fields) < 6:
                continue
            vol_id = fields[0] or "0"
            vol_type = fields[3] or "default"
            seq_text = fields[4] if len(fields) > 4 else "0"
            title = _clean_text(fields[5])
            if not title:
                continue
            build_candidates = []
            for idx in (16, 15, 14, 13):
                if idx < len(fields):
                    build_candidates.append(cls._extract_datetime(fields[idx]))
            update_time = next((value for value in build_candidates if ":" in value), "")
            if not update_time:
                update_time = next((value for value in build_candidates if value), "")
            try:
                seq = int(seq_text)
            except ValueError:
                seq = 0
            try:
                vol_order = int(vol_id)
            except ValueError:
                vol_order = 0
            update = AdapterUpdate(
                update_id=f"{item_id}:{vol_id}:{vol_type}",
                title=title,
                url=detail_url,
            )
            rows.append((seq, vol_order, update, update_time))

        rows.sort(key=lambda item: (item[0], item[1]))
        updates = [row[2] for row in rows]
        latest_time = ""
        for row in reversed(rows):
            if row[3]:
                latest_time = row[3]
                break
        return updates, latest_time

    @staticmethod
    def _search_url(base_url: str, query: str, page: int) -> str:
        if page <= 1:
            return f"{base_url}/list.php?s={quote(query)}"
        return f"{base_url}/l/{quote(query)}/{page}.htm"

    @staticmethod
    def _has_next_page(html: str, query: str, page: int) -> bool:
        # The site uses '/l/<query>/<page>.htm' links; checking next-page marker keeps
        # API pagination usable without requiring a strict total counter endpoint.
        next_path = f"/l/{quote(query)}/{page + 1}.htm"
        return next_path in (html or "")

    def _fetch_item_snapshot(
        self, client: httpx.Client, base_url: str, item_id: str
    ) -> dict[str, str | list[str]]:
        detail_url = f"{base_url}/c/{item_id}.htm"
        detail = client.get(detail_url)
        detail.raise_for_status()
        html = detail.text
        token = self._extract_token(html)
        if not token:
            return {
                "item_title": self._extract_title(html),
                "cover": self._extract_cover(html),
                "latest_update_time": "",
                "latest_chapters": [],
            }

        book = client.get(f"{base_url}/book_data.php?h={token}")
        book.raise_for_status()
        updates, latest_time = self._parse_book_data(book.text, item_id, detail_url)
        latest_chapter = updates[-1].title if updates else ""
        return {
            "item_title": self._extract_title(html),
            "cover": self._extract_cover(html),
            "latest_update_time": latest_time,
            "latest_chapters": [latest_chapter] if latest_chapter else [],
        }

    def _enrich_search_items(
        self, items: list[AdapterSearchResult], base_url: str, headers: dict
    ) -> None:
        if not items:
            return

        # Restrict worker count to reduce anti-bot pressure while still enriching quickly.
        max_workers = min(4, len(items))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._enrich_search_item, base_url, headers, item.item_id): item
                for item in items
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    snapshot = future.result()
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "kxo search meta enrich failed source=%s item_id=%s error=%s",
                        self.code,
                        item.item_id,
                        exc,
                    )
                    item.meta = {**(item.meta or {}), "meta_fetch_status": "fetch_failed"}
                    continue
                merged = {**(item.meta or {})}
                latest_time = snapshot.get("latest_update_time")
                if isinstance(latest_time, str) and latest_time:
                    merged["latest_update_time"] = latest_time
                latest_chapters = snapshot.get("latest_chapters")
                if isinstance(latest_chapters, list):
                    merged["latest_chapters"] = latest_chapters
                merged["meta_fetch_status"] = "ok"
                item.meta = merged

    def _enrich_search_item(self, base_url: str, headers: dict, item_id: str) -> dict:
        with httpx.Client(timeout=self._timeout, headers=headers, follow_redirects=True) as client:
            return self._fetch_item_snapshot(client, base_url, item_id)

    def fetch_item_snapshot(self, item_id: str, item_meta: dict | None = None) -> dict:
        options = self._runtime()
        if isinstance(item_meta, dict):
            options.update(
                {
                    "kxo_base_url": item_meta.get("kxo_base_url", options["kxo_base_url"]),
                    "kxo_cookie": item_meta.get("kxo_cookie", options.get("kxo_cookie", "")),
                    "kxo_user_agent": item_meta.get(
                        "kxo_user_agent", options.get("kxo_user_agent", "")
                    ),
                }
            )
        bases = self._candidate_bases(str(options.get("kxo_base_url", "")))
        headers = self._headers(
            str(options.get("kxo_cookie", "")),
            str(options.get("kxo_user_agent", "")),
        )
        last_error: Exception | None = None
        for base in bases:
            try:
                with httpx.Client(
                    timeout=self._timeout, headers=headers, follow_redirects=True
                ) as client:
                    return self._fetch_item_snapshot(client, base, item_id)
            except httpx.HTTPError as exc:
                last_error = exc
                log.warning(
                    "kxo snapshot request failed source=%s item_id=%s base=%s error=%s",
                    self.code,
                    item_id,
                    base,
                    exc,
                )
                continue
        if last_error:
            raise AdapterUpstreamError(f"kxo snapshot request failed: {last_error}") from last_error
        raise AdapterUpstreamError("kxo snapshot failed: no available host")

    def search(self, query: str, page: int) -> SearchPage:
        options = self._runtime()
        cookie = str(options.get("kxo_cookie", "")).strip()
        if not cookie:
            raise AdapterAuthRequiredError("kxo search auth_required: cookie is not configured")

        bases = self._candidate_bases(str(options.get("kxo_base_url", "")))
        headers = self._headers(cookie, str(options.get("kxo_user_agent", "")))
        last_error: Exception | None = None
        page = max(1, page)
        for base in bases:
            try:
                with httpx.Client(
                    timeout=self._timeout, headers=headers, follow_redirects=True
                ) as client:
                    url = self._search_url(base, query, page)
                    response = client.get(url)
                    response.raise_for_status()
                    html = response.text
                    if self._is_login_page(html, str(response.url)):
                        raise AdapterSessionInvalidError(
                            f"kxo search session_invalid: redirected to login at base={base}"
                        )
                    items = self._parse_search_items(html)
                    self._enrich_search_items(items, base, headers)
                    per_page = max(20, len(items))
                    if self._has_next_page(html, query, page):
                        total = page * per_page + 1
                    else:
                        total = (page - 1) * per_page + len(items)
                    return SearchPage(page=page, total=total, items=items)
            except AdapterSessionInvalidError as exc:
                last_error = exc
                # Session-invalid is not recoverable by host fallback when cookie is bad.
                break
            except httpx.HTTPError as exc:
                last_error = exc
                log.warning(
                    "kxo search request failed source=%s status=transport_error base=%s error=%s",
                    self.code,
                    base,
                    exc,
                )
                continue

        if isinstance(last_error, AdapterSessionInvalidError):
            raise last_error
        if last_error:
            raise AdapterUpstreamError(f"kxo search request failed: {last_error}") from last_error
        raise AdapterUpstreamError("kxo search failed: no available host")

    def list_updates(self, item_id: str, item_meta: dict | None = None) -> list[AdapterUpdate]:
        options = self._runtime()
        if isinstance(item_meta, dict):
            options.update(
                {
                    "kxo_base_url": item_meta.get("kxo_base_url", options["kxo_base_url"]),
                    "kxo_cookie": item_meta.get("kxo_cookie", options.get("kxo_cookie", "")),
                    "kxo_user_agent": item_meta.get(
                        "kxo_user_agent", options.get("kxo_user_agent", "")
                    ),
                }
            )
        bases = self._candidate_bases(str(options.get("kxo_base_url", "")))
        headers = self._headers(
            str(options.get("kxo_cookie", "")),
            str(options.get("kxo_user_agent", "")),
        )

        last_error: Exception | None = None
        for base in bases:
            try:
                detail_url = f"{base}/c/{item_id}.htm"
                with httpx.Client(
                    timeout=self._timeout, headers=headers, follow_redirects=True
                ) as client:
                    detail = client.get(detail_url)
                    detail.raise_for_status()
                    token = self._extract_token(detail.text)
                    if not token:
                        log.warning(
                            "kxo updates missing token source=%s item_id=%s base=%s",
                            self.code,
                            item_id,
                            base,
                        )
                        continue
                    book = client.get(f"{base}/book_data.php?h={token}")
                    book.raise_for_status()
                    updates, _ = self._parse_book_data(book.text, item_id, detail_url)
                    if updates:
                        return updates
            except httpx.HTTPError as exc:
                last_error = exc
                log.warning(
                    "kxo updates request failed source=%s item_id=%s base=%s error=%s",
                    self.code,
                    item_id,
                    base,
                    exc,
                )
                continue

        if last_error:
            raise AdapterUpstreamError(f"kxo updates request failed: {last_error}") from last_error
        return []

    def healthcheck(self) -> bool:
        options = self._runtime()
        bases = self._candidate_bases(str(options.get("kxo_base_url", "")))
        headers = self._headers(
            str(options.get("kxo_cookie", "")),
            str(options.get("kxo_user_agent", "")),
        )
        for base in bases:
            try:
                with httpx.Client(timeout=8, headers=headers, follow_redirects=True) as client:
                    response = client.get(f"{base}/")
                    response.raise_for_status()
                    return True
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "kxo healthcheck failed source=%s base=%s error=%s",
                    self.code,
                    base,
                    exc,
                )
                continue
        return False
