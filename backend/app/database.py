from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.models import Base, Location
from app.seed import seed_sample_data

# Names already stored before country_code existed. Only countries with an AQI
# methodology in this app are filled in. Others stay blank.
_COUNTRY_CODES = {
    "india": "IN",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "romania": "RO",
}


def ensure_sqlite_path(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    path = database_url.removeprefix("sqlite:///")
    if not path or path == ":memory:":
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _align_existing_sqlite(engine) -> None:
    """Add columns that create_all cannot add to a database from an earlier version."""
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "locations" in tables:
            columns = {column["name"] for column in inspector.get_columns("locations")}
            if "country_code" not in columns:
                connection.execute(text("ALTER TABLE locations ADD COLUMN country_code VARCHAR(2)"))
            for name, code in _COUNTRY_CODES.items():
                connection.execute(
                    text(
                        "UPDATE locations SET country_code = :code "
                        "WHERE country_code IS NULL AND lower(country) = :name"
                    ),
                    {"code": code, "name": name},
                )
        if "aqi_records" in tables:
            columns = {column["name"] for column in inspector.get_columns("aqi_records")}
            if "source_type" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE aqi_records ADD COLUMN source_type "
                        "VARCHAR(20) NOT NULL DEFAULT 'observation'"
                    )
                )


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
    _align_existing_sqlite(engine)
    with factory() as session:
        count = session.scalar(select(func.count()).select_from(Location))
        if not count:
            seed_sample_data(session)
            session.commit()
    return factory
