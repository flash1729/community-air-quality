from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.timeutils import as_utc


@dataclass
class Place:
    name: str
    country: str
    country_code: str
    latitude: float
    longitude: float
    timezone: str


@dataclass
class ForecastPoint:
    parameter: str
    value: float
    unit: str
    forecast_for: datetime
    kind: str


@dataclass
class WeatherObservation:
    temperature_c: float | None
    humidity_percent: float | None
    wind_speed_kmh: float | None
    wind_direction_deg: float | None
    precipitation_mm: float | None
    recorded_at: datetime
    source: str = "open-meteo"
    kind: str = "model"


class OpenMeteoError(RuntimeError):
    pass


# Open-Meteo reports carbon monoxide in µg/m³. This app stores CO in mg/m³.
AQ_FIELDS = {
    "pm2_5": ("pm25", "µg/m³", 1.0),
    "pm10": ("pm10", "µg/m³", 1.0),
    "carbon_monoxide": ("co", "mg/m³", 0.001),
    "nitrogen_dioxide": ("no2", "µg/m³", 1.0),
    "sulphur_dioxide": ("so2", "µg/m³", 1.0),
    "ozone": ("o3", "µg/m³", 1.0),
}
WEATHER_FIELDS = {
    "temperature_2m": ("temperature", "°C", 1.0),
    "relative_humidity_2m": ("humidity", "%", 1.0),
    "wind_speed_10m": ("wind_speed", "km/h", 1.0),
    "precipitation": ("precipitation", "mm", 1.0),
}


class OpenMeteoClient:
    def __init__(
        self,
        forecast_url: str,
        client: httpx.Client,
        air_quality_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality",
    ):
        self.forecast_url = forecast_url
        self.air_quality_url = air_quality_url
        self.client = client

    def geocode(self, name: str) -> list[Place]:
        response = self.client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 5, "language": "en", "format": "json"},
        )
        if response.status_code >= 400:
            raise OpenMeteoError(f"Open-Meteo geocoding failed with status {response.status_code}.")
        places: list[Place] = []
        for item in (response.json() or {}).get("results") or []:
            if item.get("latitude") is None or item.get("longitude") is None or not item.get("name"):
                continue
            places.append(
                Place(
                    name=item["name"],
                    country=item.get("country") or "",
                    country_code=(item.get("country_code") or "").upper(),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    timezone=item.get("timezone") or "UTC",
                )
            )
        return places

    def current_weather(self, latitude: float, longitude: float) -> WeatherObservation:
        response = self.client.get(
            self.forecast_url,
            params={
                "latitude": f"{latitude:.4f}",
                "longitude": f"{longitude:.4f}",
                "current": ",".join(
                    [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "wind_speed_10m",
                        "wind_direction_10m",
                        "precipitation",
                    ]
                ),
                "wind_speed_unit": "kmh",
                "timezone": "UTC",
            },
        )
        if response.status_code >= 400:
            raise OpenMeteoError(f"Open-Meteo request failed with status {response.status_code}.")
        current = (response.json() or {}).get("current") or {}
        stamp = current.get("time")
        if not stamp:
            raise OpenMeteoError("Open-Meteo response did not include a timestamp.")
        recorded_at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        return WeatherObservation(
            temperature_c=_number(current.get("temperature_2m")),
            humidity_percent=_number(current.get("relative_humidity_2m")),
            wind_speed_kmh=_number(current.get("wind_speed_10m")),
            wind_direction_deg=_number(current.get("wind_direction_10m")),
            precipitation_mm=_number(current.get("precipitation")),
            recorded_at=as_utc(recorded_at),
        )

    def air_quality_forecast(self, latitude: float, longitude: float) -> list[ForecastPoint]:
        response = self.client.get(
            self.air_quality_url,
            params={
                "latitude": f"{latitude:.4f}",
                "longitude": f"{longitude:.4f}",
                "hourly": ",".join(AQ_FIELDS),
                "forecast_days": 3,
                "timezone": "UTC",
            },
        )
        if response.status_code >= 400:
            raise OpenMeteoError(f"Open-Meteo air-quality request failed with status {response.status_code}.")
        return parse_hourly_payload((response.json() or {}).get("hourly") or {}, AQ_FIELDS, "air_quality")

    def hourly_weather(self, latitude: float, longitude: float) -> list[ForecastPoint]:
        response = self.client.get(
            self.forecast_url,
            params={
                "latitude": f"{latitude:.4f}",
                "longitude": f"{longitude:.4f}",
                "hourly": ",".join(WEATHER_FIELDS),
                "forecast_days": 3,
                "wind_speed_unit": "kmh",
                "timezone": "UTC",
            },
        )
        if response.status_code >= 400:
            raise OpenMeteoError(f"Open-Meteo weather forecast failed with status {response.status_code}.")
        return parse_hourly_payload((response.json() or {}).get("hourly") or {}, WEATHER_FIELDS, "weather")


def parse_hourly_payload(
    hourly: dict,
    fields: dict[str, tuple[str, str, float]],
    kind: str,
) -> list[ForecastPoint]:
    times = hourly.get("time") or []
    points: list[ForecastPoint] = []
    for provider_name, (parameter, unit, factor) in fields.items():
        values = hourly.get(provider_name) or []
        for index, stamp in enumerate(times):
            if index >= len(values):
                break
            number = _number(values[index])
            if number is None or not stamp:
                continue
            points.append(
                ForecastPoint(
                    parameter=parameter,
                    value=round(number * factor, 4),
                    unit=unit,
                    forecast_for=_parse_time(stamp),
                    kind=kind,
                )
            )
    return points


def _parse_time(stamp: str) -> datetime:
    recorded_at = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
    return as_utc(recorded_at)


def _number(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
