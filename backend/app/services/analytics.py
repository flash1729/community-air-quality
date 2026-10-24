"""History, comparison, and export. These reads use stored rows only."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.aggregate import averages_at
from app.aqi import calculate_aqi
from app.config import Settings
from app.models import Location, Measurement, Sensor, Station
from app.schemas import (
    CompareLocationOut,
    CompareOut,
    HistoryOut,
    HistoryPointOut,
    MeasurementOut,
    MeasurementPage,
)
from app.services.dashboard import (
    CARD_PARAMETERS,
    _choose_summary,
    _load_series,
    _measurement_count,
    _prefer_live_stations,
    _values_only,
    build_overview,
    get_location,
    preferred_location,
)
from app.timeutils import as_utc, db_time

HOUR_NOTE = (
    "Hourly station observations in UTC. The AQI line is a rolling CPCB calculation "
    "and stays empty until coverage rules are met. Gaps are not filled. "
    "Model forecasts are not included."
)
DAY_NOTE = (
    "Daily means of stored hourly station observations, grouped by UTC day. "
    "The AQI value is the rolling CPCB calculation at 23:00 UTC, not an average of AQI numbers. "
    "Days without coverage stay empty. Model forecasts are not included."
)
COMPARE_NOTE = (
    "Comparison uses stored station observations for each city. "
    "A city that has not been opened yet is loaded from OpenAQ on this request, then reused. "
    "Model weather and model air-quality forecasts are not mixed into these values."
)


def ranged_history(
    session: Session,
    location: Location,
    start: date,
    end: date,
    bucket: str,
) -> HistoryOut:
    summary, series = _summary_series(session, location.id)
    values = _values_only(series)
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time(23, 0), tzinfo=timezone.utc)
    if bucket == "day":
        points = _daily_points(values, start_dt, end_dt)
    else:
        points = _hourly_points(values, start_dt, end_dt)
    span_hours = max(1, int((end_dt - start_dt).total_seconds() // 3600) + 1)
    return HistoryOut(
        location_id=location.id,
        station_id=summary.id if summary else None,
        station_name=summary.name if summary else None,
        hours=span_hours,
        bucket=bucket,
        start=start_dt,
        end=end_dt,
        points=points,
        note=DAY_NOTE if bucket == "day" else HOUR_NOTE,
    )


def compare_locations(
    session: Session,
    location_ids: list[int],
    settings: Settings,
    openaq=None,
    weather_client=None,
) -> CompareOut:
    items: list[CompareLocationOut] = []
    for location_id in location_ids:
        location = get_location(session, location_id)
        if location is None:
            raise LookupError(f"Location {location_id} was not found.")
        location = preferred_location(session, location)
        had_readings = _measurement_count(session, location.id) > 0
        payload, failed = build_overview(
            session,
            location,
            settings,
            openaq=openaq,
            weather_client=weather_client,
            history_hours=1,
        )
        if payload.summary_station is None and openaq is not None and not had_readings and not failed:
            payload.aqi.reason = "OpenAQ has no recent monitoring stations near this place."
        measured_at = next((item.measured_at for item in payload.pollutants if item.measured_at), None)
        items.append(
            CompareLocationOut(
                location=payload.location,
                freshness=payload.freshness,
                data_origin=payload.data_origin,
                summary_station=payload.summary_station.name if payload.summary_station else None,
                measured_at=measured_at,
                aqi=payload.aqi,
                pollutants=payload.pollutants,
            )
        )
    return CompareOut(locations=items, note=COMPARE_NOTE)


def export_csv(session: Session, location: Location, start: datetime, end: datetime) -> str:
    rows = session.execute(
        select(
            Station.name,
            Station.provider,
            Sensor.parameter,
            Measurement.value,
            Measurement.unit,
            Measurement.measured_at,
            Measurement.fetched_at,
            Measurement.source,
            Measurement.averaging_period,
        )
        .join(Sensor, Sensor.station_id == Station.id)
        .join(Measurement, Measurement.sensor_id == Sensor.id)
        .where(
            Station.location_id == location.id,
            Measurement.measured_at >= db_time(start),
            Measurement.measured_at <= db_time(end),
        )
        .order_by(Measurement.measured_at, Station.name, Sensor.parameter)
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "location",
            "station",
            "provider",
            "parameter",
            "value",
            "unit",
            "measured_at_utc",
            "fetched_at_utc",
            "source",
            "averaging_period",
        ]
    )
    for station, provider, parameter, value, unit, measured_at, fetched_at, source, period in rows:
        writer.writerow(
            [
                location.name,
                station,
                provider,
                parameter,
                value,
                unit,
                as_utc(measured_at).strftime("%Y-%m-%dT%H:%M:%SZ"),
                as_utc(fetched_at).strftime("%Y-%m-%dT%H:%M:%SZ"),
                source,
                period,
            ]
        )
    return buffer.getvalue()


def station_measurements(
    session: Session,
    station_id: int,
    parameter: str | None,
    limit: int,
    offset: int,
) -> MeasurementPage | None:
    station = session.get(Station, station_id)
    if station is None:
        return None
    filters = [Sensor.station_id == station_id]
    if parameter:
        filters.append(Sensor.parameter == parameter)
    total = session.scalar(
        select(func.count(Measurement.id)).join(Sensor, Sensor.id == Measurement.sensor_id).where(*filters)
    ) or 0
    rows = session.execute(
        select(Measurement, Sensor.parameter)
        .join(Sensor, Sensor.id == Measurement.sensor_id)
        .where(*filters)
        .order_by(Measurement.measured_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return MeasurementPage(
        station_id=station_id,
        count=total,
        limit=limit,
        offset=offset,
        results=[
            MeasurementOut(
                parameter=parameter_name,
                value=row.value,
                unit=row.unit,
                measured_at=as_utc(row.measured_at),
                fetched_at=as_utc(row.fetched_at),
                source=row.source,
                averaging_period=row.averaging_period,
            )
            for row, parameter_name in rows
        ],
    )


def _summary_series(session: Session, location_id: int):
    stations = list(session.scalars(select(Station).where(Station.location_id == location_id).order_by(Station.name)))
    loaded = {station.id: _load_series(session, station.id) for station in stations}
    stations = _prefer_live_stations(stations, loaded)
    summary = _choose_summary(stations, loaded)
    series = loaded.get(summary.id, {}) if summary else {}
    return summary, series


def _hourly_points(values: dict, start: datetime, end: datetime) -> list[HistoryPointOut]:
    points: list[HistoryPointOut] = []
    moment = start
    while moment <= end:
        pollutants = {}
        for parameter in CARD_PARAMETERS:
            match = [value for measured_at, value in values.get(parameter, []) if as_utc(measured_at) == moment]
            pollutants[parameter] = round(match[-1], 3) if match else None
        result = calculate_aqi(averages_at(values, moment))
        points.append(
            HistoryPointOut(
                measured_at=moment,
                aqi=result.aqi if result.available else None,
                category=result.category if result.available else None,
                pollutants=pollutants,
            )
        )
        moment += timedelta(hours=1)
    return points


def _daily_points(values: dict, start: datetime, end: datetime) -> list[HistoryPointOut]:
    points: list[HistoryPointOut] = []
    day = start
    while day.date() <= end.date():
        next_day = day + timedelta(days=1)
        pollutants = {}
        for parameter in CARD_PARAMETERS:
            samples = [
                value
                for measured_at, value in values.get(parameter, [])
                if day <= as_utc(measured_at) < next_day
            ]
            pollutants[parameter] = round(sum(samples) / len(samples), 3) if samples else None
        moment = day.replace(hour=23)
        if moment > end:
            moment = end
        result = calculate_aqi(averages_at(values, moment))
        points.append(
            HistoryPointOut(
                measured_at=day,
                aqi=result.aqi if result.available else None,
                category=result.category if result.available else None,
                pollutants=pollutants,
            )
        )
        day = next_day
    return points
