from __future__ import annotations

import hashlib
import html
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring


def render_rss(base_url: str, events: list[dict]) -> str:
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "Manga Update Platform"
    SubElement(channel, "link").text = f"{base_url.rstrip('/')}/api/notifications/rss.xml"
    SubElement(channel, "description").text = "Recent detected updates"

    for event in events:
        item = SubElement(channel, "item")
        # Escape user-originated fields to keep generated XML well-formed.
        SubElement(item, "title").text = html.escape(event["update_title"])
        SubElement(item, "guid").text = event["dedupe_key"]
        SubElement(item, "link").text = event["update_url"] or base_url
        pub = event.get("detected_at")
        if isinstance(pub, datetime):
            SubElement(item, "pubDate").text = pub.strftime("%a, %d %b %Y %H:%M:%S GMT")
        SubElement(item, "description").text = html.escape(
            f"{event['source_code']} / subscription {event['subscription_id']}"
        )

    xml_bytes = tostring(rss, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def compute_payload_hash(events: list[dict]) -> str:
    joined = "\n".join(f"{e['dedupe_key']}|{e['update_title']}" for e in events)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
