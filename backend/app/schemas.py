from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LocationOut(BaseModel):
    id: int
    name: str
    city: str
    country: str
    country_code: str | None = None  # NEW
    latitude: float
    longitude: float
    timezone: str
    is_popular: bool


class LocationSearchOut(BaseModel):
    results: list[LocationOut]


class SubIndexOut(BaseModel):
    parameter: str
    display_name: str
    sub_index: int
    concentration_used: float
    unit: str
    averaging_period: str
    coverage_hours: int | None = None  # CHANGED: was int
    category: str | None = None  # NEW
    category_code: str | None = None  # NEW
    category_color: str | None = None  # NEW


class AQIOut(BaseModel):
    available: bool
    value: int | None = None
    category: str | None = None
    category_code: str | None = None  # NEW
    category_color: str | None = None  # NEW
    category_text_color: str | None = None  # NEW
    dominant_pollutants: list[str] = Field(default_factory=list)
    calculated_at: datetime | None = None
    methodology: str
    methodology_display: str | None = None  # NEW
    max_scale: int = 500  # NEW: Maximum AQI value for gauge (500 for CPCB/US EPA, 150 for European)
    source_type: str = "observation"  # NEW
    reason: str | None = None
    sub_indices: list[SubIndexOut] = Field(default_factory=list)
    station_id: int | None = None
    station_name: str | None = None


class PollutantOut(BaseModel):
    parameter: str
    display_name: str
    value: float | None = None
    unit: str
    measured_at: datetime | None = None
    source: str | None = None
    status: str
    average_used: float | None = None
    averaging_period: str | None = None


class HealthOut(BaseModel):
    category: str
    summary: str
    precautions: list[str]
    disclaimer: str


class WeatherOut(BaseModel):
    temperature_c: float | None = None
    humidity_percent: float | None = None
    wind_speed_kmh: float | None = None
    wind_direction_deg: float | None = None
    precipitation_mm: float | None = None
    recorded_at: datetime | None = None
    source: str | None = None
    kind: str
    label: str


class StationPollutantOut(BaseModel):
    parameter: str
    display_name: str
    value: float | None = None
    unit: str
    measured_at: datetime | None = None
    source: str | None = None


class StationOut(BaseModel):
    id: int
    name: str
    provider: str
    latitude: float
    longitude: float
    is_monitor: bool
    aqi: AQIOut
    pollutants: list[StationPollutantOut]


class HistoryPointOut(BaseModel):
    measured_at: datetime
    aqi: int | None = None
    category: str | None = None
    pollutants: dict[str, float | None]


class HistoryOut(BaseModel):
    location_id: int
    station_id: int | None = None
    station_name: str | None = None
    hours: int
    bucket: str = "hour"
    start: datetime | None = None
    end: datetime | None = None
    points: list[HistoryPointOut]
    note: str


class ForecastPointOut(BaseModel):
    forecast_for: datetime
    parameter: str
    display_name: str
    value: float
    unit: str
    kind: str


class ForecastOut(BaseModel):
    location_id: int
    source: str
    cache: str
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    points: list[ForecastPointOut]
    note: str


class CompareLocationOut(BaseModel):
    location: LocationOut
    freshness: str
    data_origin: str
    summary_station: str | None = None
    measured_at: datetime | None = None
    aqi: AQIOut
    pollutants: list[PollutantOut]


class CompareOut(BaseModel):
    locations: list[CompareLocationOut]
    note: str


class MeasurementOut(BaseModel):
    parameter: str
    value: float
    unit: str
    measured_at: datetime
    fetched_at: datetime
    source: str
    averaging_period: str


class MeasurementPage(BaseModel):
    station_id: int
    count: int
    limit: int
    offset: int
    results: list[MeasurementOut]


class IngestionRunOut(BaseModel):
    id: int
    provider: str
    location_id: int | None = None
    started_at: datetime
    completed_at: datetime | None = None
    status: str


class MetricsOut(BaseModel):
    popular_locations: int
    on_demand_locations: int
    measurements: int
    forecasts: int
    cache_entries: int
    cache_hits: int
    latest_ingestions: list[IngestionRunOut]
    note: str


class OverviewOut(BaseModel):
    location: LocationOut
    freshness: str
    data_origin: str
    warnings: list[str]
    summary_station: StationOut | None = None
    aqi: AQIOut
    pollutants: list[PollutantOut]
    health: HealthOut | None = None
    weather: WeatherOut | None = None
    stations: list[StationOut]
    history: HistoryOut
    sources: list[str]


class RefreshOut(BaseModel):
    location_id: int
    status: str
    message: str
    stations_updated: int = 0
    measurements_stored: int = 0


class CommunitySensorReadingOut(BaseModel):
    sensor_id: str
    sequence_number: int
    pm25: float
    pm10: float
    temperature: float | None = None
    humidity: float | None = None
    recorded_at: datetime
    received_at: datetime
    quality_status: str


class CommunitySensorOut(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    sensor_type: str
    status: str
    created_at: datetime
    last_seen: datetime | None = None
    latest_reading: CommunitySensorReadingOut | None = None


class CommunitySensorReadingSubmit(BaseModel):
    sensor_id: str
    sequence_number: int
    pm25: float
    pm10: float
    temperature: float | None = None
    humidity: float | None = None
    recorded_at: datetime


class CommunitySensorRegister(BaseModel):
    sensor_id: str
    name: str
    latitude: float
    longitude: float
    sensor_type: str = "virtual"
