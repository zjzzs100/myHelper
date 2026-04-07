"""Step 1: verify Python can import all runtime dependencies."""


def test_import_fastapi():
    import fastapi  # noqa: F401

    assert fastapi.__version__


def test_import_sqlalchemy():
    import sqlalchemy as sa

    assert sa.__version__


def test_import_apscheduler():
    from apscheduler.schedulers.background import BackgroundScheduler  # noqa: F401


def test_import_pydantic():
    from pydantic import BaseModel  # noqa: F401


def test_import_httpx():
    import httpx  # noqa: F401
