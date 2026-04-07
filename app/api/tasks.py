from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_scheduler
from app.schemas.task import (
    TaskCancelResponse,
    TaskCreate,
    TaskListResponse,
    TaskRead,
    task_to_read,
)
from app.scheduler.engine import SchedulerPort
from app.services import task_service

router = APIRouter()


@router.post("/tasks/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreate,
    db: Session = Depends(get_db),
    scheduler: SchedulerPort = Depends(get_scheduler),
) -> TaskRead:
    t = task_service.create_task(db, body)
    scheduler.schedule_task(t.id)
    return task_to_read(t)


@router.get("/tasks/", response_model=TaskListResponse)
def list_tasks(db: Session = Depends(get_db)) -> TaskListResponse:
    items = task_service.list_tasks(db)
    return TaskListResponse(items=items, total=len(items))


@router.delete("/tasks/{task_id}", response_model=TaskCancelResponse)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    scheduler: SchedulerPort = Depends(get_scheduler),
) -> TaskCancelResponse:
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already completed.",
        )
    ok = task_service.cancel_task(db, task_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel task.",
        )
    scheduler.unschedule_task(task_id)
    return TaskCancelResponse(task_id=str(task_id), status="cancelled")
