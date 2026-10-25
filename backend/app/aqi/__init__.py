"""Global AQI calculation engine.

Public API for calculating AQI using the appropriate methodology
based on location country code.
"""

from __future__ import annotations

from .base import AQIResult, CategoryMetadata, PollutantReading, SubIndexResult
from .categories import get_categories, get_category_for_aqi, get_max_scale
from .cpcb import (
    CANONICAL_UNIT,
    DISPLAY_NAME,
    EIGHT_HOUR,
    METHODOLOGY_VERSION,
    MIN_COVERAGE_24H,
    MIN_COVERAGE_8H,
    TWENTY_FOUR_HOUR,
    sub_index_for,
)
from .resolver import get_calculator, get_methodology_display_name, resolve_methodology

# Backward compatibility alias
PollutantAverage = PollutantReading

__all__ = [
    "calculate_aqi_for_location",
    "calculate_aqi",  # Backward compatible
    "PollutantReading",
    "PollutantAverage",  # Backward compatible
    "AQIResult",
    "SubIndexResult",
    "CategoryMetadata",
    "get_category_for_aqi",
    "get_categories",
    "get_max_scale",
    "get_methodology_display_name",
    "CANONICAL_UNIT",  # Backward compatible
    "DISPLAY_NAME",  # Backward compatible
    "METHODOLOGY_VERSION",  # Backward compatible
    "EIGHT_HOUR",  # Backward compatible
    "TWENTY_FOUR_HOUR",  # Backward compatible
    "MIN_COVERAGE_8H",  # Backward compatible
    "MIN_COVERAGE_24H",  # Backward compatible
    "sub_index_for",  # Backward compatible
]


def calculate_aqi(readings: list[PollutantReading]) -> AQIResult:
    """
    Backward-compatible CPCB-only AQI calculation.
    
    This function exists for compatibility with existing code and tests.
    New code should use calculate_aqi_for_location() which supports multiple methodologies.
    """
    from .cpcb import CPCBAQICalculator
    calculator = CPCBAQICalculator()
    return calculator.calculate(readings)


def calculate_aqi_for_location(
    readings: list[PollutantReading], country_code: str | None
) -> AQIResult:
    """
    Calculate AQI using the appropriate methodology for the given country.
    
    Args:
        readings: List of pollutant averages
        country_code: ISO 3166-1 alpha-2 country code (e.g., "IN", "US", "GB")
    
    Returns:
        AQIResult with methodology-specific calculation
    """
    methodology = resolve_methodology(country_code)

    if methodology == "unavailable":
        country_name = country_code if country_code else "this location"
        return AQIResult(
            available=False,
            aqi=None,
            category=None,
            dominant_pollutants=[],
            sub_indices=[],
            reason=f"AQI calculation is unavailable for {country_name}. Supported standards: CPCB (India), US EPA (United States), European AQI (EU/EEA countries).",
            methodology="unavailable",
            methodology_version="N/A",
        )

    calculator = get_calculator(methodology)
    if calculator is None:
        return AQIResult(
            available=False,
            aqi=None,
            category=None,
            dominant_pollutants=[],
            sub_indices=[],
            reason="Calculator not found.",
            methodology="unknown",
            methodology_version="N/A",
        )

    return calculator.calculate(readings)
