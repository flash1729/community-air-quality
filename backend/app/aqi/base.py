"""Base interfaces and utilities for AQI calculation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class PollutantReading:
    """Input to AQI calculation — already averaged and validated."""
    parameter: str  # "pm25", "pm10", "no2", "so2", "co", "o3", "nh3", "pb"
    concentration: float  # In canonical unit for this methodology
    averaging_period: str  # "1h", "8h", "24h"
    coverage_hours: int  # Number of valid hours in the averaging window


@dataclass
class SubIndexResult:
    """Result of calculating sub-index for a single pollutant."""
    parameter: str
    display_name: str
    sub_index: int
    concentration_used: float
    unit: str
    averaging_period: str
    coverage_hours: int | None  # None for methodologies that don't use coverage rules


@dataclass
class AQIResult:
    """Result of AQI calculation."""
    available: bool
    aqi: int | None
    category: str | None
    dominant_pollutants: list[str] = field(default_factory=list)
    sub_indices: list[SubIndexResult] = field(default_factory=list)
    reason: str | None = None
    methodology: str = ""
    methodology_version: str = ""


@dataclass
class CategoryMetadata:
    """Frontend rendering metadata for an AQI category."""
    name: str  # "Good", "Moderate", "Unhealthy for Sensitive Groups", etc.
    code: str  # CSS-safe: "good", "uso", "unhealthy"
    min_aqi: int
    max_aqi: int
    color: str  # Hex color code
    text_color: str  # Readable text over background
    description: str  # User-facing guidance


@runtime_checkable
class AQICalculator(Protocol):
    """Protocol for AQI calculation implementations."""

    @property
    def methodology_name(self) -> str:
        """e.g., 'CPCB', 'US-EPA', 'European'"""
        ...

    @property
    def methodology_version(self) -> str:
        """e.g., 'CPCB-NAQI-2014', 'US-EPA-AQI-2016', 'EEA-AQI-2021'"""
        ...

    def calculate(self, readings: list[PollutantReading]) -> AQIResult:
        """Calculate AQI from averaged pollutant concentrations."""
        ...

    def get_category_metadata(self) -> list[CategoryMetadata]:
        """Return category definitions for this methodology."""
        ...


def round_half_up(value: float) -> int:
    """Round using half-up strategy (0.5 rounds to 1)."""
    return int(math.floor(value + 0.5))


def linear_interpolation(
    concentration: float,
    bp_low: float,
    bp_high: float,
    i_low: int,
    i_high: int,
) -> int:
    """Standard EPA-style linear interpolation between breakpoints."""
    if bp_high == bp_low:
        return i_low
    raw = ((i_high - i_low) / (bp_high - bp_low)) * (concentration - bp_low) + i_low
    return min(500, round_half_up(raw))


def truncate_concentration(value: float, decimals: int) -> float:
    """Truncate concentration to specified decimal places."""
    multiplier = 10**decimals
    return math.floor(value * multiplier) / multiplier
