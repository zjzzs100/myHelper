"""
Step 2: SQLAlchemy models + engine + create tables + CRUD smoke test.

Run: pytest tests/test_02_database.py -v
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Task
from app.db.session import init_db, make_engine


def test_create_tables_and_insert_task():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db: Session = SessionLocal()
    try:
        run_at = datetime(2026, 4, 2, 10, 0, 0, tzinfo=timezone.utc)
        t = Task(
            title="t1",
            message="hello",
            task_type="once",
            run_at_utc=run_at,
            status="scheduled",
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        assert t.id is not None
        assert t.title == "t1"
        assert t.status == "scheduled"

        row = db.execute(select(Task).where(Task.id == t.id)).scalar_one()
        assert row.message == "hello"
    finally:
        db.close()
