from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="India")
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    is_popular: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    stations: Mapped[list[Station]] = relationship(back_populates="location")
    weather_records: Mapped[list[WeatherRecord]] = relationship(back_populates="location")


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_station_provider_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_monitor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    location: Mapped[Location] = relationship(back_populates="stations")
    sensors: Mapped[list[Sensor]] = relationship(back_populates="station")


class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (UniqueConstraint("station_id", "parameter", name="uq_sensor_station_parameter"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    parameter: Mapped[str] = mapped_column(String(16), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    station: Mapped[Station] = relationship(back_populates="sensors")
    measurements: Mapped[list[Measurement]] = relationship(back_populates="sensor")


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "measured_at",
            "averaging_period",
            name="uq_measurement_sensor_time",
        ),
        Index("ix_measurements_sensor_time", "sensor_id", "measured_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    averaging_period: Mapped[str] = mapped_column(String(16), nullable=False, default="1h")

    sensor: Mapped[Sensor] = relationship(back_populates="measurements")


class AQIRecord(Base):
    __tablename__ = "aqi_records"
    __table_args__ = (
        Index("ix_aqi_location_methodology_time", "location_id", "methodology", "calculated_at"),
        Index("ix_aqi_station_methodology_time", "station_id", "methodology", "calculated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True, index=True)
    station_id: Mapped[int | None] = mapped_column(ForeignKey("stations.id"), nullable=True, index=True)
    aqi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)  # CHANGED: 32 -> 64 for longer category names
    dominant_pollutant: Mapped[str | None] = mapped_column(String(80), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="observation")  # NEW: "observation" or "model"
    inputs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default="model")

    location: Mapped[Location] = relationship(back_populates="weather_records")


class Forecast(Base):
    """Model output. Kept out of measurements so it cannot be read as a station observation."""

    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "parameter",
            "forecast_for",
            "kind",
            name="uq_forecast_location_parameter_time",
        ),
        Index("ix_forecasts_location_time", "location_id", "forecast_for"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    parameter: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    forecast_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class CommunitySensor(Base):
    __tablename__ = "community_sensors"
    __table_args__ = (Index("ix_community_sensors_status", "status"),)

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="virtual")
    auth_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    readings: Mapped[list[CommunitySensorReading]] = relationship(back_populates="sensor")


class CommunitySensorReading(Base):
    __tablename__ = "community_sensor_readings"
    __table_args__ = (
        UniqueConstraint("sensor_id", "sequence_number", name="uq_reading_sensor_sequence"),
        Index("ix_readings_sensor_time", "sensor_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[str] = mapped_column(ForeignKey("community_sensors.id"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pm25: Mapped[float] = mapped_column(Float, nullable=False)
    pm10: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(20), nullable=False, default="accepted")

    sensor: Mapped[CommunitySensor] = relationship(back_populates="readings")
