"""Remember when a location was last sent to OpenAQ so a fresh dashboard read stays local."""

from __future__ import annotations

import logging
import threading
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app.models import CacheEntry, Location, Measurement, Sensor, Station
from app.timeutils import as_utc, db_time, utcnow

logger = logging.getLogger(__name__)
_refreshing: set[int] = set()
_refresh_lock = threading.Lock()


def provider_fetch_is_fresh(session: Session, location_id: int, ttl_minutes: int, now) -> bool:
    entry = _entry(session, location_id)
    if entry is not None and as_utc(entry.expires_at) > now:
        return True
    latest = session.scalar(
        select(Measurement.fetched_at)
        .join(Sensor, Sensor.id == Measurement.sensor_id)
        .join(Station, Station.id == Sensor.station_id)
        .where(Station.location_id == location_id, Station.provider == "openaq")
        .order_by(Measurement.fetched_at.desc())
        .limit(1)
    )
    if latest is None:
        return False
    return now - as_utc(latest) <= timedelta(minutes=ttl_minutes)


def remember_provider_fetch(session: Session, location_id: int, ttl_minutes: int, now=None) -> None:
    moment = now or utcnow()
    entry = _entry(session, location_id)
    if entry is None:
        session.add(
            CacheEntry(
                cache_key=f"openaq:{location_id}",
                provider="openaq",
                location_id=location_id,
                fetched_at=db_time(moment),
                expires_at=db_time(moment + timedelta(minutes=ttl_minutes)),
                payload_ref="measurements",
                hit_count=0,
            )
        )
    else:
        entry.fetched_at = db_time(moment)
        entry.expires_at = db_time(moment + timedelta(minutes=ttl_minutes))
        entry.hit_count = 0
    session.flush()


def schedule_provider_refresh(session: Session, location_id: int, settings) -> bool:
    """Refresh one city without blocking the dashboard response."""
    with _refresh_lock:
        if location_id in _refreshing:
            return False
        _refreshing.add(location_id)
    bind = session.get_bind()
    engine = bind.engine if isinstance(bind, Connection) else bind

    def run() -> None:
        from app.clients import open_clients
        from app.services.ingest import refresh_location

        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        db = factory()
        http = None
        try:
            http, openaq, weather = open_clients(settings)
            location = db.get(Location, location_id)
            if location is None or openaq is None:
                return
            refresh_location(db, location, openaq, weather)
            remember_provider_fetch(db, location_id, settings.cache_ttl_minutes)
            db.commit()
        except Exception:
            logger.exception("Background refresh failed for location %s", location_id)
            db.rollback()
            try:
                remember_provider_fetch(db, location_id, settings.cache_ttl_minutes)
                db.commit()
            except Exception:
                db.rollback()
        finally:
            if http is not None:
                http.close()
            db.close()
            with _refresh_lock:
                _refreshing.discard(location_id)

    threading.Thread(target=run, daemon=True, name=f"openaq-refresh-{location_id}").start()
    return True


def _entry(session: Session, location_id: int) -> CacheEntry | None:
    return session.scalar(select(CacheEntry).where(CacheEntry.cache_key == f"openaq:{location_id}"))
