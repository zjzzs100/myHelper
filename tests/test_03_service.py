"""
Step 3: task_service (create / list / cancel) + TaskCreate validation.

Run: pytest tests/test_03_service.py -v
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import init_db, make_engine
from app.schemas.task import TaskCreate
from app.services import task_service


@pytest.fixture
def db_session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _run_at_future() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


def test_create_once(db_session: Session):
    data = TaskCreate(
        title="t1",
        message="m1",
        task_type="once",
        run_at=_run_at_future(),
    )
    t = task_service.create_task(db_session, data)
    assert t.id is not None
    assert t.task_type == "once"
    assert t.interval_seconds is None
    assert t.cron_expr is None


def test_create_interval(db_session: Session):
    data = TaskCreate(
        title="t2",
        message="m2",
        task_type="interval",
        run_at=_run_at_future(),
        interval_seconds=3600,
    )
    t = task_service.create_task(db_session, data)
    assert t.interval_seconds == 3600


def test_create_cron(db_session: Session):
    data = TaskCreate(
        title="t3",
        message="m3",
        task_type="cron",
        run_at=_run_at_future(),
        cron_expr="0 9 * * 1-5",
    )
    t = task_service.create_task(db_session, data)
    assert t.cron_expr == "0 9 * * 1-5"


def test_list_tasks_excludes_cancelled(db_session: Session):
    d1 = TaskCreate(title="a", message="x", task_type="once", run_at=_run_at_future())
    t1 = task_service.create_task(db_session, d1)
    d2 = TaskCreate(title="b", message="y", task_type="once", run_at=_run_at_future())
    t2 = task_service.create_task(db_session, d2)
    assert task_service.cancel_task(db_session, t1.id) is True
    items = task_service.list_tasks(db_session)
    ids = {x.task_id for x in items}
    assert t1.id not in ids
    assert t2.id in ids


def test_cancel_idempotent(db_session: Session):
    d = TaskCreate(title="c", message="z", task_type="once", run_at=_run_at_future())
    t = task_service.create_task(db_session, d)
    assert task_service.cancel_task(db_session, t.id) is True
    assert task_service.cancel_task(db_session, t.id) is True


def test_cancel_not_found(db_session: Session):
    assert task_service.cancel_task(db_session, 99999) is False


def test_cancel_completed_not_allowed(db_session: Session):
    d = TaskCreate(title="d", message="w", task_type="once", run_at=_run_at_future())
    t = task_service.create_task(db_session, d)
    t.status = "completed"
    db_session.commit()
    assert task_service.cancel_task(db_session, t.id) is False


def test_taskcreate_once_rejects_extra_fields():
    with pytest.raises(ValidationError):
        TaskCreate(
            title="x",
            message="y",
            task_type="once",
            run_at=_run_at_future(),
            interval_seconds=60,
        )


def test_taskcreate_interval_requires_interval():
    with pytest.raises(ValidationError):
        TaskCreate(
            title="x",
            message="y",
            task_type="interval",
            run_at=_run_at_future(),
        )


def test_task_to_read_iso8601_z(db_session: Session):
    run_at = datetime(2026, 4, 2, 10, 0, 0, tzinfo=timezone.utc)
    data = TaskCreate(
        title="iso",
        message="msg",
        task_type="once",
        run_at=run_at,
    )
    t = task_service.create_task(db_session, data)
    reads = task_service.list_tasks(db_session)
    one = next(x for x in reads if x.task_id == t.id)
    assert one.run_at.endswith("Z") or "+00:00" in one.run_at
