from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/airquality.db"
    openaq_api_key: str = ""
    openaq_base_url: str = "https://api.openaq.org/v3"
    openmeteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    openmeteo_air_quality_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    cache_ttl_minutes: int = 30
    stale_after_minutes: int = 180
    cors_origins: str = "http://localhost:3000"
    scheduler_token: str = ""
    # Dev/demo only: hand each newly registered sensor's token to the local
    # simulator by writing it to the simulator's tokens file.
    simulator_auto_provision: bool = False
    simulator_tokens_file: str = "data/sensor_tokens.json"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
