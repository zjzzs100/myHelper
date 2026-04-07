from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.tasks import router as tasks_router
from app.core.config import get_settings
from app.db.session import session_factory
from app.scheduler.engine import SchedulerEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    SessionLocal, _engine = session_factory(settings.database_url)
    app.state.SessionLocal = SessionLocal
    app.state.settings = settings
    sched = SchedulerEngine(SessionLocal, settings)
    sched.start()
    app.state.scheduler = sched
    yield
    sched.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(title="myHelper", lifespan=lifespan)
    app.include_router(tasks_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
