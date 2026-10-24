from __future__ import annotations

import httpx

from app.config import Settings
from app.providers.openaq import OpenAQClient
from app.providers.openmeteo import OpenMeteoClient


def open_clients(settings: Settings):
    """Provider clients for one request or one scheduled run. Callers close the HTTP client."""
    http = httpx.Client(timeout=30)
    openaq = None
    if settings.openaq_api_key:
        openaq = OpenAQClient(settings.openaq_api_key, settings.openaq_base_url, http)
    weather = OpenMeteoClient(
        settings.openmeteo_forecast_url,
        http,
        settings.openmeteo_air_quality_url,
    )
    return http, openaq, weather
