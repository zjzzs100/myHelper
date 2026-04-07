"""Business logic for tasks (DB only; scheduler hooks in later steps)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Task, utcnow
from app.schemas.task import TaskCreate, TaskRead, task_to_read


def create_task(db: Session, data: TaskCreate) -> Task:
    cron = data.cron_expr.strip() if data.cron_expr else None
    t = Task(
        title=data.title,
        message=data.message,
        task_type=data.task_type,
        run_at_utc=data.run_at_utc(),
        interval_seconds=data.interval_seconds,
        cron_expr=cron,
        status="scheduled",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def list_tasks(db: Session) -> list[TaskRead]:
    """Return all tasks except cancelled (scheduled/triggered/failed/completed)."""
    stmt = (
        select(Task)
        .where(Task.status != "cancelled")
        .order_by(Task.run_at_utc.asc(), Task.id.asc())
    )
    rows = db.execute(stmt).scalars().all()
    return [task_to_read(t) for t in rows]


def get_task(db: Session, task_id: int) -> Task | None:
    return db.get(Task, task_id)


def cancel_task(db: Session, task_id: int) -> bool:
    """
    Mark task as cancelled. Idempotent if already cancelled.
    Returns False if task not found or already completed.
    """
    t = db.get(Task, task_id)
    if t is None:
        return False
    if t.status == "cancelled":
        return True
    if t.status == "completed":
        return False
    if t.status in ("scheduled", "triggered", "failed"):
        t.status = "cancelled"
        t.updated_at_utc = utcnow()
        db.commit()
        return True
    return False
