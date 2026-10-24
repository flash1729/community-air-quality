from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.models import CacheEntry, Forecast, IngestionRun, Location, Measurement
from app.schemas import IngestionRunOut, MetricsOut

from app.routers.locations import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "community-air-api"}


@router.get("/metrics", response_model=MetricsOut)
def metrics(db=Depends(get_db)):
    """Ingestion and cache counters. A cloud deployment can scrape this from the same API."""
    popular = db.scalar(select(func.count()).select_from(Location).where(Location.is_popular.is_(True))) or 0
    total = db.scalar(select(func.count()).select_from(Location)) or 0
    runs = db.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(8)).all()
    return MetricsOut(
        popular_locations=popular,
        on_demand_locations=total - popular,
        measurements=db.scalar(select(func.count()).select_from(Measurement)) or 0,
        forecasts=db.scalar(select(func.count()).select_from(Forecast)) or 0,
        cache_entries=db.scalar(select(func.count()).select_from(CacheEntry)) or 0,
        cache_hits=db.scalar(select(func.coalesce(func.sum(CacheEntry.hit_count), 0))) or 0,
        latest_ingestions=[
            IngestionRunOut(
                id=run.id,
                provider=run.provider,
                location_id=run.location_id,
                started_at=run.started_at,
                completed_at=run.completed_at,
                status=run.status,
            )
            for run in runs
        ],
        note=(
            "The API process is stateless. Stored measurements, forecasts, and cache_entries "
            "are the shared cache. The popular-city job is a separate process and does not "
            "refresh on-demand cities."
        ),
    )
