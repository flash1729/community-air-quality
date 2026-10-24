from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.clients import open_clients
from app.config import get_settings
from app.schemas import ForecastOut, HistoryOut, LocationSearchOut, OverviewOut, RefreshOut
from app.services.analytics import export_csv, ranged_history
from app.services.dashboard import (
    build_overview,
    discover_location,
    get_location,
    location_out,
    search_locations,
)
from app.services.forecasts import load_forecast
from app.services.ingest import refresh_location
from app.timeutils import utcnow

router = APIRouter(prefix="/locations", tags=["locations"])


def get_db(request: Request):
    session: Session = request.app.state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _clients(settings):
    return open_clients(settings)


@router.get("", response_model=LocationSearchOut)
def list_locations(
    q: str = Query("", max_length=80),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    locations = search_locations(db, q, limit)
    if not locations and q.strip():
        settings = get_settings()
        http, _openaq, weather = _clients(settings)
        try:
            locations = discover_location(db, q, weather)
        finally:
            http.close()
    return LocationSearchOut(results=[location_out(location) for location in locations])


@router.get("/{location_id}/overview", response_model=OverviewOut)
def overview(
    location_id: int,
    hours: int = Query(48, ge=1, le=168),
    db: Session = Depends(get_db),
):
    location = get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    settings = get_settings()
    http, openaq, weather = _clients(settings)
    try:
        payload, _failed = build_overview(
            db,
            location,
            settings,
            openaq=openaq,
            weather_client=weather,
            history_hours=hours,
            refresh_when_stale=True,
        )
    finally:
        http.close()
    return payload


@router.get("/{location_id}/aqi")
def location_aqi(location_id: int, db: Session = Depends(get_db)):
    location = get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    settings = get_settings()
    payload, _failed = build_overview(db, location, settings, openaq=None, weather_client=None)
    return payload.aqi


@router.get("/{location_id}/history", response_model=HistoryOut)
def history(
    location_id: int,
    hours: int | None = Query(None, ge=1, le=336),
    start: date | None = None,
    end: date | None = None,
    bucket: str = Query("hour", pattern="^(hour|day)$"),
    db: Session = Depends(get_db),
):
    location = get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    if (start is None) != (end is None):
        raise HTTPException(status_code=422, detail="Provide both start and end dates, or neither.")
    if start is not None and end is not None:
        if end < start:
            raise HTTPException(status_code=422, detail="end must be on or after start.")
        span = (end - start).days
        limit = 14 if bucket == "hour" else 90
        if span > limit:
            raise HTTPException(
                status_code=422,
                detail=f"That range is longer than {limit} days for {bucket} data.",
            )
        return ranged_history(db, location, start, end, bucket)
    settings = get_settings()
    payload, _failed = build_overview(
        db,
        location,
        settings,
        openaq=None,
        weather_client=None,
        history_hours=hours or 48,
    )
    return payload.history


@router.get("/{location_id}/forecast", response_model=ForecastOut)
def forecast(location_id: int, db: Session = Depends(get_db)):
    location = get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    settings = get_settings()
    http, _openaq, weather = _clients(settings)
    try:
        return load_forecast(db, location, weather, settings.cache_ttl_minutes)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The model forecast could not be loaded.") from exc
    finally:
        http.close()


@router.get("/{location_id}/export")
def export(
    location_id: int,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    location = get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    if (start is None) != (end is None):
        raise HTTPException(status_code=422, detail="Provide both start and end dates, or neither.")
    if start is not None and end is not None:
        if end < start:
            raise HTTPException(status_code=422, detail="end must be on or after start.")
        if (end - start).days > 31:
            raise HTTPException(status_code=422, detail="CSV export is limited to 31 days.")
        start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(end, time(23, 0), tzinfo=timezone.utc)
    else:
        end_dt = utcnow().replace(minute=0, second=0, microsecond=0)
        start_dt = end_dt - timedelta(hours=48)
    body = export_csv(db, location, start_dt, end_dt)
    filename = f"{location.city.lower().replace(' ', '-')}-measurements.csv"
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{location_id}/weather")
def weather(location_id: int, db: Session = Depends(get_db)):
    location = get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    settings = get_settings()
    payload, _failed = build_overview(db, location, settings, openaq=None, weather_client=None)
    if payload.weather is None:
        raise HTTPException(status_code=404, detail="No weather is stored for this location.")
    return payload.weather


@router.post("/{location_id}/refresh", response_model=RefreshOut)
def refresh(location_id: int, db: Session = Depends(get_db)):
    location = get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    settings = get_settings()
    http, openaq, weather = _clients(settings)
    try:
        if openaq is None:
            result = refresh_location(db, location, None, weather)
        else:
            result = refresh_location(db, location, openaq, weather)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        http.close()
    return RefreshOut(location_id=location.id, **result)
