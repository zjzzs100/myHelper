from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

TaskType = Literal["once", "interval", "cron"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)
    task_type: TaskType
    run_at: datetime = Field(description="First run time; must include timezone.")
    interval_seconds: Optional[int] = Field(default=None, ge=1, le=315360000)
    cron_expr: Optional[str] = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def check_type_fields(self) -> TaskCreate:
        if self.task_type == "once":
            if self.interval_seconds is not None or self.cron_expr is not None:
                raise ValueError("once task must not set interval_seconds or cron_expr")
        elif self.task_type == "interval":
            if self.interval_seconds is None:
                raise ValueError("interval task requires interval_seconds")
            if self.cron_expr is not None:
                raise ValueError("interval task must not set cron_expr")
        else:  # cron
            if self.cron_expr is None or not self.cron_expr.strip():
                raise ValueError("cron task requires cron_expr")
            if self.interval_seconds is not None:
                raise ValueError("cron task must not set interval_seconds")
        return self

    def run_at_utc(self) -> datetime:
        return self.run_at.astimezone(timezone.utc)


class TaskRead(BaseModel):
    task_id: int
    status: str
    title: str
    run_at: str
    message: str

    model_config = {"from_attributes": False}


class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int


class TaskCancelResponse(BaseModel):
    task_id: str
    status: str


def task_to_read(t) -> TaskRead:
    from app.db import models as m

    assert isinstance(t, m.Task)
    dt = t.run_at_utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    run_at_str = dt.isoformat().replace("+00:00", "Z")
    return TaskRead(
        task_id=t.id,
        status=t.status,
        title=t.title,
        run_at=run_at_str,
        message=t.message,
    )
