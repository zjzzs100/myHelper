"""APScheduler: load scheduled tasks, fire at run_at, push Gotify, update DB."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Protocol

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.models import Task, utcnow
from app.integrations.gotify import send_gotify_message

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def normalize_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SchedulerPort(Protocol):
    def schedule_task(self, task_id: int) -> None: ...
    def unschedule_task(self, task_id: int) -> None: ...


class NoOpScheduler:
    """Used in API tests when scheduler is not started."""

    def schedule_task(self, task_id: int) -> None:
        pass

    def unschedule_task(self, task_id: int) -> None:
        pass

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


class SchedulerEngine:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
    ) -> None:
        self.SessionLocal = session_factory
        self.settings = settings
        tz = settings.scheduler_timezone or "UTC"
        self.scheduler = BackgroundScheduler(timezone=tz)
        self._scan_seconds = max(1, settings.scan_interval_seconds)
        self._misfire = settings.misfire_grace_seconds

    def _job_id(self, task_id: int) -> str:
        return f"task_{task_id}"

    def start(self) -> None:
        self.scheduler.add_job(
            self.reconcile,
            trigger="interval",
            seconds=self._scan_seconds,
            id="reconcile",
            replace_existing=True,
        )
        self.reconcile()
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def schedule_task(self, task_id: int) -> None:
        db = self.SessionLocal()
        try:
            task = db.get(Task, task_id)
            if task is None or task.status != "scheduled":
                try:
                    self.scheduler.remove_job(self._job_id(task_id))
                except Exception:
                    pass
                return
            run_dt = normalize_utc(task.run_at_utc)
            self.scheduler.add_job(
                self.execute_task,
                trigger=DateTrigger(run_date=run_dt),
                args=[task_id],
                id=self._job_id(task_id),
                replace_existing=True,
                misfire_grace_time=self._misfire,
                coalesce=True,
                max_instances=1,
            )
        finally:
            db.close()

    def unschedule_task(self, task_id: int) -> None:
        try:
            self.scheduler.remove_job(self._job_id(task_id))
        except Exception:
            pass

    def reconcile(self) -> None:
        db = self.SessionLocal()
        try:
            rows = db.execute(
                select(Task).where(Task.status == "scheduled")
            ).scalars().all()
            active = {int(t.id) for t in rows}
            for tid in active:
                self.schedule_task(int(tid))
            for job in list(self.scheduler.get_jobs()):
                if job.id == "reconcile":
                    continue
                if not job.id.startswith("task_"):
                    continue
                try:
                    jid = int(job.id.split("_", 1)[1])
                except Exception:
                    continue
                if jid not in active:
                    try:
                        self.scheduler.remove_job(job.id)
                    except Exception:
                        pass
        finally:
            db.close()

    def execute_task(self, task_id: int) -> None:
        db = self.SessionLocal()
        try:
            task = db.get(Task, task_id)
            if task is None or task.status != "scheduled":
                return

            try:
                send_gotify_message(
                    self.settings,
                    title=task.title,
                    message=task.message,
                )
            except Exception as e:
                logger.exception("Gotify failed for task %s", task_id)
                task.status = "failed"
                task.last_error = str(e)[:2000]
                task.updated_at_utc = utcnow()
                db.commit()
                return

            if task.task_type == "once":
                task.status = "triggered"
                task.last_triggered_at_utc = utcnow()
                task.updated_at_utc = utcnow()
                task.last_error = None
                db.commit()
                self.unschedule_task(task_id)
                return

            if task.task_type == "interval":
                assert task.interval_seconds is not None
                now = utcnow()
                base = normalize_utc(task.run_at_utc)
                step = timedelta(seconds=int(task.interval_seconds))
                nxt = base + step
                for _ in range(100000):
                    if nxt > now:
                        break
                    nxt += step
                task.run_at_utc = nxt
                task.last_triggered_at_utc = utcnow()
                task.updated_at_utc = utcnow()
                task.last_error = None
                db.commit()
                self.schedule_task(task_id)
                return

            if task.task_type == "cron":
                assert task.cron_expr
                prev = normalize_utc(task.run_at_utc)
                now_dt = utcnow()
                trig = CronTrigger.from_crontab(
                    task.cron_expr.strip(), timezone=timezone.utc
                )
                next_dt = trig.get_next_fire_time(prev, now_dt)
                if next_dt is None:
                    task.status = "completed"
                    task.updated_at_utc = utcnow()
                    task.last_triggered_at_utc = utcnow()
                    task.last_error = None
                    db.commit()
                    self.unschedule_task(task_id)
                    return
                task.run_at_utc = normalize_utc(next_dt)
                task.last_triggered_at_utc = utcnow()
                task.updated_at_utc = utcnow()
                task.last_error = None
                db.commit()
                self.schedule_task(task_id)
                return

            task.status = "failed"
            task.last_error = f"Unknown task_type: {task.task_type}"
            task.updated_at_utc = utcnow()
            db.commit()
        finally:
            db.close()
