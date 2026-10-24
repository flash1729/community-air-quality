"""Parameter names and units brought onto the CPCB scale."""

from __future__ import annotations

# Molecular weight / molar volume (24.45 L at 25°C, 1 atm), expressed as µg/m³ per ppm.
_UG_PER_PPM = {
    "co": 1145.0,
    "no2": 1880.0,
    "so2": 2620.0,
    "o3": 1960.0,
    "nh3": 697.0,
}

_NAME_MAP = {
    "pm25": "pm25",
    "pm25ugm3": "pm25",
    "pm2_5": "pm25",
    "no2": "no2",
    "nitrogendioxide": "no2",
    "so2": "so2",
    "sulphurdioxide": "so2",
    "sulfurdioxide": "so2",
    "o3": "o3",
    "ozone": "o3",
    "co": "co",
    "carbonmonoxide": "co",
    "nh3": "nh3",
    "ammonia": "nh3",
    "pb": "pb",
    "lead": "pb",
    "pm10": "pm10",
}


def canonical_parameter(name: str | None) -> str | None:
    if not name:
        return None
    key = (
        name.strip()
        .lower()
        .replace("µ", "u")
        .replace("μ", "u")
        .replace(".", "")
        .replace("_", "")
        .replace(" ", "")
        .replace("/", "")
        .replace("³", "3")
    )
    if key in _NAME_MAP:
        return _NAME_MAP[key]
    if key.startswith("pm25"):
        return "pm25"
    if key.startswith("pm10"):
        return "pm10"
    return None


def _unit_key(unit: str | None) -> str:
    if not unit:
        return ""
    return (
        unit.strip()
        .lower()
        .replace("µ", "u")
        .replace("μ", "u")
        .replace(" ", "")
        .replace("³", "3")
    )


def to_canonical_unit(parameter: str, value: float, unit: str | None) -> float | None:
    """Convert a provider value into µg/m³, or mg/m³ for CO. None if unsafe to convert."""
    if value is None or value < 0:
        return None
    key = _unit_key(unit)
    if parameter == "co":
        if key in {"mg/m3", "mg/m³", "mgm3"}:
            return value
        if key in {"ug/m3", "ug/m³", "ugm3", "µg/m3", "μg/m3"}:
            return value / 1000.0
        if key in {"ppm", "ppb"}:
            ppm = value if key == "ppm" else value / 1000.0
            return (ppm * _UG_PER_PPM["co"]) / 1000.0
        if key in {"", "unknown"}:
            return None
        return None
    if key in {"ug/m3", "ug/m³", "ugm3", "µg/m³", "μg/m³"}:
        return value
    if key == "mg/m3":
        return value * 1000.0
    if key == "ppm":
        factor = _UG_PER_PPM.get(parameter)
        if factor is None:
            return None
        return value * factor
    if key == "ppb":
        factor = _UG_PER_PPM.get(parameter)
        if factor is None:
            return None
        return value * factor / 1000.0
    return None
