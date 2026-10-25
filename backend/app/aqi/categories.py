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


def get_max_scale(methodology: str) -> int:
    """Return the maximum AQI scale value for the given methodology."""
    if methodology == "European":
        return 150  # European AQI caps at 150
    return 500  # CPCB and US EPA use 0-500 scale
