from __future__ import annotations

import json
import logging
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.aggregate import averages_at, latest_value
from app.aqi import (
    PollutantReading,
    calculate_aqi_for_location,
    get_category_for_aqi,
    get_methodology_display_name,
)
# Keep CPCB constants for backward compatibility with pollutant display
from app.aqi.cpcb import CANONICAL_UNIT, DISPLAY_NAME
from app.config import Settings
from app.guidance import guidance_for
from app.models import AQIRecord, Location, Measurement, Sensor, Station, WeatherRecord
from app.schemas import (
    AQIOut,
    HistoryOut,
    HistoryPointOut,
    LocationOut,
    OverviewOut,
    PollutantOut,
    StationOut,
    StationPollutantOut,
    SubIndexOut,
    WeatherOut,
)
from app.services.cache import provider_fetch_is_fresh, remember_provider_fetch, schedule_provider_refresh
from app.services.ingest import refresh_location
from app.timeutils import as_utc, db_time, hour_floor, utcnow

logger = logging.getLogger(__name__)

CARD_PARAMETERS = ["pm25", "pm10", "no2", "so2", "co", "o3"]
Series = dict[str, list[tuple]]


def search_locations(session: Session, query: str, limit: int = 20) -> list[Location]:
    statement = select(Location).order_by(Location.id.asc()).limit(limit)
    cleaned = query.strip()
    if cleaned:
        pattern = f"%{cleaned}%"
        statement = (
            select(Location)
            .where(or_(Location.name.ilike(pattern), Location.city.ilike(pattern)))
            .order_by(Location.id.asc())
            .limit(limit)
        )
    return _collapse_locations(session, list(session.scalars(statement)))


def discover_location(session: Session, query: str, geocoder) -> list[Location]:
    """Find a city that is not in the seeded list and store it for an OpenAQ fetch."""
    cleaned = query.strip()
    if len(cleaned) < 3:
        return []
    try:
        places = geocoder.geocode(cleaned)
    except Exception as exc:
        logger.warning("Geocoding failed for %s: %s", cleaned, exc)
        return []
    place = _choose_place(cleaned, places)
    if place is None:
        return []
    existing = _same_place(session, place.name, place.latitude, place.longitude)
    if existing is not None:
        return [existing]
    location = Location(
        name=place.name,
        city=place.name,
        country=place.country or "Unknown",
        country_code=place.country_code,  # ADD THIS
        latitude=place.latitude,
        longitude=place.longitude,
        timezone=place.timezone,
        is_popular=False,
    )
    session.add(location)
    session.flush()
    return [location]


def _choose_place(query: str, places):
    query_key = query.strip().lower()
    matches = [
        place
        for place in places
        if place.name.lower() == query_key or place.name.lower().startswith(query_key)
    ]
    if not matches:
        return None
    india = [place for place in matches if place.country_code == "IN"]
    exact = [place for place in (india or matches) if place.name.lower() == query_key]
    return (exact or india or matches)[0]


def preferred_location(session: Session, location: Location) -> Location:
    """Use the copy of a city that already has readings when search created duplicates."""
    siblings = _same_place_rows(session, location.name, location.latitude, location.longitude)
    if location not in siblings:
        siblings.append(location)
    ranked = sorted(siblings, key=lambda item: (-_measurement_count(session, item.id), item.id))
    return ranked[0]


def _same_place(session: Session, name: str, latitude: float, longitude: float) -> Location | None:
    rows = _same_place_rows(session, name, latitude, longitude)
    if not rows:
        return None
    return sorted(rows, key=lambda item: (-_measurement_count(session, item.id), item.id))[0]


def _same_place_rows(session: Session, name: str, latitude: float, longitude: float) -> list[Location]:
    rows = session.scalars(select(Location)).all()
    found = []
    for location in rows:
        same_name = location.name.casefold() == name.casefold()
        same_spot = abs(location.latitude - latitude) < 0.05 and abs(location.longitude - longitude) < 0.05
        if same_name or same_spot:
            found.append(location)
    return found


def _collapse_locations(session: Session, rows: list[Location]) -> list[Location]:
    chosen: list[Location] = []
    seen: set[int] = set()
    for location in rows:
        preferred = preferred_location(session, location)
        if preferred.id in seen:
            continue
        seen.add(preferred.id)
        chosen.append(preferred)
    return chosen


def get_location(session: Session, location_id: int) -> Location | None:
    return session.get(Location, location_id)


def location_out(location: Location) -> LocationOut:
    return LocationOut(
        id=location.id,
        name=location.name,
        city=location.city,
        country=location.country,
        country_code=location.country_code,
        latitude=location.latitude,
        longitude=location.longitude,
        timezone=location.timezone,
        is_popular=location.is_popular,
    )


def build_overview(
    session: Session,
    location: Location,
    settings: Settings,
    openaq=None,
    weather_client=None,
    history_hours: int = 48,
    refresh_when_stale: bool = False,
) -> tuple[OverviewOut, bool]:
    """Return the dashboard payload and whether a provider refresh failed."""
    warnings: list[str] = []
    refresh_failed = False
    now = utcnow()
    if openaq is not None and _should_fetch(session, location.id, settings, now, refresh_when_stale):
        has_live = _has_live_readings(session, location.id)
        if has_live and refresh_when_stale:
            if schedule_provider_refresh(session, location.id, settings):
                warnings.append("Stored readings are on screen while a newer fetch runs in the background.")
        else:
            try:
                refresh_location(session, location, openaq, weather_client)
                remember_provider_fetch(session, location.id, settings.cache_ttl_minutes, now)
                session.commit()
            except Exception as exc:
                session.rollback()
                remember_provider_fetch(session, location.id, settings.cache_ttl_minutes, now)
                session.commit()
                refresh_failed = True
                if _measurement_count(session, location.id) > 0:
                    warnings.append("OpenAQ could not be reached. The last stored readings are shown and marked stale.")
                else:
                    warnings.append("OpenAQ could not be reached for this city. No stored readings are available yet.")
                logger.warning("Provider refresh failed for %s: %s", location.name, exc)

    stations = list(
        session.scalars(select(Station).where(Station.location_id == location.id).order_by(Station.name))
    )
    loaded = {station.id: _load_series(session, station.id) for station in stations}
    stations = _prefer_live_stations(stations, loaded)
    station_payloads = [
        _station_out(session, station, loaded[station.id], now, location) for station in stations
    ]
    summary = _choose_summary(stations, loaded)
    summary_payload = next((item for item in station_payloads if summary and item.id == summary.id), None)
    series = loaded.get(summary.id, {}) if summary else {}
    aqi = summary_payload.aqi if summary_payload else _empty_aqi("No monitoring data is stored for this location.")
    pollutants = _pollutant_cards(series, now, aqi)
    history = _history(location, summary, series, history_hours, now)
    weather = _latest_weather(session, location.id)
    origin = summary.provider if summary else "unavailable"
    if origin == "sample":
        warnings.insert(
            0,
            "This city is configured with sample readings. Choose Refresh data to load live stations.",
        )
    freshness = _freshness(series, now, settings.stale_after_minutes, refresh_failed)
    health = guidance_for(aqi.category) if aqi.available else None
    sources = _sources(origin, weather, aqi.methodology, location.country)
    overview = OverviewOut(
        location=location_out(location),
        freshness=freshness,
        data_origin=origin if origin in {"sample", "openaq"} else "unavailable",
        warnings=warnings,
        summary_station=summary_payload,
        aqi=aqi,
        pollutants=pollutants,
        health=health,
        weather=weather,
        stations=station_payloads,
        history=history,
        sources=sources,
    )
    return overview, refresh_failed


def station_detail(session: Session, station_id: int) -> StationOut | None:
    station = session.get(Station, station_id)
    if station is None:
        return None
    location = session.get(Location, station.location_id)
    if location is None:
        return None
    series = _load_series(session, station.id)
    return _station_out(session, station, series, utcnow(), location)


def location_stations(session: Session, location_id: int) -> list[StationOut] | None:
    location = session.get(Location, location_id)
    if location is None:
        return None
    stations = list(session.scalars(select(Station).where(Station.location_id == location_id).order_by(Station.name)))
    loaded = {station.id: _load_series(session, station.id) for station in stations}
    stations = _prefer_live_stations(stations, loaded)
    now = utcnow()
    return [_station_out(session, station, loaded[station.id], now, location) for station in stations]


def _has_live_readings(session: Session, location_id: int) -> bool:
    count = session.scalar(
        select(func.count(Measurement.id))
        .join(Sensor, Sensor.id == Measurement.sensor_id)
        .join(Station, Station.id == Sensor.station_id)
        .where(Station.location_id == location_id, Station.provider == "openaq")
    )
    return bool(count)


def _measurement_count(session: Session, location_id: int) -> int:
    return session.scalar(
        select(func.count(Measurement.id))
        .join(Sensor, Sensor.id == Measurement.sensor_id)
        .join(Station, Station.id == Sensor.station_id)
        .where(Station.location_id == location_id)
    ) or 0


def _should_fetch(session: Session, location_id: int, settings: Settings, now, refresh_when_stale: bool) -> bool:
    if provider_fetch_is_fresh(session, location_id, settings.cache_ttl_minutes, now):
        return False
    if _measurement_count(session, location_id) == 0:
        return True
    return refresh_when_stale


def _load_series(session: Session, station_id: int) -> Series:
    rows = session.execute(
        select(Sensor.parameter, Measurement.measured_at, Measurement.value, Measurement.source)
        .join(Measurement, Measurement.sensor_id == Sensor.id)
        .where(Sensor.station_id == station_id, Measurement.averaging_period == "1h")
        .order_by(Measurement.measured_at.asc())
    ).all()
    series: Series = {}
    for parameter, measured_at, value, source in rows:
        series.setdefault(parameter, []).append((as_utc(measured_at), float(value), source))
    return series


def _values_only(series: Series) -> dict[str, list[tuple]]:
    return {
        parameter: [(measured_at, value) for measured_at, value, _source in points]
        for parameter, points in series.items()
    }


def _prefer_live_stations(stations: list[Station], loaded: dict[int, Series]) -> list[Station]:
    """Hide the bundled sample stations once real OpenAQ readings exist."""
    live = [station for station in stations if station.provider == "openaq" and loaded.get(station.id)]
    return live or stations


def _choose_summary(stations: list[Station], loaded: dict[int, Series]) -> Station | None:
    best: Station | None = None
    best_score = -1
    for station in stations:
        parameters = set(loaded.get(station.id, {}))
        if not parameters:
            continue
        score = len(parameters)
        if "pm25" in parameters or "pm10" in parameters:
            score += 10
        if station.provider == "openaq":
            score += 5
        if score > best_score:
            best = station
            best_score = score
    return best


def _station_out(session: Session, station: Station, series: Series, now, location: Location) -> StationOut:
    values = _values_only(series)
    averages = averages_at(values, now)
    # Convert to PollutantReading format
    readings = [
        PollutantReading(
            parameter=avg.parameter,
            concentration=avg.concentration,
            averaging_period=avg.averaging_period,
            coverage_hours=avg.coverage_hours,
        )
        for avg in averages
    ]
    result = calculate_aqi_for_location(readings, location.country_code)
    calculated_at = _latest_timestamp(series)
    aqi = _aqi_out(result, calculated_at, station)
    _remember_aqi(session, station, aqi)
    pollutants = []
    for parameter in _parameter_list(series):
        points = series.get(parameter) or []
        latest = latest_value([(item[0], item[1]) for item in points], now)
        if latest is None:
            pollutants.append(
                StationPollutantOut(
                    parameter=parameter,
                    display_name=DISPLAY_NAME[parameter],
                    value=None,
                    unit=CANONICAL_UNIT[parameter],
                    measured_at=None,
                    source=None,
                )
            )
            continue
        measured_at, value = latest
        source = points[-1][2] if points else None
        pollutants.append(
            StationPollutantOut(
                parameter=parameter,
                display_name=DISPLAY_NAME[parameter],
                value=round(value, 3),
                unit=CANONICAL_UNIT[parameter],
                measured_at=measured_at,
                source=source,
            )
        )
    return StationOut(
        id=station.id,
        name=station.name,
        provider=station.provider,
        latitude=station.latitude,
        longitude=station.longitude,
        is_monitor=station.is_monitor,
        aqi=aqi,
        pollutants=pollutants,
    )


def _parameter_list(series: Series) -> list[str]:
    extras = [parameter for parameter in series if parameter not in CARD_PARAMETERS and parameter in DISPLAY_NAME]
    return CARD_PARAMETERS + extras


def _aqi_out(result, calculated_at, station: Station | None) -> AQIOut:
    """Convert AQIResult to AQIOut schema with category metadata."""
    category_style = None
    if result.available and result.aqi is not None:
        category_style = get_category_for_aqi(result.methodology, result.aqi)

    methodology_display = get_methodology_display_name(result.methodology)

    return AQIOut(
        available=result.available,
        value=result.aqi,
        category=result.category,
        category_code=category_style.code if category_style else None,
        category_color=category_style.color if category_style else None,
        category_text_color=category_style.text_color if category_style else None,
        dominant_pollutants=result.dominant_pollutants,
        calculated_at=calculated_at,
        methodology=result.methodology,
        methodology_display=methodology_display,
        source_type="observation",
        reason=result.reason,
        sub_indices=[
            _sub_index_out(item, result.methodology) for item in result.sub_indices
        ],
        station_id=station.id if station else None,
        station_name=station.name if station else None,
    )


def _sub_index_out(sub_index, methodology: str) -> SubIndexOut:
    """Convert SubIndexResult to SubIndexOut with category metadata."""
    category_style = get_category_for_aqi(methodology, sub_index.sub_index)

    return SubIndexOut(
        parameter=sub_index.parameter,
        display_name=sub_index.display_name,
        sub_index=sub_index.sub_index,
        concentration_used=sub_index.concentration_used,
        unit=sub_index.unit,
        averaging_period=sub_index.averaging_period,
        coverage_hours=sub_index.coverage_hours,
        category=category_style.name if category_style else None,
        category_code=category_style.code if category_style else None,
        category_color=category_style.color if category_style else None,
    )


def _empty_aqi(reason: str) -> AQIOut:
    return AQIOut(
        available=False,
        methodology="unavailable",
        reason=reason,
    )


def _remember_aqi(session: Session, station: Station, aqi: AQIOut) -> None:
    if aqi.calculated_at is None:
        return
    stamp = db_time(aqi.calculated_at)
    existing = session.scalar(
        select(AQIRecord.id).where(
            AQIRecord.station_id == station.id,
            AQIRecord.calculated_at == stamp,
        )
    )
    if existing:
        return
    session.add(
        AQIRecord(
            location_id=station.location_id,
            station_id=station.id,
            aqi=aqi.value,
            category=aqi.category,
            dominant_pollutant=", ".join(aqi.dominant_pollutants) or None,
            available=aqi.available,
            reason=aqi.reason,
            methodology=aqi.methodology,
            source_type=aqi.source_type,
            inputs_json=json.dumps([item.model_dump(mode="json") for item in aqi.sub_indices]),
            calculated_at=stamp,
        )
    )


def _pollutant_cards(series: Series, now, aqi: AQIOut) -> list[PollutantOut]:
    averages = {item.parameter: item for item in aqi.sub_indices}
    cards: list[PollutantOut] = []
    for parameter in _parameter_list(series):
        points = series.get(parameter) or []
        latest = latest_value([(item[0], item[1]) for item in points], now)
        used = averages.get(parameter)
        if latest is None:
            cards.append(
                PollutantOut(
                    parameter=parameter,
                    display_name=DISPLAY_NAME[parameter],
                    value=None,
                    unit=CANONICAL_UNIT[parameter],
                    status="unavailable",
                    average_used=used.concentration_used if used else None,
                    averaging_period=used.averaging_period if used else None,
                )
            )
            continue
        measured_at, value = latest
        cards.append(
            PollutantOut(
                parameter=parameter,
                display_name=DISPLAY_NAME[parameter],
                value=round(value, 3),
                unit=CANONICAL_UNIT[parameter],
                measured_at=measured_at,
                source=points[-1][2],
                status="available",
                average_used=used.concentration_used if used else None,
                averaging_period=used.averaging_period if used else None,
            )
        )
    return cards


def _history(location: Location, station: Station | None, series: Series, hours: int, now) -> HistoryOut:
    values = _values_only(series)
    end = _latest_timestamp(series) or now
    end = as_utc(end).replace(minute=0, second=0, microsecond=0)
    points: list[HistoryPointOut] = []
    for offset in range(hours - 1, -1, -1):
        moment = end - timedelta(hours=offset)
        pollutants = {
            parameter: value_at_hour(values.get(parameter, []), moment) for parameter in CARD_PARAMETERS
        }
        averages = averages_at(values, moment)
        readings = [
            PollutantReading(
                parameter=avg.parameter,
                concentration=avg.concentration,
                averaging_period=avg.averaging_period,
                coverage_hours=avg.coverage_hours,
            )
            for avg in averages
        ]
        result = calculate_aqi_for_location(readings, location.country_code)
        points.append(
            HistoryPointOut(
                measured_at=moment,
                aqi=result.aqi if result.available else None,
                category=result.category if result.available else None,
                pollutants=pollutants,
            )
        )
    return HistoryOut(
        location_id=location.id,
        station_id=station.id if station else None,
        station_name=station.name if station else None,
        hours=hours,
        points=points,
        note=(
            "Pollutant lines are hourly observations. The AQI line is calculated using "
            "the appropriate methodology for this country and stays empty until coverage "
            "rules are met. Gaps are not filled."
        ),
    )


def value_at_hour(points: list[tuple], moment) -> float | None:
    """Use the latest observation that falls inside the chart hour.

    Several Indian monitors publish the hour at minute 30. An exact timestamp
    match then leaves every pollutant empty while the rolling AQI still draws.
    """
    hour = hour_floor(moment)
    matched = [value for measured_at, value in points if hour_floor(measured_at) == hour]
    if not matched:
        return None
    return round(matched[-1], 3)


def _latest_timestamp(series: Series):
    stamps = [points[-1][0] for points in series.values() if points]
    if not stamps:
        return None
    return max(as_utc(stamp) for stamp in stamps)


def _latest_weather_row(session: Session, location_id: int) -> WeatherRecord | None:
    return session.scalar(
        select(WeatherRecord)
        .where(WeatherRecord.location_id == location_id)
        .order_by(WeatherRecord.fetched_at.desc())
        .limit(1)
    )


def _latest_weather(session: Session, location_id: int) -> WeatherOut | None:
    row = _latest_weather_row(session, location_id)
    if row is None:
        return None
    if row.source == "open-meteo":
        label = "Model estimate from Open-Meteo. Not a monitoring-station observation."
    else:
        label = "Sample weather values for the local demo. Not a live observation."
    return WeatherOut(
        temperature_c=row.temperature_c,
        humidity_percent=row.humidity_percent,
        wind_speed_kmh=row.wind_speed_kmh,
        wind_direction_deg=row.wind_direction_deg,
        precipitation_mm=row.precipitation_mm,
        recorded_at=as_utc(row.recorded_at),
        source=row.source,
        kind=row.kind,
        label=label,
    )


def _freshness(series: Series, now, stale_after_minutes: int, refresh_failed: bool) -> str:
    latest = _latest_timestamp(series)
    if latest is None:
        return "unavailable"
    if refresh_failed:
        return "stale"
    age = now - as_utc(latest)
    if age <= timedelta(minutes=stale_after_minutes):
        return "recent"
    return "stale"


def _sources(origin: str, weather: WeatherOut | None, methodology: str, country: str) -> list[str]:
    sources = []
    if origin == "openaq":
        sources.append("Station observations: OpenAQ")
    elif origin == "sample":
        sources.append("Station observations: bundled sample dataset")
    else:
        sources.append("Station observations: unavailable")

    # Dynamic methodology label
    if methodology == "CPCB":
        sources.append("Indian AQI: calculated with CPCB National AQI (2014)")
    elif methodology == "US-EPA":
        sources.append("US AQI: calculated with EPA AQI methodology (2016)")
    elif methodology == "European":
        sources.append("European AQI: calculated with EEA Air Quality Index (2021)")
    elif methodology == "unavailable":
        sources.append(f"AQI calculation unavailable for {country}")
    
    if weather is not None:
        sources.append(f"Weather: {weather.label}")
    return sources
