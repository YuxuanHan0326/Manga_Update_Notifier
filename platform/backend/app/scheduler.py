from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from .db import SessionLocal
from .services.checker import run_update_check
from .services.settings import get_runtime_settings
from .services.summary import run_daily_summary

log = logging.getLogger(__name__)


class SchedulerManager:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
        self.reload_jobs()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def _job_check_updates(self) -> None:
        db = SessionLocal()
        try:
            run_update_check(db)
        finally:
            db.close()

    def _job_daily_summary(self) -> None:
        db = SessionLocal()
        try:
            run_daily_summary(db)
        finally:
            db.close()

    def reload_jobs(self) -> None:
        db: Session = SessionLocal()
        try:
            cfg = get_runtime_settings(db)
        finally:
            db.close()

        timezone = ZoneInfo(cfg["timezone"])
        self.scheduler.remove_all_jobs()

        self.scheduler.add_job(
            self._job_check_updates,
            CronTrigger.from_crontab(cfg["check_cron"], timezone=timezone),
            id="check_updates",
            replace_existing=True,
            max_instances=1,
            # coalesce=True prevents backlog bursts after temporary process downtime.
            coalesce=True,
        )
        self.scheduler.add_job(
            self._job_daily_summary,
            CronTrigger.from_crontab(cfg["daily_summary_cron"], timezone=timezone),
            id="daily_summary",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        log.info("scheduler jobs loaded")


scheduler_manager = SchedulerManager()
