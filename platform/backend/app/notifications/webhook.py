from __future__ import annotations

import hashlib
import json
from datetime import datetime

import httpx


class WebhookNotifier:
    channel = "webhook"

    def send(
        self,
        url: str,
        title: str,
        events: list[dict],
        window_start: datetime,
        window_end: datetime,
    ) -> tuple[bool, str, str]:
        # Payload hash is persisted for traceability/retry diagnostics.
        payload = {
            "title": title,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "count": len(events),
            "events": events,
        }
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        try:
            response = httpx.post(url, json=payload, timeout=20)
            response.raise_for_status()
            return True, payload_hash, ""
        except Exception as exc:  # noqa: BLE001
            return False, payload_hash, str(exc)
