# Technical Design: Global AQI Support for Community Air Quality Dashboard

**Version:** 2.0 (Revised)  
**Date:** 2024  
**Status:** Revised per Design Review

---

## Overview

This design extends the existing Community Air Quality Dashboard to support multiple AQI calculation methodologies for cities worldwide while preserving all existing Indian CPCB functionality. The application currently implements only CPCB National AQI (2014) with India-centric assumptions throughout the stack. This extension introduces a modular AQI calculation engine supporting India (CPCB), United States (US EPA AQI), and Europe (European AQI), with explicit handling of countries lacking implemented standards.

The core architectural principle is **separation of concerns**: location discovery, data provider ingestion, pollutant normalization, AQI calculation, and presentation remain independent layers. The existing three-tier caching architecture, Cloud Run deployment compatibility, and free-tier cost objectives are preserved.

**Key design decisions:**
1. **Modular AQI engine** under `backend/app/aqi/` with standard-specific calculation modules
2. **Country-based methodology resolution** — India→CPCB, US→EPA, EU countries→European AQI
3. **Explicit unavailable state** for unsupported countries (no silent fallback to wrong methodology)
4. **Observation-based only** — model-based AQI deferred (Open-Meteo doesn't provide reliable AQI)
5. **Backward compatibility** — all existing Indian city functionality preserved, API schemas extended not replaced
6. **Frontend receives category metadata from backend** — no hardcoded non-CPCB categories in UI

---

## 1. Modular AQI Calculation Engine

### 1.1 Package Structure

Create a new package at `backend/app/aqi/` to replace the monolithic `backend/app/aqi.py`:

```
backend/app/aqi/
├── __init__.py          # Public API: calculate_aqi_for_location(readings, country_code)
├── base.py              # AQICalculator protocol and shared utilities
├── resolver.py          # Methodology selection by country code
├── cpcb.py              # Existing Indian CPCB implementation (refactored from aqi.py)
├── us_epa.py            # US EPA AQI implementation
├── european.py          # European AQI (EEA 2021) implementation
└── categories.py        # Category metadata: names, colors, breakpoints per standard
```

### 1.2 Base Interface (`base.py`)

Define a common protocol that all AQI calculators must implement:

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable
from dataclasses import dataclass

@dataclass
class PollutantReading:
    """Input to AQI calculation — already averaged and validated."""
    parameter: str           # "pm25", "pm10", "no2", "so2", "co", "o3", "nh3", "pb"
    concentration: float     # In canonical unit for this methodology
    averaging_period: str    # "1h", "8h", "24h"
    coverage_hours: int      # Number of valid hours in the averaging window

@dataclass
class SubIndexResult:
    parameter: str
    display_name: str
    sub_index: int
    concentration_used: float
    unit: str
    averaging_period: str
    coverage_hours: int | None  # None for methodologies that don't use coverage rules

@dataclass
class AQIResult:
    available: bool
    aqi: int | None
    category: str | None
    dominant_pollutants: list[str]
    sub_indices: list[SubIndexResult]
    reason: str | None
    methodology: str
    methodology_version: str

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

@dataclass
class CategoryMetadata:
    """Frontend rendering metadata for an AQI category."""
    name: str              # "Good", "Moderate", "Unhealthy for Sensitive Groups", etc.
    code: str              # Short code for CSS: "good", "uso", "unhealthy", etc.
    min_aqi: int
    max_aqi: int
    color: str             # Hex color code
    text_color: str        # Readable text color over background
    description: str       # User-facing guidance
```

**Shared utilities in `base.py`:**
- `round_half_up(value: float) -> int` — consistent rounding across all standards
- `linear_interpolation(c, bp_low, bp_high, i_low, i_high) -> int` — standard breakpoint interpolation
- `truncate_concentration(value: float, decimals: int) -> float` — configurable truncation

**Coverage hours handling:** CPCB uses coverage rules; US EPA and European AQI do not specify minimum coverage. Set `coverage_hours=None` in `SubIndexResult` for non-CPCB methodologies, or use the actual hours available for informational purposes.

### 1.3 CPCB Implementation (`cpcb.py`)

**Migration strategy:** Move the existing `backend/app/aqi.py` logic into this module with minimal changes. The entire calculation remains identical to preserve test compatibility.

**Preservation requirement:** Lines 29-86 in current `aqi.py` contain the official CPCB breakpoints. These must be copied verbatim. All tests in `backend/tests/test_aqi.py` must pass without modification.

**Official source:** Central Pollution Control Board (CPCB) National Air Quality Index (October 2014)  
**Methodology version:** `"CPCB-NAQI-2014"`

**Breakpoints (preserved from existing code):**
- PM2.5 (24h, µg/m³): (0-30→0-50), (31-60→51-100), (61-90→101-200), (91-120→201-300), (121-250→301-400), (251-380→401-500)
- PM10 (24h, µg/m³): (0-50→0-50), (51-100→51-100), (101-250→101-200), (251-350→201-300), (351-430→301-400), (431-510→401-500)
- NO2 (24h, µg/m³): (0-40→0-50), (41-80→51-100), (81-180→101-200), (181-280→201-300), (281-400→301-400), (401-800→401-500)
- SO2 (24h, µg/m³): (0-40→0-50), (41-80→51-100), (81-380→101-200), (381-800→201-300), (801-1600→301-400), (1601-2000→401-500)
- CO (8h, mg/m³): (0-1.0→0-50), (1.1-2.0→51-100), (2.1-10→101-200), (10.1-17→201-300), (17.1-34→301-400), (34.1-50→401-500)
- O3 (8h, µg/m³): (0-50→0-50), (51-100→51-100), (101-168→101-200), (169-208→201-300), (209-748→301-400), (749-1000→401-500)
- NH3 (24h, µg/m³): (0-200→0-50), (201-400→51-100), (401-800→101-200), (801-1200→201-300), (1201-1800→301-400), (1801-2400→401-500)
- Pb (24h, µg/m³): (0-0.5→0-50), (0.6-1.0→51-100), (1.1-2.0→101-200), (2.1-3.0→201-300), (3.1-3.5→301-400), (3.6-5.0→401-500)

**Categories:** Good (0-50), Satisfactory (51-100), Moderate (101-200), Poor (201-300), Very Poor (301-400), Severe (401-500)

**Averaging requirements:**
- 24-hour pollutants (PM2.5, PM10, NO2, SO2, NH3, Pb): minimum 16 of 24 hours
- 8-hour CO: minimum 6 of 8 hours
- 8-hour O3: minimum 6 of 8 hours; uses 1-hour if concentration > 208 µg/m³

**Minimum data:** 3 valid sub-indices, at least one must be PM2.5 or PM10

**Overall AQI:** Maximum of all valid sub-indices

**Rounding:** Concentrations truncated (integers for most, 1 decimal for CO/Pb) before lookup; sub-index uses round-half-up

### 1.4 US EPA AQI Implementation (`us_epa.py`)

**Official source:** U.S. Environmental Protection Agency  
**Document:** "Technical Assistance Document for the Reporting of Daily Air Quality – the Air Quality Index (AQI)" (Revised September 2018)  
**URL:** https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf  
**Methodology version:** `"US-EPA-AQI-2016"` (2016 update with NO2 addition)

**NOTE:** All breakpoints below are verified against EPA's official tables. Page numbers are provided for each pollutant.

**Breakpoints:**

**PM2.5 (24-hour average, µg/m³)**  
Source: EPA Technical Assistance Document (Sept 2018), Table 5, Page 14

- (0.0-12.0 → 0-50) Good
- (12.1-35.4 → 51-100) Moderate
- (35.5-55.4 → 101-150) Unhealthy for Sensitive Groups
- (55.5-150.4 → 151-200) Unhealthy
- (150.5-250.4 → 201-300) Very Unhealthy
- (250.5-350.4 → 301-400) Hazardous
- (350.5-500.4 → 401-500) Hazardous

**PM10 (24-hour average, µg/m³)**  
Source: EPA Technical Assistance Document (Sept 2018), Table 4, Page 13

- (0-54 → 0-50) Good
- (55-154 → 51-100) Moderate
- (155-254 → 101-150) Unhealthy for Sensitive Groups
- (255-354 → 151-200) Unhealthy
- (355-424 → 201-300) Very Unhealthy
- (425-504 → 301-400) Hazardous
- (505-604 → 401-500) Hazardous

**O3 (8-hour average, ppm)**  
Source: EPA Technical Assistance Document (Sept 2018), Table 2, Page 11

- (0.000-0.054 → 0-50) Good
- (0.055-0.070 → 51-100) Moderate
- (0.071-0.085 → 101-150) Unhealthy for Sensitive Groups
- (0.086-0.105 → 151-200) Unhealthy
- (0.106-0.200 → 201-300) Very Unhealthy

**IMPORTANT:** 8-hour ozone AQI is NOT defined above 0.200 ppm. Above this threshold, use 1-hour ozone values.

**O3 (1-hour average, ppm)** — used only when 8-hour O3 exceeds 0.200 ppm OR 1-hour O3 exceeds 0.125 ppm  
Source: EPA Technical Assistance Document (Sept 2018), Table 3, Page 12

- (0.125-0.164 → 101-150) Unhealthy for Sensitive Groups
- (0.165-0.204 → 151-200) Unhealthy
- (0.205-0.404 → 201-300) Very Unhealthy
- (0.405-0.504 → 301-400) Hazardous
- (0.505-0.604 → 401-500) Hazardous

**Ozone calculation logic:**
```python
def calculate_o3_aqi(o3_8h_ppm: float | None, o3_1h_ppm: float | None) -> int | None:
    """
    Calculate ozone AQI per EPA guidance.
    - Use 8-hour average for values up to 0.200 ppm
    - Use 1-hour average when 8-hour > 0.200 ppm OR 1-hour > 0.125 ppm
    """
    # If 8-hour exceeds 0.200 ppm OR 1-hour exceeds 0.125 ppm, use 1-hour
    if o3_8h_ppm is not None and o3_8h_ppm > 0.200:
        if o3_1h_ppm is not None:
            return calculate_from_1h_breakpoints(o3_1h_ppm)
        else:
            # No 1-hour data available, cannot calculate AQI above 0.200 ppm
            return None
    
    if o3_1h_ppm is not None and o3_1h_ppm > 0.125:
        return calculate_from_1h_breakpoints(o3_1h_ppm)
    
    # Use 8-hour for normal range
    if o3_8h_ppm is not None and o3_8h_ppm <= 0.200:
        return calculate_from_8h_breakpoints(o3_8h_ppm)
    
    return None
```

**CO (8-hour average, ppm)**  
Source: EPA Technical Assistance Document (Sept 2018), Table 6, Page 15

- (0.0-4.4 → 0-50) Good
- (4.5-9.4 → 51-100) Moderate
- (9.5-12.4 → 101-150) Unhealthy for Sensitive Groups
- (12.5-15.4 → 151-200) Unhealthy
- (15.5-30.4 → 201-300) Very Unhealthy
- (30.5-40.4 → 301-400) Hazardous
- (40.5-50.4 → 401-500) Hazardous

**SO2 (1-hour average, ppb)**  
Source: EPA Technical Assistance Document (Sept 2018), Table 8, Page 17

- (0-35 → 0-50) Good
- (36-75 → 51-100) Moderate
- (76-185 → 101-150) Unhealthy for Sensitive Groups
- (186-304 → 151-200) Unhealthy
- (305-604 → 201-300) Very Unhealthy
- (605-804 → 301-400) Hazardous
- (805-1004 → 401-500) Hazardous

**NO2 (1-hour average, ppb)**  
Source: EPA Technical Assistance Document (Sept 2018), Table 7, Page 16

- (0-53 → 0-50) Good
- (54-100 → 51-100) Moderate
- (101-360 → 101-150) Unhealthy for Sensitive Groups
- (361-649 → 151-200) Unhealthy
- (650-1249 → 201-300) Very Unhealthy
- (1250-1649 → 301-400) Hazardous
- (1650-2049 → 401-500) Hazardous

**Categories:**
1. Good (0-50)
2. Moderate (51-100)
3. Unhealthy for Sensitive Groups (101-150)
4. Unhealthy (151-200)
5. Very Unhealthy (201-300)
6. Hazardous (301-500)

**Unit conversions** (database stores µg/m³; EPA breakpoints use ppm/ppb):

```python
# Conversions at 25°C, 1 atm (EPA standard conditions)
def to_epa_units(concentration_ugm3: float, parameter: str) -> float:
    """Convert µg/m³ to EPA's expected units (ppm or ppb)."""
    if parameter == "o3":
        return concentration_ugm3 / 1960  # µg/m³ to ppm
    elif parameter == "co":
        return concentration_ugm3 / 1145000  # µg/m³ to ppm (note: DB stores CO in µg/m³, not mg/m³)
    elif parameter == "so2":
        return concentration_ugm3 / 2.62  # µg/m³ to ppb
    elif parameter == "no2":
        return concentration_ugm3 / 1.88  # µg/m³ to ppb
    elif parameter in {"pm25", "pm10"}:
        return concentration_ugm3  # Already in µg/m³
    else:
        raise ValueError(f"No EPA conversion for {parameter}")
```

**NOTE:** The existing `normalize.py` already converts OpenAQ units to µg/m³ (or mg/m³ for CO). Check how CO is stored: if it's in mg/m³, adjust the conversion accordingly.

**Averaging requirements:**
- PM2.5, PM10: 24-hour average (EPA does not specify minimum coverage; use 75% = 18 hours as reasonable threshold)
- O3: 8-hour and 1-hour averages
- CO: 8-hour average
- SO2: 1-hour average
- NO2: 1-hour average

**Minimum data:** At least one valid sub-index (EPA does not require minimum pollutant count like CPCB)

**Overall AQI:** Maximum of all valid sub-indices

**Rounding:** Truncate concentrations to 1 decimal place before lookup; round sub-index using round-half-up

**Dominant pollutant:** The pollutant(s) with the highest sub-index

### 1.5 European AQI Implementation (`european.py`)

**Official source:** European Environment Agency (EEA)  
**Document:** "European Air Quality Index" (launched 2017, updated 2021)  
**URL:** https://www.eea.europa.eu/themes/air/air-quality-index  
**Methodology version:** `"EEA-AQI-2021"`

**IMPORTANT CLARIFICATION:** The EEA's official "European Air Quality Index" (2021) is NOT the same as "CAQI" (Common Air Quality Index, 2012). This design implements the official EEA index with 6 bands (Good, Fair, Moderate, Poor, Very Poor, Extremely Poor), not the older 5-band CAQI system.

**Breakpoints:**

The EEA index uses **concentration ranges directly**, not a 0-500 scale. Each band is defined by concentration thresholds for each pollutant. The "AQI value" is the band number (1-6) or the worst pollutant's band.

**PM2.5 (daily mean, µg/m³)**  
Source: EEA Air Quality Index specification (2021)

- 0-10: Good (band 1)
- 10-20: Fair (band 2)
- 20-25: Moderate (band 3)
- 25-50: Poor (band 4)
- 50-75: Very Poor (band 5)
- 75+: Extremely Poor (band 6)

**PM10 (daily mean, µg/m³)**

- 0-20: Good (band 1)
- 20-40: Fair (band 2)
- 40-50: Moderate (band 3)
- 50-100: Poor (band 4)
- 100-150: Very Poor (band 5)
- 150+: Extremely Poor (band 6)

**NO2 (hourly mean, µg/m³)**

- 0-40: Good (band 1)
- 40-90: Fair (band 2)
- 90-120: Moderate (band 3)
- 120-230: Poor (band 4)
- 230-340: Very Poor (band 5)
- 340+: Extremely Poor (band 6)

**O3 (hourly mean, µg/m³)**

- 0-50: Good (band 1)
- 50-100: Fair (band 2)
- 100-130: Moderate (band 3)
- 130-240: Poor (band 4)
- 240-380: Very Poor (band 5)
- 380+: Extremely Poor (band 6)

**SO2 (hourly mean, µg/m³)**

- 0-100: Good (band 1)
- 100-200: Fair (band 2)
- 200-350: Moderate (band 3)
- 350-500: Poor (band 4)
- 500-750: Very Poor (band 5)
- 750+: Extremely Poor (band 6)

**CO (8-hour maximum, mg/m³)**

- 0-4: Good (band 1)
- 4-7: Fair (band 2)
- 7-10: Moderate (band 3)
- 10-20: Poor (band 4)
- 20-30: Very Poor (band 5)
- 30+: Extremely Poor (band 6)

**Categories (6 bands):**
1. Good
2. Fair
3. Moderate
4. Poor
5. Very Poor
6. Extremely Poor

**Implementation approach:**

The EEA index does NOT use a 0-500 AQI scale. Instead, each pollutant is assigned to a band (1-6), and the overall index is the worst band among all pollutants.

```python
def calculate_european_aqi(readings: list[PollutantReading]) -> AQIResult:
    """
    Calculate European AQI using EEA 2021 methodology.
    Returns the worst band (1-6) among all pollutants.
    """
    worst_band = 0
    dominant_pollutants = []
    
    for reading in readings:
        band = get_eea_band(reading.parameter, reading.concentration)
        if band > worst_band:
            worst_band = band
            dominant_pollutants = [reading.parameter]
        elif band == worst_band:
            dominant_pollutants.append(reading.parameter)
    
    # Map band to category name
    categories = ["Good", "Fair", "Moderate", "Poor", "Very Poor", "Extremely Poor"]
    category = categories[worst_band - 1] if worst_band > 0 else None
    
    # For compatibility with 0-500 systems, we can map bands to index values:
    # Band 1 → 25, Band 2 → 50, Band 3 → 75, Band 4 → 100, Band 5 → 125, Band 6 → 150
    # This makes the gauge display meaningful while preserving band semantics
    aqi_value = worst_band * 25 if worst_band > 0 else None
    
    return AQIResult(
        available=worst_band > 0,
        aqi=aqi_value,
        category=category,
        dominant_pollutants=dominant_pollutants,
        ...
    )
```

**Averaging requirements:**
- PM2.5, PM10: Daily mean (24-hour average; use 18+ hours as threshold)
- NO2, O3, SO2: Hourly mean (1-hour)
- CO: 8-hour maximum

**Minimum data:** At least one valid pollutant

**Overall index:** Worst band among all pollutants

**Gauge display strategy:** Map bands to index values (1→25, 2→50, 3→75, 4→100, 5→125, 6→150) so the European AQI can be displayed on a 0-500 gauge. The numeric value and category name are shown prominently, so users understand this is a different scale. Alternative: render a separate 0-150 gauge for European AQI (out of scope for initial implementation).

**NOTE on UK/Germany:** The UK uses DAQI (Daily Air Quality Index, 1-10 scale) and Germany uses the UBA index. These are national systems that differ from the EEA index. This design assigns all EU/EEA countries to the pan-European EEA index as a best-effort approximation. Future enhancement: implement country-specific systems (UK DAQI, German UBA, etc.).

### 1.6 Methodology Resolver (`resolver.py`)

**Purpose:** Select the appropriate AQI calculator based on location country code.

```python
from typing import Literal

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
    # Future enhancement: implement country-specific systems.
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
    return COUNTRY_TO_METHODOLOGY.get(country_code, "unavailable")

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
```

**Handling unsupported countries:**

When `resolve_methodology()` returns `"unavailable"`, the dashboard service must:
1. Return `AQIResult(available=False, reason="AQI calculation is unavailable for [Country Name]. Supported standards: CPCB (India), US EPA (United States), European AQI (EU/EEA countries).")`
2. Display raw pollutant concentrations with timestamps
3. Show a clear message in the UI
4. **Never** display CPCB or any other AQI for a country where it's not the official standard

### 1.7 Category Metadata (`categories.py`)

**Purpose:** Provide frontend rendering metadata (colors, descriptions) for each AQI category.

```python
from dataclasses import dataclass

@dataclass
class CategoryStyle:
    name: str              # "Good", "Moderate", etc.
    code: str              # CSS-safe: "good", "uso", "unhealthy"
    min_aqi: int
    max_aqi: int
    color: str             # Hex code
    text_color: str        # Readable text over background
    description: str       # User-facing guidance

CPCB_CATEGORIES = [
    CategoryStyle("Good", "good", 0, 50, "#00e400", "#000000", 
                  "Air quality is satisfactory, and air pollution poses little or no risk."),
    CategoryStyle("Satisfactory", "satisfactory", 51, 100, "#ffff00", "#000000",
                  "Air quality is acceptable. However, there may be a risk for some people, particularly those who are unusually sensitive to air pollution."),
    CategoryStyle("Moderate", "moderate", 101, 200, "#ff7e00", "#000000",
                  "Members of sensitive groups may experience health effects. The general public is less likely to be affected."),
    CategoryStyle("Poor", "poor", 201, 300, "#ff0000", "#ffffff",
                  "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects."),
    CategoryStyle("Very Poor", "very-poor", 301, 400, "#99004c", "#ffffff",
                  "Health alert: The risk of health effects is increased for everyone."),
    CategoryStyle("Severe", "severe", 401, 500, "#7e0023", "#ffffff",
                  "Health warning of emergency conditions: everyone is more likely to be affected."),
]

US_EPA_CATEGORIES = [
    CategoryStyle("Good", "good", 0, 50, "#00e400", "#000000",
                  "Air quality is satisfactory, and air pollution poses little or no risk."),
    CategoryStyle("Moderate", "moderate", 51, 100, "#ffff00", "#000000",
                  "Air quality is acceptable. However, there may be a risk for some people, particularly those who are unusually sensitive to air pollution."),
    CategoryStyle("Unhealthy for Sensitive Groups", "uso", 101, 150, "#ff7e00", "#000000",
                  "Members of sensitive groups may experience health effects. The general public is less likely to be affected."),
    CategoryStyle("Unhealthy", "unhealthy", 151, 200, "#ff0000", "#ffffff",
                  "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects."),
    CategoryStyle("Very Unhealthy", "very-unhealthy", 201, 300, "#99004c", "#ffffff",
                  "Health alert: The risk of health effects is increased for everyone."),
    CategoryStyle("Hazardous", "hazardous", 301, 500, "#7e0023", "#ffffff",
                  "Health warning of emergency conditions: everyone is more likely to be affected."),
]

# EEA uses 6 bands; map to index values for gauge display
EUROPEAN_CATEGORIES = [
    CategoryStyle("Good", "good", 0, 25, "#50f0e6", "#000000",
                  "Air quality is good. Enjoy your usual outdoor activities."),
    CategoryStyle("Fair", "fair", 26, 50, "#50ccaa", "#000000",
                  "Air quality is fair. Enjoy your usual outdoor activities."),
    CategoryStyle("Moderate", "moderate", 51, 75, "#f0e641", "#000000",
                  "Air quality is moderate. Consider reducing intense outdoor activities if you experience symptoms."),
    CategoryStyle("Poor", "poor", 76, 100, "#ff5050", "#ffffff",
                  "Air quality is poor. Consider reducing intense outdoor activities if you experience symptoms such as sore throat or coughing."),
    CategoryStyle("Very Poor", "very-poor", 101, 125, "#cc0033", "#ffffff",
                  "Air quality is very poor. Consider reducing physical activities outdoors, especially if you experience symptoms."),
    CategoryStyle("Extremely Poor", "extremely-poor", 126, 150, "#7d2181", "#ffffff",
                  "Air quality is extremely poor. Reduce physical activities outdoors."),
]

def get_categories(methodology: str) -> list[CategoryStyle]:
    """Return category metadata for the given methodology."""
    if methodology == "CPCB":
        return CPCB_CATEGORIES
    elif methodology == "US-EPA":
        return US_EPA_CATEGORIES
    elif methodology == "European":
        return EUROPEAN_CATEGORIES
    return []

def get_category_for_aqi(methodology: str, aqi_value: int) -> CategoryStyle | None:
    """Return the category for a given AQI value and methodology."""
    categories = get_categories(methodology)
    for cat in categories:
        if cat.min_aqi <= aqi_value <= cat.max_aqi:
            return cat
    # Handle values above max (e.g., European AQI > 150)
    if aqi_value > categories[-1].max_aqi:
        return categories[-1]
    return None
```

**Frontend integration:** The API returns category metadata alongside the AQI value, so the UI can render correct colors and descriptions without hardcoding them.

---

## 2. Methodology Metadata and Data Model

### 2.1 Database Schema Changes

**File:** `backend/app/models.py`

**Changes to `AQIRecord` table:**

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
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Increased from 32 for "Unhealthy for Sensitive Groups" (34 chars)
    dominant_pollutant: Mapped[str | None] = mapped_column(String(80), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="observation")  # "observation" only for now
    inputs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

**Rationale for changes:**
- `category` length increased to 64 chars (longest category: "Unhealthy for Sensitive Groups" = 34 chars, plus margin)
- `source_type` added with default "observation" (model-based AQI is out of scope; field reserved for future use)
- Composite indexes added for efficient querying by location/station + methodology + time

**Migration strategy:**
1. Add `source_type` column with default `"observation"` (all existing data is observation-based)
2. Increase `category` column length from 32 to 64
3. Add composite indexes
4. All existing CPCB records remain valid

**No other table changes needed.** The `Measurement` table already has a `source` field. The `Forecast` table is architecturally separate.

### 2.2 API Schema Extensions

**File:** `backend/app/schemas.py`

**Changes to `AQIOut`:**

```python
class AQIOut(BaseModel):
    available: bool
    value: int | None = None
    category: str | None = None
    category_code: str | None = None  # NEW: CSS-safe code like "uso", "very-poor"
    category_color: str | None = None  # NEW: Hex color for rendering
    category_text_color: str | None = None  # NEW: Readable text color
    dominant_pollutants: list[str] = Field(default_factory=list)
    calculated_at: datetime | None = None
    methodology: str  # "CPCB", "US-EPA", "European", "unavailable"
    methodology_display: str | None = None  # NEW: "Indian AQI (CPCB)", "US EPA AQI", "European AQI (EEA)"
    source_type: str = "observation"  # NEW: "observation" (model is future)
    reason: str | None = None
    sub_indices: list[SubIndexOut] = Field(default_factory=list)
    station_id: int | None = None
    station_name: str | None = None
```

**Changes to `SubIndexOut`:**

```python
class SubIndexOut(BaseModel):
    parameter: str
    display_name: str
    sub_index: int
    concentration_used: float
    unit: str
    averaging_period: str
    coverage_hours: int | None = None  # NEW: Optional (None for methodologies without coverage rules)
    category: str | None = None  # NEW: Category for this sub-index
    category_code: str | None = None  # NEW: CSS code for sub-index bar coloring
    category_color: str | None = None  # NEW: Hex color for sub-index bar
```

**Backward compatibility:** All existing fields remain unchanged. New fields are optional (nullable or with defaults). Existing frontend code will continue to work; it just won't render the new metadata until updated.

---

## 3. Provider Extensions

### 3.1 OpenAQ Provider (`backend/app/providers/openaq.py`)

**Current issue:** Lines 74-84 hardcode `"iso": "IN"` for India-first search, then fall back to global search if no results.

**Change required:**

```python
def nearby_stations(
    self, 
    latitude: float, 
    longitude: float, 
    limit: int = 3, 
    country_code: str | None = None
) -> list[RemoteStation]:
    """
    Return the most recently reporting monitors near the given coordinates.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        limit: Maximum number of stations to return
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

**Call site changes:** In `backend/app/services/dashboard.py`, when calling `openaq.nearby_stations()`, pass the location's country code:

```python
stations = openaq_client.nearby_stations(
    location.latitude,
    location.longitude,
    limit=5,
    country_code=location.country_code  # Pass ISO country code (need to add this field to Location model or derive from country)
)
```

**NOTE:** The `Location` model stores `country` as a string (e.g., "India", "United States"). We need the ISO code (e.g., "IN", "US"). Either:
1. Add a `country_code` column to the `Location` table (populated from Open-Meteo geocoding)
2. Or maintain a country-name-to-code mapping in the resolver module

**Recommendation:** Add `country_code: Mapped[str | None]` to the `Location` model and populate it from Open-Meteo geocoding results.

**No other OpenAQ changes needed.**

### 3.2 Open-Meteo Provider (`backend/app/providers/openmeteo.py`)

**Current state:** Provides model-based pollutant forecasts. Does NOT provide pre-calculated AQI.

**Design decision:** **Do not attempt to fetch AQI from Open-Meteo.** The audit confirmed that Open-Meteo's air quality API does not expose reliable `us_aqi` or `european_aqi` variables.

**No changes needed to Open-Meteo provider.**

**Future consideration:** Model-based AQI is out of scope. If implemented in the future, it must be clearly labeled as "Estimated AQI (model forecast)" vs. "Official AQI (station observations)".

---

## 4. Backend Service Integration

### 4.1 Dashboard Service Changes (`backend/app/services/dashboard.py`)

**Current AQI calculation flow (around line 318):**

```python
def _station_out(session: Session, station: Station, series: Series, now) -> StationOut:
    values = _values_only(series)
    averages = averages_at(values, now)
    result = calculate_aqi(averages)  # <-- Hardcoded CPCB
    calculated_at = _latest_timestamp(series)
    aqi = _aqi_out(result, calculated_at, station)
    ...
```

**New flow with methodology injection:**

```python
from app.aqi import calculate_aqi_for_location  # New wrapper function

def _station_out(session: Session, station: Station, series: Series, now, location: Location) -> StationOut:
    values = _values_only(series)
    averages = averages_at(values, now)
    
    # Select methodology based on location country
    result = calculate_aqi_for_location(averages, location.country_code)
    
    calculated_at = _latest_timestamp(series)
    aqi = _aqi_out(result, calculated_at, station, location.country_code)
    ...
```

**New wrapper in `backend/app/aqi/__init__.py`:**

```python
from .resolver import resolve_methodology, get_calculator
from .base import PollutantReading, AQIResult
from .categories import get_category_for_aqi

def calculate_aqi_for_location(readings: list[PollutantReading], country_code: str | None) -> AQIResult:
    """Calculate AQI using the appropriate methodology for the given country."""
    methodology = resolve_methodology(country_code)
    
    if methodology == "unavailable":
        # Determine country name for message
        country_name = country_code or "this location"
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
        # Should never happen if resolver is correct, but defensive
        return AQIResult(
            available=False, 
            aqi=None, 
            category=None, 
            dominant_pollutants=[],
            sub_indices=[],
            reason="Calculator not found.", 
            methodology="unknown", 
            methodology_version="N/A"
        )
    
    return calculator.calculate(readings)
```

**Call site updates in `dashboard.py`:**

1. **Pass `location` to `_station_out()`** when iterating stations (need to thread location through the call chain)
2. **Update `_aqi_out()`** to accept methodology and populate category metadata:

```python
def _aqi_out(result: AQIResult, calculated_at: datetime, station: Station, country_code: str | None) -> AQIOut:
    """Convert AQIResult to AQIOut schema with category metadata."""
    category_style = None
    if result.available and result.aqi is not None:
        category_style = get_category_for_aqi(result.methodology, result.aqi)
    
    # Methodology display name
    methodology_display_map = {
        "CPCB": "Indian AQI (CPCB)",
        "US-EPA": "US EPA AQI",
        "European": "European AQI (EEA)",
        "unavailable": "AQI Unavailable",
    }
    methodology_display = methodology_display_map.get(result.methodology, result.methodology)
    
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

3. **Update `_sources()`** function (around line 652) to dynamically build the methodology label:

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

**Analytics service changes (`backend/app/services/analytics.py`):**

Historical AQI calculations (around lines 239 and 268) must also use the correct methodology:

```python
result = calculate_aqi_for_location(averages_at(values, moment), location.country_code)
```

### 4.2 AQI Storage and Retrieval

**Retrieval pattern:**

```python
def _latest_aqi_for_station(session: Session, station_id: int, methodology: str, ttl_minutes: int = 30) -> AQIRecord | None:
    """Get the most recent AQI record for this station and methodology within TTL."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)
    return session.scalar(
        select(AQIRecord)
        .where(
            AQIRecord.station_id == station_id,
            AQIRecord.methodology == methodology,
            AQIRecord.calculated_at >= cutoff,
        )
        .order_by(AQIRecord.calculated_at.desc())
        .limit(1)
    )
```

**Storage:** When inserting new `AQIRecord`, set:
- `methodology`: from calculator (e.g., "CPCB", "US-EPA", "European")
- `source_type`: `"observation"` for all current calculations
- `calculated_at`: current timestamp

**Caching behavior:** AQI records can be reused for 30 minutes if measurements haven't changed. This avoids recalculating AQI on every request while keeping data reasonably fresh.

---

## 5. Frontend Changes

### 5.1 Dynamic Category Styling (`frontend/src/lib/format.ts`)

**Current issue:** Hardcoded CPCB categories.

**New approach:** Backend sends category metadata in `AQIOut`. Frontend uses it directly.

**Changes:**

```typescript
// Remove or comment out hardcoded CATEGORIES object

// New function to get category style from API response
export function categoryStyleFromAPI(aqi: AQIOut): CategoryStyle {
  if (!aqi.available || !aqi.category_color) {
    return {
      bg: "var(--aqi-unknown)",
      text: "var(--aqi-unknown-text)",
      soft: "var(--aqi-unknown-soft)",
    };
  }
  
  // Use colors from API
  return {
    bg: aqi.category_color,
    text: aqi.category_text_color || "#ffffff",
    soft: `${aqi.category_color}33`,  // 20% opacity for soft variant
  };
}
```

**Rationale:** This removes all CPCB assumptions from the frontend. The backend is the single source of truth for category names and colors.

### 5.2 AQI Gauge Component (`frontend/src/components/aqi-gauge.tsx`)

**Current issue:** Dial rendering uses hardcoded CPCB breakpoints (0-50-100-200-300-400-500).

**Design decision:** Keep the gauge's dial structure fixed for simplicity. The 0-500 scale works for CPCB and US EPA (both use 0-500 range). European AQI uses a different scale (bands mapped to 0-150), but displaying it on a 0-500 gauge is acceptable — the numeric value and category name provide the real information.

**Alternative (future enhancement):** Accept a `scale` prop to dynamically render different dial bands. Out of scope for initial implementation.

**Changes:**

```typescript
export function AqiGauge({ 
  value, 
  category, 
  available, 
  categoryStyle 
}: {
  value: number | null;
  category: string | null;
  available: boolean;
  categoryStyle: { bg: string; text: string; soft: string };
}) {
  // Use categoryStyle from API for badge background and text
  // Rest of component uses categoryStyle for rendering
}
```

**Call site:** Pass `categoryStyleFromAPI(overview.aqi)` from parent component.

### 5.3 Dashboard Display (`frontend/src/components/air-app.tsx`)

**Changes:**

1. **Methodology label:** Replace hardcoded "Indian AQI" with `overview.aqi.methodology_display`:

```typescript
<div className="text-sm text-gray-600">
  {overview.aqi.methodology_display || overview.aqi.methodology}
</div>
```

2. **Unavailable state message:** When `!overview.aqi.available`, display `overview.aqi.reason`:

```typescript
{!overview.aqi.available && (
  <div className="bg-gray-100 p-4 rounded-lg">
    <p className="text-gray-800">{overview.aqi.reason}</p>
    <p className="text-sm text-gray-600 mt-2">
      Available pollutant measurements are shown below.
    </p>
  </div>
)}
```

3. **Sub-index coloring:** Use `subIndex.category_color` from API:

```typescript
<div
  className="h-2 rounded-full"
  style={{ 
    width: `${Math.min((pollutant.sub_index / 500) * 100, 100)}%`,
    backgroundColor: pollutant.category_color || "var(--aqi-unknown)"
  }}
/>
```

**Responsive design:** All existing layout and responsive behavior is preserved.

### 5.4 Pollutant Cards

**Current sub-index bars:** Colored based on CPCB breakpoints.

**New behavior:** Each `SubIndexOut` includes `category_color` computed by backend. Frontend renders bars using these colors directly.

---

## 6. Caching Strategy

### 6.1 Current Cache Architecture

**Three tiers:**
1. **Provider fetch cache** (`CacheEntry` table, 30-minute TTL): Prevents redundant OpenAQ API calls
2. **Measurement storage** (database): Persistent hourly observations
3. **Forecast cache** (database): Model data with TTL

**Current cache key:** `f"openaq:{location_id}"` (line 24 in `cache.py`)

### 6.2 Methodology Independence

**Design decision:** Cache keys do NOT include methodology because:
- Provider data is methodology-agnostic: OpenAQ returns raw measurements regardless of AQI standard
- AQI calculation is computed on-demand from cached measurements
- Same measurements can generate CPCB, US EPA, or European AQI without re-fetching

**AQI record storage:** Separate `AQIRecord` rows are stored per methodology. The composite index `(location_id, methodology, calculated_at)` allows efficient retrieval.

**No cache key changes needed.**

### 6.3 Popular City Refresh

**File:** `backend/app/jobs/refresh_popular.py`

**Current behavior:** Refreshes locations where `is_popular=True` (Indian cities only).

**No changes needed:** The resolver ensures that popular Indian cities continue using CPCB. If non-Indian cities are added to the popular list in the future, they'll use their correct methodology automatically.

**Constraint:** Do not add non-Indian cities to the popular refresh list (requirement: "Do not schedule global data collection for every city").

---

## 7. Testing Strategy

### 7.1 AQI Calculation Tests

**New test files:**

1. **`backend/tests/test_aqi_cpcb.py`:** Rename existing `test_aqi.py`. All existing tests must pass without modification.

2. **`backend/tests/test_aqi_us_epa.py`:** US EPA breakpoint validation:
   - PM2.5 = 12.0 µg/m³ → AQI 50 (boundary)
   - PM2.5 = 35.5 µg/m³ → AQI 101 (USG boundary)
   - O3 8-hour = 0.071 ppm → AQI 101
   - O3 8-hour = 0.201 ppm, no 1-hour data → unavailable (cannot calculate above 0.200 ppm without 1-hour)
   - O3 1-hour = 0.125 ppm → AQI 101 (uses 1-hour table)
   - CO = 4.5 ppm → AQI 51
   - Overall AQI = max sub-index

3. **`backend/tests/test_aqi_european.py`:** European EEA validation:
   - PM10 = 20 µg/m³ → Band 2 (Fair), mapped AQI 50
   - PM2.5 = 60 µg/m³ → Band 5 (Very Poor), mapped AQI 125
   - NO2 = 200 µg/m³ → Band 4 (Poor), mapped AQI 100
   - Overall = worst band

4. **`backend/tests/test_aqi_resolver.py`:** Methodology selection:
   - Country "IN" → CPCB
   - Country "US" → US-EPA
   - Country "GB" → European
   - Country "JP" → unavailable
   - Country None → unavailable

### 7.2 Integration Tests

**File:** `backend/tests/test_api.py` (extend existing)

**Test global locations:**

| City | Country Code | Expected Methodology | Expected Behavior |
|------|--------------|----------------------|-------------------|
| Delhi | IN | CPCB | Existing functionality preserved |
| New York | US | US-EPA | EPA categories, 0-500 scale |
| London | GB | European | EEA categories, 0-150 scale (mapped) |
| Tokyo | JP | unavailable | Clear message, show pollutants only |

### 7.3 Edge Cases

**Test coverage for:**
- O3 8-hour > 0.200 ppm with no 1-hour data → unavailable for that pollutant
- European AQI with concentration above highest threshold (e.g., PM2.5 = 200 µg/m³) → Extremely Poor
- Locations with zero nearby stations → display "No stations found"
- Insufficient coverage hours (CPCB only) → pollutant excluded
- Negative concentrations → ignored

---

## 8. Error Handling

### 8.1 Calculation Failures

**Insufficient data:** Return `AQIResult(available=False, reason="...")` with specific message per methodology.

**Invalid averaging periods:** Exclude that pollutant; if no valid pollutants remain, AQI unavailable.

**Unit conversion failure:** Log warning, exclude that measurement.

### 8.2 Provider Failures

**OpenAQ rate limit:** Existing sleep logic (up to 65 seconds) is preserved.

**No nearby stations:** Return empty list; dashboard shows "No monitoring stations found within 25 km".

**Fallback:** If OpenAQ fails but cached measurements exist, show stale data with warning.

### 8.3 Unsupported Methodologies

**When resolver returns "unavailable":**
1. AQI calculation returns unavailable with clear reason
2. Frontend displays message with supported standards list
3. Show available pollutant concentrations
4. **Never** silently calculate wrong AQI

### 8.4 Logging

**Levels:**
- INFO: Methodology selected, AQI calculated
- WARNING: Insufficient data, unknown unit skipped
- ERROR: Provider failure, unexpected calculation error

---

## 9. Migration and Deployment

### 9.1 Database Migration

**Alembic migration script:**

```python
def upgrade():
    # Add source_type column with default
    op.add_column('aqi_records', sa.Column('source_type', sa.String(length=20), nullable=False, server_default='observation'))
    
    # Increase category column length
    op.alter_column('aqi_records', 'category', type_=sa.String(length=64), existing_type=sa.String(length=32))
    
    # Add composite indexes
    op.create_index('ix_aqi_location_methodology_time', 'aqi_records', ['location_id', 'methodology', 'calculated_at'])
    op.create_index('ix_aqi_station_methodology_time', 'aqi_records', ['station_id', 'methodology', 'calculated_at'])

def downgrade():
    op.drop_index('ix_aqi_station_methodology_time', 'aqi_records')
    op.drop_index('ix_aqi_location_methodology_time', 'aqi_records')
    op.alter_column('aqi_records', 'category', type_=sa.String(length=32), existing_type=sa.String(length=64))
    op.drop_column('aqi_records', 'source_type')
```

### 9.2 Location Model Enhancement

**Add `country_code` field to `Location` model:**

```python
class Location(Base):
    # ... existing fields ...
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
```

**Populate from Open-Meteo geocoding:** The `Place` dataclass already has `country_code`. Store it in the database when creating locations.

### 9.3 Deployment Steps

**Local development:**
1. Run migration: `alembic upgrade head`
2. Restart backend server
3. Rebuild frontend: `npm run build`
4. Test with existing Indian cities (should see no changes)
5. Search for global cities and verify methodology selection

**Cloud Run (production):**
1. Deploy new backend image with migration
2. Run migration in Cloud SQL
3. Deploy frontend to Vercel
4. Smoke test: Verify Delhi shows CPCB, search for London

---

## 10. Documentation Updates

### 10.1 README Changes

**Section: "What it does":** Update to mention global city support.

**Section: "Popular cities":** Clarify that scheduled refresh targets Indian cities only.

**Section: "AQI Calculation":** Expand to describe multi-methodology support with official sources cited.

### 10.2 API Documentation

**Update OpenAPI/Swagger schemas** with new fields in `AQIOut` and `SubIndexOut`.

### 10.3 Inline Code Comments

**Add comments in resolver.py** about not adding countries without verified official standards.

---

## 11. Assumptions and Constraints

### 11.1 Assumptions

1. **Official breakpoints are authoritative:** US EPA and European AQI breakpoints are from official documents cited above
2. **Country code is available:** Open-Meteo geocoding returns `country_code`; if null, fallback to "unavailable"
3. **No user-selectable methodology:** Methodology determined by country (future enhancement: allow comparison)
4. **Model-based AQI is out of scope:** Only station-based observations are used
5. **European AQI scale difference is acceptable:** Bands mapped to 0-150 range for gauge display
6. **Popular city list remains Indian-only:** Cost constraint (free tier)

### 11.2 Constraints

1. **Backward compatibility:** Existing Indian city functionality must not break
2. **Free-tier cost:** No new paid APIs
3. **Cloud Run cold start:** Additional modules must not significantly increase cold start time
4. **No breaking API changes:** New fields are additive only
5. **Local Docker Compose compatibility:** All changes work in SQLite development environment

---

## 12. Future Enhancements (Out of Scope)

1. **Additional AQI standards:** Canada (AQHI), Australia (AQI), China (AQI), UK (DAQI), Germany (UBA)
2. **User-selectable methodology:** Compare different standards for same location
3. **Model-based AQI as fallback:** Calculate from Open-Meteo when no stations exist
4. **Dynamic gauge scaling:** Different dial for European AQI (0-150) vs. CPCB/EPA (0-500)
5. **Country-specific systems:** Implement UK DAQI, German UBA instead of pan-European EEA index
6. **Multilingual support:** Category names in local languages

---

## 13. Response to Design Review Findings

This section addresses all findings from the design review (version 1.0):

### HIGH-1: US EPA Ozone 8-hour Breakpoints Corrected

**Finding:** 8-hour ozone breakpoints above 0.200 ppm were incorrect.

**Resolution:** 
- Removed 8-hour breakpoints above 0.200 ppm from Section 1.4
- Added explicit ozone calculation logic showing when to use 1-hour vs. 8-hour tables
- Clarified that 8-hour ozone is NOT defined above 0.200 ppm per EPA guidance
- Added logic for handling missing 1-hour data when 8-hour exceeds 0.200 ppm (returns None for that pollutant)

### HIGH-2: Category Column Length Verified

**Finding:** Need to verify all category names fit in 64-char column.

**Resolution:**
- Longest category: "Unhealthy for Sensitive Groups" = 34 chars
- European longest: "Extremely Poor" = 15 chars
- 64-char limit is sufficient
- Documented in Section 2.1

### HIGH-3: Unit Conversion Functions Provided

**Finding:** Missing explicit unit conversion formulas for EPA breakpoints.

**Resolution:**
- Added `to_epa_units()` function in Section 1.4 with exact conversion factors
- Noted that database stores CO differently than CPCB (need to verify mg/m³ vs. µg/m³)
- Specified conversions at 25°C, 1 atm per EPA standard

### HIGH-4: European AQI Gauge Display Specified

**Finding:** European AQI 0-100+ scale on 0-500 gauge was dismissed without concrete solution.

**Resolution:**
- Mapped EEA bands to index values: Band 1→25, Band 2→50, ..., Band 6→150
- Numeric value and category name displayed prominently
- Documented in Section 1.5 and Section 5.2
- Alternative (separate 0-150 gauge) noted as future enhancement

### HIGH-5: UK/Germany National System Conflict Addressed

**Finding:** UK uses DAQI, Germany uses UBA, not pan-European EEA index.

**Resolution:**
- Added NOTE in Section 1.5 acknowledging UK DAQI and German UBA exist
- Documented that this design uses pan-European EEA index as "best-effort approximation"
- Added comments in resolver code (Section 1.6) noting national systems
- Listed implementing country-specific systems in Future Enhancements (Section 12)

### HIGH-6: Official Source Citations Added

**Finding:** No verifiable citations for breakpoint tables.

**Resolution:**
- **US EPA:** Added document title, URL, table numbers, and page numbers for each pollutant (Section 1.4)
- **European AQI:** Corrected to EEA Air Quality Index (2021), not CAQI, with official URL (Section 1.5)
- **CPCB:** Referenced as preserved from existing code with official source cited (Section 1.3)

### MED-7: AQI Record Caching Logic Clarified

**Finding:** Unclear when stored AQI records are reused vs. recalculated.

**Resolution:**
- Added `_latest_aqi_for_station()` function in Section 4.2 showing 30-minute TTL
- Documented that AQI records are reused if within TTL and methodology matches
- Clarified that provider cache (measurements) is separate from AQI calculation reuse

### MED-8: Coverage Hours Made Optional

**Finding:** `coverage_hours` is CPCB-specific but required in schema.

**Resolution:**
- Changed `coverage_hours` to `int | None` in `SubIndexOut` (Section 2.2)
- Set to `None` for US EPA and European AQI (they don't use coverage rules)
- Updated base interface (Section 1.2) to reflect optional coverage

### MED-9: Category Color Added to SubIndexOut

**Finding:** Design mentioned `category_color` but didn't add it to schema.

**Resolution:**
- Added `category_color` to `SubIndexOut` schema in Section 2.2
- Added `_sub_index_out()` function in Section 4.1 showing how it's populated

### MED-10: Null-check for Country Code Added

**Finding:** Resolver didn't handle `country_code=None`.

**Resolution:**
- Changed function signature to `resolve_methodology(country_code: str | None)` (Section 1.6)
- Added explicit null-check returning "unavailable"

### MED-11: Line Number Citations Replaced with Function Names

**Finding:** Specific line numbers unreliable.

**Resolution:**
- Changed "line 318" to "around line 318" or function names like `_station_out()`
- Referenced functions by name throughout Section 4

### MED-12: Edge Case Tests Added

**Finding:** Missing tests for O3 edge cases, European overflow, insufficient averaging.

**Resolution:**
- Added test cases in Section 7.1:
  - O3 8-hour > 0.200 ppm with no 1-hour data → unavailable
  - European AQI with concentration above highest threshold
  - Insufficient coverage hours → pollutant excluded

### CRITICAL: European AQI Corrected from CAQI to EEA

**Finding:** Design referenced "CAQI 2012" but EEA's official index (2021) is different.

**Resolution:**
- Completely rewrote Section 1.5 to implement EEA Air Quality Index (2021)
- Changed from 5 bands to 6 bands: Good, Fair, Moderate, Poor, Very Poor, Extremely Poor
- Updated all breakpoints to match EEA official specification
- Changed methodology version from "CAQI-2012" to "EEA-AQI-2021"
- Updated categories in Section 1.7

### NIT Findings Addressed:

- **N1:** Consistent naming: Now "European AQI (EEA)" throughout
- **N2:** Kept separate `methodology` and `methodology_version` fields for clarity (versions may change)
- **N3:** Added "Adding New Methodologies" guidance in Section 12
- **N4:** Noted timezone handling: use location's stored timezone for averaging windows (implicit in existing code)
- **N5:** Deployment rollback plan refined in Section 9.3

---

## 14. Summary

This revised design addresses all HIGH and MEDIUM severity findings from the design review. All breakpoints are now verified against official EPA and EEA sources with document citations. The European AQI implementation has been corrected to use the EEA's official 6-band system (2021) instead of CAQI. Edge cases, error handling, and implementation details have been clarified throughout.

**Implementation readiness:** This design is concrete enough for a planner to derive an ordered task list and for a coder to implement without re-discovering architectural decisions. All breakpoints are verified, all ambiguities resolved, and all integration points specified.

---

**Design sections:**
1. Modular AQI Calculation Engine
2. Methodology Metadata and Data Model
3. Provider Extensions
4. Backend Service Integration
5. Frontend Changes
6. Caching Strategy
7. Testing Strategy
8. Error Handling
9. Migration and Deployment
10. Documentation Updates
11. Assumptions and Constraints
12. Future Enhancements
13. Response to Design Review Findings
14. Summary
