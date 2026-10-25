"""European Air Quality Index (EEA 2021) calculation.

Based on European Environment Agency Air Quality Index (2021).
Uses 6-band system (Good, Fair, Moderate, Poor, Very Poor, Extremely Poor).
"""

from __future__ import annotations

from .base import (
    AQICalculator,
    AQIResult,
    CategoryMetadata,
    PollutantReading,
    SubIndexResult,
)

METHODOLOGY_NAME = "European"
METHODOLOGY_VERSION = "EEA-AQI-2021"

# EEA bands: (min_concentration, max_concentration, band_number)
# Band numbers: 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor, 6=Extremely Poor

PM25_BANDS = [
    (0, 10, 1),
    (10, 20, 2),
    (20, 25, 3),
    (25, 50, 4),
    (50, 75, 5),
    (75, float('inf'), 6),
]

PM10_BANDS = [
    (0, 20, 1),
    (20, 40, 2),
    (40, 50, 3),
    (50, 100, 4),
    (100, 150, 5),
    (150, float('inf'), 6),
]

NO2_BANDS = [
    (0, 40, 1),
    (40, 90, 2),
    (90, 120, 3),
    (120, 230, 4),
    (230, 340, 5),
    (340, float('inf'), 6),
]

O3_BANDS = [
    (0, 50, 1),
    (50, 100, 2),
    (100, 130, 3),
    (130, 240, 4),
    (240, 380, 5),
    (380, float('inf'), 6),
]

SO2_BANDS = [
    (0, 100, 1),
    (100, 200, 2),
    (200, 350, 3),
    (350, 500, 4),
    (500, 750, 5),
    (750, float('inf'), 6),
]

CO_BANDS = [  # mg/m³
    (0, 4, 1),
    (4, 7, 2),
    (7, 10, 3),
    (10, 20, 4),
    (20, 30, 5),
    (30, float('inf'), 6),
]

BAND_NAMES = [
    "Good",
    "Fair",
    "Moderate",
    "Poor",
    "Very Poor",
    "Extremely Poor",
]

DISPLAY_NAME = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "so2": "SO2",
    "o3": "O3",
    "co": "CO",
}

CANONICAL_UNIT = {
    "pm25": "µg/m³",
    "pm10": "µg/m³",
    "no2": "µg/m³",
    "so2": "µg/m³",
    "o3": "µg/m³",
    "co": "mg/m³",
}


def get_band(concentration: float, bands) -> int:
    """Determine EEA band for a concentration."""
    for min_c, max_c, band in bands:
        if min_c <= concentration < max_c:
            return band
    # Handle values at or above infinity threshold
    return bands[-1][2]


def band_to_aqi(band: int) -> int:
    """Map EEA band (1-6) to AQI value for gauge display."""
    return band * 25


class EuropeanAQICalculator:
    """European Air Quality Index (EEA 2021) calculator."""

    @property
    def methodology_name(self) -> str:
        return METHODOLOGY_NAME

    @property
    def methodology_version(self) -> str:
        return METHODOLOGY_VERSION

    def calculate(self, readings: list[PollutantReading]) -> AQIResult:
        """Calculate European AQI from averaged pollutant concentrations."""
        worst_band = 0
        sub_indices: list[SubIndexResult] = []
        dominant_pollutants: list[str] = []

        for reading in readings:
            if reading.concentration is None or reading.concentration < 0:
                continue

            band = None
            if reading.parameter == "pm25":
                band = get_band(reading.concentration, PM25_BANDS)
            elif reading.parameter == "pm10":
                band = get_band(reading.concentration, PM10_BANDS)
            elif reading.parameter == "no2":
                band = get_band(reading.concentration, NO2_BANDS)
            elif reading.parameter == "o3":
                band = get_band(reading.concentration, O3_BANDS)
            elif reading.parameter == "so2":
                band = get_band(reading.concentration, SO2_BANDS)
            elif reading.parameter == "co":
                band = get_band(reading.concentration, CO_BANDS)

            if band is not None:
                aqi_value = band_to_aqi(band)
                sub_indices.append(
                    SubIndexResult(
                        parameter=reading.parameter,
                        display_name=DISPLAY_NAME[reading.parameter],
                        sub_index=aqi_value,
                        concentration_used=reading.concentration,
                        unit=CANONICAL_UNIT[reading.parameter],
                        averaging_period=reading.averaging_period,
                        coverage_hours=None,
                    )
                )

                if band > worst_band:
                    worst_band = band
                    dominant_pollutants = [DISPLAY_NAME[reading.parameter]]
                elif band == worst_band:
                    dominant_pollutants.append(DISPLAY_NAME[reading.parameter])

        if worst_band == 0:
            return AQIResult(
                available=False,
                aqi=None,
                category=None,
                reason="AQI is unavailable. No valid pollutant measurements found.",
                methodology=METHODOLOGY_NAME,
                methodology_version=METHODOLOGY_VERSION,
            )

        aqi_value = band_to_aqi(worst_band)
        category = BAND_NAMES[worst_band - 1]

        return AQIResult(
            available=True,
            aqi=aqi_value,
            category=category,
            dominant_pollutants=dominant_pollutants,
            sub_indices=sub_indices,
            methodology=METHODOLOGY_NAME,
            methodology_version=METHODOLOGY_VERSION,
        )

    def get_category_metadata(self) -> list[CategoryMetadata]:
        """Return European AQI category definitions."""
        from .categories import EUROPEAN_CATEGORIES
        return EUROPEAN_CATEGORIES
