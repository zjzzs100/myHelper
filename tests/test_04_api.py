"""
Step 4: FastAPI routes (POST/GET/DELETE /tasks/) with in-memory DB and NoOp scheduler.

Run: pytest tests/test_04_api.py -v
"""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.tasks import router as tasks_router
from app.db.models import Task  # noqa: F401 — register metadata
from app.db.session import init_db, make_engine
from app.scheduler.engine import NoOpScheduler


def _run_at_future_iso() -> str:
    t = datetime.now(timezone.utc) + timedelta(hours=1)
    return t.isoformat()


def _make_client() -> TestClient:
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    app = FastAPI()
    app.state.SessionLocal = SessionLocal
    app.state.scheduler = NoOpScheduler()
    app.include_router(tasks_router)
    return TestClient(app)


def test_post_get_delete_tasks():
    client = _make_client()
    r = client.post(
        "/tasks/",
        json={
            "title": "api-once",
            "message": "hello",
            "task_type": "once",
            "run_at": _run_at_future_iso(),
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "api-once"
    tid = data["task_id"]

    r2 = client.get("/tasks/")
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] >= 1
    assert any(x["task_id"] == tid for x in body["items"])

    r3 = client.delete(f"/tasks/{tid}")
    assert r3.status_code == 200
    assert r3.json()["status"] == "cancelled"

    r4 = client.get("/tasks/")
    assert not any(x["task_id"] == tid for x in r4.json()["items"])


def test_delete_unknown_404():
    client = _make_client()
    r = client.delete("/tasks/99999")
    assert r.status_code == 404
