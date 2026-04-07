from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base

# Import models so Base.metadata includes all tables on create_all.
from app.db import models as _models  # noqa: F401


def make_engine(database_url: str):
    connect_args: dict = {}
    extra = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # :memory: is a new empty DB per connection unless we pin one connection.
        if ":memory:" in database_url:
            extra["poolclass"] = StaticPool
    return create_engine(
        database_url, connect_args=connect_args, echo=False, **extra
    )


def init_db(engine) -> None:
    Base.metadata.create_all(bind=engine)


def session_factory(database_url: str):
    engine = make_engine(database_url)
    init_db(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine), engine


def get_db_session(
    SessionLocal: sessionmaker[Session],
) -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
