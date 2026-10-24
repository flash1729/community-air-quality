from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas import MeasurementPage, StationOut
from app.services.analytics import station_measurements
from app.services.dashboard import location_stations, station_detail

from app.routers.locations import get_db

router = APIRouter(tags=["stations"])


@router.get("/locations/{location_id}/stations", response_model=list[StationOut])
def stations_for_location(location_id: int, db: Session = Depends(get_db)):
    stations = location_stations(db, location_id)
    if stations is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    return stations


@router.get("/stations/{station_id}", response_model=StationOut)
def station(station_id: int, db: Session = Depends(get_db)):
    payload = station_detail(db, station_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Station not found.")
    return payload


@router.get("/stations/{station_id}/measurements", response_model=MeasurementPage)
def measurements(
    station_id: int,
    parameter: str | None = Query(None, max_length=16),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    page = station_measurements(db, station_id, parameter, limit, offset)
    if page is None:
        raise HTTPException(status_code=404, detail="Station not found.")
    return page
