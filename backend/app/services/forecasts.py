from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.aqi import DISPLAY_NAME
from app.models import CacheEntry, Forecast, Location
from app.providers.openmeteo import ForecastPoint
from app.schemas import ForecastOut, ForecastPointOut
from app.timeutils import as_utc, db_time, utcnow

FORECAST_NOTE = (
    "Open-Meteo model estimate. This is not a monitoring-station observation "
    "and it is not an official CPCB AQI."
)
DISPLAY = {
    **DISPLAY_NAME,
    "temperature": "Temperature",
    "humidity": "Humidity",
    "wind_speed": "Wind speed",
    "precipitation": "Precipitation",
}


def replace_forecasts(
    session: Session,
    location: Location,
    points: list[ForecastPoint],
    ttl_minutes: int,
) -> None:
    session.execute(delete(Forecast).where(Forecast.location_id == location.id))
    fetched = utcnow()
    for point in points:
        session.add(
            Forecast(
                location_id=location.id,
                parameter=point.parameter,
                value=point.value,
                unit=point.unit,
                forecast_for=db_time(point.forecast_for),
                fetched_at=db_time(fetched),
                source="open-meteo",
                kind=point.kind,
            )
        )
    _write_cache(session, location.id, fetched, ttl_minutes)
    session.flush()


def load_forecast(session: Session, location: Location, weather, ttl_minutes: int) -> ForecastOut:
    """Return a stored model forecast. Fetch only when the cache entry is missing or expired."""
    entry = _cache_entry(session, location.id)
    now = utcnow()
    if entry is not None and as_utc(entry.expires_at) > now and _has_rows(session, location.id):
        entry.hit_count += 1
        return _payload(session, location.id, "hit", entry)

    if weather is None:
        if _has_rows(session, location.id):
            return _payload(session, location.id, "stale", entry)
        return _empty(location.id)

    try:
        points = list(weather.air_quality_forecast(location.latitude, location.longitude))
        points.extend(weather.hourly_weather(location.latitude, location.longitude))
    except Exception:
        if _has_rows(session, location.id):
            return _payload(session, location.id, "stale", entry)
        raise
    if not points:
        if _has_rows(session, location.id):
            return _payload(session, location.id, "stale", entry)
        return _empty(location.id)
    replace_forecasts(session, location, points, ttl_minutes)
    entry = _cache_entry(session, location.id)
    return _payload(session, location.id, "miss", entry)


def _write_cache(session: Session, location_id: int, fetched, ttl_minutes: int) -> None:
    key = f"forecast:{location_id}"
    entry = session.scalar(select(CacheEntry).where(CacheEntry.cache_key == key))
    expires = fetched + timedelta(minutes=ttl_minutes)
    if entry is None:
        session.add(
            CacheEntry(
                cache_key=key,
                provider="open-meteo",
                location_id=location_id,
                fetched_at=db_time(fetched),
                expires_at=db_time(expires),
                payload_ref="forecasts",
                hit_count=0,
            )
        )
        return
    entry.fetched_at = db_time(fetched)
    entry.expires_at = db_time(expires)
    entry.hit_count = 0
    entry.payload_ref = "forecasts"


def _cache_entry(session: Session, location_id: int) -> CacheEntry | None:
    return session.scalar(select(CacheEntry).where(CacheEntry.cache_key == f"forecast:{location_id}"))


def _has_rows(session: Session, location_id: int) -> bool:
    return session.scalar(select(Forecast.id).where(Forecast.location_id == location_id).limit(1)) is not None


def _empty(location_id: int) -> ForecastOut:
    return ForecastOut(
        location_id=location_id,
        source="open-meteo",
        cache="miss",
        points=[],
        note=FORECAST_NOTE,
    )


def _payload(session: Session, location_id: int, cache: str, entry: CacheEntry | None) -> ForecastOut:
    rows = session.scalars(
        select(Forecast)
        .where(Forecast.location_id == location_id)
        .order_by(Forecast.forecast_for, Forecast.kind, Forecast.parameter)
    )
    return ForecastOut(
        location_id=location_id,
        source="open-meteo",
        cache=cache,
        fetched_at=as_utc(entry.fetched_at) if entry else None,
        expires_at=as_utc(entry.expires_at) if entry else None,
        points=[
            ForecastPointOut(
                forecast_for=as_utc(row.forecast_for),
                parameter=row.parameter,
                display_name=DISPLAY.get(row.parameter, row.parameter),
                value=row.value,
                unit=row.unit,
                kind=row.kind,
            )
            for row in rows
        ],
        note=FORECAST_NOTE,
    )
