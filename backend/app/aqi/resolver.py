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
