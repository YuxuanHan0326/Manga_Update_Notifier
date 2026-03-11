from __future__ import annotations

import hashlib
import json

import httpx


class WebhookNotifier:
    channel = "webhook"

    def send(self, url: str, payload: dict) -> tuple[bool, str, str]:
        # Persist stable hash of the exact outbound body for traceability/debug.
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        try:
            response = httpx.post(url, json=payload, timeout=20)
            response.raise_for_status()
            return True, payload_hash, ""
        except Exception as exc:  # noqa: BLE001
            return False, payload_hash, str(exc)
