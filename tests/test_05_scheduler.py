"""
Step 5: APScheduler engine execute_task + Gotify mocked.

Run: pytest tests/test_05_scheduler.py -v
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.session import init_db, make_engine
from app.schemas.task import TaskCreate
from app.scheduler.engine import SchedulerEngine, normalize_utc
from app.services import task_service


def _session_factory():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        gotify_url="http://localhost:8080",
        gotify_token="test-token",
        scheduler_timezone="UTC",
        scan_interval_seconds=5,
        misfire_grace_seconds=60,
    )


@patch("app.scheduler.engine.send_gotify_message")
def test_execute_once_marks_triggered(mock_send):
    SessionLocal = _session_factory()
    settings = _settings()
    eng = SchedulerEngine(SessionLocal, settings)

    run_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db = SessionLocal()
    try:
        t = task_service.create_task(
            db,
            TaskCreate(
                title="s1",
                message="m",
                task_type="once",
                run_at=run_at,
            ),
        )
        tid = t.id
    finally:
        db.close()

    eng.execute_task(tid)
    mock_send.assert_called_once()
    db = SessionLocal()
    try:
        row = task_service.get_task(db, tid)
        assert row is not None
        assert row.status == "triggered"
    finally:
        db.close()


@patch("app.scheduler.engine.send_gotify_message")
def test_execute_interval_updates_next_run(mock_send):
    SessionLocal = _session_factory()
    settings = _settings()
    eng = SchedulerEngine(SessionLocal, settings)

    run_at = datetime.now(timezone.utc) + timedelta(seconds=10)
    db = SessionLocal()
    try:
        t = task_service.create_task(
            db,
            TaskCreate(
                title="s2",
                message="m2",
                task_type="interval",
                run_at=run_at,
                interval_seconds=3600,
            ),
        )
        tid = t.id
    finally:
        db.close()

    eng.execute_task(tid)
    mock_send.assert_called_once()
    db = SessionLocal()
    try:
        row = task_service.get_task(db, tid)
        assert row is not None
        assert row.status == "scheduled"
        assert normalize_utc(row.run_at_utc) > normalize_utc(run_at)
    finally:
        db.close()


@patch("app.scheduler.engine.send_gotify_message")
def test_execute_cron_advances_or_completes(mock_send):
    SessionLocal = _session_factory()
    settings = _settings()
    eng = SchedulerEngine(SessionLocal, settings)

    run_at = datetime(2026, 4, 6, 9, 0, 0, tzinfo=timezone.utc)
    db = SessionLocal()
    try:
        t = task_service.create_task(
            db,
            TaskCreate(
                title="s3",
                message="m3",
                task_type="cron",
                run_at=run_at,
                cron_expr="0 9 * * 1-5",
            ),
        )
        tid = t.id
    finally:
        db.close()

    eng.execute_task(tid)
    mock_send.assert_called_once()
    db = SessionLocal()
    try:
        row = task_service.get_task(db, tid)
        assert row is not None
        assert row.status in ("scheduled", "completed")
    finally:
        db.close()


@patch("app.integrations.gotify.httpx.Client")
def test_gotify_client_posts(mock_client_cls):
    from app.integrations.gotify import send_gotify_message

    settings = Settings(
        gotify_url="http://example.com",
        gotify_token="tok",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_inner = MagicMock()
    mock_inner.post.return_value = mock_resp
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_inner
    mock_cm.__exit__.return_value = None
    mock_client_cls.return_value = mock_cm

    send_gotify_message(settings, title="T", message="M")
    mock_inner.post.assert_called_once()
