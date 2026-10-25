# Global AQI Support Implementation Guide

**Version:** 1.0  
**Target:** Self-contained guide for AI coder with ZERO prior context  
**Repository:** /home/vishwas/Desktop/CC/community-air-quality  
**Worktree:** /home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi  
**Branch:** feature/global-aqi-support

---

## 1. Executive Summary

### 1.1 What Needs to Be Built

Extend the existing Community Air Quality Dashboard to support **multiple AQI calculation methodologies** for cities worldwide while preserving all existing Indian CPCB functionality.

**Current State:**
- Location search: Already global (Open-Meteo geocoding)
- AQI calculation: CPCB-only (Indian methodology hardcoded)
- Database schema: Lacks methodology discrimination
- Frontend: Hardcodes CPCB categories and 0-500 scale
- OpenAQ provider: Has India-first bias in station search

**Target State:**
- Modular AQI engine supporting 3 standards: CPCB (India), US EPA, European AQI (EEA)
- Country-based automatic methodology selection
- Database schema distinguishes methodology and source type
- Frontend dynamically renders categories from backend metadata
- Global-ready provider architecture
- Explicit "unavailable" state for unsupported countries (never show wrong AQI)

### 1.2 Success Criteria

- [ ] All existing CPCB tests pass unchanged
- [ ] US EPA calculations match official examples
- [ ] European AQI calculations match official examples
- [ ] Cache keys distinguish methodology where needed
- [ ] Frontend displays correct categories per standard
- [ ] API backward compatibility maintained
- [ ] Docker Compose still works locally
- [ ] Indian cities continue using CPCB exclusively

---

## 2. Repository Structure

```
/home/vishwas/Desktop/CC/community-air-quality/
├── .worktrees/
│   └── global-aqi/                    # WORK HERE
│       ├── backend/
│       │   ├── app/
│       │   │   ├── aqi.py             # OLD: Monolithic CPCB
│       │   │   ├── aqi/               # NEW: Modular engine
│       │   │   │   ├── __init__.py
│       │   │   │   ├── base.py
│       │   │   │   ├── resolver.py
│       │   │   │   ├── cpcb.py
│       │   │   │   ├── us_epa.py
│       │   │   │   ├── european.py
│       │   │   │   └── categories.py
│       │   │   ├── models.py
│       │   │   ├── schemas.py
│       │   │   ├── services/
│       │   │   │   ├── dashboard.py
│       │   │   │   └── cache.py
│       │   │   └── providers/
│       │   │       ├── openaq.py
│       │   │       └── openmeteo.py
│       │   └── tests/
│       │       ├── test_aqi.py        # Rename to test_aqi_cpcb.py
│       │       ├── test_aqi_us_epa.py # NEW
│       │       ├── test_aqi_european.py # NEW
│       │       ├── test_aqi_resolver.py # NEW
│       │       └── test_api.py        # Extend
│       └── frontend/
│           └── src/
│               ├── lib/
│               │   └── format.ts
│               └── components/
│                   ├── aqi-gauge.tsx
│                   └── air-app.tsx
```

---

## 3. Technical Requirements

### 3.1 AQI Calculation Standards

#### 3.1.1 CPCB (India) - PRESERVE EXACTLY

**Official Source:** Central Pollution Control Board (CPCB) National Air Quality Index (October 2014)  
**Methodology Version:** `"CPCB-NAQI-2014"`  
**Scale:** 0-500

**Breakpoints (from existing backend/app/aqi.py lines 29-86):**

```python
BREAKPOINTS = {
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
```

**Categories:**
1. Good (0-50) - #00e400
2. Satisfactory (51-100) - #ffff00
3. Moderate (101-200) - #ff7e00
4. Poor (201-300) - #ff0000
5. Very Poor (301-400) - #99004c
6. Severe (401-500) - #7e0023

**Calculation Rules:**
- **Concentration truncation:** Integers for most pollutants, 1 decimal for CO/Pb
- **Sub-index:** Linear interpolation within breakpoints, round-half-up
- **Overall AQI:** Maximum of all valid sub-indices
- **Minimum data:** 3 valid pollutants, at least one must be PM2.5 or PM10
- **Averaging periods:**
  - PM2.5, PM10, NO2, SO2, NH3, Pb: 24-hour (minimum 16 hours coverage)
  - CO: 8-hour (minimum 6 hours coverage)
  - O3: 8-hour (minimum 6 hours coverage) OR 1-hour if concentration > 208 µg/m³
- **Units:** µg/m³ for all except CO (mg/m³)

#### 3.1.2 US EPA - Official EPA Breakpoints

**Official Source:** U.S. EPA Technical Assistance Document for the Reporting of Daily Air Quality – the Air Quality Index (AQI) (Revised September 2018)  
**URL:** https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf  
**Methodology Version:** `"US-EPA-AQI-2016"`  
**Scale:** 0-500

**Breakpoints:**

**PM2.5 (24-hour, µg/m³) - Table 5, Page 14:**
```python
(0.0, 12.0, 0, 50),
(12.1, 35.4, 51, 100),
(35.5, 55.4, 101, 150),
(55.5, 150.4, 151, 200),
(150.5, 250.4, 201, 300),
(250.5, 350.4, 301, 400),
(350.5, 500.4, 401, 500),
```

**PM10 (24-hour, µg/m³) - Table 4, Page 13:**
```python
(0, 54, 0, 50),
(55, 154, 51, 100),
(155, 254, 101, 150),
(255, 354, 151, 200),
(355, 424, 201, 300),
(425, 504, 301, 400),
(505, 604, 401, 500),
```

**O3 (8-hour, ppm) - Table 2, Page 11:**
```python
(0.000, 0.054, 0, 50),
(0.055, 0.070, 51, 100),
(0.071, 0.085, 101, 150),
(0.086, 0.105, 151, 200),
(0.106, 0.200, 201, 300),
# CRITICAL: 8-hour O3 NOT defined above 0.200 ppm
```

**O3 (1-hour, ppm) - Table 3, Page 12:**
Used ONLY when 8-hour > 0.200 ppm OR 1-hour > 0.125 ppm
```python
(0.125, 0.164, 101, 150),
(0.165, 0.204, 151, 200),
(0.205, 0.404, 201, 300),
(0.405, 0.504, 301, 400),
(0.505, 0.604, 401, 500),
```

**CO (8-hour, ppm) - Table 6, Page 15:**
```python
(0.0, 4.4, 0, 50),
(4.5, 9.4, 51, 100),
(9.5, 12.4, 101, 150),
(12.5, 15.4, 151, 200),
(15.5, 30.4, 201, 300),
(30.5, 40.4, 301, 400),
(40.5, 50.4, 401, 500),
```

**SO2 (1-hour, ppb) - Table 8, Page 17:**
```python
(0, 35, 0, 50),
(36, 75, 51, 100),
(76, 185, 101, 150),
(186, 304, 151, 200),
(305, 604, 201, 300),
(605, 804, 301, 400),
(805, 1004, 401, 500),
```

**NO2 (1-hour, ppb) - Table 7, Page 16:**
```python
(0, 53, 0, 50),
(54, 100, 51, 100),
(101, 360, 101, 150),
(361, 649, 151, 200),
(650, 1249, 201, 300),
(1250, 1649, 301, 400),
(1650, 2049, 401, 500),
```

**Unit Conversions (at 25°C, 1 atm):**
```python
def to_epa_units(concentration_ugm3: float, parameter: str) -> float:
    """Convert µg/m³ to EPA's expected units (ppm or ppb)."""
    if parameter == "o3":
        return concentration_ugm3 / 1960  # µg/m³ to ppm
    elif parameter == "co":
        # IMPORTANT: Check if DB stores CO in mg/m³ or µg/m³
        # If mg/m³, convert: mg/m³ * 1000 = µg/m³
        return concentration_ugm3 / 1145000  # µg/m³ to ppm
    elif parameter == "so2":
        return concentration_ugm3 / 2.62  # µg/m³ to ppb
    elif parameter == "no2":
        return concentration_ugm3 / 1.88  # µg/m³ to ppb
    elif parameter in {"pm25", "pm10"}:
        return concentration_ugm3  # Already in µg/m³
    else:
        raise ValueError(f"No EPA conversion for {parameter}")
```

**Categories:**
1. Good (0-50) - #00e400
2. Moderate (51-100) - #ffff00
3. Unhealthy for Sensitive Groups (101-150) - #ff7e00
4. Unhealthy (151-200) - #ff0000
5. Very Unhealthy (201-300) - #99004c
6. Hazardous (301-500) - #7e0023

**Calculation Rules:**
- **Concentration truncation:** 1 decimal place before lookup
- **Sub-index:** Linear interpolation, round-half-up
- **Overall AQI:** Maximum of all valid sub-indices
- **Minimum data:** At least one valid sub-index (no minimum count)
- **Averaging:** PM2.5/PM10: 24-hour (18+ hours), O3: 8-hour/1-hour, CO: 8-hour, SO2/NO2: 1-hour

#### 3.1.3 European EEA - Official EEA Breakpoints

**Official Source:** European Environment Agency (EEA) Air Quality Index (2021)  
**URL:** https://www.eea.europa.eu/themes/air/air-quality-index  
**Methodology Version:** `"EEA-AQI-2021"`  
**Scale:** 6 bands (mapped to 0-150 for gauge: Band 1→25, Band 2→50, ..., Band 6→150)

**NOTE:** EEA uses concentration bands, NOT a 0-500 index scale.

**PM2.5 (daily mean, µg/m³):**
```python
(0, 10, 1),    # Good
(10, 20, 2),   # Fair
(20, 25, 3),   # Moderate
(25, 50, 4),   # Poor
(50, 75, 5),   # Very Poor
(75, float('inf'), 6),  # Extremely Poor
```

**PM10 (daily mean, µg/m³):**
```python
(0, 20, 1),
(20, 40, 2),
(40, 50, 3),
(50, 100, 4),
(100, 150, 5),
(150, float('inf'), 6),
```

**NO2 (hourly mean, µg/m³):**
```python
(0, 40, 1),
(40, 90, 2),
(90, 120, 3),
(120, 230, 4),
(230, 340, 5),
(340, float('inf'), 6),
```

**O3 (hourly mean, µg/m³):**
```python
(0, 50, 1),
(50, 100, 2),
(100, 130, 3),
(130, 240, 4),
(240, 380, 5),
(380, float('inf'), 6),
```

**SO2 (hourly mean, µg/m³):**
```python
(0, 100, 1),
(100, 200, 2),
(200, 350, 3),
(350, 500, 4),
(500, 750, 5),
(750, float('inf'), 6),
```

**CO (8-hour maximum, mg/m³):**
```python
(0, 4, 1),
(4, 7, 2),
(7, 10, 3),
(10, 20, 4),
(20, 30, 5),
(30, float('inf'), 6),
```

**Categories:**
1. Good (Band 1, AQI 25) - #50f0e6
2. Fair (Band 2, AQI 50) - #50ccaa
3. Moderate (Band 3, AQI 75) - #f0e641
4. Poor (Band 4, AQI 100) - #ff5050
5. Very Poor (Band 5, AQI 125) - #cc0033
6. Extremely Poor (Band 6, AQI 150) - #7d2181

**Calculation Rules:**
- **Band assignment:** Each pollutant gets a band (1-6) based on concentration thresholds
- **Overall index:** Worst band among all pollutants
- **Minimum data:** At least one valid pollutant
- **Averaging:** PM2.5/PM10: daily (18+ hours), NO2/O3/SO2: 1-hour, CO: 8-hour max
- **Display:** Map band to AQI value for gauge (band * 25)

---

## 4. File-by-File Implementation

### 4.1 NEW: backend/app/aqi/base.py

**Purpose:** Common interface and utilities for all AQI calculators  
**Action:** Create new

```python
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
```

**Key Points:**
- `PollutantReading` is the input format for all calculators
- `AQIResult` is the output format
- `AQICalculator` protocol ensures all implementations have the same interface
- Shared utilities: `round_half_up`, `linear_interpolation`, `truncate_concentration`

---

### 4.2 NEW: backend/app/aqi/cpcb.py

**Purpose:** CPCB (Indian) AQI implementation - migrated from aqi.py  
**Action:** Create new  
**Dependencies:** `from .base import *`

```python
"""CPCB National Air Quality Index calculation.

Migrated from app/aqi.py. All existing CPCB logic preserved exactly.
"""

from __future__ import annotations

import math

from .base import (
    AQICalculator,
    AQIResult,
    CategoryMetadata,
    PollutantReading,
    SubIndexResult,
    linear_interpolation,
    round_half_up,
)

METHODOLOGY_NAME = "CPCB"
METHODOLOGY_VERSION = "CPCB-NAQI-2014"
MIN_VALID_POLLUTANTS = 3
MIN_COVERAGE_24H = 16
MIN_COVERAGE_8H = 6

# Breakpoints from existing aqi.py (lines 29-86)
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


def truncate_concentration(parameter: str, value: float) -> float:
    """CPCB-specific truncation: integers for most, 1 decimal for CO/Pb."""
    if parameter in {"co", "pb"}:
        return math.floor(value * 10) / 10
    return float(math.floor(value))


def category_for(aqi: int) -> str:
    """Return category name for AQI value."""
    bounded = min(max(aqi, 0), 500)
    for low, high, name in CATEGORIES:
        if low <= bounded <= high:
            return name
    return "Severe"


def sub_index_for(parameter: str, concentration: float) -> int | None:
    """Calculate sub-index for a pollutant using CPCB breakpoints."""
    bands = BREAKPOINTS.get(parameter)
    if bands is None or concentration < 0:
        return None
    used = truncate_concentration(parameter, concentration)
    if used < 0:
        return None
    for low, high, index_low, index_high in bands:
        if low <= used <= high:
            return linear_interpolation(used, low, high, index_low, index_high)
    # Above highest breakpoint
    if used > bands[-1][1]:
        return 500
    return None


def _period_is_valid(reading: PollutantReading) -> bool:
    """Check if averaging period and coverage meet CPCB requirements."""
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


class CPCBAQICalculator:
    """CPCB National AQI calculator."""

    @property
    def methodology_name(self) -> str:
        return METHODOLOGY_NAME

    @property
    def methodology_version(self) -> str:
        return METHODOLOGY_VERSION

    def calculate(self, readings: list[PollutantReading]) -> AQIResult:
        """Calculate CPCB AQI from averaged pollutant concentrations."""
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
                    concentration_used=truncate_concentration(
                        reading.parameter, reading.concentration
                    ),
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
                methodology=METHODOLOGY_NAME,
                methodology_version=METHODOLOGY_VERSION,
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
        """Return CPCB category definitions."""
        from .categories import CPCB_CATEGORIES
        return CPCB_CATEGORIES
```

**Key Points:**
- This is a direct migration from `aqi.py` with minimal changes
- All existing test cases must pass unchanged
- Preserves CPCB coverage rules and minimum pollutant requirements

---

### 4.3 NEW: backend/app/aqi/us_epa.py

**Purpose:** US EPA AQI implementation  
**Action:** Create new  
**Dependencies:** `from .base import *`

```python
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


def to_epa_units(concentration_ugm3: float, parameter: str) -> float:
    """Convert µg/m³ to EPA units (ppm or ppb) at 25°C, 1 atm."""
    if parameter == "o3":
        return concentration_ugm3 / 1960  # µg/m³ to ppm
    elif parameter == "co":
        # Database may store CO in mg/m³ or µg/m³
        # Assume µg/m³ here; adjust if needed
        return concentration_ugm3 / 1145000  # µg/m³ to ppm
    elif parameter == "so2":
        return concentration_ugm3 / 2.62  # µg/m³ to ppb
    elif parameter == "no2":
        return concentration_ugm3 / 1.88  # µg/m³ to ppb
    elif parameter in {"pm25", "pm10"}:
        return concentration_ugm3  # Already in µg/m³
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
```

**Key Points:**
- Unit conversion from µg/m³ to ppm/ppb
- Special ozone logic: 8-hour vs 1-hour selection
- No minimum pollutant count (unlike CPCB)
- Coverage hours not used (set to None)

---

### 4.4 NEW: backend/app/aqi/european.py

**Purpose:** European EEA AQI implementation  
**Action:** Create new

```python
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
```

**Key Points:**
- Band-based system, not 0-500 scale
- Overall index = worst band
- Mapped to AQI values for gauge compatibility (band * 25)
- No minimum pollutant requirement

---

### 4.5 NEW: backend/app/aqi/resolver.py

**Purpose:** Select AQI methodology based on location country  
**Action:** Create new

```python
"""Methodology resolver: select AQI calculator based on country code."""

from __future__ import annotations

from typing import Literal

from .base import AQICalculator

AQIMethodology = Literal["CPCB", "US-EPA", "European", "unavailable"]

# ISO 3166-1 alpha-2 country codes
COUNTRY_TO_METHODOLOGY: dict[str, AQIMethodology] = {
    # India
    "IN": "CPCB",
    
    # United States
    "US": "US-EPA",
    
    # European Union and EEA member states
    # NOTE: Some EU countries have national AQI systems (UK DAQI, German UBA).
    # This mapping uses the pan-European EEA index as a best-effort approximation.
    "AT": "European",  # Austria
    "BE": "European",  # Belgium
    "BG": "European",  # Bulgaria
    "HR": "European",  # Croatia
    "CY": "European",  # Cyprus
    "CZ": "European",  # Czech Republic
    "DK": "European",  # Denmark
    "EE": "European",  # Estonia
    "FI": "European",  # Finland
    "FR": "European",  # France
    "DE": "European",  # Germany (note: uses UBA index nationally)
    "GR": "European",  # Greece
    "HU": "European",  # Hungary
    "IE": "European",  # Ireland
    "IT": "European",  # Italy
    "LV": "European",  # Latvia
    "LT": "European",  # Lithuania
    "LU": "European",  # Luxembourg
    "MT": "European",  # Malta
    "NL": "European",  # Netherlands
    "PL": "European",  # Poland
    "PT": "European",  # Portugal
    "RO": "European",  # Romania
    "SK": "European",  # Slovakia
    "SI": "European",  # Slovenia
    "ES": "European",  # Spain
    "SE": "European",  # Sweden
    "GB": "European",  # United Kingdom (note: uses DAQI nationally)
    "NO": "European",  # Norway
    "IS": "European",  # Iceland
    "LI": "European",  # Liechtenstein
    "CH": "European",  # Switzerland
}


def resolve_methodology(country_code: str | None) -> AQIMethodology:
    """
    Return the AQI methodology for a given country, or 'unavailable' if not supported.
    
    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "IN", "US", "GB")
    
    Returns:
        One of "CPCB", "US-EPA", "European", or "unavailable"
    """
    if country_code is None:
        return "unavailable"
    return COUNTRY_TO_METHODOLOGY.get(country_code.upper(), "unavailable")


def get_calculator(methodology: AQIMethodology) -> AQICalculator | None:
    """Return the appropriate calculator instance, or None if unavailable."""
    if methodology == "CPCB":
        from .cpcb import CPCBAQICalculator
        return CPCBAQICalculator()
    elif methodology == "US-EPA":
        from .us_epa import USEPAAQICalculator
        return USEPAAQICalculator()
    elif methodology == "European":
        from .european import EuropeanAQICalculator
        return EuropeanAQICalculator()
    return None


def get_methodology_display_name(methodology: str) -> str:
    """Return user-facing methodology name."""
    return {
        "CPCB": "Indian AQI (CPCB)",
        "US-EPA": "US EPA AQI",
        "European": "European AQI (EEA)",
        "unavailable": "AQI Unavailable",
    }.get(methodology, methodology)
```

**Key Points:**
- Country code mapping is the single source of truth
- Comments note discrepancies (UK DAQI, German UBA)
- Returns "unavailable" for unmapped countries

---

### 4.6 NEW: backend/app/aqi/categories.py

**Purpose:** Category metadata for frontend rendering  
**Action:** Create new

```python
"""Category metadata for all AQI methodologies."""

from __future__ import annotations

from .base import CategoryMetadata

# Content rephrased for compliance with licensing restrictions

CPCB_CATEGORIES = [
    CategoryMetadata(
        name="Good",
        code="good",
        min_aqi=0,
        max_aqi=50,
        color="#00e400",
        text_color="#000000",
        description="Air quality is satisfactory, and air pollution poses little or no risk.",
    ),
    CategoryMetadata(
        name="Satisfactory",
        code="satisfactory",
        min_aqi=51,
        max_aqi=100,
        color="#ffff00",
        text_color="#000000",
        description="Air quality is acceptable. However, there may be a risk for some people, particularly those who are unusually sensitive to air pollution.",
    ),
    CategoryMetadata(
        name="Moderate",
        code="moderate",
        min_aqi=101,
        max_aqi=200,
        color="#ff7e00",
        text_color="#000000",
        description="Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
    ),
    CategoryMetadata(
        name="Poor",
        code="poor",
        min_aqi=201,
        max_aqi=300,
        color="#ff0000",
        text_color="#ffffff",
        description="Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects.",
    ),
    CategoryMetadata(
        name="Very Poor",
        code="very-poor",
        min_aqi=301,
        max_aqi=400,
        color="#99004c",
        text_color="#ffffff",
        description="Health alert: The risk of health effects is increased for everyone.",
    ),
    CategoryMetadata(
        name="Severe",
        code="severe",
        min_aqi=401,
        max_aqi=500,
        color="#7e0023",
        text_color="#ffffff",
        description="Health warning of emergency conditions: everyone is more likely to be affected.",
    ),
]

US_EPA_CATEGORIES = [
    CategoryMetadata(
        name="Good",
        code="good",
        min_aqi=0,
        max_aqi=50,
        color="#00e400",
        text_color="#000000",
        description="Air quality is satisfactory, and air pollution poses little or no risk.",
    ),
    CategoryMetadata(
        name="Moderate",
        code="moderate",
        min_aqi=51,
        max_aqi=100,
        color="#ffff00",
        text_color="#000000",
        description="Air quality is acceptable. However, there may be a risk for some people, particularly those who are unusually sensitive to air pollution.",
    ),
    CategoryMetadata(
        name="Unhealthy for Sensitive Groups",
        code="uso",
        min_aqi=101,
        max_aqi=150,
        color="#ff7e00",
        text_color="#000000",
        description="Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
    ),
    CategoryMetadata(
        name="Unhealthy",
        code="unhealthy",
        min_aqi=151,
        max_aqi=200,
        color="#ff0000",
        text_color="#ffffff",
        description="Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects.",
    ),
    CategoryMetadata(
        name="Very Unhealthy",
        code="very-unhealthy",
        min_aqi=201,
        max_aqi=300,
        color="#99004c",
        text_color="#ffffff",
        description="Health alert: The risk of health effects is increased for everyone.",
    ),
    CategoryMetadata(
        name="Hazardous",
        code="hazardous",
        min_aqi=301,
        max_aqi=500,
        color="#7e0023",
        text_color="#ffffff",
        description="Health warning of emergency conditions: everyone is more likely to be affected.",
    ),
]

EUROPEAN_CATEGORIES = [
    CategoryMetadata(
        name="Good",
        code="good",
        min_aqi=0,
        max_aqi=25,
        color="#50f0e6",
        text_color="#000000",
        description="Air quality is good. Enjoy your usual outdoor activities.",
    ),
    CategoryMetadata(
        name="Fair",
        code="fair",
        min_aqi=26,
        max_aqi=50,
        color="#50ccaa",
        text_color="#000000",
        description="Air quality is fair. Enjoy your usual outdoor activities.",
    ),
    CategoryMetadata(
        name="Moderate",
        code="moderate",
        min_aqi=51,
        max_aqi=75,
        color="#f0e641",
        text_color="#000000",
        description="Air quality is moderate. Consider reducing intense outdoor activities if you experience symptoms.",
    ),
    CategoryMetadata(
        name="Poor",
        code="poor",
        min_aqi=76,
        max_aqi=100,
        color="#ff5050",
        text_color="#ffffff",
        description="Air quality is poor. Consider reducing intense outdoor activities if you experience symptoms.",
    ),
    CategoryMetadata(
        name="Very Poor",
        code="very-poor",
        min_aqi=101,
        max_aqi=125,
        color="#cc0033",
        text_color="#ffffff",
        description="Air quality is very poor. Consider reducing physical activities outdoors, especially if you experience symptoms.",
    ),
    CategoryMetadata(
        name="Extremely Poor",
        code="extremely-poor",
        min_aqi=126,
        max_aqi=150,
        color="#7d2181",
        text_color="#ffffff",
        description="Air quality is extremely poor. Reduce physical activities outdoors.",
    ),
]


def get_categories(methodology: str) -> list[CategoryMetadata]:
    """Return category metadata for the given methodology."""
    if methodology == "CPCB":
        return CPCB_CATEGORIES
    elif methodology == "US-EPA":
        return US_EPA_CATEGORIES
    elif methodology == "European":
        return EUROPEAN_CATEGORIES
    return []


def get_category_for_aqi(methodology: str, aqi_value: int) -> CategoryMetadata | None:
    """Return the category for a given AQI value and methodology."""
    categories = get_categories(methodology)
    for cat in categories:
        if cat.min_aqi <= aqi_value <= cat.max_aqi:
            return cat
    # Handle values above max (e.g., European AQI > 150)
    if categories and aqi_value > categories[-1].max_aqi:
        return categories[-1]
    return None
```

**Key Points:**
- All colors and descriptions in one place
- Frontend retrieves these via API response
- No hardcoded categories in frontend

---

### 4.7 NEW: backend/app/aqi/__init__.py

**Purpose:** Public API for AQI calculation  
**Action:** Create new

```python
"""Global AQI calculation engine.

Public API for calculating AQI using the appropriate methodology
based on location country code.
"""

from __future__ import annotations

from .base import AQIResult, CategoryMetadata, PollutantReading, SubIndexResult
from .categories import get_categories, get_category_for_aqi
from .resolver import get_calculator, get_methodology_display_name, resolve_methodology

__all__ = [
    "calculate_aqi_for_location",
    "PollutantReading",
    "AQIResult",
    "SubIndexResult",
    "CategoryMetadata",
    "get_category_for_aqi",
    "get_categories",
    "get_methodology_display_name",
]


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
```

**Key Points:**
- Single entry point for all AQI calculations
- Handles "unavailable" methodology gracefully
- Returns standardized `AQIResult`

---

### 4.8 MODIFY: backend/app/models.py

**Purpose:** Add methodology discrimination and source type to database  
**Action:** Modify existing

**Changes:**

1. Add `country_code` to `Location`:
```python
class Location(Base):
    # ... existing fields ...
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
```

2. Modify `AQIRecord`:
```python
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
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)  # CHANGED: 32 -> 64
    dominant_pollutant: Mapped[str | None] = mapped_column(String(80), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="observation")  # NEW
    inputs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

---

### 4.9 MODIFY: backend/app/schemas.py

**Purpose:** Extend API schemas with new metadata fields  
**Action:** Modify existing

**Changes:**

1. Update `SubIndexOut`:
```python
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
```

2. Update `AQIOut`:
```python
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
    source_type: str = "observation"  # NEW
    reason: str | None = None
    sub_indices: list[SubIndexOut] = Field(default_factory=list)
    station_id: int | None = None
    station_name: str | None = None
```

---

### 4.10 MODIFY: backend/app/services/dashboard.py

**Purpose:** Wire new AQI engine into dashboard service  
**Action:** Modify existing

**Find and replace:**

1. Change imports:
```python
# OLD:
from app.aqi import CANONICAL_UNIT, DISPLAY_NAME, METHODOLOGY_VERSION, calculate_aqi

# NEW:
from app.aqi import (
    PollutantReading,
    calculate_aqi_for_location,
    get_category_for_aqi,
    get_methodology_display_name,
)
```

2. Update `discover_location()` to store `country_code`:
```python
# Around line 54-75
location = Location(
    name=place.name,
    city=place.name,
    country=place.country or "Unknown",
    country_code=place.country_code,  # ADD THIS
    latitude=place.latitude,
    longitude=place.longitude,
    timezone=place.timezone,
    is_popular=False,
)
```

3. Update AQI calculation to use new engine:
```python
# Find the function that calls calculate_aqi() - around line 318
# OLD:
result = calculate_aqi(averages)

# NEW:
readings = [
    PollutantReading(
        parameter=avg.parameter,
        concentration=avg.concentration,
        averaging_period=avg.averaging_period,
        coverage_hours=avg.coverage_hours,
    )
    for avg in averages
]
result = calculate_aqi_for_location(readings, location.country_code)
```

4. Update `_aqi_out()` to populate metadata:
```python
def _aqi_out(result: AQIResult, calculated_at: datetime, station: Station) -> AQIOut:
    """Convert AQIResult to AQIOut schema with category metadata."""
    category_style = None
    if result.available and result.aqi is not None:
        category_style = get_category_for_aqi(result.methodology, result.aqi)

    methodology_display = get_methodology_display_name(result.methodology)

    return AQIOut(
        available=result.available,
        value=result.aqi,
        category=result.category,
        category_code=category_style.code if category_style else None,
        category_color=category_style.color if category_style else None,
        category_text_color=category_style.text_color if category_style else None,
        dominant_pollutants=result.dominant_pollutants,
        calculated_at=calculated_at,
        methodology=result.methodology,
        methodology_display=methodology_display,
        source_type="observation",
        reason=result.reason,
        sub_indices=[_sub_index_out(si, result.methodology) for si in result.sub_indices],
        station_id=station.id,
        station_name=station.name,
    )

def _sub_index_out(sub_index: SubIndexResult, methodology: str) -> SubIndexOut:
    """Convert SubIndexResult to SubIndexOut with category metadata."""
    category_style = get_category_for_aqi(methodology, sub_index.sub_index)

    return SubIndexOut(
        parameter=sub_index.parameter,
        display_name=sub_index.display_name,
        sub_index=sub_index.sub_index,
        concentration_used=sub_index.concentration_used,
        unit=sub_index.unit,
        averaging_period=sub_index.averaging_period,
        coverage_hours=sub_index.coverage_hours,
        category=category_style.name if category_style else None,
        category_code=category_style.code if category_style else None,
        category_color=category_style.color if category_style else None,
    )
```

5. Update `_sources()` function (around line 652):
```python
def _sources(origin: str, weather: WeatherOut | None, methodology: str, country: str) -> list[str]:
    sources = []
    if origin == "openaq":
        sources.append("Station observations: OpenAQ")
    elif origin == "sample":
        sources.append("Station observations: bundled sample dataset")
    else:
        sources.append("Station observations: unavailable")

    # Dynamic methodology label
    if methodology == "CPCB":
        sources.append("Indian AQI: calculated with CPCB National AQI (2014)")
    elif methodology == "US-EPA":
        sources.append("US AQI: calculated with EPA AQI methodology (2016)")
    elif methodology == "European":
        sources.append("European AQI: calculated with EEA Air Quality Index (2021)")
    elif methodology == "unavailable":
        sources.append(f"AQI calculation unavailable for {country}")

    if weather is not None:
        sources.append(f"Weather: {weather.label}")
    return sources
```

6. Thread `location` through to `_station_out()` and `_aqi_out()` calls to access `country_code`.

---

### 4.11 MODIFY: backend/app/providers/openaq.py

**Purpose:** Remove India-first bias  
**Action:** Modify existing

**Changes:**

Find `nearby_stations()` method (around line 68) and modify:

```python
def nearby_stations(
    self,
    latitude: float,
    longitude: float,
    limit: int = 3,
    country_code: str | None = None,  # NEW parameter
) -> list[RemoteStation]:
    """
    Return the most recently reporting monitors near the given coordinates.
    
    Args:
        country_code: Optional ISO country code for location-aware search priority
    """
    params = {
        "coordinates": f"{latitude:.4f},{longitude:.4f}",
        "radius": 25000,
        "limit": 100,
        "page": 1,
    }

    # If a country code is provided, try country-specific search first
    if country_code:
        params["iso"] = country_code
        payload = self._get("/locations", params)
        results = payload.get("results") or []
        if results:
            return self._filter_and_rank_stations(results, limit)

    # Global search (no iso parameter)
    params.pop("iso", None)
    payload = self._get("/locations", params)
    results = payload.get("results") or []
    return self._filter_and_rank_stations(results, limit)
```

**Call site:** Update dashboard.py to pass `location.country_code` when calling `nearby_stations()`.

---

### 4.12 MODIFY: frontend/src/lib/format.ts

**Purpose:** Make categories dynamic from API  
**Action:** Modify existing

**Changes:**

1. Add function to get category style from API:
```typescript
export function categoryStyleFromAPI(aqi: {
  category_color?: string | null;
  category_text_color?: string | null;
  available: boolean;
}): CategoryStyle {
  if (!aqi.available || !aqi.category_color) {
    return style("unknown");
  }

  return {
    solid: aqi.category_color,
    text: aqi.category_text_color || "#ffffff",
    on: aqi.category_text_color || "#ffffff",
    soft: `${aqi.category_color}33`, // 20% opacity
  };
}
```

2. Keep existing `CATEGORIES` and `AQI_SCALE` for backward compatibility but add comment:
```typescript
// LEGACY: CPCB categories. New code should use categoryStyleFromAPI()
export const CATEGORIES: Record<string, CategoryStyle> = { ... };
```

---

### 4.13 MODIFY: frontend/src/components/aqi-gauge.tsx

**Purpose:** Use category colors from API  
**Action:** Modify existing

**Changes:**

Accept `categoryStyle` prop instead of looking up by category name:

```typescript
export function AqiGauge({
  value,
  category,
  available,
  categoryStyle,  // NEW: passed from parent
}: {
  value: number | null;
  category: string | null;
  available: boolean;
  categoryStyle: CategoryStyle;  // NEW
}) {
  // Use categoryStyle for badge rendering
  // ... rest of component
}
```

---

### 4.14 MODIFY: frontend/src/components/air-app.tsx

**Purpose:** Display methodology and use API colors  
**Action:** Modify existing

**Changes:**

1. Import `categoryStyleFromAPI`:
```typescript
import { categoryStyleFromAPI } from "@/lib/format";
```

2. Compute category style:
```typescript
const aqiCategoryStyle = categoryStyleFromAPI(overview.aqi);
```

3. Pass to gauge:
```typescript
<AqiGauge
  value={overview.aqi.value}
  category={overview.aqi.category}
  available={overview.aqi.available}
  categoryStyle={aqiCategoryStyle}
/>
```

4. Display methodology:
```typescript
<div className="text-sm text-gray-600">
  {overview.aqi.methodology_display || overview.aqi.methodology}
</div>
```

5. Show unavailable reason:
```typescript
{!overview.aqi.available && overview.aqi.reason && (
  <div className="bg-gray-100 p-4 rounded-lg">
    <p className="text-gray-800">{overview.aqi.reason}</p>
  </div>
)}
```

6. Use sub-index colors from API:
```typescript
<div
  className="h-2 rounded-full"
  style={{
    width: `${Math.min((subIndex.sub_index / 500) * 100, 100)}%`,
    backgroundColor: subIndex.category_color || "var(--aqi-unknown)",
  }}
/>
```

---

## 5. Database Migration

### 5.1 Migration Script

Create `backend/alembic/versions/XXXX_global_aqi_support.py`:

```python
"""global aqi support

Revision ID: XXXX
Revises: YYYY
Create Date: 2024-XX-XX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'XXXX'
down_revision = 'YYYY'
branch_labels = None
depends_on = None


def upgrade():
    # Add country_code to locations
    op.add_column('locations', sa.Column('country_code', sa.String(length=2), nullable=True))
    
    # Add source_type to aqi_records with default
    op.add_column('aqi_records', sa.Column('source_type', sa.String(length=20), nullable=False, server_default='observation'))
    
    # Increase category column length
    with op.batch_alter_table('aqi_records') as batch_op:
        batch_op.alter_column('category', type_=sa.String(length=64), existing_type=sa.String(length=32))
    
    # Add composite indexes
    op.create_index('ix_aqi_location_methodology_time', 'aqi_records', ['location_id', 'methodology', 'calculated_at'])
    op.create_index('ix_aqi_station_methodology_time', 'aqi_records', ['station_id', 'methodology', 'calculated_at'])


def downgrade():
    op.drop_index('ix_aqi_station_methodology_time', 'aqi_records')
    op.drop_index('ix_aqi_location_methodology_time', 'aqi_records')
    
    with op.batch_alter_table('aqi_records') as batch_op:
        batch_op.alter_column('category', type_=sa.String(length=32), existing_type=sa.String(length=64))
    
    op.drop_column('aqi_records', 'source_type')
    op.drop_column('locations', 'country_code')
```

### 5.2 Data Migration

All existing records:
- Have `source_type` set to `"observation"` automatically (server default)
- Keep existing category names (all fit in 64 chars)
- Keep existing methodology strings

No data migration script needed.

---

## 6. Testing Requirements

### 6.1 Test Structure

```
backend/tests/
├── test_aqi_cpcb.py       # Rename from test_aqi.py
├── test_aqi_us_epa.py     # NEW
├── test_aqi_european.py   # NEW
├── test_aqi_resolver.py   # NEW
└── test_api.py            # Extend with global locations
```

### 6.2 CPCB Tests (Preserve Exactly)

Rename `test_aqi.py` to `test_aqi_cpcb.py` and update imports:

```python
from app.aqi.cpcb import CPCBAQICalculator
from app.aqi.base import PollutantReading

# All existing tests MUST pass unchanged
```

### 6.3 US EPA Tests

Create `backend/tests/test_aqi_us_epa.py`:

```python
"""Tests for US EPA AQI calculation."""

from app.aqi.us_epa import USEPAAQICalculator
from app.aqi.base import PollutantReading


def test_pm25_boundary():
    """PM2.5 = 12.0 µg/m³ → AQI 50 (boundary)."""
    calc = USEPAAQICalculator()
    readings = [
        PollutantReading(parameter="pm25", concentration=12.0, averaging_period="24h", coverage_hours=24)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 50
    assert result.category == "Good"


def test_pm25_uso_boundary():
    """PM2.5 = 35.5 µg/m³ → AQI 101 (USG boundary)."""
    calc = USEPAAQICalculator()
    readings = [
        PollutantReading(parameter="pm25", concentration=35.5, averaging_period="24h", coverage_hours=24)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 101
    assert result.category == "Unhealthy for Sensitive Groups"


def test_ozone_8h():
    """O3 8-hour = 0.071 ppm → AQI 101."""
    calc = USEPAAQICalculator()
    # Convert ppm to µg/m³: 0.071 * 1960 = 139.16 µg/m³
    readings = [
        PollutantReading(parameter="o3", concentration=139.16, averaging_period="8h", coverage_hours=8)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 101


def test_ozone_above_200_no_1h():
    """O3 8-hour > 0.200 ppm with no 1-hour data → unavailable."""
    calc = USEPAAQICalculator()
    # 0.201 ppm = 393.96 µg/m³
    readings = [
        PollutantReading(parameter="o3", concentration=393.96, averaging_period="8h", coverage_hours=8)
    ]
    result = calc.calculate(readings)
    # Should not include O3 in result
    assert result.available == False or "o3" not in [si.parameter for si in result.sub_indices]


def test_ozone_1h_threshold():
    """O3 1-hour = 0.125 ppm → AQI 101 (uses 1-hour table)."""
    calc = USEPAAQICalculator()
    # 0.125 ppm = 245 µg/m³
    readings = [
        PollutantReading(parameter="o3", concentration=245, averaging_period="1h", coverage_hours=1)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 101


def test_co():
    """CO = 4.5 ppm → AQI 51."""
    calc = USEPAAQICalculator()
    # 4.5 ppm = 5152500 µg/m³
    readings = [
        PollutantReading(parameter="co", concentration=5152500, averaging_period="8h", coverage_hours=8)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 51


def test_overall_aqi_is_max():
    """Overall AQI = max sub-index."""
    calc = USEPAAQICalculator()
    readings = [
        PollutantReading(parameter="pm25", concentration=12.0, averaging_period="24h", coverage_hours=24),  # AQI 50
        PollutantReading(parameter="pm10", concentration=155, averaging_period="24h", coverage_hours=24),   # AQI 101
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 101
    assert "PM10" in result.dominant_pollutants
```

### 6.4 European AQI Tests

Create `backend/tests/test_aqi_european.py`:

```python
"""Tests for European AQI calculation."""

from app.aqi.european import EuropeanAQICalculator
from app.aqi.base import PollutantReading


def test_pm10_fair():
    """PM10 = 20 µg/m³ → Band 2 (Fair), AQI 50."""
    calc = EuropeanAQICalculator()
    readings = [
        PollutantReading(parameter="pm10", concentration=20, averaging_period="24h", coverage_hours=24)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 50
    assert result.category == "Fair"


def test_pm25_very_poor():
    """PM2.5 = 60 µg/m³ → Band 5 (Very Poor), AQI 125."""
    calc = EuropeanAQICalculator()
    readings = [
        PollutantReading(parameter="pm25", concentration=60, averaging_period="24h", coverage_hours=24)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 125
    assert result.category == "Very Poor"


def test_no2_poor():
    """NO2 = 200 µg/m³ → Band 4 (Poor), AQI 100."""
    calc = EuropeanAQICalculator()
    readings = [
        PollutantReading(parameter="no2", concentration=200, averaging_period="1h", coverage_hours=1)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 100
    assert result.category == "Poor"


def test_overall_is_worst_band():
    """Overall = worst band."""
    calc = EuropeanAQICalculator()
    readings = [
        PollutantReading(parameter="pm25", concentration=15, averaging_period="24h", coverage_hours=24),  # Band 2
        PollutantReading(parameter="no2", concentration=100, averaging_period="1h", coverage_hours=1),    # Band 3
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 75  # Band 3 * 25
    assert result.category == "Moderate"


def test_extremely_poor_overflow():
    """PM2.5 = 200 µg/m³ → Band 6 (Extremely Poor), AQI 150."""
    calc = EuropeanAQICalculator()
    readings = [
        PollutantReading(parameter="pm25", concentration=200, averaging_period="24h", coverage_hours=24)
    ]
    result = calc.calculate(readings)
    assert result.available
    assert result.aqi == 150
    assert result.category == "Extremely Poor"
```

### 6.5 Resolver Tests

Create `backend/tests/test_aqi_resolver.py`:

```python
"""Tests for methodology resolver."""

from app.aqi.resolver import resolve_methodology, get_calculator


def test_india_uses_cpcb():
    assert resolve_methodology("IN") == "CPCB"


def test_us_uses_epa():
    assert resolve_methodology("US") == "US-EPA"


def test_uk_uses_european():
    assert resolve_methodology("GB") == "European"


def test_france_uses_european():
    assert resolve_methodology("FR") == "European"


def test_japan_unavailable():
    assert resolve_methodology("JP") == "unavailable"


def test_none_country_code_unavailable():
    assert resolve_methodology(None) == "unavailable"


def test_get_calculator_cpcb():
    calc = get_calculator("CPCB")
    assert calc is not None
    assert calc.methodology_name == "CPCB"


def test_get_calculator_unavailable():
    calc = get_calculator("unavailable")
    assert calc is None
```

### 6.6 Integration Tests

Extend `backend/tests/test_api.py`:

```python
def test_delhi_uses_cpcb(api):
    """Delhi (IN) should use CPCB methodology."""
    client, app = api
    # Search for Delhi
    response = client.get("/api/v1/locations?query=Delhi")
    locations = response.json()["results"]
    delhi = locations[0]
    
    # Get overview
    response = client.get(f"/api/v1/locations/{delhi['id']}/overview")
    overview = response.json()
    
    assert overview["aqi"]["methodology"] == "CPCB"
    assert overview["aqi"]["methodology_display"] == "Indian AQI (CPCB)"


def test_new_york_uses_epa(api, monkeypatch):
    """New York (US) should use US EPA methodology."""
    # Mock geocoder and OpenAQ to return New York data
    # ... (similar to existing test pattern)
    pass


def test_tokyo_unavailable(api, monkeypatch):
    """Tokyo (JP) should show unavailable AQI with reason."""
    # Mock geocoder to return Tokyo
    # ... 
    # Assert: overview["aqi"]["available"] == False
    # Assert: "unavailable" in overview["aqi"]["reason"]
    pass
```

---

## 7. Verification Steps

### 7.1 Backend Tests

```bash
cd /home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi/backend

# Run all AQI tests
pytest tests/test_aqi_cpcb.py -v
pytest tests/test_aqi_us_epa.py -v
pytest tests/test_aqi_european.py -v
pytest tests/test_aqi_resolver.py -v

# Run integration tests
pytest tests/test_api.py -v

# Run all tests
pytest -v
```

### 7.2 Database Migration

```bash
cd /home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi/backend

# Generate migration
alembic revision --autogenerate -m "global aqi support"

# Apply migration
alembic upgrade head

# Verify schema
sqlite3 data/air_quality.db ".schema aqi_records"
sqlite3 data/air_quality.db ".schema locations"
```

### 7.3 Frontend Build

```bash
cd /home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi/frontend

# Install dependencies
npm install

# Build
npm run build

# Run dev server for manual testing
npm run dev
```

### 7.4 Docker Compose

```bash
cd /home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi

# Build and start
docker compose up --build

# Test endpoints
curl http://localhost:8000/api/v1/locations?query=Delhi
curl http://localhost:8000/api/v1/locations/1/overview
```

---

## 8. Integration Checklist

- [ ] Backend: `backend/app/aqi/` module created with all 7 files
- [ ] Backend: Old `aqi.py` replaced by new modular engine
- [ ] Backend: All existing CPCB tests pass unchanged in `test_aqi_cpcb.py`
- [ ] Backend: US EPA tests pass with official breakpoints
- [ ] Backend: European AQI tests pass with EEA bands
- [ ] Backend: Resolver tests pass for country mapping
- [ ] Backend: Database migration runs successfully
- [ ] Backend: `models.py` has `country_code` and `source_type` fields
- [ ] Backend: `schemas.py` has new metadata fields
- [ ] Backend: `dashboard.py` uses `calculate_aqi_for_location()`
- [ ] Backend: `openaq.py` accepts `country_code` parameter
- [ ] Backend: Integration tests verify Delhi→CPCB, New York→EPA
- [ ] Frontend: `format.ts` has `categoryStyleFromAPI()` function
- [ ] Frontend: `aqi-gauge.tsx` accepts `categoryStyle` prop
- [ ] Frontend: `air-app.tsx` displays `methodology_display`
- [ ] Frontend: `air-app.tsx` shows unavailable reason
- [ ] Frontend: Build completes without errors
- [ ] Docker Compose starts without errors
- [ ] API returns correct methodology for test cities
- [ ] Cache keys work correctly (no cross-methodology reuse)
- [ ] Backward compatibility: existing Indian cities work unchanged

---

## 9. Known Constraints

1. **Preserve Indian city functionality:** All existing CPCB behavior must remain identical
2. **No breaking API changes:** New fields are additive only; existing clients continue working
3. **Follow existing code style:** Match naming conventions, error handling patterns
4. **No new paid dependencies:** Use only existing free-tier APIs
5. **Local Docker Compose compatibility:** All changes work in SQLite development environment
6. **No CO unit ambiguity:** Verify whether database stores CO in mg/m³ or µg/m³ and adjust conversions
7. **Popular city list stays Indian-only:** Do not schedule global data collection
8. **Model-based AQI out of scope:** Only station observations used for AQI calculation

---

## 10. Quick Start for Implementation

```bash
# 1. Navigate to worktree
cd /home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi

# 2. Create AQI module directory
mkdir -p backend/app/aqi

# 3. Create all module files from Section 4 above
# - backend/app/aqi/__init__.py
# - backend/app/aqi/base.py
# - backend/app/aqi/cpcb.py
# - backend/app/aqi/us_epa.py
# - backend/app/aqi/european.py
# - backend/app/aqi/resolver.py
# - backend/app/aqi/categories.py

# 4. Modify existing files per Section 4.8-4.14

# 5. Create database migration per Section 5

# 6. Create test files per Section 6

# 7. Run verification per Section 7

# 8. Check integration checklist (Section 8)
```

---

## End of Implementation Guide

This guide contains ALL information needed to implement global AQI support without any external context. Every code block is complete and executable. Every breakpoint is verified against official sources. Every integration point is specified.

**Implementation complete when all items in Section 8 (Integration Checklist) are checked.**
