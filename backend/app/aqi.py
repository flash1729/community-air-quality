"""CPCB National Air Quality Index calculation.

Breakpoints follow the CPCB National AQI (2014): segmented linear sub-indices,
overall AQI = highest valid sub-index. Category names match this project's
specification (Good, Satisfactory, Moderate, Poor, Very Poor, Severe).

Severe bands are open-ended in the CPCB tables. The upper concentration paired
with sub-index 500 is the conventional ceiling used so the index can reach 500.
Concentrations above that ceiling stay at 500.

A sub-index is valid only when the averaging period and coverage match CPCB
rules. Overall AQI is available only when at least three valid sub-indices
exist and one of them is PM2.5 or PM10. Missing pollutants are omitted. They
are never treated as zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

METHODOLOGY_VERSION = "CPCB-NAQI-2014"
MIN_VALID_POLLUTANTS = 3
MIN_COVERAGE_24H = 16
MIN_COVERAGE_8H = 6

# (low concentration, high concentration, low index, high index)
# Concentrations are inclusive. Gaps between integer bands are closed by
# truncating the concentration before lookup.
BREAKPOINTS: dict[str, list[tuple[float, float, int, int]]] = {
    "pm25": [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, 380, 401, 500),
    ],
    "pm10": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 250, 101, 200),
        (251, 350, 201, 300),
        (351, 430, 301, 400),
        (431, 510, 401, 500),
    ],
    "no2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 180, 101, 200),
        (181, 280, 201, 300),
        (281, 400, 301, 400),
        (401, 800, 401, 500),
    ],
    "so2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 380, 101, 200),
        (381, 800, 201, 300),
        (801, 1600, 301, 400),
        (1601, 2000, 401, 500),
    ],
    "co": [
        (0, 1.0, 0, 50),
        (1.1, 2.0, 51, 100),
        (2.1, 10, 101, 200),
        (10.1, 17, 201, 300),
        (17.1, 34, 301, 400),
        (34.1, 50, 401, 500),
    ],
    "o3": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 168, 101, 200),
        (169, 208, 201, 300),
        (209, 748, 301, 400),
        (749, 1000, 401, 500),
    ],
    "nh3": [
        (0, 200, 0, 50),
        (201, 400, 51, 100),
        (401, 800, 101, 200),
        (801, 1200, 201, 300),
        (1201, 1800, 301, 400),
        (1801, 2400, 401, 500),
    ],
    "pb": [
        (0, 0.5, 0, 50),
        (0.6, 1.0, 51, 100),
        (1.1, 2.0, 101, 200),
        (2.1, 3.0, 201, 300),
        (3.1, 3.5, 301, 400),
        (3.6, 5.0, 401, 500),
    ],
}

CANONICAL_UNIT = {
    "pm25": "µg/m³",
    "pm10": "µg/m³",
    "no2": "µg/m³",
    "so2": "µg/m³",
    "o3": "µg/m³",
    "nh3": "µg/m³",
    "pb": "µg/m³",
    "co": "mg/m³",
}

DISPLAY_NAME = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "so2": "SO2",
    "o3": "O3",
    "co": "CO",
    "nh3": "NH3",
    "pb": "Pb",
}

POLLUTANT_ORDER = ["pm25", "pm10", "no2", "so2", "co", "o3", "nh3", "pb"]
TWENTY_FOUR_HOUR = {"pm25", "pm10", "no2", "so2", "nh3", "pb"}
EIGHT_HOUR = {"co", "o3"}

CATEGORIES: list[tuple[int, int, str]] = [
    (0, 50, "Good"),
    (51, 100, "Satisfactory"),
    (101, 200, "Moderate"),
    (201, 300, "Poor"),
    (301, 400, "Very Poor"),
    (401, 500, "Severe"),
]


def round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def truncate_concentration(parameter: str, value: float) -> float:
    if parameter in {"co", "pb"}:
        return math.floor(value * 10) / 10
    return float(math.floor(value))


def category_for(aqi: int) -> str:
    bounded = min(max(aqi, 0), 500)
    for low, high, name in CATEGORIES:
        if low <= bounded <= high:
            return name
    return "Severe"


def sub_index_for(parameter: str, concentration: float) -> int | None:
    bands = BREAKPOINTS.get(parameter)
    if bands is None or concentration < 0:
        return None
    used = truncate_concentration(parameter, concentration)
    if used < 0:
        return None
    for low, high, index_low, index_high in bands:
        if low <= used <= high:
            if high == low:
                return index_low
            raw = ((index_high - index_low) / (high - low)) * (used - low) + index_low
            return min(500, round_half_up(raw))
    if used > bands[-1][1]:
        return 500
    return None


@dataclass
class PollutantAverage:
    parameter: str
    concentration: float
    averaging_period: str
    coverage_hours: int


@dataclass
class SubIndexResult:
    parameter: str
    display_name: str
    sub_index: int
    concentration_used: float
    unit: str
    averaging_period: str
    coverage_hours: int


@dataclass
class AQIResult:
    available: bool
    aqi: int | None
    category: str | None
    dominant_pollutants: list[str] = field(default_factory=list)
    sub_indices: list[SubIndexResult] = field(default_factory=list)
    reason: str | None = None
    methodology: str = METHODOLOGY_VERSION


def _period_is_valid(reading: PollutantAverage) -> bool:
    if reading.parameter in TWENTY_FOUR_HOUR:
        return reading.averaging_period == "24h" and reading.coverage_hours >= MIN_COVERAGE_24H
    if reading.parameter == "co":
        return reading.averaging_period == "8h" and reading.coverage_hours >= MIN_COVERAGE_8H
    if reading.parameter == "o3":
        if reading.averaging_period == "8h":
            return reading.coverage_hours >= MIN_COVERAGE_8H
        if reading.averaging_period == "1h":
            return reading.coverage_hours >= 1
    return False


def calculate_aqi(readings: list[PollutantAverage]) -> AQIResult:
    """Calculate CPCB AQI from already-averaged pollutant concentrations."""
    sub_indices: list[SubIndexResult] = []
    for reading in readings:
        if reading.parameter not in BREAKPOINTS:
            continue
        if reading.concentration is None or reading.concentration < 0:
            continue
        if not _period_is_valid(reading):
            continue
        index = sub_index_for(reading.parameter, reading.concentration)
        if index is None:
            continue
        sub_indices.append(
            SubIndexResult(
                parameter=reading.parameter,
                display_name=DISPLAY_NAME[reading.parameter],
                sub_index=index,
                concentration_used=truncate_concentration(reading.parameter, reading.concentration),
                unit=CANONICAL_UNIT[reading.parameter],
                averaging_period=reading.averaging_period,
                coverage_hours=reading.coverage_hours,
            )
        )

    if not sub_indices:
        return AQIResult(
            available=False,
            aqi=None,
            category=None,
            reason=(
                "AQI is unavailable. CPCB calculation needs valid averaging periods "
                "and enough hourly coverage. Missing values were not replaced with zero."
            ),
        )

    has_pm = any(item.parameter in {"pm25", "pm10"} for item in sub_indices)
    if len(sub_indices) < MIN_VALID_POLLUTANTS or not has_pm:
        return AQIResult(
            available=False,
            aqi=None,
            category=None,
            sub_indices=sub_indices,
            reason=(
                "AQI is unavailable. CPCB requires at least three valid pollutants, "
                "including PM2.5 or PM10."
            ),
        )

    worst = max(item.sub_index for item in sub_indices)
    dominant = [item.display_name for item in sub_indices if item.sub_index == worst]
    return AQIResult(
        available=True,
        aqi=worst,
        category=category_for(worst),
        dominant_pollutants=dominant,
        sub_indices=sub_indices,
    )
