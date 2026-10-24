from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.normalize import canonical_parameter, to_canonical_unit
from app.timeutils import as_utc

TRACKED_PARAMETERS = {"pm25", "pm10", "no2", "so2", "co", "o3"}
RECENT_DAYS = 14


@dataclass
class RemoteSensor:
    external_id: str
    parameter: str
    unit: str


@dataclass
class RemoteStation:
    external_id: str
    name: str
    latitude: float
    longitude: float
    is_monitor: bool
    sensors: list[RemoteSensor]


@dataclass
class HourlyObservation:
    sensor_external_id: str
    parameter: str
    value: float
    unit: str
    measured_at: datetime


class OpenAQError(RuntimeError):
    pass


class OpenAQClient:
    def __init__(self, api_key: str, base_url: str, client: httpx.Client):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = client
        self._remaining: int | None = None
        self._reset_seconds = 60

    def _wait_for_budget(self) -> None:
        # OpenAQ documents 60 requests per minute. x-ratelimit-reset is seconds until reset.
        if self._remaining is not None and self._remaining <= 1:
            time.sleep(min(max(self._reset_seconds, 1), 65))
            self._remaining = None

    def _remember_limits(self, response: httpx.Response) -> None:
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")
        if remaining is not None and remaining.isdigit():
            self._remaining = int(remaining)
        if reset is not None and reset.isdigit():
            self._reset_seconds = int(reset)

    def _get(self, path: str, params: dict) -> dict:
        for _attempt in range(3):
            self._wait_for_budget()
            response = self.client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"X-API-Key": self.api_key},
            )
            self._remember_limits(response)
            if response.status_code == 429:
                time.sleep(min(max(self._reset_seconds, 1), 65))
                self._remaining = None
                continue
            if response.status_code in {401, 403}:
                raise OpenAQError("OpenAQ rejected the API key.")
            if response.status_code >= 400:
                raise OpenAQError(f"OpenAQ request failed with status {response.status_code}.")
            return response.json()
        raise OpenAQError("OpenAQ rate limit was reached.")

    def nearby_stations(self, latitude: float, longitude: float, limit: int = 3) -> list[RemoteStation]:
        """Return the most recently reporting monitors, not the oldest location ids.

        OpenAQ orders /locations by id unless told otherwise, so the first rows near a
        city are often stations that stopped reporting years ago.
        """
        payload = self._get(
            "/locations",
            {
                "coordinates": f"{latitude:.4f},{longitude:.4f}",
                "radius": 25000,
                "limit": 100,
                "page": 1,
                "iso": "IN",
            },
        )
        results = payload.get("results") or []
        if not results:
            payload = self._get(
                "/locations",
                {
                    "coordinates": f"{latitude:.4f},{longitude:.4f}",
                    "radius": 25000,
                    "limit": 100,
                    "page": 1,
                },
            )
            results = payload.get("results") or []
        ranked: list[tuple[bool, datetime, RemoteStation]] = []
        now = datetime.now(timezone.utc)
        for item in results:
            if item.get("isMobile") is True:
                continue
            last_reported = _last_reported(item)
            if last_reported is None or now - last_reported > timedelta(days=RECENT_DAYS):
                continue
            station = _station_from_location(item)
            if station is None:
                continue
            ranked.append((bool(item.get("isMonitor")), last_reported, station))
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [station for _monitor, _when, station in ranked[:limit]]

    def hourly_observations(
        self,
        sensor: RemoteSensor,
        start: datetime,
        end: datetime,
    ) -> list[HourlyObservation]:
        payload = self._get(
            f"/sensors/{sensor.external_id}/hours",
            {
                "datetime_from": as_utc(start).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "datetime_to": as_utc(end).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "limit": 200,
                "page": 1,
            },
        )
        observations: list[HourlyObservation] = []
        for item in payload.get("results") or []:
            parsed = _parse_hourly_item(item, sensor)
            if parsed is not None:
                observations.append(parsed)
        return observations


def _last_reported(item: dict) -> datetime | None:
    stamp = (item.get("datetimeLast") or {}).get("utc")
    if not isinstance(stamp, str) or not stamp.strip():
        return None
    return as_utc(datetime.fromisoformat(stamp.strip().replace("Z", "+00:00")))


def _station_from_location(item: dict) -> RemoteStation | None:
    coordinates = item.get("coordinates") or {}
    lat = coordinates.get("latitude")
    lon = coordinates.get("longitude")
    if lat is None or lon is None:
        return None
    if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
        return None
    sensors: list[RemoteSensor] = []
    seen_parameters: set[str] = set()
    for sensor in item.get("sensors") or []:
        parameter_info = sensor.get("parameter") or {}
        parameter = canonical_parameter(parameter_info.get("name") or sensor.get("name"))
        if parameter not in TRACKED_PARAMETERS or parameter in seen_parameters or sensor.get("id") is None:
            continue
        seen_parameters.add(parameter)
        sensors.append(
            RemoteSensor(
                external_id=str(sensor["id"]),
                parameter=parameter,
                unit=(parameter_info.get("units") or "").strip(),
            )
        )
    if not sensors or item.get("id") is None:
        return None
    return RemoteStation(
        external_id=str(item.get("id")),
        name=(item.get("name") or f"Station {item.get('id')}").strip(),
        latitude=float(lat),
        longitude=float(lon),
        is_monitor=bool(item.get("isMonitor", True)),
        sensors=sensors,
    )


def _parse_hourly_item(item: dict, sensor: RemoteSensor) -> HourlyObservation | None:
    raw_value = item.get("value")
    if raw_value is None:
        return None
    try:
        numeric = float(raw_value)
    except (TypeError, ValueError):
        return None
    parameter_info = item.get("parameter") or {}
    parameter = canonical_parameter(parameter_info.get("name")) or sensor.parameter
    unit = (parameter_info.get("units") or sensor.unit or "").strip()
    converted = to_canonical_unit(parameter, numeric, unit)
    if converted is None:
        return None
    period = item.get("period") or {}
    stamp = None
    datetime_to = period.get("datetimeTo") or {}
    datetime_from = period.get("datetimeFrom") or {}
    if isinstance(datetime_to, dict):
        stamp = datetime_to.get("utc")
    if stamp is None and isinstance(datetime_from, dict):
        stamp = datetime_from.get("utc")
    coverage = item.get("coverage") or {}
    if isinstance(coverage, dict) and stamp is None:
        coverage_to = coverage.get("datetimeTo") or {}
        if isinstance(coverage_to, dict):
            stamp = coverage_to.get("utc")
    if not isinstance(stamp, str) or not stamp.strip():
        return None
    try:
        measured_at = datetime.fromisoformat(stamp.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    from app.aqi import CANONICAL_UNIT

    return HourlyObservation(
        sensor_external_id=sensor.external_id,
        parameter=parameter,
        value=converted,
        unit=CANONICAL_UNIT[parameter],
        measured_at=as_utc(measured_at),
    )
