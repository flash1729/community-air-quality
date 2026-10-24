"""Bundled sample dataset so the dashboard runs before an OpenAQ key is added.

Values are synthetic. They follow realistic ranges so CPCB calculation can be
demonstrated, and they are labeled source='sample' everywhere they appear.
"""

from __future__ import annotations

import math
from datetime import timedelta

from sqlalchemy.orm import Session

from app.aqi import CANONICAL_UNIT
from app.cities import POPULAR_CITIES
from app.models import Location, Measurement, Sensor, Station, WeatherRecord
from app.timeutils import db_time, hour_floor, utcnow

# base, amplitude in canonical units (µg/m³, CO in mg/m³)
PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    "very_poor": {
        "pm25": (165, 22),
        "pm10": (280, 30),
        "no2": (78, 10),
        "so2": (22, 4),
        "co": (1.6, 0.25),
        "o3": (48, 10),
    },
    "severe_pm": {
        "pm25": (280, 20),
        "pm10": (450, 20),
        "no2": (90, 12),
        "so2": (28, 5),
        "co": (1.9, 0.3),
        "o3": (55, 12),
    },
    "poor": {
        "pm25": (108, 14),
        "pm10": (200, 22),
        "no2": (62, 8),
        "so2": (18, 3),
        "co": (1.2, 0.2),
        "o3": (52, 10),
    },
    "moderate": {
        "pm25": (74, 10),
        "pm10": (140, 16),
        "no2": (48, 7),
        "so2": (14, 3),
        "co": (0.9, 0.15),
        "o3": (60, 12),
    },
    "satisfactory": {
        "pm25": (42, 7),
        "pm10": (78, 10),
        "no2": (30, 5),
        "so2": (9, 2),
        "co": (0.6, 0.1),
        "o3": (46, 8),
    },
    "partial_no_pm": {
        "co": (0.7, 0.1),
        "o3": (58, 8),
    },
}

SAMPLE_WEATHER = {
    "New Delhi": (26.0, 38, 12.0, 300, 0.0),
    "Mumbai": (30.0, 72, 16.0, 240, 0.2),
    "Bengaluru": (24.0, 60, 14.0, 270, 0.0),
    "Kolkata": (29.0, 74, 10.0, 180, 0.4),
    "Chennai": (31.0, 70, 18.0, 90, 0.1),
    "Hyderabad": (28.0, 48, 13.0, 280, 0.0),
    "Pune": (27.0, 46, 12.0, 290, 0.0),
    "Ahmedabad": (32.0, 35, 15.0, 320, 0.0),
}


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def _hourly_value(base: float, amplitude: float, index: int, phase: float) -> float:
    raw = base + amplitude * math.sin((index + phase) * math.pi / 12)
    return round(max(0.05, raw), 3)


def seed_sample_data(session: Session, now=None) -> None:
    moment = hour_floor(now or utcnow())
    fetched_at = now or utcnow()
    for city in POPULAR_CITIES:
        location = Location(
            name=city["name"],
            city=city["city"],
            country=city["country"],
            latitude=city["latitude"],
            longitude=city["longitude"],
            timezone=city["timezone"],
            is_popular=True,
        )
        session.add(location)
        session.flush()

        for station_index, station_info in enumerate(city["stations"]):
            profile = PROFILES[station_info["profile"]]
            station = Station(
                location_id=location.id,
                provider="sample",
                external_id=f"sample-{_slug(city['name'])}-{_slug(station_info['name'])}",
                name=station_info["name"],
                latitude=station_info["latitude"],
                longitude=station_info["longitude"],
                is_monitor=True,
            )
            session.add(station)
            session.flush()

            for parameter, (base, amplitude) in profile.items():
                unit = CANONICAL_UNIT[parameter]
                sensor = Sensor(
                    station_id=station.id,
                    external_id=f"{station.external_id}-{parameter}",
                    parameter=parameter,
                    unit=unit,
                )
                session.add(sensor)
                session.flush()
                phase = (station_index * 3) + (len(parameter) * 1.7)
                for hour_index in range(48):
                    measured_at = moment - timedelta(hours=47 - hour_index)
                    session.add(
                        Measurement(
                            sensor_id=sensor.id,
                            value=_hourly_value(base, amplitude, hour_index, phase),
                            unit=unit,
                            measured_at=db_time(measured_at),
                            fetched_at=db_time(fetched_at),
                            source="sample",
                            averaging_period="1h",
                        )
                    )

        temperature, humidity, wind, direction, rain = SAMPLE_WEATHER[city["name"]]
        session.add(
            WeatherRecord(
                location_id=location.id,
                temperature_c=temperature,
                humidity_percent=humidity,
                wind_speed_kmh=wind,
                wind_direction_deg=direction,
                precipitation_mm=rain,
                recorded_at=db_time(moment),
                fetched_at=db_time(fetched_at),
                source="sample",
                kind="sample",
            )
        )
