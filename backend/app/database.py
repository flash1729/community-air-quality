from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from app.models import Base, Location
from app.seed import seed_sample_data


def ensure_sqlite_path(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    path = database_url.removeprefix("sqlite:///")
    if not path or path == ":memory:":
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(database_url: str):
    ensure_sqlite_path(database_url)
    sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args)
    if sqlite:

        @event.listens_for(engine, "connect")
        def _enable_sqlite_wal(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with factory() as session:
        count = session.scalar(select(func.count()).select_from(Location))
        if not count:
            seed_sample_data(session)
            session.commit()
    return factory
