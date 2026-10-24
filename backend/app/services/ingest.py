from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aqi import CANONICAL_UNIT
from app.config import get_settings
from app.models import IngestionRun, Location, Measurement, Sensor, Station, WeatherRecord
from app.providers.openaq import HourlyObservation, OpenAQClient, RemoteStation
from app.providers.openmeteo import OpenMeteoClient, WeatherObservation
from app.services.forecasts import replace_forecasts
from app.timeutils import db_time, utcnow

logger = logging.getLogger(__name__)


def refresh_location(
    session: Session,
    location: Location,
    openaq: OpenAQClient | None,
    weather: OpenMeteoClient | None,
    hours: int = 48,
) -> dict:
    """Fetch provider data for one location and store it. Existing hours are updated."""
    started = utcnow()
    run = IngestionRun(
        provider="openaq" if openaq else "none",
        location_id=location.id,
        started_at=started,
        status="running",
    )
    session.add(run)
    session.flush()

    stations_updated = 0
    measurements_stored = 0
    messages: list[str] = []
    try:
        if openaq is None:
            run.status = "skipped"
            run.error = "OPENAQ_API_KEY is not set"
            messages.append("OpenAQ key is not configured. Stored readings were left unchanged.")
        else:
            end = utcnow()
            start = end - timedelta(hours=hours)
            remote_stations = openaq.nearby_stations(location.latitude, location.longitude)
            if not remote_stations:
                messages.append("OpenAQ returned no monitoring stations near this location.")
            for remote in remote_stations:
                station = _upsert_station(session, location, remote)
                stations_updated += 1
                for sensor in remote.sensors:
                    try:
                        observations = openaq.hourly_observations(sensor, start, end)
                    except Exception as exc:
                        logger.warning("Skipping sensor %s: %s", sensor.external_id, exc)
                        continue
                    local_sensor = _upsert_sensor(session, station, sensor.external_id, sensor.parameter)
                    for observation in observations:
                        if _upsert_measurement(session, local_sensor, observation):
                            measurements_stored += 1
            run.status = "success"
        if weather is not None:
            try:
                observation = weather.current_weather(location.latitude, location.longitude)
                _store_weather(session, location, observation)
            except Exception as exc:
                logger.warning("Weather fetch failed for %s: %s", location.name, exc)
                messages.append("Weather could not be refreshed. The last stored weather is being shown.")
                if run.status == "success":
                    run.status = "partial"
            if hasattr(weather, "air_quality_forecast") and hasattr(weather, "hourly_weather"):
                try:
                    points = list(weather.air_quality_forecast(location.latitude, location.longitude))
                    points.extend(weather.hourly_weather(location.latitude, location.longitude))
                    if points:
                        replace_forecasts(session, location, points, get_settings().cache_ttl_minutes)
                except Exception as exc:
                    logger.warning("Forecast fetch failed for %s: %s", location.name, exc)
                    messages.append("The model forecast could not be refreshed. The last stored forecast is being shown.")
                    if run.status == "success":
                        run.status = "partial"
        if run.status == "running":
            run.status = "skipped"
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:500]
        raise
    finally:
        run.completed_at = utcnow()
        session.flush()

    return {
        "status": run.status,
        "message": " ".join(messages) or "Location data was refreshed.",
        "stations_updated": stations_updated,
        "measurements_stored": measurements_stored,
    }


def _upsert_station(session: Session, location: Location, remote: RemoteStation) -> Station:
    station = session.scalar(
        select(Station).where(Station.provider == "openaq", Station.external_id == remote.external_id)
    )
    if station is None:
        station = Station(
            location_id=location.id,
            provider="openaq",
            external_id=remote.external_id,
            name=remote.name,
            latitude=remote.latitude,
            longitude=remote.longitude,
            is_monitor=remote.is_monitor,
        )
        session.add(station)
    else:
        station.location_id = location.id
        station.name = remote.name
        station.latitude = remote.latitude
        station.longitude = remote.longitude
        station.is_monitor = remote.is_monitor
    session.flush()
    return station


def _upsert_sensor(session: Session, station: Station, external_id: str, parameter: str) -> Sensor:
    sensor = session.scalar(
        select(Sensor).where(Sensor.station_id == station.id, Sensor.parameter == parameter)
    )
    unit = CANONICAL_UNIT[parameter]
    if sensor is None:
        sensor = Sensor(
            station_id=station.id,
            external_id=external_id,
            parameter=parameter,
            unit=unit,
        )
        session.add(sensor)
    else:
        sensor.external_id = external_id
        sensor.unit = unit
    session.flush()
    return sensor


def _upsert_measurement(session: Session, sensor: Sensor, observation: HourlyObservation) -> bool:
    measured_at = db_time(observation.measured_at)
    existing = session.scalar(
        select(Measurement).where(
            Measurement.sensor_id == sensor.id,
            Measurement.measured_at == measured_at,
            Measurement.averaging_period == "1h",
        )
    )
    fetched_at = utcnow()
    if existing is None:
        session.add(
            Measurement(
                sensor_id=sensor.id,
                value=observation.value,
                unit=observation.unit,
                measured_at=measured_at,
                fetched_at=fetched_at,
                source="openaq",
                averaging_period="1h",
            )
        )
        return True
    existing.value = observation.value
    existing.unit = observation.unit
    existing.fetched_at = fetched_at
    existing.source = "openaq"
    return False


def _store_weather(session: Session, location: Location, observation: WeatherObservation) -> None:
    session.add(
        WeatherRecord(
            location_id=location.id,
            temperature_c=observation.temperature_c,
            humidity_percent=observation.humidity_percent,
            wind_speed_kmh=observation.wind_speed_kmh,
            wind_direction_deg=observation.wind_direction_deg,
            precipitation_mm=observation.precipitation_mm,
            recorded_at=db_time(observation.recorded_at),
            fetched_at=db_time(utcnow()),
            source=observation.source,
            kind=observation.kind,
        )
    )
