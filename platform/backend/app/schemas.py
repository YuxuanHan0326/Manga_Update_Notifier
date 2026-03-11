from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    code: str
    name: str
    supports_search: bool = True


class SearchItem(BaseModel):
    item_id: str
    title: str
    cover: str = ""
    author: str = ""
    group_word: str = "default"
    meta: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    source: str
    page: int
    total: int
    items: list[SearchItem]


class SubscriptionCreate(BaseModel):
    source_code: str
    item_id: str
    item_title: str
    group_word: str = "default"
    item_meta: dict[str, Any] = Field(default_factory=dict)


class KxoManualSubscriptionCreate(BaseModel):
    ref: str = Field(min_length=1)
    item_title: str | None = None


class SubscriptionUpdate(BaseModel):
    item_title: str | None = None
    group_word: str | None = None
    status: str | None = None


class SubscriptionResponse(BaseModel):
    id: int
    source_code: str
    item_id: str
    item_title: str
    group_word: str
    status: str
    last_seen_update_id: str | None
    last_seen_update_title: str | None = None
    last_seen_update_at: str | None = None
    item_meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseModel):
    id: int
    source_code: str
    subscription_id: int
    update_id: str
    update_title: str
    update_url: str
    detected_at: datetime
    summarized_at: datetime | None
    notified_at: datetime | None


class ScheduleUpdate(BaseModel):
    cron: str


class DailyScheduleUpdate(BaseModel):
    cron: str
    timezone: str | None = None


class SettingsResponse(BaseModel):
    timezone: str
    timezone_auto: bool
    check_cron: str
    daily_summary_cron: str
    webhook_enabled: bool
    webhook_url: str
    rss_enabled: bool
    app_base_url: str
    kxo_base_url: str
    kxo_auth_mode: str
    kxo_cookie_configured: bool
    kxo_remember_session: bool
    kxo_user_agent: str


class SettingsUpdate(BaseModel):
    timezone: str | None = None
    timezone_auto: bool | None = None
    check_cron: str | None = None
    daily_summary_cron: str | None = None
    webhook_enabled: bool | None = None
    webhook_url: str | None = None
    rss_enabled: bool | None = None
    app_base_url: str | None = None
    kxo_base_url: str | None = None
    kxo_auth_mode: str | None = None
    kxo_cookie: str | None = None
    kxo_remember_session: bool | None = None
    kxo_user_agent: str | None = None


class JobRunResponse(BaseModel):
    status: str
    detail: str


class CheckRunStats(BaseModel):
    scanned: int
    discovered: int


class SummaryRunStats(BaseModel):
    candidates: int
    delivered_channels: list[str]
    status: str
