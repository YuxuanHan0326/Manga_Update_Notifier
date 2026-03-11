from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models import SystemSetting

_DEFAULTS = {
    "timezone": settings.app_timezone,
    "timezone_auto": settings.timezone_auto,
    "check_cron": settings.check_cron,
    "daily_summary_cron": settings.daily_summary_cron,
    "webhook_enabled": settings.webhook_enabled,
    "webhook_url": settings.webhook_url,
    "rss_enabled": settings.rss_enabled,
    "app_base_url": settings.app_base_url,
    "kxo_base_url": settings.kxo_base_url,
    "kxo_auth_mode": settings.kxo_auth_mode,
    "kxo_cookie": settings.kxo_cookie,
    "kxo_user_agent": settings.kxo_user_agent,
    "kxo_remember_session": settings.kxo_remember_session,
}

_EPHEMERAL_OVERRIDES: dict[str, Any] = {}


def get_runtime_settings(db: Session) -> dict[str, Any]:
    # DB overrides env defaults; missing keys keep deterministic fallback behavior.
    values = dict(_DEFAULTS)
    records = db.query(SystemSetting).all()
    for row in records:
        values[row.key] = json.loads(row.value_json)
    values.update(_EPHEMERAL_OVERRIDES)
    return values


def upsert_settings(db: Session, updates: dict[str, Any]) -> dict[str, Any]:
    for key, value in updates.items():
        if value is None:
            continue
        row = db.query(SystemSetting).filter(SystemSetting.key == key).one_or_none()
        if row is None:
            row = SystemSetting(key=key, value_json=json.dumps(value, ensure_ascii=False))
            db.add(row)
        else:
            row.value_json = json.dumps(value, ensure_ascii=False)
    db.commit()
    return get_runtime_settings(db)


def upsert_ephemeral_settings(updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if value is None:
            continue
        _EPHEMERAL_OVERRIDES[key] = value
