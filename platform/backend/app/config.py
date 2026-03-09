from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MUP_", case_sensitive=False)

    app_name: str = "Manga Update Platform"
    database_url: str = "sqlite:///./data/app.db"
    app_timezone: str = "Asia/Shanghai"
    timezone_auto: bool = True
    ip_timezone_api_url_template: str = "https://ipapi.co/{ip}/json/"
    ip_timezone_self_api_url: str = "https://ipapi.co/json/"
    ip_timezone_timeout_sec: float = 5.0
    check_cron: str = "0 */6 * * *"
    daily_summary_cron: str = "0 21 * * *"
    webhook_enabled: bool = False
    webhook_url: str = ""
    rss_enabled: bool = True
    app_base_url: str = "http://localhost:8000"
    cm_api_base_url: str = "https://api.mangacopy.com"
    static_dir: str = ""
    scheduler_enabled: bool = True


settings = AppSettings()


def ensure_data_dir() -> None:
    db_url = settings.database_url
    if not db_url.startswith("sqlite:///"):
        return

    # Ensure SQLite parent directory exists both in local dev and Docker volume mounts.
    raw = db_url.removeprefix("sqlite:///")
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
