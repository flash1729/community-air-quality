"""US EPA Air Quality Index calculation.

Based on EPA Technical Assistance Document (September 2018).
Breakpoints verified against official EPA tables.
"""

from __future__ import annotations

from .base import (
    AQICalculator,
    AQIResult,
    CategoryMetadata,
    PollutantReading,
    SubIndexResult,
    linear_interpolation,
    truncate_concentration,
)

METHODOLOGY_NAME = "US-EPA"
METHODOLOGY_VERSION = "US-EPA-AQI-2016"

# EPA breakpoints from official tables
# Format: (concentration_low, concentration_high, index_low, index_high)

PM25_BREAKPOINTS = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 504, 301, 400),
    (505, 604, 401, 500),
]

# Ozone 8-hour (ppm) - only valid up to 0.200
O3_8H_BREAKPOINTS = [
    (0.000, 0.054, 0, 50),
    (0.055, 0.070, 51, 100),
    (0.071, 0.085, 101, 150),
    (0.086, 0.105, 151, 200),
    (0.106, 0.200, 201, 300),
]

# Ozone 1-hour (ppm) - used when 8h > 0.200 OR 1h > 0.125
O3_1H_BREAKPOINTS = [
    (0.125, 0.164, 101, 150),
    (0.165, 0.204, 151, 200),
    (0.205, 0.404, 201, 300),
    (0.405, 0.504, 301, 400),
    (0.505, 0.604, 401, 500),
]

CO_BREAKPOINTS = [  # ppm
    (0.0, 4.4, 0, 50),
    (4.5, 9.4, 51, 100),
    (9.5, 12.4, 101, 150),
    (12.5, 15.4, 151, 200),
    (15.5, 30.4, 201, 300),
    (30.5, 40.4, 301, 400),
    (40.5, 50.4, 401, 500),
]

SO2_BREAKPOINTS = [  # ppb
    (0, 35, 0, 50),
    (36, 75, 51, 100),
    (76, 185, 101, 150),
    (186, 304, 151, 200),
    (305, 604, 201, 300),
    (605, 804, 301, 400),
    (805, 1004, 401, 500),
]

NO2_BREAKPOINTS = [  # ppb
    (0, 53, 0, 50),
    (54, 100, 51, 100),
    (101, 360, 101, 150),
    (361, 649, 151, 200),
    (650, 1249, 201, 300),
    (1250, 1649, 301, 400),
    (1650, 2049, 401, 500),
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
    "no2": "ppb",
    "so2": "ppb",
    "o3": "ppm",
    "co": "ppm",
}

CATEGORIES = [
    (0, 50, "Good"),
    (51, 100, "Moderate"),
    (101, 150, "Unhealthy for Sensitive Groups"),
    (151, 200, "Unhealthy"),
    (201, 300, "Very Unhealthy"),
    (301, 500, "Hazardous"),
]


def to_epa_units(concentration_canonical: float, parameter: str) -> float:
    """Convert canonical database units to EPA units (ppm or ppb) at 25°C, 1 atm.
    
    IMPORTANT: Database stores CO in mg/m³ (verified in providers/openmeteo.py line 50).
    All other pollutants are stored in µg/m³.
    """
    if parameter == "o3":
        return concentration_canonical / 1960  # µg/m³ to ppm
    elif parameter == "co":
        # Database stores CO in mg/m³, convert to ppm
        # mg/m³ * 1000 = µg/m³, then µg/m³ / 1145 = ppm
        return (concentration_canonical * 1000) / 1145  # mg/m³ to ppm
    elif parameter == "so2":
        return concentration_canonical / 2.62  # µg/m³ to ppb
    elif parameter == "no2":
        return concentration_canonical / 1.88  # µg/m³ to ppb
    elif parameter in {"pm25", "pm10"}:
        return concentration_canonical  # Already in µg/m³
    else:
        raise ValueError(f"No EPA conversion for {parameter}")


def category_for(aqi: int) -> str:
    """Return category name for AQI value."""
    bounded = min(max(aqi, 0), 500)
    for low, high, name in CATEGORIES:
        if low <= bounded <= high:
            return name
    return "Hazardous"


def calculate_sub_index(parameter: str, concentration: float, breakpoints) -> int | None:
    """Calculate sub-index using EPA linear interpolation."""
    if concentration < 0:
        return None
    truncated = truncate_concentration(concentration, 1)
    for low, high, i_low, i_high in breakpoints:
        if low <= truncated <= high:
            return linear_interpolation(truncated, low, high, i_low, i_high)
    # Above highest breakpoint
    if truncated > breakpoints[-1][1]:
        return 500
    return None


def calculate_ozone_aqi(readings: list[PollutantReading]) -> tuple[int | None, str, float | None]:
    """
    Calculate ozone AQI per EPA guidance.
    Returns (sub_index, period_used, concentration_used).
    """
    o3_8h = None
    o3_1h = None

    for reading in readings:
        if reading.parameter == "o3":
            conc_ppm = to_epa_units(reading.concentration, "o3")
            if reading.averaging_period == "8h":
                o3_8h = conc_ppm
            elif reading.averaging_period == "1h":
                o3_1h = conc_ppm

    # Use 1-hour if 8-hour > 0.200 OR 1-hour > 0.125
    if o3_8h is not None and o3_8h > 0.200:
        if o3_1h is not None:
            idx = calculate_sub_index("o3", o3_1h, O3_1H_BREAKPOINTS)
            return (idx, "1h", o3_1h)
        else:
            # Cannot calculate above 0.200 without 1-hour data
            return (None, "8h", o3_8h)

    if o3_1h is not None and o3_1h > 0.125:
        idx = calculate_sub_index("o3", o3_1h, O3_1H_BREAKPOINTS)
        return (idx, "1h", o3_1h)

    # Use 8-hour for normal range
    if o3_8h is not None and o3_8h <= 0.200:
        idx = calculate_sub_index("o3", o3_8h, O3_8H_BREAKPOINTS)
        return (idx, "8h", o3_8h)

    return (None, "", None)


class USEPAAQICalculator:
    """US EPA AQI calculator."""

    @property
    def methodology_name(self) -> str:
        return METHODOLOGY_NAME

    @property
    def methodology_version(self) -> str:
        return METHODOLOGY_VERSION

    def calculate(self, readings: list[PollutantReading]) -> AQIResult:
        """Calculate US EPA AQI from averaged pollutant concentrations."""
        sub_indices: list[SubIndexResult] = []

        # Special handling for ozone
        o3_idx, o3_period, o3_conc = calculate_ozone_aqi(readings)
        if o3_idx is not None and o3_conc is not None:
            sub_indices.append(
                SubIndexResult(
                    parameter="o3",
                    display_name="O3",
                    sub_index=o3_idx,
                    concentration_used=o3_conc,
                    unit="ppm",
                    averaging_period=o3_period,
                    coverage_hours=None,
                )
            )

        # Other pollutants
        for reading in readings:
            if reading.parameter == "o3":
                continue  # Already handled

            if reading.parameter == "pm25":
                conc = to_epa_units(reading.concentration, "pm25")
                idx = calculate_sub_index("pm25", conc, PM25_BREAKPOINTS)
                if idx is not None:
                    sub_indices.append(
                        SubIndexResult(
                            parameter="pm25",
                            display_name="PM2.5",
                            sub_index=idx,
                            concentration_used=truncate_concentration(conc, 1),
                            unit="µg/m³",
                            averaging_period=reading.averaging_period,
                            coverage_hours=None,
                        )
                    )

            elif reading.parameter == "pm10":
                conc = to_epa_units(reading.concentration, "pm10")
                idx = calculate_sub_index("pm10", conc, PM10_BREAKPOINTS)
                if idx is not None:
                    sub_indices.append(
                        SubIndexResult(
                            parameter="pm10",
                            display_name="PM10",
                            sub_index=idx,
                            concentration_used=truncate_concentration(conc, 1),
                            unit="µg/m³",
                            averaging_period=reading.averaging_period,
                            coverage_hours=None,
                        )
                    )

            elif reading.parameter == "co":
                conc = to_epa_units(reading.concentration, "co")
                idx = calculate_sub_index("co", conc, CO_BREAKPOINTS)
                if idx is not None:
                    sub_indices.append(
                        SubIndexResult(
                            parameter="co",
                            display_name="CO",
                            sub_index=idx,
                            concentration_used=truncate_concentration(conc, 1),
                            unit="ppm",
                            averaging_period=reading.averaging_period,
                            coverage_hours=None,
                        )
                    )

            elif reading.parameter == "so2":
                conc = to_epa_units(reading.concentration, "so2")
                idx = calculate_sub_index("so2", conc, SO2_BREAKPOINTS)
                if idx is not None:
                    sub_indices.append(
                        SubIndexResult(
                            parameter="so2",
                            display_name="SO2",
                            sub_index=idx,
                            concentration_used=truncate_concentration(conc, 1),
                            unit="ppb",
                            averaging_period=reading.averaging_period,
                            coverage_hours=None,
                        )
                    )

            elif reading.parameter == "no2":
                conc = to_epa_units(reading.concentration, "no2")
                idx = calculate_sub_index("no2", conc, NO2_BREAKPOINTS)
                if idx is not None:
                    sub_indices.append(
                        SubIndexResult(
                            parameter="no2",
                            display_name="NO2",
                            sub_index=idx,
                            concentration_used=truncate_concentration(conc, 1),
                            unit="ppb",
                            averaging_period=reading.averaging_period,
                            coverage_hours=None,
                        )
                    )

        if not sub_indices:
            return AQIResult(
                available=False,
                aqi=None,
                category=None,
                reason="AQI is unavailable. No valid pollutant measurements found.",
                methodology=METHODOLOGY_NAME,
                methodology_version=METHODOLOGY_VERSION,
            )

        worst = max(item.sub_index for item in sub_indices)
        dominant = [item.display_name for item in sub_indices if item.sub_index == worst]

        return AQIResult(
            available=True,
            aqi=worst,
            category=category_for(worst),
            dominant_pollutants=dominant,
            sub_indices=sub_indices,
            methodology=METHODOLOGY_NAME,
            methodology_version=METHODOLOGY_VERSION,
        )

    def get_category_metadata(self) -> list[CategoryMetadata]:
        """Return US EPA category definitions."""
        from .categories import US_EPA_CATEGORIES
        return US_EPA_CATEGORIES
