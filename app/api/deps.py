from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.scheduler.engine import SchedulerPort


def get_db(request: Request):
    SessionLocal: sessionmaker[Session] = request.app.state.SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_scheduler(request: Request) -> SchedulerPort:
    return request.app.state.scheduler
