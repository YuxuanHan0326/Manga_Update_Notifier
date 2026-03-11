from __future__ import annotations

import hashlib
import html
from datetime import UTC, datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from zoneinfo import ZoneInfo

_NS_ATOM = "http://www.w3.org/2005/Atom"
_NS_CONTENT = "http://purl.org/rss/1.0/modules/content/"


def _safe_feed_link(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/notifications/rss.xml"


def render_rss(base_url: str, events: list[dict], timezone_name: str = "UTC") -> str:
    rss = Element(
        "rss",
        {
            "version": "2.0",
            "xmlns:atom": _NS_ATOM,
            "xmlns:content": _NS_CONTENT,
        },
    )
    channel = SubElement(rss, "channel")
    feed_link = _safe_feed_link(base_url)

    SubElement(channel, "title").text = "Manga Update Platform"
    SubElement(channel, "link").text = feed_link
    SubElement(channel, "description").text = "Manga updates optimized for RSS readers"
    SubElement(channel, "language").text = "zh-CN"
    # Explicit self link improves compatibility for some readers and aggregators.
    SubElement(channel, "atom:link", href=feed_link, rel="self", type="application/rss+xml")

    try:
        timezone = ZoneInfo(timezone_name)
    except Exception:  # noqa: BLE001
        timezone = UTC

    for event in events:
        subscription = event.get("subscription", {}) if isinstance(event, dict) else {}
        update = event.get("update", {}) if isinstance(event, dict) else {}
        item_title = str(subscription.get("item_title") or "未知作品")
        update_title = str(update.get("update_title") or "未知更新")
        source_code = str(event.get("source_code") or "unknown")
        source_item_url = str(subscription.get("source_item_url") or "")
        update_url = str(update.get("update_url") or source_item_url or base_url)
        dedupe_key = str(update.get("dedupe_key") or event.get("id") or "")

        item = SubElement(channel, "item")
        SubElement(item, "title").text = f"{item_title} · {update_title}"
        SubElement(item, "guid", isPermaLink="false").text = dedupe_key
        SubElement(item, "link").text = update_url
        SubElement(item, "category").text = source_code

        detected_raw = str(update.get("detected_at") or "")
        pub = None
        if detected_raw:
            try:
                pub = datetime.fromisoformat(detected_raw)
            except ValueError:
                pub = None
        if isinstance(pub, datetime):
            pub_utc = pub.astimezone(UTC)
            SubElement(item, "pubDate").text = pub_utc.strftime("%a, %d %b %Y %H:%M:%S GMT")
            local_text = pub_utc.astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            local_text = "unknown"

        # Keep `description` short so list view in RSS readers stays clean and readable.
        SubElement(item, "description").text = (
            f"来源: {source_code} | 时间: {local_text} | 打开章节: {update_url}"
        )

        # Put detailed content in `content:encoded` for readers that support expanded preview.
        content_lines = [
            f"作品：{item_title}",
            f"最新更新：{update_title}",
            f"来源：{source_code}",
            f"检测时间：{local_text}",
            f"章节链接：{update_url}",
        ]
        if source_item_url and source_item_url != update_url:
            content_lines.append(f"作品页：{source_item_url}")
        SubElement(item, "content:encoded").text = "\n".join(
            html.escape(line) for line in content_lines
        )
        # RSS output is intentionally text-only to maximize reader compatibility.
        # Cover URLs remain available in webhook payloads and internal subscription metadata.

    xml_bytes = tostring(rss, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def compute_payload_hash(events: list[dict]) -> str:
    flattened: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        update = event.get("update", {}) if isinstance(event.get("update"), dict) else {}
        dedupe_key = str(update.get("dedupe_key") or event.get("dedupe_key") or "")
        update_title = str(update.get("update_title") or event.get("update_title") or "")
        flattened.append(f"{dedupe_key}|{update_title}")
    joined = "\n".join(flattened)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
