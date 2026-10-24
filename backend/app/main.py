from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_session_factory
from app.routers import compare, health, locations, stations

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Community Air Quality API",
        version="0.1.0",
        summary="Local MVP for the Community Air Quality and Environmental Health Dashboard.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.session_factory = create_session_factory(settings.database_url)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(locations.router, prefix="/api/v1")
    app.include_router(stations.router, prefix="/api/v1")
    app.include_router(compare.router, prefix="/api/v1")

    @app.get("/")
    def root():
        return {"service": "community-air-api", "docs": "/docs"}

    return app


app = create_app()
